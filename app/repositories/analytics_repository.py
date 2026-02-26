# Standard library
import uuid
from datetime import date
from decimal import Decimal

# Third-party
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — models
from app.models.appointment import Appointment
from app.models.consultation import Consultation
from app.models.patient import Patient


class AnalyticsRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview_metrics(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> dict:
        """
        Aggregate all headline metrics in a single efficient query set.
        Returns a dict ready to build AnalyticsOverviewResponse.
        """
        # ---- Appointment aggregations ----
        appt_q = (
            select(
                func.count().label("total_appointments"),
                func.sum(case((Appointment.status == "completed", 1), else_=0)).label("completed"),
                func.sum(case((Appointment.status == "cancelled", 1), else_=0)).label("cancelled"),
                func.sum(case((Appointment.status == "no_show", 1), else_=0)).label("no_show"),
                func.sum(case((Appointment.appointment_type == "walk_in", 1), else_=0)).label("walk_ins"),
                func.sum(case((Appointment.appointment_type == "follow_up", 1), else_=0)).label("follow_ups"),
                func.count(
                    Appointment.patient_id.distinct()
                ).label("unique_patients"),
            )
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
        )
        appt_row = (await self.db.execute(appt_q)).mappings().one()

        # ---- Revenue from completed consultations in range ----
        rev_q = (
            select(
                func.coalesce(func.sum(Consultation.fee_charged), 0).label("total_revenue"),
                func.coalesce(func.avg(Consultation.fee_charged), 0).label("avg_fee"),
            )
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(
                Consultation.clinic_id == clinic_id,
                Consultation.is_submitted == True,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
        )
        rev_row = (await self.db.execute(rev_q)).mappings().one()

        # ---- New vs returning patients ----
        # "New" = first appointment in this clinic is within the period
        new_patients = await self._count_new_patients(clinic_id, date_from, date_to)
        unique = appt_row["unique_patients"] or 0
        returning = max(0, unique - new_patients)

        total = appt_row["total_appointments"] or 0
        completed = appt_row["completed"] or 0

        return {
            "total_appointments": total,
            "completed": completed,
            "cancelled": appt_row["cancelled"] or 0,
            "no_show": appt_row["no_show"] or 0,
            "walk_ins": appt_row["walk_ins"] or 0,
            "follow_ups": appt_row["follow_ups"] or 0,
            "completion_rate": round((completed / total * 100) if total else 0.0, 2),
            "total_revenue": Decimal(str(rev_row["total_revenue"])),
            "average_fee": Decimal(str(rev_row["avg_fee"])),
            "unique_patients": unique,
            "new_patients": new_patients,
            "returning_patients": returning,
        }

    async def get_appointment_stats(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> dict:
        """Breakdown by status, by type, and daily appointment counts."""
        # By status
        status_q = (
            select(Appointment.status, func.count().label("cnt"))
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
            .group_by(Appointment.status)
        )
        status_rows = (await self.db.execute(status_q)).all()
        by_status = {r.status: r.cnt for r in status_rows}

        # By type
        type_q = (
            select(Appointment.appointment_type, func.count().label("cnt"))
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
            .group_by(Appointment.appointment_type)
        )
        type_rows = (await self.db.execute(type_q)).all()
        by_type = {r.appointment_type: r.cnt for r in type_rows}

        # Daily breakdown
        daily_q = (
            select(
                Appointment.scheduled_date.label("day"),
                func.count().label("cnt"),
            )
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
            .group_by(Appointment.scheduled_date)
            .order_by(Appointment.scheduled_date)
        )
        daily_rows = (await self.db.execute(daily_q)).all()
        daily = [{"date_label": str(r.day), "count": r.cnt, "revenue": Decimal("0")} for r in daily_rows]

        total_q = select(func.count()).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        total = (await self.db.execute(total_q)).scalar_one()

        return {
            "total": total,
            "by_status": by_status,
            "by_type": by_type,
            "daily_breakdown": daily,
        }

    async def get_revenue_stats(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> dict:
        """Total revenue, average fee, and daily revenue breakdown from submitted consultations."""
        total_q = (
            select(
                func.coalesce(func.sum(Consultation.fee_charged), 0).label("total"),
                func.coalesce(func.avg(Consultation.fee_charged), 0).label("avg_fee"),
            )
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(
                Consultation.clinic_id == clinic_id,
                Consultation.is_submitted == True,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
        )
        row = (await self.db.execute(total_q)).mappings().one()

        daily_q = (
            select(
                Appointment.scheduled_date.label("day"),
                func.coalesce(func.sum(Consultation.fee_charged), 0).label("rev"),
            )
            .join(Appointment, Consultation.appointment_id == Appointment.id)
            .where(
                Consultation.clinic_id == clinic_id,
                Consultation.is_submitted == True,
                Appointment.scheduled_date >= date_from,
                Appointment.scheduled_date <= date_to,
            )
            .group_by(Appointment.scheduled_date)
            .order_by(Appointment.scheduled_date)
        )
        daily_rows = (await self.db.execute(daily_q)).all()
        daily = [
            {"date_label": str(r.day), "count": 0, "revenue": Decimal(str(r.rev))}
            for r in daily_rows
        ]

        return {
            "total_revenue": Decimal(str(row["total"])),
            "average_per_appointment": Decimal(str(row["avg_fee"])),
            "daily_breakdown": daily,
        }

    async def get_patient_stats(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> dict:
        """Unique, new vs returning patients."""
        unique_q = select(func.count(Appointment.patient_id.distinct())).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        unique = (await self.db.execute(unique_q)).scalar_one() or 0
        new = await self._count_new_patients(clinic_id, date_from, date_to)
        returning = max(0, unique - new)
        retention = round((returning / unique * 100) if unique else 0.0, 2)
        return {
            "unique_patients": unique,
            "new_patients": new,
            "returning_patients": returning,
            "retention_rate": retention,
        }

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    async def _count_new_patients(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> int:
        """
        "New" patient = patient whose FIRST appointment in this clinic falls within [date_from, date_to].
        Uses a subquery: first_appt per patient, then filter by range.
        """
        first_appt_sub = (
            select(
                Appointment.patient_id,
                func.min(Appointment.scheduled_date).label("first_date"),
            )
            .where(Appointment.clinic_id == clinic_id)
            .group_by(Appointment.patient_id)
            .subquery()
        )
        count_q = select(func.count()).where(
            first_appt_sub.c.first_date >= date_from,
            first_appt_sub.c.first_date <= date_to,
        )
        return (await self.db.execute(count_q)).scalar_one() or 0
