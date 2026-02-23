# PROJECT_STRUCTURE.md
# Dentist AI SaaS — Production Ready Project Structure
> Every file named. Every folder explained. No guessing.

---

## Root Structure

```
dentist-saas/
│
├── app/                          # All application source code lives here
├── tests/                        # All tests — mirrors app/ structure
├── alembic/                      # Database migrations
├── storage/                      # Local file storage (PDF reports etc.)
├── scripts/                      # Utility scripts (seed, maintenance etc.)
├── docker/                       # Docker related files
│
├── .env                          # Local environment variables — NEVER commit
├── .env.example                  # Template — ALWAYS commit
├── .gitignore                    # Standard Python + project ignores
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Dev/test only dependencies
├── alembic.ini                   # Alembic config
├── docker-compose.yml            # Local dev environment (app + db)
├── docker-compose.prod.yml       # Production docker compose reference
├── Dockerfile                    # App container definition
├── README.md                     # Project setup and overview
└── pytest.ini                    # Pytest configuration
```

---

## App Directory — Full Tree

```
app/
│
├── main.py                       # FastAPI app entry point
├── dependencies.py               # Shared FastAPI dependencies (DB session etc.)
│
├── core/                         # App-wide config, security, middleware
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings — all env vars loaded here
│   ├── security.py               # JWT creation, validation, password hashing
│   ├── middleware.py             # CORS, logging middleware registration
│   ├── exceptions.py             # Base AppException + all custom exceptions
│   ├── error_handlers.py         # Global FastAPI exception handlers
│   └── logging.py                # Logging configuration (JSON prod, pretty dev)
│
├── database/                     # Database connection and session management
│   ├── __init__.py
│   ├── base.py                   # SQLAlchemy Base, metadata
│   ├── session.py                # Async engine + session factory
│   └── mixins.py                 # Reusable model mixins (timestamps, soft delete)
│
├── models/                       # SQLAlchemy ORM models (DB tables)
│   ├── __init__.py               # Imports all models (required by Alembic)
│   ├── clinic.py                 # Clinic model
│   ├── user.py                   # User model
│   ├── user_permission.py        # UserPermission model
│   ├── patient.py                # Patient model
│   ├── appointment.py            # Appointment model
│   ├── consultation.py           # Consultation model
│   ├── medication.py             # Medication model (within consultation)
│   └── follow_up.py              # FollowUp model
│
├── schemas/                      # Pydantic schemas (request + response shapes)
│   ├── __init__.py
│   ├── common.py                 # Shared schemas (pagination, response envelope)
│   ├── auth.py                   # Login, register, token schemas
│   ├── clinic.py                 # Clinic settings, staff schemas
│   ├── user.py                   # User profile schemas
│   ├── patient.py                # Patient create, update, response schemas
│   ├── appointment.py            # Appointment create, update, response schemas
│   ├── consultation.py           # Consultation form, draft, submit schemas
│   ├── medication.py             # Medication schemas
│   └── analytics.py             # Analytics query params + response schemas
│
├── api/                          # All route definitions
│   ├── __init__.py
│   ├── router.py                 # Master router — registers all sub-routers
│   │
│   └── v1/                       # API version 1
│       ├── __init__.py
│       ├── auth.py               # /api/v1/auth/* routes
│       ├── clinic.py             # /api/v1/clinic/* routes
│       ├── appointments.py       # /api/v1/appointments/* routes
│       ├── patients.py           # /api/v1/patients/* routes
│       ├── consultations.py      # /api/v1/patients/{id}/consultations/* routes
│       └── analytics.py          # /api/v1/analytics/* routes
│
├── services/                     # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py           # Login, token issue, register logic
│   ├── clinic_service.py         # Clinic settings, staff management logic
│   ├── appointment_service.py    # Appointment lifecycle, queue logic
│   ├── patient_service.py        # Patient create, search, history logic
│   ├── consultation_service.py   # Consultation draft, submit, lock logic
│   ├── analytics_service.py      # Metric aggregation, filter logic
│   ├── pdf_service.py            # PDF report generation
│   └── whatsapp_service.py       # WhatsApp integration — STUBBED FOR MVP
│
├── repositories/                 # Data access layer — DB queries only
│   ├── __init__.py
│   ├── base_repository.py        # Generic CRUD base class
│   ├── clinic_repository.py      # Clinic + staff DB queries
│   ├── user_repository.py        # User DB queries
│   ├── patient_repository.py     # Patient DB queries
│   ├── appointment_repository.py # Appointment DB queries
│   ├── consultation_repository.py# Consultation DB queries
│   └── analytics_repository.py  # Raw analytics queries
│
├── rbac/                         # Role-based access control
│   ├── __init__.py
│   ├── permissions.py            # Permission constants (all permission strings)
│   ├── roles.py                  # Role definitions + default permission sets
│   └── dependencies.py           # FastAPI RBAC Depends() functions
│
├── tasks/                        # Background tasks — Celery (POST-MVP)
│   ├── __init__.py
│   ├── celery_app.py             # Celery app init — COMMENTED OUT MVP
│   ├── appointment_tasks.py      # No-show detection, reminders — STUBBED
│   └── whatsapp_tasks.py         # WP message tasks — STUBBED
│
├── integrations/                 # Third-party service integrations
│   ├── __init__.py
│   ├── whatsapp/
│   │   ├── __init__.py
│   │   ├── client.py             # WhatsApp API client — STUBBED MVP
│   │   └── templates.py          # Message templates — STUBBED MVP
│   └── storage/
│       ├── __init__.py
│       └── local.py              # Local file storage handler (PDF save/retrieve)
│
├── utils/                        # Pure utility functions — no business logic
│   ├── __init__.py
│   ├── datetime_utils.py         # Date range helpers, timezone handling
│   ├── id_generator.py           # Appointment ID, patient ID generation
│   ├── pagination.py             # Pagination helpers
│   └── validators.py             # Custom field validators
│
└── constants/                    # App-wide constants
    ├── __init__.py
    ├── appointment.py            # Appointment status enums, transition map
    ├── roles.py                  # Role name constants
    └── messages.py               # Standard API response messages
```

---

## Tests Directory — Full Tree

```
tests/
│
├── conftest.py                   # Pytest fixtures (test DB, test client, auth helpers)
├── factories.py                  # Test data factories (create test clinic, user, etc.)
│
├── unit/                         # Unit tests — test one function/class in isolation
│   ├── __init__.py
│   ├── test_security.py          # JWT creation, validation, password hash
│   ├── test_rbac.py              # Permission checks, role enforcement
│   ├── test_appointment_states.py# State machine transition rules
│   ├── test_datetime_utils.py    # Date range helpers
│   └── test_id_generator.py      # ID generation uniqueness
│
├── integration/                  # Integration tests — test full request → DB cycle
│   ├── __init__.py
│   ├── test_auth.py              # Register, login, refresh, logout
│   ├── test_clinic.py            # Settings GET/PATCH, staff CRUD
│   ├── test_appointments.py      # Full appointment lifecycle
│   ├── test_patients.py          # Patient CRUD + search
│   ├── test_consultations.py     # Draft, update, submit, lock
│   └── test_analytics.py         # Filter periods, metric accuracy
│
└── rbac/                         # RBAC enforcement tests
    ├── __init__.py
    ├── test_role_enforcement.py  # Wrong role → 403 on every protected route
    └── test_clinic_isolation.py  # Clinic A cannot access Clinic B data
```

---

## Alembic Directory

```
alembic/
│
├── env.py                        # Alembic env config — async SQLAlchemy setup
├── script.py.mako                # Migration file template
└── versions/                     # Auto-generated migration files
    └── (migration files go here)
```

---

## Storage Directory

```
storage/
│
├── .gitkeep                      # Keep folder in git, ignore contents
├── reports/                      # Generated PDF reports
│   └── .gitkeep
└── temp/                         # Temporary files during generation
    └── .gitkeep
```

---

## Scripts Directory

```
scripts/
│
├── seed_dev.py                   # Seed local DB with dev data (clinic, users, patients)
└── create_superuser.py           # Create first clinic owner via CLI
```

---

## Docker Files

```
docker/
│
├── nginx/
│   └── nginx.conf                # Nginx reverse proxy config (production reference)
└── postgres/
    └── init.sql                  # DB init script (create DB, extensions)

docker-compose.yml                # Dev: app + postgres + (redis commented out)
docker-compose.prod.yml           # Prod reference: app + nginx + postgres
Dockerfile                        # Multi-stage build (dev + prod stages)
```

---

## File Responsibilities — Quick Reference

| File | Single Responsibility |
|---|---|
| `main.py` | Create FastAPI app, register middleware, register routers, startup/shutdown events |
| `dependencies.py` | DB session dependency, current_user dependency |
| `core/config.py` | Load and validate ALL environment variables at startup |
| `core/security.py` | ONLY JWT and password operations — nothing else |
| `core/exceptions.py` | Define all custom exception classes |
| `core/error_handlers.py` | Map exceptions to HTTP responses |
| `database/session.py` | Create async engine, session factory — nothing else |
| `database/mixins.py` | `TimestampMixin`, `SoftDeleteMixin` used by models |
| `models/*.py` | SQLAlchemy table definition ONLY — no logic |
| `schemas/*.py` | Pydantic input/output shapes ONLY — no DB interaction |
| `api/v1/*.py` | Route definition ONLY — call service, return response |
| `services/*.py` | Business logic ONLY — call repository, enforce rules |
| `repositories/*.py` | DB queries ONLY — no business logic |
| `rbac/permissions.py` | Permission string constants ONLY |
| `rbac/dependencies.py` | FastAPI Depends() for permission enforcement |
| `tasks/*.py` | Celery task definitions — STUBBED in MVP |
| `integrations/whatsapp/` | WhatsApp API calls ONLY — STUBBED in MVP |
| `utils/*.py` | Pure functions — no DB, no business logic, no side effects |
| `constants/*.py` | Enums and string constants ONLY |

---

## Naming Conventions Summary

### Files
```
snake_case for all Python files
appointment_service.py ✅
AppointmentService.py  ❌
```

### Folders
```
snake_case, singular or plural as shown above
services/    ✅
Services/    ❌
service/     ❌ (use plural)
```

### Classes
```
PascalCase
AppointmentService  ✅
appointmentService  ❌
```

### Functions / Variables
```
snake_case
get_appointment_by_id()  ✅
getAppointmentById()     ❌
```

### Constants
```
UPPER_SNAKE_CASE
APPOINTMENT_STATUS_PENDING  ✅
appointment_status_pending  ❌
```

### Database Tables
```
snake_case, plural
appointments  ✅
Appointment   ❌
appt          ❌ (no abbreviations)
```

### API Routes
```
kebab-case, plural nouns, no verbs
/api/v1/appointments          ✅
/api/v1/getAppointments       ❌
/api/v1/appointment           ❌ (use plural)
```

---

## Layer Rules — Strictly Enforced

```
API layer      → ONLY calls Service layer. Never touches Repository or Model directly.
Service layer  → ONLY calls Repository layer. Contains all business logic.
Repository     → ONLY talks to DB. Returns model instances or raw data.
Schema         → ONLY used for input validation and output serialization.
Model          → ONLY defines DB structure. Zero business logic.
Utils          → Pure functions. No imports from services, repositories, or models.
Constants      → No logic. Enums and strings only.
```

**If you find business logic in a repository → move it to service.**
**If you find a DB query in a service → move it to repository.**
**If you find a DB query in a route → it's wrong, full stop.**

---

## Stubbed Files — MVP Marker Convention

Any file that is stubbed for post-MVP will have this header comment:

```python
# ============================================================
# STUBBED — POST-MVP
# This module is not active in MVP.
# Implementation required before enabling:
#   - [list what's needed]
# ============================================================
```

Files currently stubbed:
```
app/services/whatsapp_service.py
app/tasks/celery_app.py
app/tasks/appointment_tasks.py
app/tasks/whatsapp_tasks.py
app/integrations/whatsapp/client.py
app/integrations/whatsapp/templates.py
```

---

## Import Order Convention (every Python file)

```python
# 1. Standard library
import uuid
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Internal — core/database
from app.core.config import settings
from app.database.session import get_db

# 4. Internal — models/schemas/services
from app.models.appointment import Appointment
from app.schemas.appointment import AppointmentCreate
from app.services.appointment_service import AppointmentService

# 5. Internal — rbac/utils/constants
from app.rbac.dependencies import require_permission
from app.constants.appointment import AppointmentStatus
```