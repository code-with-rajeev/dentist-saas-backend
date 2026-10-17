# ============================================================
# models/__init__.py
# Import ALL models here so Alembic can discover them via Base.metadata.
# Add each model in FK dependency order.
# ============================================================

from app.models.user import User
from app.models.clinic import Clinic
from app.models.clinic_member import ClinicMember
from app.models.user_permission import UserPermission
from app.models.patient import Patient
from app.models.appointment import Appointment
from app.models.consultation_visit import ConsultationVisit
from app.models.consultation_branch import ConsultationBranch
from app.models.consultation_case import ConsultationCase
from app.models.pending_treatment import PendingTreatment
from app.models.medication import Medication
from app.models.med_library import MedLibrary
from app.models.follow_up import FollowUp
from app.models.user_otp import UserOtp

__all__ = [
    "User",
    "Clinic",
    "ClinicMember",
    "UserPermission",
    "Patient",
    "Appointment",
    "ConsultationVisit",
    "ConsultationBranch",
    "ConsultationCase",
    "PendingTreatment",
    "Medication",
    "MedLibrary",
    "FollowUp",
    "UserOtp",
]
