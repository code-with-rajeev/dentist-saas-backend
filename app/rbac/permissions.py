# ============================================================
# All 12 permission strings — from RBAC.md
# Always import from here. Never hardcode permission strings.
# ============================================================

# Clinic management
CLINIC_SETTINGS_READ = "clinic:settings:read"
CLINIC_SETTINGS_WRITE = "clinic:settings:write"
CLINIC_STAFF_MANAGE = "clinic:staff:manage"

# Appointments
APPOINTMENT_READ = "appointment:read"
APPOINTMENT_WRITE = "appointment:write"
APPOINTMENT_CANCEL = "appointment:cancel"
APPOINTMENT_COMPLETE = "appointment:complete"

# Patients
PATIENT_READ = "patient:read"
PATIENT_WRITE = "patient:write"

# Consultations
CONSULTATION_WRITE = "consultation:write"
CONSULTATION_SUBMIT = "consultation:submit"

# Analytics
ANALYTICS_READ = "analytics:read"

# ============================================================
# Permission groupings
# ============================================================

# All 12 permissions — used for validation
ALL_PERMISSIONS: list[str] = [
    CLINIC_SETTINGS_READ,
    CLINIC_SETTINGS_WRITE,
    CLINIC_STAFF_MANAGE,
    APPOINTMENT_READ,
    APPOINTMENT_WRITE,
    APPOINTMENT_CANCEL,
    APPOINTMENT_COMPLETE,
    PATIENT_READ,
    PATIENT_WRITE,
    CONSULTATION_WRITE,
    CONSULTATION_SUBMIT,
    ANALYTICS_READ,
]

# Permissions only the clinic_owner can have — staff cannot be granted these
OWNER_EXCLUSIVE_PERMISSIONS: list[str] = [
    CLINIC_SETTINGS_WRITE,
    CLINIC_STAFF_MANAGE,
    APPOINTMENT_COMPLETE,
    CONSULTATION_WRITE,
    CONSULTATION_SUBMIT,
    ANALYTICS_READ,
]

# Permissions that CAN be granted to staff
GRANTABLE_PERMISSIONS: list[str] = [
    p for p in ALL_PERMISSIONS if p not in OWNER_EXCLUSIVE_PERMISSIONS
]
