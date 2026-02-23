# MVP_TECH.md
# Dentist AI SaaS — MVP Technical Specification
> What we build. What we skip. What we stub. No ambiguity.

---

## 1. MVP Goal

Deliver a working, production-structured backend that supports:
- One clinic onboarding and operating end-to-end
- Role-based access for dentist + staff
- Full appointment lifecycle (book → queue → consult → complete)
- Patient record management
- Basic analytics
- A codebase that can scale into the full product without structural rewrites

**Not a prototype. Not throwaway code. MVP = lean but production-shaped.**

---

## 2. What Is IN the MVP

### 2.1 Authentication & Authorization
| Feature | Status |
|---|---|
| User registration (clinic owner self-signup) | ✅ MVP |
| User login — email + password | ✅ MVP |
| JWT Access Token (15 min expiry) | ✅ MVP |
| JWT Refresh Token via HttpOnly cookie (7 days) | ✅ MVP |
| Logout (clear refresh cookie) | ✅ MVP |
| RBAC — role-based permission enforcement on all routes | ✅ MVP |
| Clinic-scope isolation on every request | ✅ MVP |
| Password hashing with bcrypt | ✅ MVP |
| Refresh token blacklist | ❌ POST-MVP (Redis required) |
| OAuth / SSO | ❌ POST-MVP |

---

### 2.2 Clinic Management
| Feature | Status |
|---|---|
| Clinic record created on owner signup | ✅ MVP |
| Owner can view clinic settings | ✅ MVP |
| Owner can edit allowed fields (operating hours) | ✅ MVP |
| Locked fields (clinic name, GST, dentist name, reg ID) | ✅ MVP |
| Owner can add staff members | ✅ MVP |
| Owner can assign/edit staff permissions | ✅ MVP |
| Owner can remove staff | ✅ MVP |
| Multi-clinic support (one user, many clinics) | ❌ POST-MVP |

---

### 2.3 Appointment Management
| Feature | Status |
|---|---|
| Create appointment — new patient | ✅ MVP |
| Create appointment — existing patient | ✅ MVP |
| Create follow-up appointment (linked to parent) | ✅ MVP |
| Appointment status lifecycle (pending → waiting → completed) | ✅ MVP |
| Cancel appointment | ✅ MVP |
| No-show status — manual trigger | ✅ MVP |
| No-show status — automatic (system, time-based) | ❌ POST-MVP (Celery required) |
| Confirm appointment (pending → waiting) by assistant | ✅ MVP |
| Queue position + estimated time slot on waiting status | ✅ MVP |
| Reschedule appointment | ✅ MVP |
| Search appointments by name / appointment_id | ✅ MVP |
| WhatsApp booking by patient (self-serve) | ❌ POST-MVP |

---

### 2.4 Patient Management
| Feature | Status |
|---|---|
| Create new patient record | ✅ MVP |
| View patient record | ✅ MVP |
| Search patients (name, patient_id, phone) | ✅ MVP |
| View full appointment history per patient | ✅ MVP |
| View all consultations per patient | ✅ MVP |
| Edit patient contact info | ✅ MVP |

---

### 2.5 Consultation (Patient Consulting — Phase 3)
| Feature | Status |
|---|---|
| Dentist views waiting queue | ✅ MVP |
| Check-in patient (start consultation) | ✅ MVP |
| Consultation form — symptoms, notes, medications, fees | ✅ MVP |
| Save consultation as draft | ✅ MVP |
| Submit and lock consultation (waiting → completed) | ✅ MVP |
| Set follow-up flag on consultation | ✅ MVP |
| Lock consultation form after submission | ✅ MVP (⚠️ confirm enforcement level) |
| Generate PDF report | ✅ MVP |
| Send PDF to patient via WhatsApp | ❌ POST-MVP (WhatsApp integration) |
| Auto-schedule WhatsApp follow-up reminder | ❌ POST-MVP (Celery + WhatsApp) |

---

### 2.6 Analytics
| Feature | Status |
|---|---|
| Overview — revenue, walk-ins, follow-up counts | ✅ MVP |
| Filter by: today, yesterday, this week, this month | ✅ MVP |
| Filter by: custom date range | ✅ MVP |
| Appointment volume + status breakdown | ✅ MVP |
| Revenue breakdown by period | ✅ MVP |
| New vs returning patient counts | ✅ MVP |
| Export analytics as PDF/CSV | ❌ POST-MVP |

---

### 2.7 PDF Report Generation
| Feature | Status |
|---|---|
| Generate consultation/prescription PDF | ✅ MVP |
| Download PDF via API | ✅ MVP |
| Send PDF via WhatsApp | ❌ POST-MVP |
| Library | ⚠️ DECISION NEEDED (WeasyPrint or ReportLab) |

---

## 3. What Is NOT in the MVP

These are explicitly deferred. Code stubs exist where noted.

| Feature | Reason Deferred | Stub Exists? |
|---|---|---|
| WhatsApp integration (booking, reminders, reports) | External API setup, webhook handling | ✅ Stubbed |
| Celery task queue | Requires Redis + worker process | ✅ Config stubbed in comments |
| Redis (caching + token blacklist + task broker) | Infrastructure dependency | ✅ Config stubbed in comments |
| LangChain / AI features | Post-MVP feature set | ✅ Folder placeholder |
| Automatic no-show detection | Requires scheduled Celery task | ❌ Manual trigger only in MVP |
| Auto follow-up WhatsApp reminder | Requires Celery + WhatsApp | ❌ |
| Subscription/billing management | Third-party integration needed | ❌ |
| Multi-clinic user support | Scope increase | ❌ |
| Patient self-service portal | Frontend scope | ❌ |
| Analytics export (PDF/CSV) | Nice-to-have, not core | ❌ |
| Rate limiting | Add slowapi post-MVP | ❌ |
| Refresh token blacklist | Redis required | ❌ |
| Audit logging | Post-MVP compliance feature | ❌ |
| SMS / Email notifications | Channel expansion | ❌ |

---

## 4. MVP Dependencies

### Python Packages (requirements.txt)

```
# Core
fastapi
uvicorn[standard]
python-dotenv
pydantic[email]
pydantic-settings

# Database
sqlalchemy[asyncio]
asyncpg
alembic

# Auth
python-jose[cryptography]
passlib[bcrypt]

# HTTP
httpx

# PDF Generation
# ⚠️ DECISION NEEDED — uncomment one:
# weasyprint
# reportlab

# Dev / Testing
pytest
pytest-asyncio
httpx
```

### Infrastructure (MVP)
```
PostgreSQL     → primary database (v15+ recommended)
Redis          → NOT active in MVP (config stubbed)
```

### Infrastructure (Post-MVP additions)
```
Redis          → task broker, token blacklist, caching
Celery worker  → background tasks
WhatsApp API   → Meta Cloud API or Twilio (decision needed)
```

---

## 5. API Surface — MVP Endpoints

All routes prefixed: `/api/v1/`

### Auth
```
POST   /api/v1/auth/register          → clinic owner signup
POST   /api/v1/auth/login             → returns access token, sets refresh cookie
POST   /api/v1/auth/refresh           → issues new access token via refresh cookie
POST   /api/v1/auth/logout            → clears refresh cookie
GET    /api/v1/auth/me                → current user profile
```

### Clinic Settings (Owner only)
```
GET    /api/v1/clinic/settings        → fetch clinic settings
PATCH  /api/v1/clinic/settings        → edit allowed fields only
GET    /api/v1/clinic/staff           → list all staff
POST   /api/v1/clinic/staff           → add staff member
PATCH  /api/v1/clinic/staff/{id}/permissions  → update staff permissions
DELETE /api/v1/clinic/staff/{id}      → remove staff member
```

### Appointments
```
POST   /api/v1/appointments/                        → create appointment
GET    /api/v1/appointments/                        → list (filterable: status, date, patient)
GET    /api/v1/appointments/{id}                    → get appointment detail
PATCH  /api/v1/appointments/{id}/confirm            → pending → waiting
PATCH  /api/v1/appointments/{id}/cancel             → cancel appointment
PATCH  /api/v1/appointments/{id}/reschedule         → reschedule appointment
PATCH  /api/v1/appointments/{id}/no-show            → mark as no-show (manual, MVP)
PATCH  /api/v1/appointments/{id}/complete           → waiting → completed (dentist only)
GET    /api/v1/appointments/queue                   → today's waiting queue (ordered)
```

### Patients
```
POST   /api/v1/patients/              → register new patient
GET    /api/v1/patients/              → search/list patients
GET    /api/v1/patients/{id}          → patient detail
PATCH  /api/v1/patients/{id}          → edit patient contact info
GET    /api/v1/patients/{id}/appointments   → full appointment history
GET    /api/v1/patients/{id}/consultations  → all consultations
```

### Consultations
```
POST   /api/v1/patients/{id}/consultations/              → create (draft) consultation
PATCH  /api/v1/patients/{id}/consultations/{cid}         → update draft
POST   /api/v1/patients/{id}/consultations/{cid}/submit  → lock and submit
GET    /api/v1/patients/{id}/consultations/{cid}         → get consultation detail
GET    /api/v1/patients/{id}/consultations/{cid}/report  → download PDF report
```

### Analytics (Dentist only)
```
GET    /api/v1/analytics/overview       → revenue, walk-ins, follow-ups
GET    /api/v1/analytics/appointments   → volume + status breakdown
GET    /api/v1/analytics/revenue        → fee collection by period
GET    /api/v1/analytics/patients       → new vs returning

Query params for all analytics:
  ?period=today|yesterday|this_week|this_month
  ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
```

---

## 6. Data Models — MVP (Conceptual)

### Clinic
```
id, name, gst_number, dentist_name, dentist_reg_id   ← LOCKED fields
operating_hours, phone, address                       ← EDITABLE fields
created_at, updated_at
```

### User (Staff + Dentist)
```
id, clinic_id, full_name, email, hashed_password
role (clinic_owner | assistant | receptionist | helper | compounder | other)
is_active
created_at, updated_at
```

### UserPermission
```
id, user_id, clinic_id, permission (string)
```

### Patient
```
id, clinic_id
full_name, age, phone (optional), email (optional)
created_at, updated_at, deleted_at (soft delete)
```

### Appointment
```
id, clinic_id, patient_id
appointment_type (new | existing | follow_up)
parent_appointment_id (nullable — for follow-ups)
status (pending | waiting | cancelled | no_show | completed)
queue_position (nullable — set when status = waiting)
scheduled_date, scheduled_time_slot
notes (pre-consultation, optional)
created_by (user_id), cancelled_by (user_id, nullable)
created_at, updated_at
```

### Consultation
```
id, appointment_id, clinic_id, patient_id
dentist_id (user_id)
symptoms, clinical_notes
fee_charged (decimal)
is_follow_up_required (boolean)
follow_up_notes (nullable)
is_submitted (boolean) ← locks the form
submitted_at (nullable)
created_at, updated_at
```

### Medication (within Consultation)
```
id, consultation_id
name, dosage, frequency, duration, instructions
```

---

## 7. Appointment Status — State Machine

```
                   ┌─────────────────┐
                   │     PENDING     │  ← created (patient booked / assistant created)
                   └────────┬────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ WAITING  │  │CANCELLED │  │RESCHEDULED│
        │(confirmed│  │          │  │(new appt  │
        │ in queue)│  │          │  │ created)  │
        └────┬─────┘  └──────────┘  └──────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
┌──────────┐   ┌──────────┐
│COMPLETED │   │ NO_SHOW  │
│(dentist  │   │(manual   │
│ only)    │   │ MVP /    │
│          │   │ auto     │
│          │   │ post-MVP)│
└──────────┘   └──────────┘
```

### Transition Rules
| From | To | Who |
|---|---|---|
| pending | waiting | assistant / dentist |
| pending | cancelled | assistant / dentist / patient |
| pending | rescheduled | assistant / dentist |
| waiting | completed | dentist only |
| waiting | cancelled | assistant / dentist |
| waiting | no_show | assistant / dentist (manual, MVP) |
| completed | — | LOCKED — no transitions |
| cancelled | — | LOCKED — no transitions |
| no_show | — | LOCKED — no transitions |

---

## 8. Configuration & Environment

### Environment Variables Required (MVP)

```bash
# App
APP_ENV=development                    # development | staging | production
APP_SECRET_KEY=your-secret-key-here
APP_DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dentist_db

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (production only — dev allows all)
ALLOWED_ORIGINS=https://yourfrontend.com

# PDF
PDF_STORAGE_PATH=./storage/reports

# Redis (POST-MVP — keep in .env.example, unused in MVP)
# REDIS_URL=redis://localhost:6379/0

# Celery (POST-MVP — keep in .env.example, unused in MVP)
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0

# WhatsApp (POST-MVP — stubbed)
# WHATSAPP_API_URL=
# WHATSAPP_TOKEN=
# WHATSAPP_PHONE_NUMBER_ID=
```

### CORS Behavior by Environment
```
development  → origins=["*"], allow all methods, allow all headers
staging      → origins=[ALLOWED_ORIGINS], strict
production   → origins=[ALLOWED_ORIGINS], strict, HTTPS only
```

---

## 9. Development Setup (Local)

```bash
# 1. Clone repo
git clone <repo>
cd dentist-saas

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your local DB credentials

# 5. Start PostgreSQL (Docker recommended, but not now for MVP)
docker-compose up -d db

# 6. Run migrations
alembic upgrade head

# 7. Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 8. API Docs (auto-generated)
# http://localhost:8000/docs      ← Swagger UI
# http://localhost:8000/redoc     ← ReDoc
```

---

## 10. Testing Strategy (MVP)

### What We Test in MVP
- Auth endpoints (register, login, refresh, logout)
- RBAC — assert that wrong roles get 403
- Clinic isolation — assert that clinic A cannot access clinic B data
- Appointment state machine — assert invalid transitions are rejected
- Consultation lock — assert submitted consultation cannot be edited

### Testing Stack
```
pytest
pytest-asyncio
httpx (async test client)
```

### Test DB
- Separate test database.
- Migrations run before test suite.
- Each test runs in a transaction that is rolled back after.

---

## 11. Open Decisions Blocking MVP

These must be resolved before the relevant module is built:

| # | Decision | Blocks |
|---|---|---|
| 1 | PDF library — WeasyPrint or ReportLab? | Consultation PDF generation |
| 2 | WhatsApp provider — Meta Cloud API or Twilio? | Post-MVP but stub must target correct API shape |
| 3 | Consultation form lock — hard lock (no edit at all) or soft lock (dentist can unlock with log)? | Consultation submit flow |
| 4 | Patient search for assistant — include name + appointment_id search in MVP? | Appointment search endpoint |
| 5 | Billing/subscription — internal or third-party (Razorpay / Stripe)? | Post-MVP but architecture decision needed now |
| 6 | File storage for PDFs — local filesystem (MVP) or S3-compatible from day one? | PDF storage path config |

---

## 12. MVP Completion Checklist

### Foundation
- [ ] Project structure created
- [ ] FastAPI app bootstrapped
- [ ] Environment config (dev/staging/prod) working
- [ ] CORS middleware configured (env-aware)
- [ ] Database connected (async SQLAlchemy)
- [ ] Alembic migrations initialized
- [ ] Global error handler registered
- [ ] Structured logging configured

### Auth Module
- [ ] User registration
- [ ] Login + JWT access token
- [ ] Refresh token (HttpOnly cookie)
- [ ] Logout
- [ ] RBAC dependency working
- [ ] Clinic-scope enforcement working

### Clinic Module
- [ ] Clinic settings GET/PATCH
- [ ] Locked field enforcement
- [ ] Staff CRUD
- [ ] Staff permission assignment

### Appointment Module
- [ ] Create appointment (new / existing / follow-up)
- [ ] List + filter appointments
- [ ] Status transitions (all valid paths)
- [ ] Queue endpoint
- [ ] Search by name / appointment_id

### Patient Module
- [ ] Create patient
- [ ] Search patients
- [ ] Patient detail + history

### Consultation Module
- [ ] Create draft
- [ ] Update draft
- [ ] Submit + lock
- [ ] PDF generation (⚠️ depends on library decision)

### Analytics Module
- [ ] Overview endpoint
- [ ] All filter periods working
- [ ] Revenue, appointment, patient endpoints

### Quality
- [ ] All endpoints documented via FastAPI OpenAPI
- [ ] Core test coverage (auth, RBAC, state machine, clinic isolation)
- [ ] .env.example complete
- [ ] README with setup instructions
