# Standard library
import uuid
from datetime import date, datetime, timezone

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.constants.messages import (
    APPOINTMENT_NOT_FOUND,
    APPOINTMENT_ALREADY_CONFIRMED,
    INVALID_STATUS_TRANSITION,
    PATIENT_NOT_FOUND,
)

# Internal — repositories
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.patient_repository import PatientRepository

# Internal — schemas
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCancelRequest,
    AppointmentFilter,
    AppointmentListItem,
    AppointmentRescheduleRequest,
    AppointmentResponse,
    QueueItem,
    QueueResponse,
)

# Internal — utils
from app.utils.id_generator import generate_appointment_code
from app.utils.pagination import PaginatedResult
from app.rbac.current_user import CurrentUser

# ============================================================
# Valid status transitions
# ============================================================
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending":  {"waiting", "cancelled"},
    "waiting":  {"completed", "cancelled", "no_show"},
    "completed": set(),
    "cancelled": set(),
    "no_show":   set(),
}


def _check_transition(current: str, target: str, error_code: str) -> None:
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValidationException(
            code=error_code,
            message=f"Cannot transition appointment from '{current}' to '{target}'",
        )


class AppointmentService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AppointmentRepository(db)
        self.patient_repo = PatientRepository(db)

    async def create_appointment(
        self, data: AppointmentCreate, clinic_id: uuid.UUID, created_by: CurrentUser
    ) -> AppointmentResponse:
        # Validate patient belongs to clinic
        patient = await self.patient_repo.get_by_id(data.patient_id, clinic_id)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found in this clinic")

        # Enforce: follow_up requires a parent, everything else ignores it
        parent_appointment_id = None
        if data.appointment_type == "follow_up":
            if not data.parent_appointment_id:
                raise ValidationException(
                    code="MISSING_REQUIRED_FIELD",
                    message="parent_appointment_id is required for follow-up appointments",
                )
            parent = await self.repo.get_by_id(data.parent_appointment_id, clinic_id)
            if parent is None:
                raise NotFoundException(
                    code="PARENT_APPOINTMENT_NOT_FOUND",
                    message="Parent appointment not found",
                )
            
            # Business rule: cannot create follow-up for a completed appointment, as it doesn't make sense to follow up on something that's already done. Follow-ups should be created for pending/waiting appointments that need further action.
            if parent.status == "completed":
                raise ValidationException(
                    code="INVALID_FOLLOW_UP_PARENT",
                    message="Cannot create follow-up for a completed appointment",
                )
            
            parent_appointment_id = data.parent_appointment_id

        code = await generate_appointment_code(clinic_id, self.db)
        appt = await self.repo.create(
            clinic_id=clinic_id,
            appointment_code=code,
            patient_id=data.patient_id,
            appointment_type=data.appointment_type,
            scheduled_date=data.scheduled_date,
            scheduled_time_slot=data.scheduled_time_slot,
            notes=data.notes,
            parent_appointment_id=parent_appointment_id,
            status="pending",
            created_by=created_by.id,
        )
        response = AppointmentResponse.model_validate(appt)
        response.consultation_id = None  # consultation not created yet at this point, Buisness Rule
        return response

    async def list_appointments(
        self,
        clinic_id: uuid.UUID,
        filters: AppointmentFilter,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        result = await self.repo.get_all_by_clinic(clinic_id, filters, page=page, per_page=per_page)
        # add consultation_id to each item for convenience
        items = []
        for a in result.items:
            item = AppointmentListItem.model_validate(a)
            item.consultation_id = a.consultation.id if a.consultation else None
            items.append(item)

        result.items = items
        return result

    async def get_appointment(
        self, appointment_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> AppointmentResponse:
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")
        return _to_response(appt)

    async def confirm_appointment(
        self, appointment_id: uuid.UUID, clinic_id: uuid.UUID, confirmed_by: CurrentUser
    ) -> AppointmentResponse:
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")

        if appt.status == "waiting":
            raise ConflictException(
                code=APPOINTMENT_ALREADY_CONFIRMED,
                message="Appointment is already confirmed (waiting)",
            )

        _check_transition(appt.status, "waiting", INVALID_STATUS_TRANSITION)

        queue_pos = await self.repo.get_next_queue_position(clinic_id, appt.scheduled_date)
        await self.repo.update(
            appt,
            status="waiting",
            queue_position=queue_pos,
            confirmed_by=confirmed_by.id,
            confirmed_at=datetime.now(timezone.utc),
        )
        return _to_response(appt)

    async def cancel_appointment(
        self,
        appointment_id: uuid.UUID,
        clinic_id: uuid.UUID,
        cancelled_by: CurrentUser,
        reason: str | None = None,
    ) -> AppointmentResponse:
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")

        _check_transition(appt.status, "cancelled", INVALID_STATUS_TRANSITION)

        await self.repo.update(
            appt,
            status="cancelled",
            cancelled_reason=reason,
            cancelled_at=datetime.now(timezone.utc),
            cancelled_by=cancelled_by.id,
        )
        return _to_response(appt)

    async def reschedule_appointment(
        self,
        appointment_id: uuid.UUID,
        clinic_id: uuid.UUID,
        data: AppointmentRescheduleRequest,
    ) -> AppointmentResponse:
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")

        # Only pending appointments can be rescheduled
        if appt.status not in ("pending", "waiting"):
            raise ValidationException(
                code=INVALID_STATUS_TRANSITION,
                message=f"Cannot reschedule a '{appt.status}' appointment",
            )

        update_data: dict = {
            "scheduled_date": data.scheduled_date,
            "scheduled_time_slot": data.scheduled_time_slot,
        }
        # Reset to pending if it was waiting (queue position lost)
        if appt.status == "waiting":
            update_data["status"] = "pending"
            update_data["queue_position"] = None
            update_data["confirmed_at"] = None
            update_data["confirmed_by"] = None

        await self.repo.update(appt, **update_data)
        return _to_response(appt)

    async def mark_no_show(
        self, appointment_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> AppointmentResponse:
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")

        _check_transition(appt.status, "no_show", INVALID_STATUS_TRANSITION)

        await self.repo.update(appt, status="no_show")
        return _to_response(appt)

    async def complete_appointment(
        self, appointment_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> AppointmentResponse:
        """
        Mark appointment as completed.
        Called by consultation submit (Phase 8) — the consultation service
        calls this after locking the form. Direct route is owner-only.
        """
        appt = await self.repo.get_by_id(appointment_id, clinic_id)
        if appt is None:
            raise NotFoundException(code=APPOINTMENT_NOT_FOUND, message="Appointment not found")

        _check_transition(appt.status, "completed", INVALID_STATUS_TRANSITION)

        await self.repo.update(appt, status="completed")
        return _to_response(appt)

    async def get_queue(self, clinic_id: uuid.UUID) -> QueueResponse:
        today = datetime.now(timezone.utc).date()
        items = await self.repo.get_queue(clinic_id, today)
        queue_items = []
        for a in items:
            item = QueueItem.model_validate(a)
            item.patient_name = a.patient.full_name if a.patient else None   # ← add
            item.appointment_type = a.appointment_type                        # ← add
            queue_items.append(item)

        return QueueResponse(
            date=today,
            total_waiting=len(items),
            items=queue_items,
        )

    async def get_patient_appointments(
        self,
        patient_id: uuid.UUID,
        clinic_id: uuid.UUID,
        *,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        # Ensure patient belongs to clinic
        patient = await self.patient_repo.get_by_id(patient_id, clinic_id)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found")

        result = await self.repo.get_appointments_by_patient(
            patient_id, clinic_id, page=page, per_page=per_page
        )
        # add consultation_id to each item for convenience (Phase 7 addition)
        items = []
        for a in result.items:
            item = AppointmentListItem.model_validate(a)
            item.consultation_id = a.consultation.id if a.consultation else None
            items.append(item)

        result.items = items
        return result


# ============================================================
# Private helpers
# ============================================================

def _to_response(appt) -> AppointmentResponse:
    response = AppointmentResponse.model_validate(appt)
    response.consultation_id = appt.consultation.id if appt.consultation else None
    return response