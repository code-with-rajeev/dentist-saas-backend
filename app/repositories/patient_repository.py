# Standard library
import uuid
from datetime import date

# Third-party
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.utils.pagination import paginate, PaginatedResult


class PatientRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, clinic_id: uuid.UUID, patient_code: str, **kwargs) -> Patient:
        patient = Patient(clinic_id=clinic_id, patient_code=patient_code, **kwargs)
        self.db.add(patient)
        await self.db.flush()
        return patient

    async def get_by_id(self, patient_id: uuid.UUID, clinic_id: uuid.UUID) -> Patient | None:
        result = await self.db.execute(
            select(Patient).where(
                Patient.id == patient_id,
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_clinic(
        self,
        clinic_id: uuid.UUID,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        """
        Search supports: full_name (ILIKE), phone (exact prefix), patient_code (exact).
        """
        base_q = select(Patient).where(
            Patient.clinic_id == clinic_id,
            Patient.deleted_at.is_(None),
        )

        if search:
            term = search.strip()
            base_q = base_q.where(
                or_(
                    Patient.full_name.ilike(f"%{term}%"),
                    Patient.phone.ilike(f"{term}%"),
                    Patient.patient_code.ilike(f"{term}%"),
                )
            )

        # Total count
        count_q = select(func.count()).select_from(base_q.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar_one()

        # Paginated rows
        offset, limit = paginate(page=page, per_page=per_page)
        rows_result = await self.db.execute(
            base_q.order_by(Patient.full_name).offset(offset).limit(limit)
        )
        items = list(rows_result.scalars().all())

        return PaginatedResult(items=items, total=total, page=page, per_page=limit)

    async def update(
        self, patient_id: uuid.UUID, clinic_id: uuid.UUID, **kwargs
    ) -> Patient | None:
        patient = await self.get_by_id(patient_id, clinic_id)
        if patient is None:
            return None
        for field, value in kwargs.items():
            setattr(patient, field, value)
        await self.db.flush()
        return patient

    async def exists_by_phone(self, clinic_id: uuid.UUID, phone: str) -> bool:
        result = await self.db.execute(
            select(Patient.id).where(
                Patient.clinic_id == clinic_id,
                Patient.phone == phone,
                Patient.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def count_appointments(self, patient_id: uuid.UUID, clinic_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Appointment.id)).where(
                Appointment.patient_id == patient_id,
                Appointment.clinic_id == clinic_id,
            )
        )
        return result.scalar_one() or 0

    async def get_last_visit_date(
        self, patient_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> date | None:
        """Returns the most recent scheduled_date for completed appointments."""
        result = await self.db.execute(
            select(func.max(Appointment.scheduled_date)).where(
                Appointment.patient_id == patient_id,
                Appointment.clinic_id == clinic_id,
                Appointment.status == "completed",
            )
        )
        return result.scalar_one_or_none()
