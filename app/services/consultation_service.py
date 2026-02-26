# Standard library
import uuid
from pathlib import Path

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.constants.messages import (
    APPOINTMENT_NOT_FOUND,
    CONSULTATION_ALREADY_EXISTS,
    CONSULTATION_LOCKED,
    CONSULTATION_NOT_FOUND,
    CONSULTATION_NOT_SUBMITTED,
    PATIENT_NOT_FOUND,
)

# Internal — repositories
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.clinic_repository import ClinicRepository
from app.repositories.consultation_repository import ConsultationRepository
from app.repositories.patient_repository import PatientRepository

# Internal — services
from app.services.pdf_service import PDFService

# Internal — schemas
from app.schemas.consultation import (
    ConsultationCreate,
    ConsultationListItem,
    ConsultationResponse,
    ConsultationUpdate,
    MedicationResponse,
)
from app.utils.pagination import PaginatedResult
from app.rbac.current_user import CurrentUser


class ConsultationService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ConsultationRepository(db)
        self.appt_repo = AppointmentRepository(db)
        self.patient_repo = PatientRepository(db)
        self.clinic_repo = ClinicRepository(db)

    async def create_consultation(
        self,
        data: ConsultationCreate,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        dentist: CurrentUser,
    ) -> ConsultationResponse:
        # Validate appointment exists and is 'waiting'
        appt = await self.appt_repo.get_by_id(data.appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")
        if appt.status != "waiting":
            raise ValidationException(
                code="APPOINTMENT_NOT_WAITING",
                message=f"Cannot create consultation: appointment is '{appt.status}', must be 'waiting'",
            )
        # Validate patient matches
        if appt.patient_id != patient_id:
            raise ValidationException(
                code=PATIENT_NOT_FOUND,
                message="Appointment does not belong to this patient",
            )
        # Check no draft exists yet
        existing = await self.repo.get_by_appointment_id(data.appointment_id)
        if existing is not None:
            raise ConflictException(
                code=CONSULTATION_ALREADY_EXISTS,
                message="A consultation already exists for this appointment",
            )

        consultation = await self.repo.create(
            clinic_id=clinic_id,
            appointment_id=data.appointment_id,
            patient_id=patient_id,
            dentist_id=dentist.id,
            symptoms=data.symptoms,
            clinical_notes=data.clinical_notes,
            diagnosis=data.diagnosis,
            fee_charged=data.fee_charged,
            is_follow_up_required=data.is_follow_up_required,
            follow_up_notes=data.follow_up_notes,
            follow_up_days=data.follow_up_days,
        )

        if data.medications:
            await self.repo.replace_medications(
                consultation,
                [m.model_dump() for m in data.medications],
            )

        consultation = await self.repo.reload_with_medications(consultation)
        return _to_response(consultation)

    async def update_consultation(
        self,
        consultation_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: ConsultationUpdate,
    ) -> ConsultationResponse:
        consultation = await self.repo.get_by_id(consultation_id, clinic_id)
        if consultation is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Consultation not found")
        if consultation.is_submitted:
            raise ValidationException(
                code=CONSULTATION_LOCKED,
                message="Cannot update a submitted consultation",
            )

        update_fields = data.model_dump(exclude_none=True, exclude={"medications"})
        if update_fields:
            await self.repo.update(consultation, **update_fields)

        # medications=None means "don't touch"; medications=[] means "clear all"
        if data.medications is not None:
            await self.repo.replace_medications(
                consultation,
                [m.model_dump() for m in data.medications],
            )

        consultation = await self.repo.reload_with_medications(consultation)
        return _to_response(consultation)

    async def submit_consultation(
        self,
        consultation_id: uuid.UUID,
        clinic_id: uuid.UUID,
    ) -> ConsultationResponse:
        consultation = await self.repo.get_by_id(consultation_id, clinic_id)
        if consultation is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Consultation not found")
        if consultation.is_submitted:
            raise ValidationException(
                code=CONSULTATION_LOCKED,
                message="Consultation is already submitted",
            )

        await self.repo.submit(consultation)

        # Auto-complete the linked appointment
        appt = await self.appt_repo.get_by_id(consultation.appointment_id, clinic_id)
        if appt is not None and appt.status == "waiting":
            await self.appt_repo.update(appt, status="completed")

        consultation = await self.repo.reload_with_medications(consultation)
        return _to_response(consultation)

    async def get_consultation(
        self, consultation_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ConsultationResponse:
        consultation = await self.repo.get_by_id(consultation_id, clinic_id)
        if consultation is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Consultation not found")
        return _to_response(consultation)

    async def get_patient_consultations(
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
        result.items = [ConsultationListItem.model_validate(c) for c in result.items]
        return result

    async def generate_pdf_report(
        self, consultation_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> ConsultationResponse:
        consultation = await self.repo.get_by_id(consultation_id, clinic_id)
        if consultation is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Consultation not found")
        if not consultation.is_submitted:
            raise ValidationException(
                code=CONSULTATION_NOT_SUBMITTED,
                message="Cannot generate PDF for an unsubmitted consultation",
            )

        patient = await self.patient_repo.get_by_id(consultation.patient_id, clinic_id)
        clinic = await self.clinic_repo.get_by_id(clinic_id)
        appointment = await self.appt_repo.get_by_id(consultation.appointment_id, clinic_id)

        pdf_svc = PDFService()
        file_path = pdf_svc.generate(
            consultation=consultation,
            patient=patient,
            clinic=clinic,
            medications=consultation.medications,
            appointment_code=appointment.appointment_code if appointment else "UNKNOWN",
        )

        await self.repo.update_report_path(consultation, file_path)
        consultation = await self.repo.reload_with_medications(consultation)
        return _to_response(consultation)

    async def get_pdf_path(
        self, consultation_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> str:
        consultation = await self.repo.get_by_id(consultation_id, clinic_id)
        if consultation is None:
            raise NotFoundException(code=CONSULTATION_NOT_FOUND, message="Consultation not found")
        if not consultation.is_submitted:
            raise ValidationException(
                code=CONSULTATION_NOT_SUBMITTED,
                message="Report is only available for submitted consultations",
            )
        if not consultation.report_generated or not consultation.report_path:
            raise NotFoundException(
                code="REPORT_NOT_FOUND",
                message="PDF report has not been generated yet. POST to /generate-report first.",
            )
        if not Path(consultation.report_path).exists():
            raise NotFoundException(
                code="REPORT_NOT_FOUND",
                message="PDF file not found on disk",
            )
        return consultation.report_path


# ============================================================
# Private helpers
# ============================================================

def _to_response(c) -> ConsultationResponse:
    return ConsultationResponse(
        id=c.id,
        clinic_id=c.clinic_id,
        appointment_id=c.appointment_id,
        patient_id=c.patient_id,
        dentist_id=c.dentist_id,
        symptoms=c.symptoms,
        clinical_notes=c.clinical_notes,
        diagnosis=c.diagnosis,
        fee_charged=c.fee_charged,
        is_follow_up_required=c.is_follow_up_required,
        follow_up_notes=c.follow_up_notes,
        follow_up_days=c.follow_up_days,
        medications=[MedicationResponse.model_validate(m) for m in (c.medications or [])],
        is_submitted=c.is_submitted,
        submitted_at=c.submitted_at,
        report_generated=c.report_generated,
        report_path=c.report_path,
        report_generated_at=c.report_generated_at,
        created_at=c.created_at,
    )
