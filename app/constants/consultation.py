# Standard library
from enum import Enum


class EntryPoint(str, Enum):
    NEW_PAIN  = "new_pain"
    CLEANING  = "cleaning"
    COSMETIC  = "cosmetic"
    ORTHO     = "ortho"
    RETURNING = "returning"
    CUSTOM    = "custom"


class BranchStatus(str, Enum):
    DONE     = "done"
    PLANNED  = "planned"
    DEFERRED = "deferred"
    REFERRED = "referred"


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID   = "paid"
    WAIVED = "waived"


class PendingTreatmentStatus(str, Enum):
    PENDING    = "pending"
    SCHEDULED  = "scheduled"
    COMPLETED  = "completed"
    ABANDONED  = "abandoned"


class PresentingProblem(str, Enum):
    TOOTH_PAIN      = "tooth_pain"
    GUM             = "gum"
    MOUTH_ULCER     = "mouth_ulcer"
    JAW_PAIN        = "jaw_pain"
    SWELLING        = "swelling"
    POST_EXTRACTION = "post_extraction"


class ProcedureCategory(str, Enum):
    ENDODONTIC    = "Endodontic"
    RESTORATIVE   = "Restorative"
    SURGICAL      = "Surgical"
    PERIODONTIC   = "Periodontic"
    PROSTHODONTIC = "Prosthodontic"
    ORTHODONTIC   = "Orthodontic"
    COSMETIC      = "Cosmetic"
