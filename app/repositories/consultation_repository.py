# Standard library
import uuid
from datetime import datetime, timezone
from decimal import Decimal

# Third-party
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Internal — models
from app.models.consultation import Consultation
from app.models.medication import Medication

# Internal — utils
from app.utils.pagination import paginate, PaginatedResult


class ConsultationRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        clinic_id: uuid.UUID,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        dentist_id: uuid.UUID,
        **kwargs,
    ) -> Consultation:
        consultation = Consultation(
            clinic_id=clinic_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            dentist_id=dentist_id,
            **kwargs,
        )
        self.db.add(consultation)
        await self.db.flush()
        return consultation

    async def get_by_id(
        self, consultation_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> Consultation | None:
        result = await self.db.execute(
            select(Consultation)
            .options(selectinload(Consultation.medications))
            .where(
                Consultation.id == consultation_id,
                Consultation.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_appointment_id(self, appointment_id: uuid.UUID) -> Consultation | None:
        result = await self.db.execute(
            select(Consultation)
            .options(selectinload(Consultation.medications))
            .where(Consultation.appointment_id == appointment_id)
        )
        return result.scalar_one_or_none()

    async def get_all_by_patient(
        self,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        base_q = select(Consultation).where(
            Consultation.patient_id == patient_id,
            Consultation.clinic_id == clinic_id,
        )
        total = (await self.db.execute(
            select(func.count()).select_from(base_q.subquery())
        )).scalar_one()

        offset, limit = paginate(page=page, per_page=per_page)
        rows = await self.db.execute(
            base_q.order_by(Consultation.created_at.desc()).offset(offset).limit(limit)
        )
        return PaginatedResult(items=list(rows.scalars().all()), total=total, page=page, per_page=limit)

    async def replace_medications(
        self,
        consultation: Consultation,
        medications: list[dict],
    ) -> None:
        """Delete all existing medications for this consultation then bulk-insert new ones."""
        await self.db.execute(
            delete(Medication).where(Medication.consultation_id == consultation.id)
        )
        for i, med in enumerate(medications):
            m = Medication(
                consultation_id=consultation.id,
                clinic_id=consultation.clinic_id,
                med_library_id=med.get("med_library_id"),
                name=med["name"],
                dosage=med.get("dosage"),
                frequency=med.get("frequency"),
                duration=med.get("duration"),
                instructions=med.get("instructions"),
                sort_order=med.get("sort_order", i),
            )
            self.db.add(m)
        await self.db.flush()

    async def update(self, consultation: Consultation, **kwargs) -> Consultation:
        for field, value in kwargs.items():
            setattr(consultation, field, value)
        await self.db.flush()
        return consultation

    async def submit(self, consultation: Consultation) -> Consultation:
        consultation.is_submitted = True
        consultation.submitted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return consultation

    async def update_report_path(
        self, consultation: Consultation, path: str
    ) -> Consultation:
        consultation.report_generated = True
        consultation.report_path = path
        consultation.report_generated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return consultation

    async def reload_with_medications(self, consultation: Consultation) -> Consultation:
        """Reload consultation with a fresh medications list.

        We expire only the 'medications' attribute on the identity-map instance,
        then run a selectinload query so SQLAlchemy fetches fresh rows from the DB.
        """
        self.db.expire(consultation, ["medications"])
        result = await self.db.execute(
            select(Consultation)
            .options(selectinload(Consultation.medications))
            .where(Consultation.id == consultation.id)
        )
        return result.scalar_one()
