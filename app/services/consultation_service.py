# Standard library
import uuid
from decimal import Decimal
from pathlib import Path

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.config import settings
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.constants.messages import (
    APPOINTMENT_NOT_FOUND,
    CONSULTATION_ALREADY_EXISTS,
    CONSULTATION_LOCKED,
    CONSULTATION_NOT_FOUND,
    CONSULTATION_NOT_SUBMITTED,
    PATIENT_NOT_FOUND,
    REPORT_NOT_FOUND,
)
from app.constants.consultation import BranchStatus

# Internal — repositories
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.consultation_repository import ConsultationVisitRepository
from app.repositories.patient_repository import PatientRepository

# Internal — services
from app.services.pdf_service import PDFService
from app.services.med_library_service import MedLibraryService

# Internal — schemas
from app.schemas.consultation_visit import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
    MedicationResponse,
    PendingTreatmentResponse,
    VisitCreate,
    VisitListItem,
    VisitResponse,
    VisitUpdate,
)
from app.utils.pagination import PaginatedResult
from app.rbac.current_user import CurrentUser


class ConsultationService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConsultationVisitRepository(db)
        self.appt_repo = AppointmentRepository(db)
        self.patient_repo = PatientRepository(db)
        self.clinic_repo = ClinicRepository(db)

    # ── Visit lifecycle ───────────────────────────────────────────────────────

    async def create_visit(
        self,
        data: VisitCreate,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        dentist: CurrentUser,
    ) -> VisitResponse:
        appt = await self.appt_repo.get_by_id(data.appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")
        if appt.status != "waiting":
            raise ValidationException(
                code="APPOINTMENT_NOT_WAITING",
                message=f"Cannot start consultation: appointment is '{appt.status}', must be 'waiting'",
            )
        if appt.patient_id != patient_id:
            raise ValidationException(code=PATIENT_NOT_FOUND, message="Appointment does not belong to this patient")

        existing = await self.repo.get_by_appointment_id(data.appointment_id)
        if existing is not None:
            raise ConflictException(code=CONSULTATION_ALREADY_EXISTS, message="A visit already exists for this appointment")

        visit = await self.repo.create(
            clinic_id=clinic_id,
            appointment_id=data.appointment_id,
            patient_id=patient_id,
            dentist_id=dentist.id,
            is_follow_up_required=data.is_follow_up_required,
            follow_up_notes=data.follow_up_notes,
            follow_up_days=data.follow_up_days,
        )
        visit = await self.repo.reload(visit)
        return _visit_to_response(visit)

    async def update_visit(
        self,
        visit_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: VisitUpdate,
    ) -> VisitResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if visit.is_finalized:
            raise ValidationException(code=CONSULTATION_LOCKED, message="Cannot update a finalized visit")

        update_fields = data.model_dump(exclude_none=True)
        if update_fields:
            await self.repo.update(visit, **update_fields)

        visit = await self.repo.reload(visit)
        return _visit_to_response(visit)

    async def finalize_visit(
        self,
        visit_id: uuid.UUID,
        clinic_id: uuid.UUID,
    ) -> VisitResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if visit.is_finalized:
            raise ValidationException(code=CONSULTATION_LOCKED, message="Visit is already finalized")
        if not visit.branches:
            raise ValidationException(
                code="NO_BRANCHES",
                message="Cannot finalize a visit with no branches. Add at least one case first.",
            )

        # Finalize — locks visit, computes total_billed
        await self.repo.finalize(visit)

        # Auto-complete linked appointment
        appt = await self.appt_repo.get_by_id(visit.appointment_id, clinic_id)
        if appt and appt.status == "waiting":
            await self.appt_repo.update(appt, status="completed")

        # Auto-create pending treatments for planned branches
        for branch in visit.branches:
            if branch.branch_status == BranchStatus.PLANNED:
                meta = branch.meta or {}
                await self.repo.create_pending_treatment(
                    clinic_id=clinic_id,
                    patient_id=visit.patient_id,
                    origin_branch=branch,
                    procedure_category=branch.procedure_category or "",
                    procedure_name=branch.procedure_name or "",
                    procedure_detail=branch.procedure_detail,
                    tooth_ids=branch.tooth_ids,
                    session_number=meta.get("session_number"),
                    session_total=meta.get("session_total"),
                )

        # Increment med_library usage counts
        med_svc = MedLibraryService(self.db)
        for branch in visit.branches:
            for med in branch.medications or []:
                if med.med_library_id is not None:
                    await med_svc.increment_usage(med.med_library_id)

        visit = await self.repo.reload(visit)
        return _visit_to_response(visit)

    async def get_visit(
        self, visit_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> VisitResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        return _visit_to_response(visit)

    async def get_patient_visits(
        self,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        patient = await self.patient_repo.get_by_id(patient_id, clinic_id)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found")
        result = await self.repo.get_all_by_patient(patient_id, clinic_id, page=page, per_page=per_page)
        result.items = [_visit_to_list_item(v) for v in result.items]
        return result

    # ── Branch lifecycle ──────────────────────────────────────────────────────

    async def add_branch(
        self,
        visit_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: BranchCreate,
    ) -> BranchResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if visit.is_finalized:
            raise ValidationException(code=CONSULTATION_LOCKED, message="Cannot add branch to a finalized visit")

        branch_fields = data.model_dump(exclude={"medications"})
        branch_fields["tooth_ids"] = data.tooth_ids  # list → stored as JSONB
        branch = await self.repo.create_branch(visit, **branch_fields)

        if data.medications:
            await self.repo.replace_branch_medications(branch, [m.model_dump() for m in data.medications])

        branch = await self.repo.reload_branch(branch)
        return _branch_to_response(branch)

    async def update_branch(
        self,
        visit_id: uuid.UUID,
        branch_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: BranchUpdate,
    ) -> BranchResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if visit.is_finalized:
            raise ValidationException(code=CONSULTATION_LOCKED, message="Cannot update a branch in a finalized visit")

        branch = await self.repo.get_branch_by_id(branch_id, clinic_id)
        if branch is None or branch.visit_id != visit_id:
            raise NotFoundException(code="BRANCH_NOT_FOUND", message="Branch not found")

        update_fields = data.model_dump(exclude_none=True, exclude={"medications"})
        if update_fields:
            await self.repo.update_branch(branch, **update_fields)

        if data.medications is not None:
            await self.repo.replace_branch_medications(branch, [m.model_dump() for m in data.medications])

        branch = await self.repo.reload_branch(branch)
        return _branch_to_response(branch)

    # ── Pending treatments ────────────────────────────────────────────────────

    async def get_patient_pending_treatments(
        self,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
    ) -> list[PendingTreatmentResponse]:
        patient = await self.patient_repo.get_by_id(patient_id, clinic_id)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found")
        items = await self.repo.get_pending_by_patient(patient_id, clinic_id)
        return [PendingTreatmentResponse.model_validate(p) for p in items]


    # ── PDF ───────────────────────────────────────────────────────────────────

    async def generate_pdf_report(
        self, visit_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> VisitResponse:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if not visit.is_finalized:
            raise ValidationException(code=CONSULTATION_NOT_SUBMITTED, message="Cannot generate PDF for an unfinalized visit")

        patient = await self.patient_repo.get_by_id(visit.patient_id, clinic_id)
        clinic = await self.clinic_repo.get_by_id(clinic_id)
        appt = await self.appt_repo.get_by_id(visit.appointment_id, clinic_id)

        # Collect all medications across all branches for the PDF
        all_meds = [med for branch in (visit.branches or []) for med in (branch.medications or [])]

        pdf_svc = PDFService()
        file_path = pdf_svc.generate(
            consultation=visit,        # PDFService reads: symptoms→None, clinical_notes→None
            patient=patient,           # handled below via branch notes
            clinic=clinic,
            medications=all_meds,
            appointment_code=appt.appointment_code if appt else "UNKNOWN",
        )

        await self.repo.update_report_path(visit, file_path)
        visit = await self.repo.reload(visit)
        return _visit_to_response(visit)

    async def get_pdf_path(self, visit_id: uuid.UUID, clinic_id: uuid.UUID) -> str:
        visit = await self.repo.get_by_id(visit_id, clinic_id)
        if visit is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Visit not found")
        if not visit.is_finalized:
            raise ValidationException(code=CONSULTATION_NOT_SUBMITTED, message="Report only available for finalized visits")
        if not visit.report_generated or not visit.report_path:
            raise NotFoundException(code=REPORT_NOT_FOUND, message="PDF not generated yet. POST to /generate-report first.")
        if not Path(visit.report_path).exists():
            raise NotFoundException(code=REPORT_NOT_FOUND, message="PDF file not found on disk")
        return visit.report_path


# ============================================================
# Private helpers
# ============================================================

def _branch_to_response(b) -> BranchResponse:
    return BranchResponse(
        id=b.id,
        visit_id=b.visit_id,
        entry_point=b.entry_point,
        presenting_problem=b.presenting_problem,
        diagnosis=b.diagnosis,
        diagnosis_custom=b.diagnosis_custom,
        procedure_category=b.procedure_category,
        procedure_name=b.procedure_name,
        procedure_detail=b.procedure_detail,
        tooth_ids=b.tooth_ids,
        notes=b.notes,
        branch_status=b.branch_status,
        billing_amount=b.billing_amount,
        payment_status=b.payment_status,
        meta=b.meta,
        medications=[MedicationResponse.model_validate(m) for m in (b.medications or [])],
        created_at=b.created_at,
    )


def _visit_to_response(v) -> VisitResponse:
    return VisitResponse(
        id=v.id,
        clinic_id=v.clinic_id,
        appointment_id=v.appointment_id,
        patient_id=v.patient_id,
        dentist_id=v.dentist_id,
        is_finalized=v.is_finalized,
        finalized_at=v.finalized_at,
        total_billed=v.total_billed,
        total_paid=v.total_paid,
        is_follow_up_required=v.is_follow_up_required,
        follow_up_notes=v.follow_up_notes,
        follow_up_days=v.follow_up_days,
        report_generated=v.report_generated,
        report_path=v.report_path,
        report_generated_at=v.report_generated_at,
        branches=[_branch_to_response(b) for b in (v.branches or [])],
        created_at=v.created_at,
    )


def _visit_to_list_item(v) -> VisitListItem:
    return VisitListItem(
        id=v.id,
        appointment_id=v.appointment_id,
        total_billed=v.total_billed,
        total_paid=v.total_paid,
        is_finalized=v.is_finalized,
        finalized_at=v.finalized_at,
        branch_count=len(v.branches or []),
        is_follow_up_required=v.is_follow_up_required,
        report_generated=v.report_generated,
        created_at=v.created_at,
    )
