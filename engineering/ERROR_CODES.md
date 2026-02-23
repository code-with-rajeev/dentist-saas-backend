# ERROR_CODES.md
# Dentist AI SaaS — Error Codes & Exception Handling
> Every error code. Every HTTP status. Every message. One source of truth.

---

## Design Philosophy

- Every error has a **machine-readable code** (constant string) — frontend handles it programmatically
- Every error has a **human-readable message** — shown to end user
- Every error has a **fixed HTTP status** — never changes per context
- Internal details (stack traces, query errors) **never exposed** in production responses
- All custom exceptions inherit from one `AppException` base class
- One global handler in `main.py` catches everything — no try/catch scattered in routes

---

## Standard Error Response Shape

```json
{
  "success": false,
  "message": "Human readable message for display",
  "error": {
    "code": "ERROR_CODE_CONSTANT",
    "detail": "Optional technical detail — null in production, visible in development"
  }
}
```

---

## Exception Class Hierarchy

Defined in `app/core/exceptions.py`

```
Exception
  └── AppException                  ← base for all custom exceptions
        ├── AuthException           ← 401 family
        ├── ForbiddenException      ← 403 family
        ├── NotFoundException       ← 404 family
        ├── ConflictException       ← 409 family
        ├── ValidationException     ← 400 family
        └── ServerException         ← 500 family
```

**Every exception carries:**
```python
class AppException(Exception):
    code: str           # ERROR_CODE_CONSTANT
    message: str        # human readable
    http_status: int    # HTTP status code
    detail: str | None  # technical detail — only shown in development
```

---

## Error Code Master Reference

### AUTH Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `UNAUTHORIZED` | 401 | Authentication required | No token or invalid token format |
| `TOKEN_EXPIRED` | 401 | Session expired, please login again | Access token past expiry |
| `TOKEN_INVALID` | 401 | Invalid token | Token tampered or malformed |
| `REFRESH_TOKEN_MISSING` | 401 | Session not found, please login | No refresh cookie present |
| `REFRESH_TOKEN_INVALID` | 401 | Invalid session, please login | Refresh token tampered |
| `REFRESH_TOKEN_EXPIRED` | 401 | Session expired, please login again | Refresh token past expiry |
| `INVALID_CREDENTIALS` | 401 | Invalid email or password | Wrong email or password on login |
| `ACCOUNT_INACTIVE` | 403 | Your account has been deactivated | `is_active = false` on user |

---

### PERMISSION / ACCESS Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `FORBIDDEN` | 403 | You do not have permission to perform this action | Valid token, wrong permission |
| `CLINIC_ACCESS_DENIED` | 403 | Access denied to this resource | Resource belongs to different clinic |
| `OWNER_EXCLUSIVE_PERMISSION` | 400 | This permission cannot be assigned to staff | Attempt to assign owner-only permission |
| `OWNER_ROLE_REQUIRED` | 403 | Only the clinic owner can perform this action | Staff attempting owner-only action |

---

### CLINIC Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `CLINIC_NOT_FOUND` | 404 | Clinic not found | Clinic ID does not exist |
| `LOCKED_FIELD_MODIFICATION` | 400 | This field cannot be modified | Attempt to edit locked clinic field |
| `INVALID_OPERATING_HOURS` | 400 | Invalid operating hours format | Bad time format or day key in hours |

---

### STAFF / USER Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `EMAIL_ALREADY_EXISTS` | 409 | An account with this email already exists | Duplicate email on register or staff add |
| `STAFF_NOT_FOUND` | 404 | Staff member not found | staff_id not in this clinic |
| `CANNOT_REMOVE_OWNER` | 400 | The clinic owner cannot be removed | Attempt to delete clinic_owner member |
| `CANNOT_DEACTIVATE_OWNER` | 400 | The clinic owner cannot be deactivated | Attempt to deactivate clinic_owner |
| `INVALID_PERMISSION_STRING` | 400 | Invalid permission | Permission string not in allowed list |
| `USER_NOT_FOUND` | 404 | User not found | user_id does not exist |

---

### PATIENT Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `PATIENT_NOT_FOUND` | 404 | Patient not found | patient_id not in this clinic |
| `PATIENT_ALREADY_EXISTS` | 409 | A patient with this phone number already exists | Duplicate phone within clinic (if enforced) |

---

### APPOINTMENT Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `APPOINTMENT_NOT_FOUND` | 404 | Appointment not found | appointment_id not in this clinic |
| `PARENT_APPOINTMENT_NOT_FOUND` | 404 | Parent appointment not found | parent_appointment_id not in this clinic |
| `INVALID_FOLLOW_UP_PARENT` | 400 | Cannot create follow-up for a completed appointment | Parent status is completed |
| `PAST_DATE` | 400 | Appointment date cannot be in the past | scheduled_date < today |
| `INVALID_STATUS_TRANSITION` | 400 | This status change is not allowed | Transition not in allowed state machine |
| `APPOINTMENT_ALREADY_CONFIRMED` | 400 | Appointment is already confirmed | Confirm called on waiting status |
| `APPOINTMENT_NOT_WAITING` | 400 | Appointment must be in waiting status | Check-in on non-waiting appointment |
| `APPOINTMENT_LOCKED` | 400 | Appointment is completed and cannot be modified | Any write on completed appointment |
| `QUEUE_POSITION_CONFLICT` | 409 | Queue position conflict, please retry | Race condition on queue position assign |

---

### CONSULTATION Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `CONSULTATION_NOT_FOUND` | 404 | Consultation not found | consultation_id not in this clinic |
| `CONSULTATION_ALREADY_EXISTS` | 409 | A consultation already exists for this appointment | Second create on same appointment |
| `CONSULTATION_LOCKED` | 400 | Consultation has been submitted and cannot be edited | Edit attempt on submitted consultation |
| `CONSULTATION_NOT_SUBMITTED` | 400 | Consultation must be submitted first | Complete/PDF on draft consultation |
| `CONSULTATION_DRAFT_REQUIRED` | 400 | No draft consultation found for this appointment | Submit called with no draft |

---

### ANALYTICS Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `INVALID_PERIOD` | 400 | Invalid period value | Period not in allowed enum |
| `INVALID_DATE_RANGE` | 400 | date_from cannot be after date_to | Bad custom date range |
| `PERIOD_AND_RANGE_CONFLICT` | 400 | Cannot use period and date range together | Both period and date_from/date_to sent |

---

### PDF / REPORT Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `REPORT_GENERATION_FAILED` | 500 | Failed to generate report, please try again | PDF generation exception |
| `REPORT_NOT_FOUND` | 404 | Report not found | report_path missing or file deleted |

---

### VALIDATION Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | Invalid request data | Pydantic validation failure — field-level errors attached |
| `MISSING_REQUIRED_FIELD` | 422 | Required field missing | Manual required field check beyond Pydantic |
| `INVALID_UUID` | 400 | Invalid ID format | Malformed UUID in path or body |
| `INVALID_DATE_FORMAT` | 400 | Invalid date format, use YYYY-MM-DD | Bad date string |
| `INVALID_TIME_FORMAT` | 400 | Invalid time format, use HH:MM | Bad time string |

---

### SERVER Errors

| Code | HTTP | Message | When |
|---|---|---|---|
| `INTERNAL_SERVER_ERROR` | 500 | Something went wrong, please try again | Unhandled exception |
| `DATABASE_ERROR` | 500 | Database error, please try again | SQLAlchemy / DB connection failure |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable | Startup failure or dependency down |

---

## Validation Error Response Shape

Pydantic validation failures return field-level detail:

```json
{
  "success": false,
  "message": "Invalid request data",
  "error": {
    "code": "VALIDATION_ERROR",
    "detail": [
      {
        "field": "email",
        "message": "value is not a valid email address"
      },
      {
        "field": "age",
        "message": "ensure this value is greater than 0"
      }
    ]
  }
}
```

---

## Environment Behavior

### Development
```json
{
  "success": false,
  "message": "Patient not found",
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "detail": "No patient with id=3fa85f64 found in clinic=abc123"
  }
}
```

### Production
```json
{
  "success": false,
  "message": "Patient not found",
  "error": {
    "code": "PATIENT_NOT_FOUND",
    "detail": null
  }
}
```

**Rule:** `detail` field is populated only when `APP_ENV=development`. In staging and production it is always `null`. Stack traces are logged server-side, never sent to client.

---

## HTTP Status Code Usage

| Status | Used For |
|---|---|
| `200` | Successful GET, PATCH, DELETE (with body) |
| `201` | Successful POST — resource created |
| `400` | Bad request — business rule violation, invalid input |
| `401` | Not authenticated — missing or invalid token |
| `403` | Authenticated but not authorized — wrong role or clinic |
| `404` | Resource not found |
| `409` | Conflict — duplicate resource |
| `422` | Pydantic validation failure — malformed request body |
| `500` | Unhandled server error |
| `503` | Service unavailable |

**Rule:** HTTP status is always consistent per error code. `PATIENT_NOT_FOUND` is always `404`. Never `400`. Never `200` with an error body. No exceptions.

---

## Global Exception Handler Map

Registered in `app/core/error_handlers.py` and mounted in `app/main.py`.

```
AppException           → format with code, message, detail (env-aware)
RequestValidationError → 422 VALIDATION_ERROR with field-level detail
ValueError             → 400 VALIDATION_ERROR
HTTPException          → pass through with standard envelope
Exception (catch-all)  → 500 INTERNAL_SERVER_ERROR + log full traceback
```

---

## Constants File Reference

Defined in `app/constants/messages.py` — error codes as Python constants.

```python
# Auth
UNAUTHORIZED                  = "UNAUTHORIZED"
TOKEN_EXPIRED                 = "TOKEN_EXPIRED"
TOKEN_INVALID                 = "TOKEN_INVALID"
REFRESH_TOKEN_MISSING         = "REFRESH_TOKEN_MISSING"
REFRESH_TOKEN_INVALID         = "REFRESH_TOKEN_INVALID"
REFRESH_TOKEN_EXPIRED         = "REFRESH_TOKEN_EXPIRED"
INVALID_CREDENTIALS           = "INVALID_CREDENTIALS"
ACCOUNT_INACTIVE              = "ACCOUNT_INACTIVE"

# Permission
FORBIDDEN                     = "FORBIDDEN"
CLINIC_ACCESS_DENIED          = "CLINIC_ACCESS_DENIED"
OWNER_EXCLUSIVE_PERMISSION    = "OWNER_EXCLUSIVE_PERMISSION"
OWNER_ROLE_REQUIRED           = "OWNER_ROLE_REQUIRED"

# Clinic
CLINIC_NOT_FOUND              = "CLINIC_NOT_FOUND"
LOCKED_FIELD_MODIFICATION     = "LOCKED_FIELD_MODIFICATION"
INVALID_OPERATING_HOURS       = "INVALID_OPERATING_HOURS"

# Staff / User
EMAIL_ALREADY_EXISTS          = "EMAIL_ALREADY_EXISTS"
STAFF_NOT_FOUND               = "STAFF_NOT_FOUND"
CANNOT_REMOVE_OWNER           = "CANNOT_REMOVE_OWNER"
CANNOT_DEACTIVATE_OWNER       = "CANNOT_DEACTIVATE_OWNER"
INVALID_PERMISSION_STRING     = "INVALID_PERMISSION_STRING"
USER_NOT_FOUND                = "USER_NOT_FOUND"

# Patient
PATIENT_NOT_FOUND             = "PATIENT_NOT_FOUND"
PATIENT_ALREADY_EXISTS        = "PATIENT_ALREADY_EXISTS"

# Appointment
APPOINTMENT_NOT_FOUND         = "APPOINTMENT_NOT_FOUND"
PARENT_APPOINTMENT_NOT_FOUND  = "PARENT_APPOINTMENT_NOT_FOUND"
INVALID_FOLLOW_UP_PARENT      = "INVALID_FOLLOW_UP_PARENT"
PAST_DATE                     = "PAST_DATE"
INVALID_STATUS_TRANSITION     = "INVALID_STATUS_TRANSITION"
APPOINTMENT_ALREADY_CONFIRMED = "APPOINTMENT_ALREADY_CONFIRMED"
APPOINTMENT_NOT_WAITING       = "APPOINTMENT_NOT_WAITING"
APPOINTMENT_LOCKED            = "APPOINTMENT_LOCKED"
QUEUE_POSITION_CONFLICT       = "QUEUE_POSITION_CONFLICT"

# Consultation
CONSULTATION_NOT_FOUND        = "CONSULTATION_NOT_FOUND"
CONSULTATION_ALREADY_EXISTS   = "CONSULTATION_ALREADY_EXISTS"
CONSULTATION_LOCKED           = "CONSULTATION_LOCKED"
CONSULTATION_NOT_SUBMITTED    = "CONSULTATION_NOT_SUBMITTED"
CONSULTATION_DRAFT_REQUIRED   = "CONSULTATION_DRAFT_REQUIRED"

# Analytics
INVALID_PERIOD                = "INVALID_PERIOD"
INVALID_DATE_RANGE            = "INVALID_DATE_RANGE"
PERIOD_AND_RANGE_CONFLICT     = "PERIOD_AND_RANGE_CONFLICT"

# PDF
REPORT_GENERATION_FAILED      = "REPORT_GENERATION_FAILED"
REPORT_NOT_FOUND              = "REPORT_NOT_FOUND"

# Validation
VALIDATION_ERROR              = "VALIDATION_ERROR"
MISSING_REQUIRED_FIELD        = "MISSING_REQUIRED_FIELD"
INVALID_UUID                  = "INVALID_UUID"
INVALID_DATE_FORMAT           = "INVALID_DATE_FORMAT"
INVALID_TIME_FORMAT           = "INVALID_TIME_FORMAT"

# Server
INTERNAL_SERVER_ERROR         = "INTERNAL_SERVER_ERROR"
DATABASE_ERROR                = "DATABASE_ERROR"
SERVICE_UNAVAILABLE           = "SERVICE_UNAVAILABLE"
```

**Total: 47 error codes**

---

## Usage Pattern in Services

```python
# In any service file — raise, never return errors
from app.core.exceptions import NotFoundException
from app.constants.messages import PATIENT_NOT_FOUND

async def get_patient(patient_id: UUID, clinic_id: UUID) -> Patient:
    patient = await patient_repository.get_by_id(patient_id, clinic_id)
    if not patient:
        raise NotFoundException(
            code=PATIENT_NOT_FOUND,
            message="Patient not found"
        )
    return patient
```

**Rules:**
- Always `raise` exceptions — never `return` error objects from services
- Always use constants from `messages.py` — never hardcode strings
- Never catch and re-raise without logging in service layer
- Global handler in `main.py` catches everything — no duplicate handling
