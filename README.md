# Dentist SaaS Backend

Production-ready backend API for a multi-tenancy Dental Clinic Management SaaS built with **FastAPI**, **SQLAlchemy**, **PostgreSQL**, and **asyncpg**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.x (async) |
| Database | PostgreSQL via asyncpg |
| Auth | JWT (access + refresh tokens) |
| PDF | ReportLab |
| Migrations | Alembic |
| Testing | pytest-asyncio + httpx |

---

## Project Structure

```
app/
├── api/v1/          # Route handlers (auth, clinic, patients, appointments, ...)
├── core/            # Config, exceptions, security, logging
├── database/        # Session factory, Alembic env
├── models/          # SQLAlchemy ORM models
├── rbac/            # Permissions, dependencies, CurrentUser
├── repositories/    # DB query layer
├── schemas/         # Pydantic request/response models
├── services/        # Business logic (state machine, PDF, analytics)
└── utils/           # pagination, ID generation, datetime utils

tests/
├── conftest.py      # Fixtures (client, clean_db, owner_headers, ...)
├── integration/     # End-to-end HTTP tests (104 tests)
├── unit/            # Pure Python unit tests (31+ tests)
└── rbac/            # Role enforcement + clinic isolation tests (10 tests)

scripts/
└── seed_dev.py      # Dev DB seeder — run against live server
engineering/         # Architecture docs, API contract, RBAC spec
```

---

## Local Setup

### 1. Prerequisites
- Python 3.12+
- PostgreSQL 14+ running locally

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, etc.
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the dev server

```bash
uvicorn app.main:app --reload
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running Tests

Tests use a separate `NullPool` engine and `TRUNCATE` each table before every test for clean isolation.

> **Requires PostgreSQL to be running.**

```bash
# All tests (integration + unit + rbac)
pytest tests/ -v

# By suite
pytest tests/integration/ -v          # 104 integration tests
pytest tests/unit/ -v                 # 31+ pure-Python unit tests
pytest tests/rbac/ -v                 # 10 RBAC isolation tests

# Single module
pytest tests/integration/test_appointments.py -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

---

## Seeding the Dev Database

Run the seed script against a running server to create realistic sample data:

```bash
# Start the server first
uvicorn app.main:app --reload

# In another terminal
python scripts/seed_dev.py
```

**What it creates:**
- 1 clinic owner (`dentist@demo-clinic.com`)
- 2 staff members (assistant + receptionist)
- 20 patients with realistic Indian names
- 20 appointments across all statuses (pending, waiting, completed, cancelled, no_show)
- 5 submitted consultations with medications and PDF reports

Credentials are printed to console after seeding.

---

## API Modules

| Module | Prefix | Endpoints |
|---|---|---|
| Auth | `/api/v1/auth` | register, login, refresh, logout, /me |
| Clinic | `/api/v1/clinic` | settings CRUD, staff management |
| Patients | `/api/v1/patients` | CRUD + search + appointments sub-route |
| Appointments | `/api/v1/appointments` | lifecycle + queue + state transitions |
| Consultations | `/api/v1/consultations` | draft → submit → PDF download |
| Analytics | `/api/v1/analytics` | overview, appointments, revenue, patients |

---

## Authentication

All routes (except `/auth/register` and `/auth/login`) require a valid JWT:

```
Authorization: Bearer <access_token>
```

Access tokens expire in 60 minutes. Use `POST /api/v1/auth/refresh` with the refresh token to get a new one.

---

## RBAC

Users have roles (`clinic_owner`, `assistant`, `receptionist`) and granular permissions:

```
appointment:read    appointment:write   appointment:cancel  appointment:complete
patient:read        patient:write
consultation:write  consultation:submit
analytics:read
clinic:settings:read   clinic:settings:write   clinic:staff:manage
```

**Owner-only permissions** (cannot be granted to staff):
`consultation:write`, `consultation:submit`, `analytics:read`,
`clinic:settings:write`, `clinic:staff:manage`, `appointment:complete`

---

## Appointment State Machine

```
pending ──confirm──► waiting ──complete──► completed (terminal)
   │                    │
   └──cancel──►cancelled └──no-show──► no_show (terminal)
   │                    │
   └──reschedule──────── └──reschedule──► pending
```

---

## PDF Reports

Consultation reports are generated with ReportLab and saved to `PDF_STORAGE_PATH/{clinic_id}/{appointment_code}.pdf`.

```bash
# Set in .env
PDF_STORAGE_PATH=./storage/reports
```

---

## Alembic Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply
alembic upgrade head

# Rollback one
alembic downgrade -1
```

---

## Engineering Docs

- [`engineering/DEVELOPMENT_PHASES.md`](engineering/DEVELOPMENT_PHASES.md) — Phase-by-phase implementation plan
- [`engineering/API_CONTRACT.md`](engineering/API_CONTRACT.md) — Full API spec
- [`engineering/RBAC.md`](engineering/RBAC.md) — RBAC design
- [`engineering/MVP_TECH_DOC.md`](engineering/MVP_TECH_DOC.md) — Technical decisions
