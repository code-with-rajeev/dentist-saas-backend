# Standard library
from enum import Enum


class AppointmentStatus(str, Enum):
    PENDING = "pending"
    WAITING = "waiting"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class AppointmentType(str, Enum):
    NEW = "new"
    EXISTING = "existing"
    FOLLOW_UP = "follow_up"


# State machine — allowed transitions per current status
# Key: current status | Value: set of allowed target statuses
APPOINTMENT_STATUS_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.WAITING,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.WAITING: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.COMPLETED: set(),     # LOCKED
    AppointmentStatus.CANCELLED: set(),     # LOCKED
    AppointmentStatus.NO_SHOW: set(),       # LOCKED
}

# ID generation
PATIENT_CODE_PREFIX = "PAT"
APPOINTMENT_CODE_PREFIX = "APT"

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
