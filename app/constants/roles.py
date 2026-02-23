# Standard library
from enum import Enum


class MemberRole(str, Enum):
    CLINIC_OWNER = "clinic_owner"
    ASSISTANT = "assistant"
    RECEPTIONIST = "receptionist"
    HELPER = "helper"
    COMPOUNDER = "compounder"
    OTHER = "other"


class FollowUpStatus(str, Enum):
    SCHEDULED = "scheduled"
    SENT = "sent"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ClinicStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
