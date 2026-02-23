# API_CONTRACT.md
# Dentist AI SaaS — API Contract
> Every endpoint. Every request. Every response. Every error. No guessing.

---

## Global Rules

### Base URL
```
Development:  http://localhost:8000/api/v1
Staging:      https://staging.yourdomain.com/api/v1
Production:   https://api.yourdomain.com/api/v1
```

### Authentication
- All protected routes require: `Authorization: Bearer <access_token>`
- Refresh token is sent/received via HttpOnly cookie: `refresh_token`
- Unauthenticated requests to protected routes → `401 UNAUTHORIZED`
- Authenticated but wrong role/permission → `403 FORBIDDEN`
- Authenticated but wrong clinic resource → `403 FORBIDDEN`

### Request Headers
```
Content-Type: application/json
Authorization: Bearer <access_token>    ← required on protected routes
```

### Standard Response Envelope

**Success**
```json
{
  "success": true,
  "message": "Human readable message",
  "data": { }
}
```

**Success with pagination**
```json
{
  "success": true,
  "message": "Appointments fetched",
  "data": {
    "items": [ ],
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

**Error**
```json
{
  "success": false,
  "message": "Human readable message",
  "error": {
    "code": "ERROR_CODE_CONSTANT",
    "detail": "Optional technical detail — null in production"
  }
}
```

### Date Format
```
All dates:      YYYY-MM-DD
All datetimes:  ISO 8601 — YYYY-MM-DDTHH:MM:SSZ
All times:      HH:MM (24hr)
```

### Pagination Query Params (all list endpoints)
```
?page=1           default: 1
?per_page=20      default: 20, max: 100
```

---

## Module 1 — Auth

### POST /auth/register
Create a new clinic + clinic owner account in one step.

**Access:** Public

**Request Body**
```json
{
  "clinic_name": "SmileCare Dental",
  "full_name": "Dr. Rajesh Kumar",
  "email": "dr.rajesh@smilecare.com",
  "password": "MinLength8Required",
  "phone": "9876543210",
  "dentist_reg_id": "MCI-2024-12345"
}
```

**Validation Rules**
```
clinic_name     required, string, 2–100 chars
full_name       required, string, 2–100 chars
email           required, valid email, unique globally
password        required, min 8 chars
phone           optional, string
dentist_reg_id  optional, string
```

**Response 201**
```json
{
  "success": true,
  "message": "Clinic registered successfully",
  "data": {
    "user": {
      "id": "uuid",
      "full_name": "Dr. Rajesh Kumar",
      "email": "dr.rajesh@smilecare.com",
      "role": "clinic_owner"
    },
    "clinic": {
      "id": "uuid",
      "name": "SmileCare Dental"
    },
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors**
```
409 EMAIL_ALREADY_EXISTS       Email already registered
422 VALIDATION_ERROR           Invalid request body
```

---

### POST /auth/login
Authenticate user, return access token, set refresh cookie.

**Access:** Public

**Request Body**
```json
{
  "email": "dr.rajesh@smilecare.com",
  "password": "yourpassword"
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "full_name": "Dr. Rajesh Kumar",
      "email": "dr.rajesh@smilecare.com",
      "role": "clinic_owner",
      "clinic_id": "uuid",
      "permissions": ["appointment:write", "patient:read"]
    }
  }
}
```

**Set-Cookie (HttpOnly)**
```
refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh
```

**Errors**
```
401 INVALID_CREDENTIALS        Wrong email or password
403 ACCOUNT_INACTIVE           Account disabled by owner
422 VALIDATION_ERROR           Invalid request body
```

---

### POST /auth/refresh
Issue a new access token using the refresh cookie.

**Access:** Public (requires valid refresh cookie)

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Token refreshed",
  "data": {
    "access_token": "eyJ...",
    "token_type": "bearer"
  }
}
```

**Errors**
```
401 REFRESH_TOKEN_MISSING      No refresh cookie present
401 REFRESH_TOKEN_INVALID      Token expired or tampered
401 REFRESH_TOKEN_EXPIRED      Token past expiry
```

---

### POST /auth/logout
Clear the refresh token cookie.

**Access:** Protected

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Logged out successfully",
  "data": null
}
```

**Clears Cookie:** `refresh_token`

---

### GET /auth/me
Get current authenticated user profile.

**Access:** Protected

**Response 200**
```json
{
  "success": true,
  "message": "Profile fetched",
  "data": {
    "id": "uuid",
    "full_name": "Dr. Rajesh Kumar",
    "email": "dr.rajesh@smilecare.com",
    "role": "clinic_owner",
    "clinic_id": "uuid",
    "clinic_name": "SmileCare Dental",
    "permissions": ["appointment:write", "patient:read"],
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

---

## Module 2 — Clinic Settings

### GET /clinic/settings
Fetch current clinic settings.

**Access:** Protected | Permission: `clinic:settings:read`

**Response 200**
```json
{
  "success": true,
  "message": "Clinic settings fetched",
  "data": {
    "id": "uuid",
    "name": "SmileCare Dental",
    "dentist_name": "Dr. Rajesh Kumar",
    "dentist_reg_id": "MCI-2024-12345",
    "gst_number": "27AAPFU0939F1ZV",
    "phone": "9876543210",
    "address": "123 Main Street, Mumbai",
    "operating_hours": {
      "monday":    { "open": "09:00", "close": "18:00", "is_closed": false },
      "tuesday":   { "open": "09:00", "close": "18:00", "is_closed": false },
      "wednesday": { "open": "09:00", "close": "18:00", "is_closed": false },
      "thursday":  { "open": "09:00", "close": "18:00", "is_closed": false },
      "friday":    { "open": "09:00", "close": "18:00", "is_closed": false },
      "saturday":  { "open": "09:00", "close": "14:00", "is_closed": false },
      "sunday":    { "open": null,    "close": null,    "is_closed": true  }
    },
    "locked_fields": ["name", "dentist_name", "dentist_reg_id", "gst_number"]
  }
}
```

---

### PATCH /clinic/settings
Update allowed clinic settings. Locked fields silently ignored or rejected.

**Access:** Protected | Permission: `clinic:settings:write` | Role: `clinic_owner` only

**Request Body** (all fields optional — send only what changes)
```json
{
  "phone": "9876543210",
  "address": "New Address, Mumbai",
  "operating_hours": {
    "monday": { "open": "10:00", "close": "19:00", "is_closed": false },
    "sunday": { "open": null, "close": null, "is_closed": true }
  }
}
```

**Fields That Cannot Be Sent (will return error if attempted)**
```
name, dentist_name, dentist_reg_id, gst_number
```

**Response 200**
```json
{
  "success": true,
  "message": "Clinic settings updated",
  "data": {
    "updated_fields": ["phone", "operating_hours"]
  }
}
```

**Errors**
```
400 LOCKED_FIELD_MODIFICATION  Attempt to edit a locked field
403 FORBIDDEN                  Not clinic owner
422 VALIDATION_ERROR           Invalid time format or day key
```

---

### GET /clinic/staff
List all staff members in the clinic.

**Access:** Protected | Permission: `clinic:staff:manage` | Role: `clinic_owner` only

**Response 200**
```json
{
  "success": true,
  "message": "Staff list fetched",
  "data": {
    "items": [
      {
        "id": "uuid",
        "full_name": "Priya Sharma",
        "email": "priya@smilecare.com",
        "role": "assistant",
        "is_active": true,
        "permissions": ["appointment:write", "patient:read"],
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 3
  }
}
```

---

### POST /clinic/staff
Add a new staff member to the clinic.

**Access:** Protected | Permission: `clinic:staff:manage` | Role: `clinic_owner` only

**Request Body**
```json
{
  "full_name": "Priya Sharma",
  "email": "priya@smilecare.com",
  "password": "TempPassword123",
  "role": "assistant",
  "permissions": ["appointment:write", "appointment:cancel", "patient:read"]
}
```

**Validation Rules**
```
full_name     required, string, 2–100 chars
email         required, valid email, unique globally
password      required, min 8 chars
role          required, enum: assistant|receptionist|helper|compounder|other
permissions   required, array of valid permission strings
```

**Response 201**
```json
{
  "success": true,
  "message": "Staff member added",
  "data": {
    "id": "uuid",
    "full_name": "Priya Sharma",
    "email": "priya@smilecare.com",
    "role": "assistant",
    "permissions": ["appointment:write", "appointment:cancel", "patient:read"]
  }
}
```

**Errors**
```
409 EMAIL_ALREADY_EXISTS       Email already registered
400 INVALID_PERMISSION         Permission string not recognized
422 VALIDATION_ERROR           Invalid request body
```

---

### PATCH /clinic/staff/{staff_id}/permissions
Update a staff member's permissions.

**Access:** Protected | Permission: `clinic:staff:manage` | Role: `clinic_owner` only

**Path Params**
```
staff_id    uuid    required
```

**Request Body**
```json
{
  "permissions": ["appointment:write", "patient:read", "appointment:cancel"]
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Staff permissions updated",
  "data": {
    "id": "uuid",
    "full_name": "Priya Sharma",
    "permissions": ["appointment:write", "patient:read", "appointment:cancel"]
  }
}
```

**Errors**
```
404 STAFF_NOT_FOUND            Staff not in this clinic
400 INVALID_PERMISSION         Permission string not recognized
```

---

### DELETE /clinic/staff/{staff_id}
Remove a staff member from the clinic (soft deactivate).

**Access:** Protected | Permission: `clinic:staff:manage` | Role: `clinic_owner` only

**Path Params**
```
staff_id    uuid    required
```

**Response 200**
```json
{
  "success": true,
  "message": "Staff member removed",
  "data": null
}
```

**Errors**
```
404 STAFF_NOT_FOUND            Staff not in this clinic
400 CANNOT_REMOVE_OWNER        Cannot remove clinic owner
```

---

## Module 3 — Appointments

### POST /appointments
Create a new appointment.

**Access:** Protected | Permission: `appointment:write`

**Request Body**
```json
{
  "patient_id": "uuid",
  "appointment_type": "new",
  "scheduled_date": "2024-06-15",
  "scheduled_time_slot": "10:00",
  "notes": "Patient complains of tooth pain",
  "parent_appointment_id": null
}
```

**Field Rules**
```
patient_id               required, must exist in same clinic
appointment_type         required, enum: new|existing|follow_up
scheduled_date           required, YYYY-MM-DD, cannot be past
scheduled_time_slot      required, HH:MM (24hr)
notes                    optional, string, max 500 chars
parent_appointment_id    required if type=follow_up, must exist + same clinic
                         parent must have status != completed for follow_up link
```

**Response 201**
```json
{
  "success": true,
  "message": "Appointment created",
  "data": {
    "id": "uuid",
    "appointment_id": "APT-2024-00123",
    "patient_id": "uuid",
    "patient_name": "Rahul Mehta",
    "appointment_type": "new",
    "status": "pending",
    "scheduled_date": "2024-06-15",
    "scheduled_time_slot": "10:00",
    "queue_position": null,
    "notes": "Patient complains of tooth pain",
    "parent_appointment_id": null,
    "created_by": "uuid",
    "created_at": "2024-06-14T08:30:00Z"
  }
}
```

**Errors**
```
404 PATIENT_NOT_FOUND               Patient not in this clinic
404 PARENT_APPOINTMENT_NOT_FOUND    Parent appointment not found
400 INVALID_FOLLOW_UP               Parent appointment status is completed
400 PAST_DATE                       Scheduled date is in the past
422 VALIDATION_ERROR                Invalid request body
```

---

### GET /appointments
List appointments with filters.

**Access:** Protected | Permission: `appointment:read`

**Query Params**
```
?status=pending|waiting|cancelled|no_show|completed
?date=2024-06-15                    exact date filter
?date_from=2024-06-01               range start
?date_to=2024-06-30                 range end
?patient_id=uuid                    filter by patient
?appointment_type=new|existing|follow_up
?search=Rahul                       search by patient name or appointment_id
?page=1
?per_page=20
```

**Response 200**
```json
{
  "success": true,
  "message": "Appointments fetched",
  "data": {
    "items": [
      {
        "id": "uuid",
        "appointment_id": "APT-2024-00123",
        "patient_id": "uuid",
        "patient_name": "Rahul Mehta",
        "appointment_type": "new",
        "status": "waiting",
        "scheduled_date": "2024-06-15",
        "scheduled_time_slot": "10:00",
        "queue_position": 3,
        "created_at": "2024-06-14T08:30:00Z"
      }
    ],
    "total": 45,
    "page": 1,
    "per_page": 20,
    "pages": 3
  }
}
```

---

### GET /appointments/queue
Get today's waiting queue in order.

**Access:** Protected | Permission: `appointment:read`

**Response 200**
```json
{
  "success": true,
  "message": "Queue fetched",
  "data": {
    "date": "2024-06-15",
    "total_waiting": 5,
    "items": [
      {
        "id": "uuid",
        "appointment_id": "APT-2024-00123",
        "queue_position": 1,
        "patient_name": "Rahul Mehta",
        "patient_age": 32,
        "appointment_type": "new",
        "scheduled_time_slot": "10:00",
        "status": "waiting",
        "notes": "Tooth pain"
      }
    ]
  }
}
```

---

### GET /appointments/{appointment_id}
Get single appointment detail.

**Access:** Protected | Permission: `appointment:read`

**Path Params**
```
appointment_id    uuid    required
```

**Response 200**
```json
{
  "success": true,
  "message": "Appointment fetched",
  "data": {
    "id": "uuid",
    "appointment_id": "APT-2024-00123",
    "patient": {
      "id": "uuid",
      "full_name": "Rahul Mehta",
      "age": 32,
      "phone": "9876543210"
    },
    "appointment_type": "new",
    "status": "waiting",
    "scheduled_date": "2024-06-15",
    "scheduled_time_slot": "10:00",
    "queue_position": 3,
    "notes": "Tooth pain",
    "parent_appointment_id": null,
    "created_by_name": "Priya Sharma",
    "cancelled_by_name": null,
    "created_at": "2024-06-14T08:30:00Z",
    "updated_at": "2024-06-15T09:00:00Z"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND      Not found or not in this clinic
```

---

### PATCH /appointments/{appointment_id}/confirm
Confirm appointment — move from pending to waiting, assign queue position.

**Access:** Protected | Permission: `appointment:write`

**Path Params**
```
appointment_id    uuid    required
```

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Appointment confirmed",
  "data": {
    "id": "uuid",
    "status": "waiting",
    "queue_position": 4,
    "scheduled_time_slot": "10:00"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND      Not found or not in this clinic
400 INVALID_STATUS_TRANSITION  Appointment is not in pending status
```

---

### PATCH /appointments/{appointment_id}/cancel
Cancel an appointment.

**Access:** Protected | Permission: `appointment:cancel`

**Request Body**
```json
{
  "reason": "Patient requested cancellation"
}
```

**Field Rules**
```
reason    optional, string, max 300 chars
```

**Response 200**
```json
{
  "success": true,
  "message": "Appointment cancelled",
  "data": {
    "id": "uuid",
    "status": "cancelled"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND      Not found or not in this clinic
400 INVALID_STATUS_TRANSITION  Cannot cancel completed or already cancelled
```

---

### PATCH /appointments/{appointment_id}/reschedule
Reschedule an appointment.

**Access:** Protected | Permission: `appointment:write`

**Request Body**
```json
{
  "scheduled_date": "2024-06-20",
  "scheduled_time_slot": "14:00"
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Appointment rescheduled",
  "data": {
    "id": "uuid",
    "status": "pending",
    "scheduled_date": "2024-06-20",
    "scheduled_time_slot": "14:00"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND      Not found or not in this clinic
400 INVALID_STATUS_TRANSITION  Cannot reschedule completed/cancelled/no_show
400 PAST_DATE                  Scheduled date is in the past
```

---

### PATCH /appointments/{appointment_id}/no-show
Mark appointment as no-show (manual trigger in MVP).

**Access:** Protected | Permission: `appointment:write`

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Appointment marked as no-show",
  "data": {
    "id": "uuid",
    "status": "no_show"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND      Not found or not in this clinic
400 INVALID_STATUS_TRANSITION  Only waiting appointments can be no-show
```

---

### PATCH /appointments/{appointment_id}/complete
Complete an appointment — dentist only, triggers consultation check.

**Access:** Protected | Permission: `appointment:complete` | Role: `clinic_owner` only

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Appointment completed",
  "data": {
    "id": "uuid",
    "status": "completed",
    "consultation_id": "uuid"
  }
}
```

**Errors**
```
404 APPOINTMENT_NOT_FOUND          Not found or not in this clinic
400 INVALID_STATUS_TRANSITION      Only waiting can be completed
400 CONSULTATION_NOT_SUBMITTED     Must submit consultation before completing
```

---

## Module 4 — Patients

### POST /patients
Register a new patient.

**Access:** Protected | Permission: `patient:write`

**Request Body**
```json
{
  "full_name": "Rahul Mehta",
  "age": 32,
  "phone": "9876543210",
  "email": "rahul@example.com"
}
```

**Validation Rules**
```
full_name    required, string, 2–100 chars
age          required, integer, 1–120
phone        optional, string, max 15 chars
email        optional, valid email
```

**Response 201**
```json
{
  "success": true,
  "message": "Patient registered",
  "data": {
    "id": "uuid",
    "patient_id": "PAT-2024-00456",
    "full_name": "Rahul Mehta",
    "age": 32,
    "phone": "9876543210",
    "email": "rahul@example.com",
    "created_at": "2024-06-14T08:30:00Z"
  }
}
```

---

### GET /patients
Search and list patients.

**Access:** Protected | Permission: `patient:read`

**Query Params**
```
?search=Rahul              search by name, phone, or patient_id
?page=1
?per_page=20
```

**Response 200**
```json
{
  "success": true,
  "message": "Patients fetched",
  "data": {
    "items": [
      {
        "id": "uuid",
        "patient_id": "PAT-2024-00456",
        "full_name": "Rahul Mehta",
        "age": 32,
        "phone": "9876543210",
        "total_appointments": 5,
        "last_visit": "2024-05-20"
      }
    ],
    "total": 120,
    "page": 1,
    "per_page": 20,
    "pages": 6
  }
}
```

---

### GET /patients/{patient_id}
Get patient detail.

**Access:** Protected | Permission: `patient:read`

**Response 200**
```json
{
  "success": true,
  "message": "Patient fetched",
  "data": {
    "id": "uuid",
    "patient_id": "PAT-2024-00456",
    "full_name": "Rahul Mehta",
    "age": 32,
    "phone": "9876543210",
    "email": "rahul@example.com",
    "total_appointments": 5,
    "last_visit": "2024-05-20",
    "created_at": "2024-01-10T00:00:00Z"
  }
}
```

**Errors**
```
404 PATIENT_NOT_FOUND    Not found or not in this clinic
```

---

### PATCH /patients/{patient_id}
Edit patient contact information.

**Access:** Protected | Permission: `patient:write`

**Request Body** (all optional — send only what changes)
```json
{
  "phone": "9123456789",
  "email": "newemail@example.com",
  "age": 33
}
```

**Response 200**
```json
{
  "success": true,
  "message": "Patient updated",
  "data": {
    "id": "uuid",
    "full_name": "Rahul Mehta",
    "age": 33,
    "phone": "9123456789",
    "email": "newemail@example.com"
  }
}
```

---

### GET /patients/{patient_id}/appointments
Get full appointment history for a patient.

**Access:** Protected | Permission: `patient:read`

**Query Params**
```
?status=pending|waiting|cancelled|no_show|completed
?page=1
?per_page=20
```

**Response 200**
```json
{
  "success": true,
  "message": "Patient appointments fetched",
  "data": {
    "items": [
      {
        "id": "uuid",
        "appointment_id": "APT-2024-00123",
        "appointment_type": "new",
        "status": "completed",
        "scheduled_date": "2024-05-20",
        "scheduled_time_slot": "10:00"
      }
    ],
    "total": 5,
    "page": 1,
    "per_page": 20,
    "pages": 1
  }
}
```

---

### GET /patients/{patient_id}/consultations
Get all consultations for a patient.

**Access:** Protected | Permission: `patient:read`

**Response 200**
```json
{
  "success": true,
  "message": "Patient consultations fetched",
  "data": {
    "items": [
      {
        "id": "uuid",
        "appointment_id": "uuid",
        "appointment_date": "2024-05-20",
        "symptoms": "Tooth pain, sensitivity",
        "is_submitted": true,
        "submitted_at": "2024-05-20T11:30:00Z",
        "fee_charged": 500.00,
        "is_follow_up_required": true
      }
    ],
    "total": 3,
    "page": 1,
    "per_page": 20,
    "pages": 1
  }
}
```

---

## Module 5 — Consultations

### POST /patients/{patient_id}/consultations
Create a consultation draft. Called when dentist checks in a waiting patient.

**Access:** Protected | Permission: `consultation:write` | Role: `clinic_owner` only

**Path Params**
```
patient_id    uuid    required
```

**Request Body**
```json
{
  "appointment_id": "uuid",
  "symptoms": "Tooth pain in lower right molar",
  "clinical_notes": "Visible cavity on tooth 46",
  "fee_charged": 500.00,
  "is_follow_up_required": false,
  "follow_up_notes": null,
  "medications": [
    {
      "name": "Amoxicillin",
      "dosage": "500mg",
      "frequency": "3 times a day",
      "duration": "5 days",
      "instructions": "After food"
    }
  ]
}
```

**Validation Rules**
```
appointment_id          required, must belong to patient + same clinic, status=waiting
symptoms                optional, string, max 1000 chars
clinical_notes          optional, string, max 2000 chars
fee_charged             optional, decimal >= 0
is_follow_up_required   optional, boolean, default false
follow_up_notes         optional, string, max 500 chars
medications             optional, array
  name                  required per medication
  dosage                required per medication
  frequency             optional
  duration              optional
  instructions          optional
```

**Response 201**
```json
{
  "success": true,
  "message": "Consultation draft created",
  "data": {
    "id": "uuid",
    "appointment_id": "uuid",
    "patient_id": "uuid",
    "symptoms": "Tooth pain in lower right molar",
    "clinical_notes": "Visible cavity on tooth 46",
    "fee_charged": 500.00,
    "is_follow_up_required": false,
    "follow_up_notes": null,
    "is_submitted": false,
    "medications": [
      {
        "id": "uuid",
        "name": "Amoxicillin",
        "dosage": "500mg",
        "frequency": "3 times a day",
        "duration": "5 days",
        "instructions": "After food"
      }
    ],
    "created_at": "2024-06-15T10:00:00Z"
  }
}
```

**Errors**
```
404 PATIENT_NOT_FOUND              Patient not in clinic
404 APPOINTMENT_NOT_FOUND          Appointment not found
400 APPOINTMENT_NOT_WAITING        Appointment must be in waiting status
400 CONSULTATION_ALREADY_EXISTS    Draft already created for this appointment
```

---

### PATCH /patients/{patient_id}/consultations/{consultation_id}
Update a draft consultation. Cannot update after submission.

**Access:** Protected | Permission: `consultation:write` | Role: `clinic_owner` only

**Request Body** (all optional — send only what changes)
```json
{
  "symptoms": "Updated symptoms",
  "clinical_notes": "Updated notes",
  "fee_charged": 750.00,
  "is_follow_up_required": true,
  "follow_up_notes": "Review in 1 week",
  "medications": [
    {
      "name": "Ibuprofen",
      "dosage": "400mg",
      "frequency": "Twice a day",
      "duration": "3 days",
      "instructions": "After food"
    }
  ]
}
```

**Note:** Sending `medications` replaces the entire medication list for this consultation.

**Response 200**
```json
{
  "success": true,
  "message": "Consultation updated",
  "data": {
    "id": "uuid",
    "is_submitted": false,
    "updated_at": "2024-06-15T10:45:00Z"
  }
}
```

**Errors**
```
404 CONSULTATION_NOT_FOUND     Not found or not in this clinic
400 CONSULTATION_LOCKED        Consultation already submitted — cannot edit
```

---

### POST /patients/{patient_id}/consultations/{consultation_id}/submit
Submit and lock the consultation. Triggers appointment completion.

**Access:** Protected | Permission: `consultation:submit` | Role: `clinic_owner` only

**Request Body:** None

**Response 200**
```json
{
  "success": true,
  "message": "Consultation submitted",
  "data": {
    "id": "uuid",
    "is_submitted": true,
    "submitted_at": "2024-06-15T11:00:00Z",
    "appointment_status": "completed"
  }
}
```

**Errors**
```
404 CONSULTATION_NOT_FOUND     Not found or not in this clinic
400 CONSULTATION_LOCKED        Already submitted
```

---

### GET /patients/{patient_id}/consultations/{consultation_id}
Get full consultation detail.

**Access:** Protected | Permission: `patient:read`

**Response 200**
```json
{
  "success": true,
  "message": "Consultation fetched",
  "data": {
    "id": "uuid",
    "appointment_id": "uuid",
    "appointment_date": "2024-06-15",
    "dentist_name": "Dr. Rajesh Kumar",
    "symptoms": "Tooth pain in lower right molar",
    "clinical_notes": "Visible cavity on tooth 46",
    "fee_charged": 500.00,
    "is_follow_up_required": true,
    "follow_up_notes": "Review in 1 week",
    "is_submitted": true,
    "submitted_at": "2024-06-15T11:00:00Z",
    "medications": [
      {
        "id": "uuid",
        "name": "Amoxicillin",
        "dosage": "500mg",
        "frequency": "3 times a day",
        "duration": "5 days",
        "instructions": "After food"
      }
    ],
    "created_at": "2024-06-15T10:00:00Z"
  }
}
```

---

### GET /patients/{patient_id}/consultations/{consultation_id}/report
Download consultation PDF report.

**Access:** Protected | Permission: `patient:read`

**Response 200**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="consultation-APT-2024-00123.pdf"

<binary PDF data>
```

**Errors**
```
404 CONSULTATION_NOT_FOUND     Not found
400 CONSULTATION_NOT_SUBMITTED Cannot generate PDF for draft
```

---

## Module 6 — Analytics

All analytics endpoints:
- **Access:** Protected | Permission: `analytics:read` | Role: `clinic_owner` only
- **Clinic scoped:** Only returns data for the authenticated user's clinic

### Common Query Params (all analytics endpoints)
```
?period=today|yesterday|this_week|this_month    shorthand periods
?date_from=2024-06-01                           custom range start (YYYY-MM-DD)
?date_to=2024-06-30                             custom range end (YYYY-MM-DD)

Rules:
- period and date_from/date_to are mutually exclusive
- If neither provided, defaults to today
- date_from without date_to defaults to date_from → today
```

---

### GET /analytics/overview
Revenue, walk-ins, follow-up summary for the period.

**Response 200**
```json
{
  "success": true,
  "message": "Analytics overview fetched",
  "data": {
    "period": "this_month",
    "date_from": "2024-06-01",
    "date_to": "2024-06-30",
    "total_revenue": 45000.00,
    "total_appointments": 90,
    "total_walkins": 60,
    "total_followups": 30,
    "total_new_patients": 25,
    "total_returning_patients": 65,
    "total_cancelled": 5,
    "total_no_shows": 3,
    "completion_rate": 91.2
  }
}
```

---

### GET /analytics/appointments
Appointment volume and status breakdown.

**Response 200**
```json
{
  "success": true,
  "message": "Appointment analytics fetched",
  "data": {
    "period": "this_month",
    "date_from": "2024-06-01",
    "date_to": "2024-06-30",
    "total": 90,
    "by_status": {
      "pending": 2,
      "waiting": 3,
      "completed": 82,
      "cancelled": 2,
      "no_show": 1
    },
    "by_type": {
      "new": 25,
      "existing": 35,
      "follow_up": 30
    },
    "daily_breakdown": [
      {
        "date": "2024-06-01",
        "total": 6,
        "completed": 5,
        "cancelled": 1
      }
    ]
  }
}
```

---

### GET /analytics/revenue
Fee collection breakdown by period.

**Response 200**
```json
{
  "success": true,
  "message": "Revenue analytics fetched",
  "data": {
    "period": "this_month",
    "date_from": "2024-06-01",
    "date_to": "2024-06-30",
    "total_revenue": 45000.00,
    "average_per_appointment": 548.78,
    "daily_breakdown": [
      {
        "date": "2024-06-01",
        "revenue": 3000.00,
        "appointments": 6
      }
    ]
  }
}
```

---

### GET /analytics/patients
New vs returning patient counts for the period.

**Response 200**
```json
{
  "success": true,
  "message": "Patient analytics fetched",
  "data": {
    "period": "this_month",
    "date_from": "2024-06-01",
    "date_to": "2024-06-30",
    "total_unique_patients": 88,
    "new_patients": 25,
    "returning_patients": 63,
    "retention_rate": 71.6
  }
}
```

---

## Error Code Master List

| Code | HTTP Status | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `ACCOUNT_INACTIVE` | 403 | Account deactivated |
| `UNAUTHORIZED` | 401 | No valid auth token |
| `FORBIDDEN` | 403 | Valid token, insufficient permission |
| `REFRESH_TOKEN_MISSING` | 401 | No refresh cookie |
| `REFRESH_TOKEN_INVALID` | 401 | Tampered or malformed |
| `REFRESH_TOKEN_EXPIRED` | 401 | Refresh token past expiry |
| `EMAIL_ALREADY_EXISTS` | 409 | Email already registered |
| `LOCKED_FIELD_MODIFICATION` | 400 | Attempt to edit locked clinic field |
| `INVALID_PERMISSION` | 400 | Permission string not recognized |
| `STAFF_NOT_FOUND` | 404 | Staff not in this clinic |
| `CANNOT_REMOVE_OWNER` | 400 | Cannot remove clinic owner |
| `PATIENT_NOT_FOUND` | 404 | Patient not in this clinic |
| `APPOINTMENT_NOT_FOUND` | 404 | Appointment not in this clinic |
| `PARENT_APPOINTMENT_NOT_FOUND` | 404 | Parent appointment not found |
| `INVALID_FOLLOW_UP` | 400 | Parent appointment is completed |
| `PAST_DATE` | 400 | Scheduled date is in the past |
| `INVALID_STATUS_TRANSITION` | 400 | Status change not allowed |
| `APPOINTMENT_NOT_WAITING` | 400 | Appointment must be waiting to check in |
| `CONSULTATION_ALREADY_EXISTS` | 400 | Draft already exists for appointment |
| `CONSULTATION_NOT_FOUND` | 404 | Consultation not in this clinic |
| `CONSULTATION_LOCKED` | 400 | Cannot edit submitted consultation |
| `CONSULTATION_NOT_SUBMITTED` | 400 | Must submit before completing/PDF |
| `INTERNAL_SERVER_ERROR` | 500 | Unhandled server error |

---

## Stub Endpoints (POST-MVP — Return Mock Response)

These routes exist in the codebase but return stubbed responses in MVP:

```
POST /patients/{id}/consultations/{cid}/send-report
→ 200 { "success": true, "message": "STUB: WhatsApp send not active in MVP" }

POST /patients/{id}/follow-up
→ 200 { "success": true, "message": "STUB: Follow-up reminder not active in MVP" }
```