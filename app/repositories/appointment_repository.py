# Standard library
import uuid
from datetime import date

# Third-party
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Internal
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.schemas.appointment import AppointmentFilter
from app.utils.pagination import paginate, PaginatedResult


class AppointmentRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, clinic_id: uuid.UUID, appointment_code: str, **kwargs) -> Appointment:
        appt = Appointment(clinic_id=clinic_id, appointment_code=appointment_code, **kwargs)
        self.db.add(appt)
        await self.db.flush()
        return appt

    async def get_by_id(self, appointment_id: uuid.UUID, clinic_id: uuid.UUID) -> Appointment | None:
        result = await self.db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_clinic(
        self,
        clinic_id: uuid.UUID,
        filters: AppointmentFilter,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        base_q = select(Appointment).where(Appointment.clinic_id == clinic_id)

        # Apply filters
        if filters.status:
            base_q = base_q.where(Appointment.status == filters.status)
        if filters.appt_date:
            base_q = base_q.where(Appointment.scheduled_date == filters.appt_date)
        if filters.date_from:
            base_q = base_q.where(Appointment.scheduled_date >= filters.date_from)
        if filters.date_to:
            base_q = base_q.where(Appointment.scheduled_date <= filters.date_to)
        if filters.patient_id:
            base_q = base_q.where(Appointment.patient_id == filters.patient_id)
        if filters.appointment_type:
            base_q = base_q.where(Appointment.appointment_type == filters.appointment_type)
        if filters.search:
            # Cast UUID to text for ILIKE search
            base_q = base_q.where(
                Appointment.appointment_code.ilike(f"%{filters.search}%")
            )

        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        offset, limit = paginate(page=page, per_page=per_page)
        rows = await self.db.execute(
            base_q.order_by(Appointment.scheduled_date.desc(), Appointment.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(rows.scalars().all())
        return PaginatedResult(items=items, total=total, page=page, per_page=limit)

    async def get_appointments_by_patient(
        self,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        base_q = select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.clinic_id == clinic_id,
        )
        count_q = select(func.count()).select_from(base_q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        offset, limit = paginate(page=page, per_page=per_page)
        rows = await self.db.execute(
            base_q.order_by(Appointment.scheduled_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return PaginatedResult(items=list(rows.scalars().all()), total=total, page=page, per_page=limit)

    async def get_queue(self, clinic_id: uuid.UUID, for_date: date) -> list[Appointment]:
        """Today's waiting list ordered by queue position."""
        result = await self.db.execute(
            select(Appointment)
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.status == "waiting",
                Appointment.scheduled_date == for_date,
            )
            .order_by(Appointment.queue_position)
        )
        return list(result.scalars().all())

    async def get_next_queue_position(self, clinic_id: uuid.UUID, for_date: date) -> int:
        """Returns the next available queue position for the given date."""
        result = await self.db.execute(
            select(func.max(Appointment.queue_position)).where(
                Appointment.clinic_id == clinic_id,
                Appointment.status == "waiting",
                Appointment.scheduled_date == for_date,
            )
        )
        max_pos = result.scalar_one_or_none()
        return (max_pos or 0) + 1

    async def update(self, appointment: Appointment, **kwargs) -> Appointment:
        for field, value in kwargs.items():
            setattr(appointment, field, value)
        await self.db.flush()
        return appointment
