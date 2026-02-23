# DEVELOPMENT_PHASES.md
# Dentist AI SaaS — Backend Build Plan
> Phased, ordered, reviewable. Every phase builds on the last.

---

## How to Use This Document

- Build phases are sequential — do not skip ahead.
- Each phase ends with a **Done Gate** — a set of verifiable checks that must pass before moving forward.
- Stubbed files (Celery, WhatsApp, LangChain) are created with stub headers in Phase 1 and never touched again in MVP.
- All code must follow `NAMING_CONVENTION.md` before being committed.

---

## Phase 1 — Project Foundation & Configuration

**Goal:** Bootstrapped FastAPI app. Runnable. Config validated. DB connected. No business logic yet.

### 1.1 Repo & Directory Structure
- Create full folder tree per `PROJECT_STRUCTURE.md`
- Add `__init__.py` to every Python package
- Create `storage/reports/.gitkeep` and `storage/temp/.gitkeep`
- Add `.gitignore` (standard Python + `.env`)

### 1.2 Dependencies
- Write `requirements.txt` with all MVP dependencies:
  - `fastapi`, `uvicorn[standard]`, `python-dotenv`, `pydantic[email]`, `pydantic-settings`
  - `sqlalchemy[asyncio]`, `asyncpg`, `alembic`
  - `python-jose[cryptography]`, `passlib[bcrypt]`
  - `httpx`
  - *(PDF library TBD — leave comment placeholder)*
- Write `requirements-dev.txt`: `pytest`, `pytest-asyncio`, `httpx`

### 1.3 Environment Configuration (`app/core/config.py`)
- Implement `Settings` class using `pydantic-settings` `BaseSettings`
- All env vars validated at startup — app refuses to start if missing
- Required vars: `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- Optional/post-MVP vars: `REDIS_URL`, `CELERY_BROKER_URL`, `WHATSAPP_TOKEN`, etc.
- `CORS_ALLOWED_ORIGINS` parsed as a list from comma-separated string

### 1.4 `.env.example`
- Document every env var from config.py with placeholder values
- Include all MVP and post-MVP vars (post-MVP ones commented out)

### 1.5 Database Layer (`app/database/`)
- `base.py` — `DeclarativeBase`, shared `metadata`
- `session.py` — async engine (`create_async_engine`), `AsyncSessionLocal`, `get_db` dependency
- `mixins.py` — `TimestampMixin` (`created_at`, `updated_at` auto-managed), `SoftDeleteMixin` (`deleted_at`)

### 1.6 FastAPI App Entry Point (`app/main.py`)
- Create FastAPI app instance with title, version, openapi_url
- Register CORS middleware (env-aware: open in dev, strict in staging/prod)
- Register global exception handlers (from `app/core/error_handlers.py`)
- Include master router (`app/api/router.py`)
- Add startup event: log app env + confirm DB connection
- No routes yet — health check only: `GET /health → 200 OK`

### 1.7 Logging (`app/core/logging.py`)
- Structured JSON logging in production (`APP_ENV=production`)
- Human-readable `uvicorn`-style logging in development
- Log level: `DEBUG` in dev, `INFO` in staging/prod
- Sensitive fields (passwords, tokens) never logged

### 1.8 Constants Layer (`app/constants/`)
- `appointment.py` — `AppointmentStatus(str, Enum)`, `AppointmentType(str, Enum)`
- `roles.py` — `MemberRole(str, Enum)`
- `messages.py` — all 47 error code constants from `ERROR_CODES.md`

### 1.9 Exception Hierarchy (`app/core/exceptions.py` + `app/core/error_handlers.py`)
- `AppException` base class with `code`, `message`, `http_status`, `detail`
- Subclasses: `AuthException`, `ForbiddenException`, `NotFoundException`, `ConflictException`, `ValidationException`, `ServerException`
- Global error handlers map every exception type to the standard error response envelope
- `detail` is `null` in production, populated in development

### 1.10 Stub Files (Post-MVP — one-time setup)
- Create stub files per `PROJECT_STRUCTURE.md` with the standard stub header comment:
  - `app/services/whatsapp_service.py`
  - `app/tasks/celery_app.py`
  - `app/tasks/appointment_tasks.py`
  - `app/tasks/whatsapp_tasks.py`
  - `app/integrations/whatsapp/client.py`
  - `app/integrations/whatsapp/templates.py`

### 1.11 Docker & Alembic Bootstrap
- `Dockerfile` — multi-stage (dev + prod targets)
- `docker-compose.yml` — app + postgres (redis service commented out)
- `alembic.ini` and `alembic/env.py` — async SQLAlchemy setup

### ✅ Phase 1 Done Gate
- [ ] `uvicorn app.main:app --reload` starts without errors
- [ ] `GET /health` returns `200 OK`
- [ ] Missing env var causes startup failure with clear error message
- [ ] `GET /docs` shows Swagger UI (no routes yet except health)
- [ ] CORS is open in `development`, restricted in `production` (verify config logic)

---

## Phase 2 — Database Models & Migrations

**Goal:** All 9 tables defined as SQLAlchemy models. First Alembic migration committed and applied.

### 2.1 Models (`app/models/`)

Build in dependency order (FK references must exist before being referenced):

1. **`user.py`** — `User` model
   - `id` (UUID PK), `email` (unique), `hashed_password`, `is_active`, `is_verified`, `last_login_at`, timestamps

2. **`clinic.py`** — `Clinic` model
   - `id`, `name`, `gst_number`, `dentist_name`, `dentist_reg_id` (locked fields)
   - `phone`, `email`, `address`, `city`, `state`, `pincode` (editable)
   - `operating_hours` (JSONB), `status` (`clinic_status` enum)
   - `subscription_plan`, `subscription_expires_at` (post-MVP columns — exist now)

3. **`clinic_member.py`** — `ClinicMember` model
   - `id`, `user_id` (FK→users), `clinic_id` (FK→clinics)
   - `full_name`, `phone`, `role` (`member_role` enum)
   - `specialization`, `experience_years`, `profile_bio` (dentist-specific / post-MVP bio)
   - `is_active`, `deleted_at` (soft delete), timestamps

4. **`user_permission.py`** — `UserPermission` model
   - `id`, `clinic_member_id` (FK→clinic_members), `clinic_id` (FK→clinics)
   - `permission` (VARCHAR), `granted_by` (FK→clinic_members nullable), `granted_at`

5. **`patient.py`** — `Patient` model
   - `id`, `clinic_id` (FK→clinics), `patient_code` (unique per clinic)
   - `full_name`, `age`, `gender`, `phone`, `email`, `general_notes`
   - `deleted_at` (soft delete), timestamps

6. **`appointment.py`** — `Appointment` model
   - `id`, `clinic_id`, `patient_id`, `appointment_code`
   - `appointment_type`, `parent_appointment_id` (self-ref FK, nullable)
   - `status` (`appointment_status` enum), `queue_position`
   - `scheduled_date`, `scheduled_time_slot`, `notes`
   - `cancelled_reason`, `cancelled_at`
   - `created_by`, `confirmed_by`, `cancelled_by` (FK→clinic_members, nullable), `confirmed_at`
   - timestamps

7. **`consultation.py`** — `Consultation` model
   - `id`, `clinic_id`, `appointment_id` (unique FK), `patient_id`, `dentist_id`
   - `symptoms`, `clinical_notes`, `diagnosis` (TEXT, post-MVP structured)
   - `fee_charged` (DECIMAL 10,2), `is_follow_up_required`, `follow_up_notes`, `follow_up_days`
   - `is_submitted`, `submitted_at`
   - `report_generated`, `report_path`, `report_generated_at`
   - timestamps

8. **`medication.py`** — `Medication` model
   - `id`, `consultation_id` (FK, CASCADE), `clinic_id`
   - `name`, `dosage`, `frequency`, `duration`, `instructions`, `sort_order`
   - `created_at`

9. **`follow_up.py`** — `FollowUp` model
   - `id`, `clinic_id`, `patient_id`, `consultation_id`
   - `follow_up_appointment_id` (FK→appointments, nullable)
   - `follow_up_date`, `notes`, `status` (`follow_up_status` enum)
   - `reminder_sent_at`, `celery_task_id` (post-MVP columns)
   - timestamps

### 2.2 Models `__init__.py`
- Import all models so Alembic can autodiscover them

### 2.3 Alembic Migration
- Generate: `alembic revision --autogenerate -m "initial_schema"`
- Review autogenerated file — verify all enums, indexes, constraints match `DB_SCHEMA.md`
- Apply: `alembic upgrade head`

### ✅ Phase 2 Done Gate
- [ ] `alembic upgrade head` applies cleanly on a fresh DB
- [ ] All 9 tables exist with correct columns, types, and indexes
- [ ] All DB-level enums created: `clinic_status`, `member_role`, `appointment_type`, `appointment_status`, `follow_up_status`
- [ ] All FK relationships correct
- [ ] `alembic downgrade -1` reverses cleanly

---

## Phase 3 — RBAC Layer

**Goal:** Permission constants, RBAC dependencies, and `CurrentUser` injection all working before any business routes are built.

### 3.1 Permission Constants (`app/rbac/permissions.py`)
- Define all 12 permission string constants
- `OWNER_EXCLUSIVE_PERMISSIONS` list (6 strings)
- `ALL_PERMISSIONS` list (12 strings)

### 3.2 Role Definitions (`app/rbac/roles.py`)
- `OWNER_PERMISSIONS` — hardcoded full list (12 permissions)
- `RECOMMENDED_PERMISSIONS` dict — starter sets per staff role

### 3.3 CurrentUser Schema
- Define `CurrentUser` dataclass/Pydantic model:
  - `id` (UUID — clinic_member id), `user_id` (UUID — users table), `clinic_id` (UUID)
  - `full_name`, `role` (`MemberRole`), `permissions` (`list[str]`), `is_active`

### 3.4 RBAC Dependencies (`app/rbac/dependencies.py`)
- `get_current_user(token)` — validates JWT, loads `CurrentUser` from payload
- `require_permission(permission: str)` — returns a `Depends()` that checks single permission
- `require_permissions(permissions: list[str])` — requires all listed permissions
- `require_role(role: str)` — role check only (used for owner-only routes)
- All three levels of check: authenticated → permission → clinic scope

### 3.5 Core Security (`app/core/security.py`)
- `create_access_token(data, expires_delta)` — returns signed JWT
- `create_refresh_token(data)` — longer-lived JWT
- `decode_token(token)` — validates and returns payload (raises on invalid/expired)
- `hash_password(plain)` → bcrypt hash
- `verify_password(plain, hashed)` → bool

### ✅ Phase 3 Done Gate
- [ ] RBAC dependencies importable with no errors
- [ ] Unit test: valid token → `CurrentUser` injected correctly
- [ ] Unit test: expired/invalid token → `401 UNAUTHORIZED`
- [ ] Unit test: valid token, missing permission → `403 FORBIDDEN`
- [ ] Unit test: owner gets all 12 permissions from `OWNER_PERMISSIONS`

---

## Phase 4 — Auth Module

**Goal:** Registration, login, refresh, logout, and `/me` working end-to-end.

### 4.1 Schemas (`app/schemas/auth.py`)
- `RegisterRequest` — `clinic_name`, `full_name`, `email`, `password`, `phone`, `dentist_reg_id`
- `LoginRequest` — `email`, `password`
- `TokenResponse` — `access_token`, `token_type`
- `UserResponse` — `id`, `full_name`, `email`, `role`, `clinic_id`, `permissions`
- `RegisterResponse` — `user`, `clinic`, `access_token`, `token_type`
- `MeResponse` — full profile shape from API_CONTRACT.md

### 4.2 Repositories (`app/repositories/`)
- `base_repository.py` — `BaseRepository` with generic `get_by_id`, `create`, `update`
- `user_repository.py` — `get_by_email`, `create`, `update_last_login`
- `clinic_repository.py` (initial) — `create`, `get_by_id`
- `user_repository.py` — `get_clinic_member_by_user_clinic`, `create_clinic_member`
- (Add `get_permissions_by_member_id` for staff)

### 4.3 Auth Service (`app/services/auth_service.py`)
- `register_clinic(data)` — atomic: create user + clinic + clinic_member(owner) in one transaction
- `login(email, password)` — validate credentials, load permissions, issue tokens
- `refresh_access_token(refresh_token)` — validate refresh JWT, issue new access token
- `get_me(current_user)` — return full profile from DB + JWT payload

### 4.4 Auth Router (`app/api/v1/auth.py`)
- `POST /auth/register` → 201 `RegisterResponse`
- `POST /auth/login` → 200 `TokenResponse` + Set-Cookie `refresh_token` (HttpOnly)
- `POST /auth/refresh` → 200 `TokenResponse`
- `POST /auth/logout` → 200, clears `refresh_token` cookie
- `GET /auth/me` → 200 `MeResponse`

### 4.5 Master Router (`app/api/router.py`)
- Include auth router with prefix `/api/v1`

### ✅ Phase 4 Done Gate
- [ ] `POST /auth/register` creates user + clinic + clinic_member in DB; returns 201
- [ ] Email uniqueness enforced — 409 `EMAIL_ALREADY_EXISTS` on duplicate
- [ ] `POST /auth/login` returns access token + sets HttpOnly refresh cookie
- [ ] Wrong password → 401 `INVALID_CREDENTIALS`
- [ ] Inactive account → 403 `ACCOUNT_INACTIVE`
- [ ] `POST /auth/refresh` issues new access token using refresh cookie
- [ ] Missing/expired refresh cookie → 401 `REFRESH_TOKEN_MISSING` / `REFRESH_TOKEN_EXPIRED`
- [ ] `POST /auth/logout` clears cookie
- [ ] `GET /auth/me` returns full profile with permissions list
- [ ] Owner JWT payload contains all 12 permissions (loaded from hardcoded set, not DB)

---

## Phase 5 — Clinic Module

**Goal:** Clinic settings GET/PATCH and full staff CRUD working.

### 5.1 Schemas (`app/schemas/clinic.py`)
- `ClinicSettingsResponse` — full clinic settings shape with `locked_fields` list
- `ClinicSettingsUpdate` — only editable fields (`phone`, `email`, `address`, `city`, `state`, `pincode`, `operating_hours`)
- `OperatingHoursDay` — `{ open: str | None, close: str | None, is_closed: bool }`
- `StaffCreate` — `full_name`, `email`, `password`, `role`, `permissions`
- `StaffResponse` — `id`, `full_name`, `email`, `role`, `is_active`, `permissions`, `created_at`
- `StaffPermissionsUpdate` — `permissions: list[str]`

### 5.2 Repositories (`app/repositories/clinic_repository.py`)
- `get_clinic_by_id(clinic_id)`
- `update_clinic_settings(clinic_id, data)` — only editable fields
- `get_all_staff_by_clinic(clinic_id)` — excludes soft-deleted
- `get_staff_member_by_id(staff_id, clinic_id)`
- `create_staff_member(data, clinic_id)` — creates user + clinic_member + user_permissions
- `update_staff_permissions(staff_id, clinic_id, permissions)` — replaces all permissions
- `soft_delete_staff_member(staff_id, clinic_id)` — sets `deleted_at`

### 5.3 Clinic Service (`app/services/clinic_service.py`)
- `get_clinic_settings(clinic_id)` — fetches + returns with `locked_fields` list
- `update_clinic_settings(clinic_id, data)` — rejects locked fields with `LOCKED_FIELD_MODIFICATION`; validates operating hours format
- `list_staff(clinic_id)` — fetches staff with permission lists
- `add_staff_member(data, clinic_id, granted_by)` — validates permissions (no owner-exclusive); creates user + member + permissions atomically
- `update_staff_permissions(staff_id, clinic_id, permissions, granted_by)` — validates + replaces
- `remove_staff_member(staff_id, clinic_id)` — soft delete; rejects if role = `clinic_owner`

### 5.4 Clinic Router (`app/api/v1/clinic.py`)
- `GET /clinic/settings` — permission: `clinic:settings:read`
- `PATCH /clinic/settings` — permission: `clinic:settings:write` + role: `clinic_owner`
- `GET /clinic/staff` — permission: `clinic:staff:manage` + role: `clinic_owner`
- `POST /clinic/staff` — permission: `clinic:staff:manage` + role: `clinic_owner`
- `PATCH /clinic/staff/{staff_id}/permissions` — permission: `clinic:staff:manage`
- `DELETE /clinic/staff/{staff_id}` — permission: `clinic:staff:manage`

### ✅ Phase 5 Done Gate
- [ ] `GET /clinic/settings` returns full settings with `locked_fields` array
- [ ] `PATCH /clinic/settings` with a locked field (`name`) → 400 `LOCKED_FIELD_MODIFICATION`
- [ ] `PATCH /clinic/settings` with invalid operating hours time format → 400 `INVALID_OPERATING_HOURS`
- [ ] `POST /clinic/staff` creates user + clinic_member + permissions atomically
- [ ] `POST /clinic/staff` with owner-exclusive permission in list → 400 `OWNER_EXCLUSIVE_PERMISSION`
- [ ] `DELETE /clinic/staff/{owner_id}` → 400 `CANNOT_REMOVE_OWNER`
- [ ] Staff member can log in after being added
- [ ] Non-owner attempting clinic routes → 403 `FORBIDDEN`

---

## Phase 6 — Patient Module

**Goal:** Patient creation, search, detail, and history working.

### 6.1 Utilities (`app/utils/id_generator.py`)
- `generate_patient_code(clinic_id, db)` — `PAT-YYYY-NNNNN` format (auto-incrementing per clinic per year)
- `generate_appointment_code(clinic_id, db)` — `APT-YYYY-NNNNN` format (same logic)

### 6.2 Schemas (`app/schemas/patient.py`)
- `PatientCreate` — `full_name`, `age`, `phone` (optional), `email` (optional), `general_notes` (optional)
- `PatientUpdate` — `phone`, `email`, `age` (all optional)
- `PatientResponse` — full patient shape + `total_appointments`, `last_visit`
- `PatientListResponse` — paginated shape

### 6.3 Pagination Utilities (`app/utils/pagination.py`)
- `Paginator` helper — calculates `offset`, `pages`, returns `PaginatedResult`

### 6.4 Common Schemas (`app/schemas/common.py`)
- `SuccessResponse` — standard success envelope
- `PaginatedResponse` — `items`, `total`, `page`, `per_page`, `pages`

### 6.5 Repository (`app/repositories/patient_repository.py`)
- `create(clinic_id, data, patient_code)`
- `get_by_id(patient_id, clinic_id)` — excludes soft-deleted
- `get_all_by_clinic(clinic_id, search, page, per_page)` — full-text search on name + phone + patient_code filter
- `update(patient_id, clinic_id, data)`
- `exists_by_phone(clinic_id, phone)` — for duplicate phone check
- `count_appointments(patient_id, clinic_id)` → int
- `get_last_visit_date(patient_id, clinic_id)` → date | None

### 6.6 Service (`app/services/patient_service.py`)
- `create_patient(data, clinic_id)`
- `list_patients(clinic_id, search, page, per_page)`
- `get_patient(patient_id, clinic_id)` — 404 if not found
- `update_patient(patient_id, clinic_id, data)`

### 6.7 Router (`app/api/v1/patients.py`)
- `POST /patients` — permission: `patient:write` → 201
- `GET /patients` — permission: `patient:read` → paginated list
- `GET /patients/{patient_id}` — permission: `patient:read`
- `PATCH /patients/{patient_id}` — permission: `patient:write`
- `GET /patients/{patient_id}/appointments` — permission: `patient:read` → paginated (Phase 7)
- `GET /patients/{patient_id}/consultations` — permission: `patient:read` → paginated (Phase 8)

### ✅ Phase 6 Done Gate
- [ ] `POST /patients` creates patient with auto-generated `PAT-YYYY-NNNNN` code
- [ ] `GET /patients?search=Rahul` returns matching results
- [ ] `GET /patients?search=98765` searches by phone
- [ ] Patient code is unique per clinic — no duplicates possible
- [ ] `PATCH /patients/{id}` updates only provided fields
- [ ] Soft-deleted patient returns 404

---

## Phase 7 — Appointment Module

**Goal:** Full appointment lifecycle — create, list, queue, status transitions.

### 7.1 Schemas (`app/schemas/appointment.py`)
- `AppointmentCreate` — `patient_id`, `appointment_type`, `scheduled_date`, `scheduled_time_slot`, `notes` (opt), `parent_appointment_id` (opt)
- `AppointmentUpdate` — `scheduled_date`, `scheduled_time_slot` (for reschedule)
- `AppointmentResponse` — full single appointment shape
- `AppointmentListResponse` — paginated shape
- `AppointmentFilter` — query param model: `status`, `date`, `date_from`, `date_to`, `patient_id`, `appointment_type`, `search`
- `AppointmentCancelRequest` — `reason` (optional)
- `QueueResponse` — `date`, `total_waiting`, `items` list

### 7.2 Repository (`app/repositories/appointment_repository.py`)
- `create(data, clinic_id, appointment_code)`
- `get_by_id(appointment_id, clinic_id)`
- `get_all_by_clinic(clinic_id, filters, page, per_page)` — all filter combinations
- `get_queue(clinic_id, date)` — status=waiting, ordered by `queue_position`
- `get_next_queue_position(clinic_id, date)` → int
- `update_status(appointment_id, clinic_id, status, **kwargs)`
- `exists_by_code(clinic_id, code)` → bool

### 7.3 Service (`app/services/appointment_service.py`)
- `create_appointment(data, clinic_id, created_by)` — validates patient exists, validates follow-up parent, validates date not in past, generates code
- `list_appointments(clinic_id, filters, page, per_page)`
- `get_appointment(appointment_id, clinic_id)` — 404 if not found or wrong clinic
- `confirm_appointment(appointment_id, clinic_id, confirmed_by)` — `pending → waiting`, assigns queue position
- `cancel_appointment(appointment_id, clinic_id, cancelled_by, reason)` — validates transition
- `reschedule_appointment(appointment_id, clinic_id, date, time_slot)` — validates not completed/cancelled; resets to pending
- `mark_no_show(appointment_id, clinic_id)` — validates status=waiting
- `complete_appointment(appointment_id, clinic_id)` — validates consultation submitted first
- `get_queue(clinic_id)` — today's waiting queue

### 7.4 State Machine (enforced in service)
```
pending   → waiting    (confirm)         ✅
pending   → cancelled  (cancel)          ✅
pending   → pending    (reschedule)      ✅ (date/time changes, status stays pending)
waiting   → completed  (complete)        ✅ requires submitted consultation
waiting   → cancelled  (cancel)          ✅
waiting   → no_show    (mark_no_show)    ✅
completed → LOCKED     (any write)       ❌
cancelled → LOCKED     (any write)       ❌
no_show   → LOCKED     (any write)       ❌
```

### 7.5 Router (`app/api/v1/appointments.py`)
- `POST /appointments` — permission: `appointment:write`
- `GET /appointments` — permission: `appointment:read`
- `GET /appointments/queue` — permission: `appointment:read` *(register before `/{id}` route)*
- `GET /appointments/{appointment_id}` — permission: `appointment:read`
- `PATCH /appointments/{appointment_id}/confirm` — permission: `appointment:write`
- `PATCH /appointments/{appointment_id}/cancel` — permission: `appointment:cancel`
- `PATCH /appointments/{appointment_id}/reschedule` — permission: `appointment:write`
- `PATCH /appointments/{appointment_id}/no-show` — permission: `appointment:write`
- `PATCH /appointments/{appointment_id}/complete` — permission: `appointment:complete` + role: `clinic_owner`

Also add to patient router:
- `GET /patients/{patient_id}/appointments` — permission: `patient:read`

### ✅ Phase 7 Done Gate
- [ ] `POST /appointments` creates pending appointment with `APT-YYYY-NNNNN` code
- [ ] `GET /appointments?status=waiting&date=2024-06-15` filters correctly
- [ ] `GET /appointments?search=APT-2024-00123` finds by appointment code
- [ ] Confirm: `pending → waiting`, assigns incrementing queue position
- [ ] Double-confirm (waiting → confirm again) → 400 `APPOINTMENT_ALREADY_CONFIRMED`
- [ ] Reschedule: resets status to `pending`, updates date/time
- [ ] Reschedule completed/cancelled appointment → 400 `INVALID_STATUS_TRANSITION`
- [ ] Complete: only works if consultation is `is_submitted=true`
- [ ] Complete: assistant role → 403 `FORBIDDEN`
- [ ] `GET /appointments/queue` returns waiting list for today, ordered by `queue_position`
- [ ] Cancel with reason → reason stored in `cancelled_reason` + `cancelled_by` set
- [ ] `GET /patients/{id}/appointments` returns paginated history for that patient only

---

## Phase 8 — Consultation Module

**Goal:** Full consultation lifecycle — draft, update, submit, lock, and PDF download.

### 8.1 Open Decision Required
> ⚠️ **PDF Library Decision (from MVP_TECH_DOC.md item #1)**  
> Choose **WeasyPrint** or **ReportLab** before implementing PDF generation.  
> If undecided, build all consultation CRUD first (create/update/submit), and add PDF as the final sub-step of this phase.

### 8.2 Schemas (`app/schemas/consultation.py`)
- `MedicationCreate` — `name`, `dosage`, `frequency`, `duration`, `instructions`
- `MedicationResponse` — above + `id`
- `ConsultationCreate` — `appointment_id`, `symptoms`, `clinical_notes`, `fee_charged`, `is_follow_up_required`, `follow_up_notes`, medications list
- `ConsultationUpdate` — all fields optional; medications replace full list if provided
- `ConsultationResponse` — full consultation shape per API_CONTRACT.md
- `ConsultationListItem` — reduced shape for patient consultation history list

### 8.3 Repository (`app/repositories/consultation_repository.py`)
- `create(data, clinic_id, patient_id, dentist_id)`
- `get_by_id(consultation_id, clinic_id)`
- `get_by_appointment_id(appointment_id)`
- `get_all_by_patient(patient_id, clinic_id, page, per_page)`
- `update(consultation_id, data)` — replaces medications list if provided
- `submit(consultation_id)` — sets `is_submitted=True`, `submitted_at=now()`
- `update_report_path(consultation_id, path)` — post PDF generation

### 8.4 Service (`app/services/consultation_service.py`)
- `create_consultation(data, patient_id, clinic_id, dentist_id)` — validate appointment is `waiting`; validate no draft exists yet
- `update_consultation(consultation_id, data, clinic_id)` — reject if `is_submitted=True` (raise `CONSULTATION_LOCKED`)
- `submit_consultation(consultation_id, clinic_id)` — lock; auto-complete the linked appointment
- `get_consultation(consultation_id, clinic_id)` — 404 if not found
- `get_patient_consultations(patient_id, clinic_id, page, per_page)`
- `generate_pdf_report(consultation_id, clinic_id)` — calls `pdf_service.generate(...)`, stores path
- `get_pdf_report(consultation_id, clinic_id)` — returns file path; 404 if not generated; 400 if draft

### 8.5 PDF Service (`app/services/pdf_service.py`)
- `generate(consultation, patient, clinic, medications)` — build PDF from consultation data
- Save to `PDF_STORAGE_PATH/{clinic_id}/{appointment_code}.pdf`
- Returns saved file path
- Raise `REPORT_GENERATION_FAILED` on any exception

### 8.6 Router (`app/api/v1/consultations.py`)
- `POST /patients/{patient_id}/consultations` — permission: `consultation:write` + role: `clinic_owner`
- `PATCH /patients/{patient_id}/consultations/{consultation_id}` — permission: `consultation:write` + role: `clinic_owner`
- `POST /patients/{patient_id}/consultations/{consultation_id}/submit` — permission: `consultation:submit` + role: `clinic_owner`
- `GET /patients/{patient_id}/consultations/{consultation_id}` — permission: `patient:read`
- `GET /patients/{patient_id}/consultations/{consultation_id}/report` — permission: `patient:read`
  - Returns `FileResponse` (PDF binary) — not JSON
- **Stub Routes** (return mock success in MVP):
  - `POST .../send-report` → `{ "success": true, "message": "STUB: WhatsApp send not active in MVP" }`
  - `POST /patients/{id}/follow-up` → same stub response

Also add to patient router:
- `GET /patients/{patient_id}/consultations` — permission: `patient:read`

### ✅ Phase 8 Done Gate
- [ ] `POST .../consultations` creates draft with medications
- [ ] `PATCH .../consultations/{cid}` replaces medications list correctly
- [ ] `PATCH .../consultations/{cid}` on submitted consultation → 400 `CONSULTATION_LOCKED`
- [ ] `POST .../consultations/{cid}/submit` locks form + auto-completes linked appointment
- [ ] Double submit → 400 `CONSULTATION_LOCKED`
- [ ] `GET .../consultations/{cid}` returns full detail with medications and dentist name
- [ ] `GET .../consultations/{cid}/report` on draft → 400 `CONSULTATION_NOT_SUBMITTED`
- [ ] `GET .../consultations/{cid}/report` on submitted → returns PDF binary with correct headers
- [ ] Stub routes return stub response (not 404)
- [ ] Only `clinic_owner` role can create/update/submit consultation; assistant → 403

---

## Phase 9 — Analytics Module

**Goal:** All analytics endpoints working with period and date range filters.

### 9.1 Schemas (`app/schemas/analytics.py`)
- `AnalyticsFilter` — query param model: `period` (today/yesterday/this_week/this_month), `date_from`, `date_to`
- `AnalyticsOverviewResponse`, `AppointmentAnalyticsResponse`, `RevenueAnalyticsResponse`, `PatientAnalyticsResponse`
- Validation: `period` and `date_from/date_to` are mutually exclusive; `date_from` ≤ `date_to`

### 9.2 Date Utilities (`app/utils/datetime_utils.py`)
- `resolve_date_range(period, date_from, date_to)` → `(date_from, date_to)` tuple
- Handle `today`, `yesterday`, `this_week`, `this_month` → concrete date range
- Raise `INVALID_PERIOD` for unknown period strings
- Raise `INVALID_DATE_RANGE` if `date_from > date_to`
- Raise `PERIOD_AND_RANGE_CONFLICT` if both period and custom range provided

### 9.3 Repository (`app/repositories/analytics_repository.py`)
- `get_overview_metrics(clinic_id, date_from, date_to)` — total revenue, appointments, walk-ins, follow-ups, new/returning patients, cancelled, no-show, completion rate
- `get_appointment_stats(clinic_id, date_from, date_to)` — by_status, by_type, daily_breakdown
- `get_revenue_stats(clinic_id, date_from, date_to)` — total, average per appointment, daily breakdown
- `get_patient_stats(clinic_id, date_from, date_to)` — unique patients, new vs returning, retention rate

### 9.4 Service (`app/services/analytics_service.py`)
- `get_overview(clinic_id, filter)` → resolves date range → calls repository
- `get_appointment_analytics(clinic_id, filter)`
- `get_revenue_analytics(clinic_id, filter)`
- `get_patient_analytics(clinic_id, filter)`

### 9.5 Router (`app/api/v1/analytics.py`)
- `GET /analytics/overview` — permission: `analytics:read` + role: `clinic_owner`
- `GET /analytics/appointments` — same
- `GET /analytics/revenue` — same
- `GET /analytics/patients` — same

### ✅ Phase 9 Done Gate
- [ ] `?period=today` returns correct date-filtered data
- [ ] `?period=this_month` returns full month data
- [ ] `?date_from=2024-06-01&date_to=2024-06-30` returns custom range data
- [ ] `?period=today&date_from=2024-06-01` → 400 `PERIOD_AND_RANGE_CONFLICT`
- [ ] `?date_from=2024-07-01&date_to=2024-06-01` → 400 `INVALID_DATE_RANGE`
- [ ] Non-owner attempting analytics → 403 `FORBIDDEN`
- [ ] Completion rate = `completed / total_appointments * 100` (verify formula)
- [ ] New patient = no prior appointments in this clinic before the period

---

## Phase 10 — Quality, Testing & Seed Data

**Goal:** Tests passing. Dev environment seeded. README complete.

### 10.1 Test Infrastructure (`tests/conftest.py`)
- `async_session` fixture — test-only DB session
- `test_client` fixture — AsyncClient with app
- `clinic_owner_token` fixture — register clinic, return auth headers
- `staff_token` fixture — add staff member, return auth headers for them
- `test_patient` fixture — create patient in test clinic

### 10.2 Unit Tests (`tests/unit/`)
- `test_security.py` — JWT create/decode, password hash/verify
- `test_rbac.py` — permission checks, owner vs staff permissions
- `test_appointment_states.py` — state machine: verify all valid and invalid transitions
- `test_datetime_utils.py` — date range resolution for all period values

### 10.3 Integration Tests (`tests/integration/`)
- `test_auth.py` — register, login, refresh, logout, /me
- `test_clinic.py` — settings CRUD, staff CRUD, locked field enforcement
- `test_appointments.py` — full lifecycle: create → confirm → consult → complete
- `test_patients.py` — CRUD + search
- `test_consultations.py` — draft, update, submit, lock enforcement, PDF
- `test_analytics.py` — period filters, metric accuracy

### 10.4 RBAC Tests (`tests/rbac/`)
- `test_role_enforcement.py` — every owner-exclusive route returns 403 for staff
- `test_clinic_isolation.py` — Clinic A token cannot read Clinic B's patients/appointments

### 10.5 Seed Script (`scripts/seed_dev.py`)
- Create 1 test clinic + owner
- Create 2 staff members (assistant, receptionist) with recommended permissions
- Create 20 patients with realistic names
- Create appointments across various statuses (pending, waiting, completed, cancelled, no_show)
- Create consultations with medications for completed appointments
- Print login credentials to console

### 10.6 Documentation
- `README.md` — setup instructions, local dev, running tests, seeding DB
- `pytest.ini` — asyncio mode, test paths, markers
- Verify `GET /docs` and `GET /redoc` render correctly with all routes

### ✅ Phase 10 Done Gate
- [ ] `pytest tests/unit/` passes — all unit tests green
- [ ] `pytest tests/integration/` passes — all integration tests green
- [ ] `pytest tests/rbac/` passes — all isolation and role tests green
- [ ] `python scripts/seed_dev.py` seeds DB and prints credentials
- [ ] Login with seeded credentials works
- [ ] `GET /docs` shows all 30+ endpoints with correct schemas

---

## Phase Summary Table

| Phase | Focus | Key Outputs |
|---|---|---|
| 1 | Foundation | FastAPI app, config, logging, exceptions, stubs |
| 2 | Database | All 9 models + first Alembic migration |
| 3 | RBAC | Permission constants, dependencies, CurrentUser |
| 4 | Auth | Register, login, refresh, logout, /me |
| 5 | Clinic | Settings CRUD, staff CRUD, permission management |
| 6 | Patients | Create, search, detail, update |
| 7 | Appointments | Full lifecycle, state machine, queue |
| 8 | Consultations | Draft, submit, lock, PDF generation |
| 9 | Analytics | Revenue, appointment, patient metrics with filters |
| 10 | Quality | Tests, seed data, documentation |

---

## Open Decisions (Must Resolve Before Relevant Phase)

| # | Decision | Blocks | Default Suggestion |
|---|---|---|---|
| 1 | PDF library — WeasyPrint or ReportLab? | Phase 8 PDF step | ReportLab (simpler install, no system deps) |
| 2 | Consultation form lock — hard or soft? | Phase 8 submit logic | Hard lock (simpler, documented in MVP_TECH_DOC) |
| 3 | Patient phone uniqueness — enforced per clinic? | Phase 6 create | Warn but allow (not unique constraint per schema) |
| 4 | Patient search scope — name + phone + patient_code? | Phase 6 list | All three (specified in API_CONTRACT) |
| 5 | File storage (MVP) — local only | Phase 8 PDF | Local filesystem (`PDF_STORAGE_PATH`) |

---

## Post-MVP Stub Activation Checklist (Not Part of MVP Build)

The following are explicitly NOT built in any phase above.
Stubs are created in Phase 1 and left untouched.

- [ ] WhatsApp integration — `app/integrations/whatsapp/client.py`
- [ ] Celery task queue — `app/tasks/celery_app.py`
- [ ] Automatic no-show detection — `app/tasks/appointment_tasks.py`
- [ ] Auto follow-up WhatsApp reminder — `app/tasks/whatsapp_tasks.py`
- [ ] Refresh token blacklist (Redis)
- [ ] Rate limiting (slowapi)
- [ ] Audit logging
- [ ] Multi-clinic user support
- [ ] LangChain / AI features (`app/integrations/langchain/`)
