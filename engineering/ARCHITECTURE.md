# ARCHITECTURE.md
# Dentist AI SaaS — Backend Architecture
> MVP Phase | Production-Ready Structure | FastAPI + Python

---

## 1. Project Philosophy

- **MVP First, Scale Later** — Build lean, but structure for growth. Every module, folder, and config decision is made with the full product in mind, even if the implementation is stubbed.
- **Clinic-Scoped Multi-Tenancy** — Every resource is owned by a clinic. No cross-clinic data leakage, ever.
- **Role-Based Access Control (RBAC)** — Permissions enforced at the route level via dependency injection, not scattered in business logic.
- **Environment-Aware Configuration** — Dev mode is open and permissive. Prod mode is locked. One codebase, two behaviors.
- **Deferred Complexity** — Celery, Redis, and LangChain are architected in, stubbed in comments, but not active in MVP.

---

## 2. Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Web Framework | FastAPI | Async-first, OpenAPI out of the box |
| Server | Uvicorn[standard] | Production-grade ASGI with websocket support |
| ORM | SQLAlchemy (async) | With Alembic for migrations |
| Database | PostgreSQL | Primary data store |
| Auth | JWT (python-jose) + bcrypt | Access + Refresh token pattern |
| Config | python-dotenv + Pydantic Settings | Environment-aware, validated config |
| PDF Generation | WeasyPrint ⚠️ DECISION NEEDED | Or ReportLab — confirm before implementing |
| WhatsApp | Meta Cloud API ⚠️ DECISION NEEDED | Or Twilio — stubbed for MVP |
| Task Queue | Celery + Redis | POST-MVP — stubbed in comments only |
| AI/LLM | LangChain | POST-MVP — stubbed in comments only |
| Migrations | Alembic | Versioned, auto-generated |

---

## 3. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│   WhatsApp (Patient) │ Web App (Staff/Dentist) │ Mobile App  │
└──────────────┬───────────────────┬─────────────────┬─────────┘
               │                   │                 │
               ▼                   ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Application                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Auth Layer  │  │  RBAC Layer  │  │   CORS Middleware │   │
│  │  (JWT)       │  │  (Depends)   │  │   (env-aware)    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                    API Routers                        │    │
│  │  /auth  /appointments  /patients  /clinic  /analytics │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                  Service Layer                        │    │
│  │   Business logic, orchestration, role enforcement    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                  Repository Layer                     │    │
│  │   DB queries only — no business logic here           │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                  Schema Layer (Pydantic)              │    │
│  │   Request validation, response serialization         │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐  ┌─────────┐  ┌──────────────┐
        │PostgreSQL│  │  Redis  │  │External APIs │
        │(primary) │  │(post-   │  │(WhatsApp,    │
        │          │  │ MVP)    │  │ PDF, etc.)   │
        └──────────┘  └─────────┘  └──────────────┘
```

---

## 4. Request Lifecycle

Every API request follows this exact path:

```
Incoming Request
      │
      ▼
CORS Middleware          ← env-aware: open in dev, strict in prod
      │
      ▼
Auth Middleware          ← validates JWT, injects `current_user`
      │
      ▼
Router (route match)     ← /api/v1/...
      │
      ▼
RBAC Dependency          ← checks role + clinic scope
      │
      ▼
Request Schema           ← Pydantic validates & parses body
      │
      ▼
Service Function         ← business logic lives here
      │
      ▼
Repository Function      ← DB interaction only
      │
      ▼
Response Schema          ← Pydantic serializes output
      │
      ▼
HTTP Response
```

---

## 5. Multi-Tenancy Model

### Clinic Isolation
- Every table that holds clinic-owned data has a `clinic_id` foreign key.
- Every authenticated request carries the user's `clinic_id` in the JWT payload.
- The RBAC dependency injects `clinic_id` into every service call.
- Repositories always filter by `clinic_id` — never query without it.

### User-Clinic Relationship
```
User → belongs to → Clinic
User → has → Role (within that clinic)
Role → grants → Permissions (defined per clinic by owner)
```

- A user exists in exactly one clinic (MVP scope).
- Multi-clinic support for a single user is POST-MVP.

---

## 6. Authentication Architecture

### Token Strategy
- **Access Token** — Short-lived (15 min). Sent with every request as `Authorization: Bearer <token>`.
- **Refresh Token** — Long-lived (7 days). Stored in HttpOnly cookie. Used to issue new access tokens.

### JWT Payload
```json
{
  "sub": "user_uuid",
  "clinic_id": "clinic_uuid",
  "role": "dentist",
  "permissions": ["appointment:write", "patient:read"],
  "exp": 1234567890
}
```

### Auth Flow
```
Login → validate credentials → issue access token + set refresh cookie
Request → validate access token → inject user context
Token expired → use refresh token → issue new access token
Logout → blacklist refresh token (POST-MVP: Redis) / clear cookie (MVP)
```

---

## 7. RBAC Design

### Role Hierarchy
```
clinic_owner (Dentist)
      │
      └── staff
            ├── assistant
            ├── receptionist
            ├── helper
            ├── compounder
            └── other
```

### Permission Model
Permissions are strings of the form `resource:action`.

| Permission | Description |
|---|---|
| `appointment:read` | View appointments |
| `appointment:write` | Create/update appointments |
| `appointment:cancel` | Cancel appointments |
| `appointment:complete` | Mark as completed (dentist only) |
| `patient:read` | View patient records |
| `patient:write` | Create/edit patient records |
| `consultation:write` | Fill consultation form |
| `consultation:submit` | Lock and submit consultation |
| `analytics:read` | View analytics dashboard |
| `clinic:settings:read` | View clinic settings |
| `clinic:settings:write` | Edit allowed clinic settings |
| `clinic:staff:manage` | Add/edit/remove staff |

### How Permissions are Enforced
- Dentist/owner has a fixed permission set — cannot be edited.
- Staff permissions are stored in DB, assigned by owner, loaded into JWT at login.
- Every protected route declares its required permission via a FastAPI `Depends()`.
- RBAC dependency checks: Is the user authenticated? Does their clinic_id match the resource? Do they have the required permission?

---

## 8. Database Architecture

### Design Principles
- UUID primary keys across all tables.
- `created_at`, `updated_at` on every table (auto-managed).
- Soft deletes (`deleted_at`) on critical tables — never hard delete patient or appointment data.
- `clinic_id` on every clinic-owned table — always.

### Core Tables (MVP)
```
clinics
users (staff + dentist)
user_permissions
patients
appointments
consultations
medications (within consultation)
follow_ups
```

### Relationships Overview
```
Clinic
  ├── Users (staff, dentist)
  │     └── UserPermissions
  ├── Patients
  │     └── Appointments
  │           ├── Consultation
  │           │     └── Medications
  │           └── FollowUp (links to new Appointment)
```

### Migrations
- Managed by Alembic.
- Migration files are versioned and committed to source control.
- Never edit DB schema manually in production.

---

## 9. Environment Configuration

### Environments
| Env | Description |
|---|---|
| `development` | Local dev. CORS open. Debug on. Detailed errors exposed. |
| `staging` | Pre-prod. CORS restricted to staging domain. Debug off. |
| `production` | Fully locked. CORS whitelist. No debug. Sentry/logging active. |

### CORS Strategy
```
development  → allow all origins, all methods, all headers
staging      → allow staging frontend origin only
production   → allow production frontend origin(s) only
```

### Config Loading
- `.env` file for local dev (never committed).
- `.env.example` committed — documents all required variables.
- `app/core/config.py` uses Pydantic `BaseSettings` — validates all env vars at startup.
- App refuses to start if required config is missing.

---

## 10. API Design Conventions

- **Base path:** `/api/v1/`
- **Versioning:** URL-based. `/v2/` added when breaking changes are introduced.
- **Response envelope:** All responses follow a consistent shape.

### Standard Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Appointment confirmed"
}
```

### Standard Error Response
```json
{
  "success": false,
  "error": {
    "code": "APPOINTMENT_NOT_FOUND",
    "message": "No appointment found with the given ID",
    "detail": null
  }
}
```

### HTTP Status Codes Used
| Code | When |
|---|---|
| 200 | Successful GET, PATCH |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE (no body) |
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Authenticated but not authorized |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate booking) |
| 422 | Pydantic validation failure |
| 500 | Unhandled server error |

---

## 11. Error Handling Strategy

- Global exception handler registered in `main.py`.
- All custom exceptions inherit from a base `AppException` class.
- Exceptions carry an error code, HTTP status, and human-readable message.
- Unhandled exceptions return 500 with no internal detail exposed in production.
- Full tracebacks logged server-side always.

---

## 12. Logging Strategy

- Structured JSON logging in production.
- Human-readable logging in development.
- Log levels: `DEBUG` (dev) → `INFO` (staging/prod).
- Every request logged with: method, path, status code, duration, user_id, clinic_id.
- Sensitive fields (passwords, tokens) never logged.

---

## 13. Post-MVP Architecture (Stubbed, Not Active)

### Celery + Redis (Task Queue)
- **Use cases:** WhatsApp message delivery, follow-up reminders, PDF generation, no-show detection.
- **Status:** Config files exist, imports are commented out. Workers not running in MVP.
- **Activation:** Uncomment Celery config, spin up Redis and worker process.

### LangChain (AI Layer)
- **Use cases:** AI-assisted prescription suggestions, patient history summarization, symptom analysis.
- **Status:** Module folder exists as placeholder. No implementation.
- **Activation:** Post-MVP feature sprint.

### WhatsApp Integration
- **Use cases:** Appointment booking, reminders, report delivery.
- **Status:** Service file exists with stubbed methods. Returns mock success in MVP.
- **Activation:** Plug in Meta Cloud API or Twilio credentials, implement service methods.

---

## 14. Security Checklist (MVP Baseline)

- [x] JWT-based auth with short-lived access tokens
- [x] Refresh tokens via HttpOnly cookie
- [x] Password hashing with bcrypt
- [x] RBAC enforced on every protected route
- [x] Clinic-scope isolation on every DB query
- [x] Input validation via Pydantic on all endpoints
- [x] No internal error details exposed in production responses
- [x] Environment-based CORS policy
- [ ] Rate limiting — POST-MVP (add slowapi)
- [ ] Refresh token blacklist — POST-MVP (Redis)
- [ ] HTTPS enforcement — infrastructure level (handled by reverse proxy/cloud)
- [ ] Audit log — POST-MVP

---

## 15. Deployment Overview (Reference)

```
Developer Machine
      │ git push
      ▼
GitHub / GitLab
      │ CI pipeline (linting, tests)
      ▼
Container Registry (Docker image)
      │
      ▼
Production Server / Cloud
      ├── Nginx (reverse proxy, HTTPS termination)
      ├── Uvicorn workers (FastAPI app)
      ├── PostgreSQL (managed DB preferred)
      └── Redis (POST-MVP — managed preferred)
```

- App is fully containerized via `Dockerfile` + `docker-compose.yml`.
- `docker-compose.yml` handles dev environment (app + postgres + redis stub).
- Production runs via Docker or cloud-native deployment (e.g., Railway, Render, EC2).

---
