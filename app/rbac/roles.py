# Internal
from app.rbac.permissions import (
    ALL_PERMISSIONS,
    APPOINTMENT_CANCEL,
    APPOINTMENT_READ,
    APPOINTMENT_WRITE,
    CLINIC_SETTINGS_READ,
    PATIENT_READ,
    PATIENT_WRITE,
)

# ============================================================
# Owner permissions — hardcoded, never stored in DB
# clinic_owner always has ALL 12 permissions
# ============================================================
OWNER_PERMISSIONS: list[str] = list(ALL_PERMISSIONS)

# ============================================================
# Recommended starter permission sets per staff role
# These are defaults — owner can customise after adding staff
# ============================================================
RECOMMENDED_PERMISSIONS: dict[str, list[str]] = {
    "assistant": [
        CLINIC_SETTINGS_READ,
        APPOINTMENT_READ,
        APPOINTMENT_WRITE,
        APPOINTMENT_CANCEL,
        PATIENT_READ,
        PATIENT_WRITE,
    ],
    "receptionist": [
        CLINIC_SETTINGS_READ,
        APPOINTMENT_READ,
        APPOINTMENT_WRITE,
        APPOINTMENT_CANCEL,
        PATIENT_READ,
    ],
    "helper": [
        APPOINTMENT_READ,
        PATIENT_READ,
    ],
    "compounder": [
        APPOINTMENT_READ,
        PATIENT_READ,
    ],
    "other": [
        APPOINTMENT_READ,
        PATIENT_READ,
    ],
}
