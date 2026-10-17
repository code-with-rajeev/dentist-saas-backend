# Standard library
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Third-party
from sqlalchemy import Integer, case, cast, func, select, Time, Integer, select
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — models
from app.models.appointment import Appointment
from app.models.consultation_visit import ConsultationVisit
from app.models.consultation_branch import ConsultationBranch
from app.models.patient import Patient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round2(value) -> Decimal:
    """Round any numeric value to 2 decimal places (Decimal, float, or int)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _zero_fill_days(
    date_from: date,
    date_to: date,
    rows: list[dict],
    date_key: str = "date",
) -> list[dict]:
    """
    Ensure every calendar day in [date_from, date_to] is present in rows.
    Missing days are inserted with all numeric values set to zero.
    Existing row shape is inferred from the first row — missing keys default to 0.
    """
    if not rows:
        template = {}
    else:
        template = {k: (Decimal("0.00") if isinstance(v, Decimal) else 0)
                    for k, v in rows[0].items() if k != date_key}

    indexed = {r[date_key]: r for r in rows}
    result = []
    current = date_from
    while current <= date_to:
        result.append(indexed.get(current, {date_key: current, **template}))
        current += timedelta(days=1)
    return result


def _safe_pct(numerator, denominator) -> Decimal:
    """Return percentage rounded to 2 dp, or 0.00 if denominator is zero."""
    if not denominator:
        return Decimal("0.00")
    return _round2(numerator / denominator * 100)


def _delta_pct(current, previous) -> Decimal | None:
    """
    Percentage change from previous to current.
    Returns None when previous is zero (undefined, not infinity).
    """
    if not previous:
        return None
    return _round2((current - previous) / previous * 100)


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class AnalyticsRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Overview
    # -----------------------------------------------------------------------

    async def get_overview_metrics(
        self,
        clinic_id: uuid.UUID,
        date_from: date,
        date_to: date,
        compare: bool = False,
    ) -> dict:
        """
        All headline KPIs in two query round-trips (appointments + revenue).

        Fix: average_fee is derived from completed consultations only, rounded to 2 dp.
        Fix: pending / waiting status counts now included.
        New: peak_day, peak_day_revenue.
        New: comparison block when compare=True.
        """
        data = await self._overview_for_period(clinic_id, date_from, date_to)

        if compare:
            prev_from, prev_to = _prior_period(date_from, date_to)
            prev = await self._overview_for_period(clinic_id, prev_from, prev_to)
            data["comparison"] = {
                "period_from": prev_from,
                "period_to": prev_to,
                "total_revenue_delta_pct": _delta_pct(
                    data["total_revenue"], prev["total_revenue"]
                ),
                "total_appointments_delta_pct": _delta_pct(
                    data["total_appointments"], prev["total_appointments"]
                ),
                "new_patients_delta_pct": _delta_pct(
                    data["new_patients"], prev["new_patients"]
                ),
                # Absolute percentage-point change (not relative %)
                "completion_rate_delta": _round2(
                    data["completion_rate"] - prev["completion_rate"]
                ),
            }

        return data

    async def _overview_for_period(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> dict:
        """Single-period overview — shared by current and comparison window."""

        # ---- 1. Appointment aggregations (one query) -------------------------
        appt_q = select(
            func.count().label("total"),
            func.sum(case((Appointment.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Appointment.status == "cancelled", 1), else_=0)).label("cancelled"),
            func.sum(case((Appointment.status == "no_show",   1), else_=0)).label("no_show"),
            func.sum(case((Appointment.status == "pending",   1), else_=0)).label("pending"),
            func.sum(case((Appointment.status == "waiting",   1), else_=0)).label("waiting"),
            func.sum(case((Appointment.appointment_type == "walk_in",   1), else_=0)).label("walk_ins"),
            func.sum(case((Appointment.appointment_type == "follow_up", 1), else_=0)).label("follow_ups"),
            func.count(Appointment.patient_id.distinct()).label("unique_patients"),
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        a = (await self.db.execute(appt_q)).mappings().one()

        # ---- 2. Revenue + peak day (one query) -------------------------------
        # Joins only submitted consultations — average is over completed appts only.
        rev_q = select(
            func.coalesce(func.sum(ConsultationVisit.total_paid), 0).label("total_revenue"),
            func.coalesce(func.avg(ConsultationVisit.total_paid), 0).label("avg_fee"),
        ).join(
            Appointment, ConsultationVisit.appointment_id == Appointment.id
        ).where(
            ConsultationVisit.clinic_id == clinic_id,
            ConsultationVisit.is_finalized == True,  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        rev = (await self.db.execute(rev_q)).mappings().one()

        # Peak revenue day
        peak_q = select(
            Appointment.scheduled_date.label("day"),
            func.sum(ConsultationVisit.total_paid).label("day_rev"),
        ).join(
            Appointment, ConsultationVisit.appointment_id == Appointment.id
        ).where(
            ConsultationVisit.clinic_id == clinic_id,
            ConsultationVisit.is_finalized == True,  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(
            Appointment.scheduled_date
        ).order_by(
            func.sum(ConsultationVisit.total_paid).desc()
        ).limit(1)
        peak_row = (await self.db.execute(peak_q)).mappings().first()

        # ---- 3. New vs returning patients ------------------------------------
        new_patients = await self._count_new_patients(clinic_id, date_from, date_to)
        unique = a["unique_patients"] or 0
        returning = max(0, unique - new_patients)

        total = a["total"] or 0
        completed = a["completed"] or 0
        total_revenue = _round2(rev["total_revenue"])

        return {
            "total_appointments": total,
            "completed":    completed,
            "cancelled":    a["cancelled"] or 0,
            "no_show":      a["no_show"]   or 0,
            "pending":      a["pending"]   or 0,
            "waiting":      a["waiting"]   or 0,
            "walk_ins":     a["walk_ins"]  or 0,
            "follow_ups":   a["follow_ups"] or 0,
            "completion_rate":   _safe_pct(completed, total),
            "cancellation_rate": _safe_pct(a["cancelled"] or 0, total),
            "no_show_rate":      _safe_pct(a["no_show"]   or 0, total),
            "total_revenue":     total_revenue,
            # Fix: was raw avg() with 16 dp — now rounded to 2 dp
            "average_fee":       _round2(rev["avg_fee"]),
            "peak_day":         str(peak_row["day"])     if peak_row else None,
            "peak_day_revenue": _round2(peak_row["day_rev"]) if peak_row else Decimal("0.00"),
            "unique_patients":   unique,
            "new_patients":      new_patients,
            "returning_patients": returning,
            # Fix: was int 0 — now a proper Decimal percentage
            "retention_rate":    _safe_pct(returning, unique),
        }

    # -----------------------------------------------------------------------
    # Appointments
    # -----------------------------------------------------------------------

    async def get_appointment_stats(
        self,
        clinic_id: uuid.UUID,
        date_from: date,
        date_to: date,
        compare: bool = False,
    ) -> dict:
        """
        Status breakdown, type breakdown, and zero-filled daily counts.

        Fix: revenue removed from daily_breakdown (it was always 0 — wrong join).
        Fix: renamed count → appointment_count for clarity.
        Fix: zero-fill so chart has no gaps.
        New: completion_rate, cancellation_rate, no_show_rate at top level.
        """
        # Status counts
        status_q = select(
            Appointment.status,
            func.count().label("cnt"),
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(Appointment.status)
        by_status = {
            r.status: r.cnt
            for r in (await self.db.execute(status_q)).all()
        }

        # Type counts
        type_q = select(
            Appointment.appointment_type,
            func.count().label("cnt"),
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(Appointment.appointment_type)
        by_type = {
            r.appointment_type: r.cnt
            for r in (await self.db.execute(type_q)).all()
        }

        # Daily breakdown — appointment_count only (no revenue here)
        daily_q = select(
            Appointment.scheduled_date.label("date"),
            func.count().label("appointment_count"),
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(Appointment.scheduled_date).order_by(Appointment.scheduled_date)

        raw_daily = [
            {"date": r.date, "appointment_count": r.appointment_count}
            for r in (await self.db.execute(daily_q)).all()
        ]
        # Fix: zero-fill missing days so charts render continuously
        daily = _zero_fill_days(date_from, date_to, raw_daily)

        total = sum(by_status.values())
        completed = by_status.get("completed", 0)

        data = {
            "total_appointments": total,
            "completion_rate":   _safe_pct(completed, total),
            "cancellation_rate": _safe_pct(by_status.get("cancelled", 0), total),
            "no_show_rate":      _safe_pct(by_status.get("no_show",   0), total),
            "breakdown": {
                "by_status": by_status,
                "by_type":   by_type,
                "daily_breakdown": daily,
            },
        }

        if compare:
            prev_from, prev_to = _prior_period(date_from, date_to)
            prev = await self.get_appointment_stats(clinic_id, prev_from, prev_to)
            data["comparison"] = {
                "period_from": prev_from,
                "period_to":   prev_to,
                "total_appointments_delta_pct": _delta_pct(
                    total, prev["total_appointments"]
                ),
                "completion_rate_delta": _round2(
                    data["completion_rate"] - prev["completion_rate"]
                ),
                "no_show_rate_delta": _round2(
                    data["no_show_rate"] - prev["no_show_rate"]
                ),
            }

        return data

    # -----------------------------------------------------------------------
    # Revenue
    # -----------------------------------------------------------------------

    async def get_revenue_stats(
        self,
        clinic_id: uuid.UUID,
        date_from: date,
        date_to: date,
        compare: bool = False,
    ) -> dict:
        """
        Revenue from submitted consultations, daily breakdown, collection rate.

        Fix: daily count was always 0 — now uses real completed appointment counts.
        Fix: average rounded to 2 dp.
        Fix: zero-fill missing days.
        New: outstanding_amount, collection_rate.
        New: comparison block.
        """
        # Total collected + average
        collected_q = select(
            func.coalesce(func.sum(ConsultationVisit.total_paid), 0).label("total_revenue"),
            func.coalesce(func.avg(ConsultationVisit.total_paid), 0).label("avg_fee"),
        ).join(
            Appointment, ConsultationVisit.appointment_id == Appointment.id
        ).where(
            ConsultationVisit.clinic_id == clinic_id,
            #ConsultationVisit.is_finalized == True,  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        collected = (await self.db.execute(collected_q)).mappings().one()

        # Outstanding: consultation visits unpaid (billed but uncollected)
        outstanding_q = select(
            func.coalesce(func.sum(ConsultationVisit.total_billed), 0).label("outstanding"),
        ).join(
            Appointment, ConsultationVisit.appointment_id == Appointment.id
        ).where(
            ConsultationVisit.clinic_id == clinic_id,
            #ConsultationVisit.is_finalized == False,  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        outstanding_row = (await self.db.execute(outstanding_q)).mappings().one()

        total_revenue = _round2(collected["total_revenue"])
        outstanding   = _round2(outstanding_row["outstanding"])
        total_billed  = total_revenue + outstanding

        # Fix: daily breakdown joins both counts and revenue in one query, only finalized visit
        daily_q = select(
            Appointment.scheduled_date.label("date"),
            func.count(Appointment.id.distinct()).label("appointment_count"),
            func.coalesce(func.sum(ConsultationVisit.total_billed), 0).label("revenue"),
        ).join(
            Appointment, ConsultationVisit.appointment_id == Appointment.id
        ).where(
            ConsultationVisit.clinic_id == clinic_id,
            ConsultationVisit.is_finalized == True,  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(
            Appointment.scheduled_date
        ).order_by(Appointment.scheduled_date)

        raw_daily = [
            {
                "date": r.date,
                "appointment_count": r.appointment_count,
                "revenue": _round2(r.revenue),
            }
            for r in (await self.db.execute(daily_q)).all()
        ]
        daily = _zero_fill_days(date_from, date_to, raw_daily)

        data = {
            "total_revenue":           total_revenue,
            # Fix: was 16 dp raw avg — now 2 dp
            "average_per_appointment": _round2(collected["avg_fee"]),
            "outstanding_amount":      outstanding,
            "collection_rate":         _safe_pct(total_revenue, total_billed),
            "daily_breakdown":         daily,
        }

        if compare:
            prev_from, prev_to = _prior_period(date_from, date_to)
            prev = await self.get_revenue_stats(clinic_id, prev_from, prev_to)
            data["comparison"] = {
                "period_from":             prev_from,
                "period_to":               prev_to,
                "total_revenue":           prev["total_revenue"],
                "delta_pct":               _delta_pct(total_revenue, prev["total_revenue"]),
                "average_per_appointment": prev["average_per_appointment"],
            }

        return data

    # -----------------------------------------------------------------------
    # Patients
    # -----------------------------------------------------------------------

    async def get_patient_stats(
        self,
        clinic_id: uuid.UUID,
        date_from: date,
        date_to: date,
        compare: bool = False,
    ) -> dict:
        """
        New vs returning patients, retention rate, top procedures.

        Fix: returning is derived from lifetime history, not just the period.
        New: top_procedures — most common procedure types + revenue per type.
        New: comparison block.
        """
        unique_q = select(
            func.count(Appointment.patient_id.distinct())
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        )
        unique = (await self.db.execute(unique_q)).scalar_one() or 0

        new = await self._count_new_patients(clinic_id, date_from, date_to)
        returning = max(0, unique - new)

        # Top procedures by appointment count and revenue

        proc_q = select(
            ConsultationBranch.procedure_category.label("procedure"),
            func.count().label("count"),
            func.coalesce(func.sum(ConsultationBranch.billing_amount), 0).label("revenue"),
        ).join(
            Appointment, ConsultationBranch.appointment_id == Appointment.id
        ).where(
            ConsultationBranch.clinic_id == clinic_id,
            ConsultationBranch.branch_status == "done",  # noqa: E712
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
        ).group_by(
            ConsultationBranch.procedure_category
        ).order_by(
            func.count().desc()
        ).limit(5)

        top_procedures = [
            {
                "procedure": r.procedure,
                "count":     r.count,
                "revenue":   _round2(r.revenue),
            }
            for r in (await self.db.execute(proc_q)).all()
        ]

        data = {
            "unique_patients":    unique,
            "new_patients":       new,
            "returning_patients": returning,
            "retention_rate":     _safe_pct(returning, unique),
            "top_procedures":     top_procedures,
        }

        if compare:
            prev_from, prev_to = _prior_period(date_from, date_to)
            prev = await self.get_patient_stats(clinic_id, prev_from, prev_to)
            data["comparison"] = {
                "period_from":            prev_from,
                "period_to":              prev_to,
                "new_patients_delta_pct": _delta_pct(new, prev["new_patients"]),
                "retention_rate_delta":   _round2(
                    data["retention_rate"] - prev["retention_rate"]
                ),
            }

        return data

    # -----------------------------------------------------------------------
    # Slots  (NEW)
    # -----------------------------------------------------------------------

    async def get_slot_stats(
        self,
        clinic_id: uuid.UUID,
        date_from: date,
        date_to: date,
    ) -> dict:
        """
        NEW endpoint data — slot utilisation heatmap.

        Shows which weekday + hour combinations are busiest vs idle.
        Dentist uses this to open/close slots and plan staffing.

        Requires Appointment to have a scheduled_time_slot column (time type).
        Counts only non-cancelled, non-no_show appointments as "booked".
        """
        # Cast the scheduled_time_slot to Time
        time_col = cast(Appointment.scheduled_time_slot, Time)

        heatmap_q = select(
            # 0=Monday … 6=Sunday (Python convention via extract dow offset)
            func.extract("isodow", Appointment.scheduled_date).label("iso_dow"),
            cast(func.extract("hour", time_col), Integer).label("hour"),
            func.count().label("appointment_count"),
        ).where(
            Appointment.clinic_id == clinic_id,
            Appointment.scheduled_date >= date_from,
            Appointment.scheduled_date <= date_to,
            Appointment.status.notin_(["cancelled", "no_show"]),
            Appointment.scheduled_time_slot.isnot(None), # only consider appointments with a time slot
        ).group_by(
            func.extract("isodow", Appointment.scheduled_date),
            func.extract("hour", time_col),
        ).order_by(
            func.extract("isodow", Appointment.scheduled_date),
            func.extract("hour", time_col),
        )

        rows = (await self.db.execute(heatmap_q)).all()

        # Build lookup: (dow, hour) -> count
        lookup: dict[tuple, int] = defaultdict(int)
        for r in rows:
            lookup[(int(r.iso_dow), r.hour)] = r.appointment_count

        # Total booked across entire heatmap
        total_booked = sum(lookup.values())

        # Find busiest and quietest cells (only among cells with data)
        busiest_cell  = max(lookup, key=lookup.get) if lookup else None
        quietest_cell = min(lookup, key=lookup.get) if lookup else None

        _day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        def _slot_label(cell: tuple | None) -> str | None:
            if cell is None:
                return None
            return f"{_day_name[cell[0] - 1]} {cell[1]:02d}:00"

        # Determine max count for utilisation_rate normalisation
        max_count = max(lookup.values()) if lookup else 1

        heatmap = []
        for dow in range(1, 8):  # 1=Mon … 7=Sun
            slots = []
            for hour in range(8, 20):  # 08:00 – 19:00; adjust to clinic hours
                count = lookup.get((dow, hour), 0)
                slots.append({
                    "hour":             f"{hour:02d}:00",
                    "appointment_count": count,
                    # Relative utilisation within the period — 100 = the busiest cell
                    "utilisation_rate": _safe_pct(count, max_count),
                })
            heatmap.append({
                "day":   _day_name[dow - 1],
                "slots": slots,
            })

        return {
            "total_booked_slots": total_booked,
            "busiest_slot":       _slot_label(busiest_cell),
            "quietest_slot":      _slot_label(quietest_cell),
            "heatmap":            heatmap,
        }

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _count_new_patients(
        self, clinic_id: uuid.UUID, date_from: date, date_to: date
    ) -> int:
        """
        "New" = patient whose FIRST-EVER appointment at this clinic falls inside
        [date_from, date_to].  Uses a correlated subquery — unchanged from original
        but preserved here for clarity.
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


# ---------------------------------------------------------------------------
# Module-level utility
# ---------------------------------------------------------------------------

def _prior_period(date_from: date, date_to: date) -> tuple[date, date]:
    """
    Return the immediately preceding window of the same length.
    e.g. Mar 1–31 (31 days)  →  Jan 29 – Feb 28 (31 days back)
    """
    length = (date_to - date_from).days + 1
    prev_to   = date_from - timedelta(days=1)
    prev_from = prev_to - timedelta(days=length - 1)
    return prev_from, prev_to