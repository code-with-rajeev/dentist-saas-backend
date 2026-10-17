# Standard library
import uuid
from datetime import datetime, timezone
from decimal import Decimal

# Third-party
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Internal — models
from app.models.consultation_visit import ConsultationVisit
from app.models.consultation_branch import ConsultationBranch
from app.models.pending_treatment import PendingTreatment
from app.models.medication import Medication

# Internal — utils
from app.utils.pagination import paginate, PaginatedResult


class ConsultationVisitRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Visit CRUD ────────────────────────────────────────────────────────────

    async def create(
        self,
        clinic_id: uuid.UUID,
        appointment_id: uuid.UUID,
        patient_id: uuid.UUID,
        dentist_id: uuid.UUID,
        **kwargs,
    ) -> ConsultationVisit:
        visit = ConsultationVisit(
            clinic_id=clinic_id,
            appointment_id=appointment_id,
            patient_id=patient_id,
            dentist_id=dentist_id,
            **kwargs,
        )
        self.db.add(visit)
        await self.db.flush()
        return visit

    async def get_by_id(
        self, visit_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ConsultationVisit | None:
        result = await self.db.execute(
            select(ConsultationVisit)
            .options(
                selectinload(ConsultationVisit.branches).selectinload(ConsultationBranch.medications)
            )
            .where(
                ConsultationVisit.id == visit_id,
                ConsultationVisit.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_appointment_id(
        self, appointment_id: uuid.UUID
    ) -> ConsultationVisit | None:
        result = await self.db.execute(
            select(ConsultationVisit)
            .options(
                selectinload(ConsultationVisit.branches).selectinload(ConsultationBranch.medications)
            )
            .where(ConsultationVisit.appointment_id == appointment_id)
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
        base_q = select(ConsultationVisit).where(
            ConsultationVisit.patient_id == patient_id,
            ConsultationVisit.clinic_id == clinic_id,
        )
        total = (await self.db.execute(
            select(func.count()).select_from(base_q.subquery())
        )).scalar_one()

        offset, limit = paginate(page=page, per_page=per_page)
        rows = await self.db.execute(
            base_q.order_by(ConsultationVisit.created_at.desc()).offset(offset).limit(limit)
        )
        return PaginatedResult(items=list(rows.scalars().all()), total=total, page=page, per_page=limit)

    async def update(self, visit: ConsultationVisit, **kwargs) -> ConsultationVisit:
        for field, value in kwargs.items():
            setattr(visit, field, value)
        await self.db.flush()
        return visit

    async def finalize(self, visit: ConsultationVisit) -> ConsultationVisit:
        """Lock visit + compute total_billed from all branches."""
        total = sum(b.billing_amount or Decimal("0") for b in (visit.branches or []))
        visit.is_finalized = True
        visit.finalized_at = datetime.now(timezone.utc)
        visit.total_billed = total
        await self.db.flush()
        return visit

    async def update_report_path(self, visit: ConsultationVisit, path: str) -> ConsultationVisit:
        visit.report_generated = True
        visit.report_path = path
        visit.report_generated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return visit

    async def reload(self, visit: ConsultationVisit) -> ConsultationVisit:
        self.db.expire(visit, ["branches"])
        result = await self.db.execute(
            select(ConsultationVisit)
            .options(
                selectinload(ConsultationVisit.branches).selectinload(ConsultationBranch.medications)
            )
            .where(ConsultationVisit.id == visit.id)
        )
        return result.scalar_one()

    # ── Branch CRUD ───────────────────────────────────────────────────────────

    async def create_branch(
        self,
        visit: ConsultationVisit,
        **kwargs,
    ) -> ConsultationBranch:
        branch = ConsultationBranch(
            clinic_id=visit.clinic_id,
            visit_id=visit.id,
            patient_id=visit.patient_id,
            **kwargs,
        )
        self.db.add(branch)
        await self.db.flush()
        return branch

    async def get_branch_by_id(
        self, branch_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ConsultationBranch | None:
        result = await self.db.execute(
            select(ConsultationBranch)
            .options(selectinload(ConsultationBranch.medications))
            .where(
                ConsultationBranch.id == branch_id,
                ConsultationBranch.clinic_id == clinic_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_branch(
        self, branch: ConsultationBranch, **kwargs
    ) -> ConsultationBranch:
        for field, value in kwargs.items():
            setattr(branch, field, value)
        await self.db.flush()
        return branch

    async def replace_branch_medications(
        self,
        branch: ConsultationBranch,
        medications: list[dict],
    ) -> None:
        await self.db.execute(
            delete(Medication).where(Medication.branch_id == branch.id)
        )
        for i, med in enumerate(medications):
            m = Medication(
                branch_id=branch.id,
                clinic_id=branch.clinic_id,
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

    async def reload_branch(self, branch: ConsultationBranch) -> ConsultationBranch:
        self.db.expire(branch, ["medications"])
        result = await self.db.execute(
            select(ConsultationBranch)
            .options(selectinload(ConsultationBranch.medications))
            .where(ConsultationBranch.id == branch.id)
        )
        return result.scalar_one()

    # ── Pending treatments ────────────────────────────────────────────────────

    async def create_pending_treatment(
        self,
        clinic_id: uuid.UUID,
        patient_id: uuid.UUID,
        origin_branch: ConsultationBranch,
        procedure_category: str,
        procedure_name: str,
        procedure_detail: str | None = None,
        tooth_ids: list | None = None,
        session_number: int | None = None,
        session_total: int | None = None,
        notes: str | None = None,
    ) -> PendingTreatment:
        pt = PendingTreatment(
            clinic_id=clinic_id,
            patient_id=patient_id,
            origin_branch_id=origin_branch.id,
            procedure_category=procedure_category,
            procedure_name=procedure_name,
            procedure_detail=procedure_detail,
            tooth_ids=tooth_ids,
            session_number=str(session_number) if session_number else None,
            session_total=str(session_total) if session_total else None,
            notes=notes,
        )
        self.db.add(pt)
        await self.db.flush()
        return pt

    async def get_pending_by_patient(
        self, patient_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> list[PendingTreatment]:
        result = await self.db.execute(
            select(PendingTreatment)
            .where(
                PendingTreatment.patient_id == patient_id,
                PendingTreatment.clinic_id == clinic_id,
                PendingTreatment.status == "pending",
            )
            .order_by(PendingTreatment.created_at.asc())
        )
        return list(result.scalars().all())

    async def complete_pending_treatment(
        self,
        pt: PendingTreatment,
        completed_in_visit_id: uuid.UUID,
    ) -> PendingTreatment:
        pt.status = "completed"
        pt.completed_in_visit_id = completed_in_visit_id
        await self.db.flush()
        return pt
