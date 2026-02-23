# DB_SCHEMA.md
# Dentist AI SaaS — Database Schema
> Production-ready. Indexed. Normalized. MVP + Post-MVP ready.

---

## Design Principles

- **UUID primary keys** everywhere — safe for distributed systems, no sequential guessing
- **snake_case** for all table and column names — matches Python/SQLAlchemy conventions
- **Soft deletes** on all critical tables — never hard delete patient or clinical data
- **Timestamps** (`created_at`, `updated_at`) on every table — auto-managed by DB
- **clinic_id on every clinic-owned table** — multi-tenancy enforced at schema level
- **Indexes** defined explicitly — no guessing on query performance
- **JSONB for flexible data** (operating hours) — queryable, not just stored text
- **Enums at DB level** — data integrity enforced before application layer

---

## Table Overview

```
users                  → Authentication only. One row per human login.
clinics                → One clinic per owner signup.
clinic_members         → Links users to clinics with a role. One row per user-clinic.
user_permissions       → Granular permission strings per clinic_member.
patients               → Patients registered in a clinic.
appointments           → Every appointment ever booked.
consultations          → Clinical notes filled by dentist per appointment.
medications            → Prescriptions within a consultation.
follow_ups             → Follow-up tasks linked to consultation + patient.
```

---

## 1. users

> Authentication only. No clinic-specific data here.
> One row = one human who can log into the system.

```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email               VARCHAR(150) NOT NULL,
    hashed_password     VARCHAR(255) NOT NULL,

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,   -- post-MVP: email verification

    last_login_at       TIMESTAMP WITH TIME ZONE,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_users_email ON users(email);
```

**Column Notes**
| Column | Note |
|---|---|
| `email` | Global unique — same email cannot register twice across any clinic |
| `hashed_password` | bcrypt hash — plain password never stored |
| `is_active` | False = cannot login. Set by clinic owner or system. |
| `is_verified` | Post-MVP email verification flag — column exists now, used later |
| `last_login_at` | Updated on every successful login |

---

## 2. clinics

> One clinic per owner signup. Core identity of the SaaS tenant.

```sql
CREATE TYPE clinic_status AS ENUM ('active', 'suspended', 'inactive');

CREATE TABLE clinics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity (LOCKED after creation — app-level enforcement)
    name                VARCHAR(150) NOT NULL,
    gst_number          VARCHAR(20),
    dentist_name        VARCHAR(120) NOT NULL,
    dentist_reg_id      VARCHAR(50),

    -- Contact (EDITABLE)
    phone               VARCHAR(20),
    email               VARCHAR(150),
    address             TEXT,
    city                VARCHAR(100),
    state               VARCHAR(100),
    pincode             VARCHAR(10),

    -- Location (optional, for maps/directions — post-MVP)
    latitude            DECIMAL(9, 6),
    longitude           DECIMAL(9, 6),

    -- Operating Hours (EDITABLE)
    -- Stored as JSONB for flexibility
    -- Format: { "monday": {"open": "09:00", "close": "18:00", "is_closed": false}, ... }
    operating_hours     JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Status
    status              clinic_status NOT NULL DEFAULT 'active',

    -- Subscription (post-MVP — columns exist now)
    subscription_plan   VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_clinics_status ON clinics(status);
```

**Column Notes**
| Column | Locked | Note |
|---|---|---|
| `name` | ✅ | Set at signup, never editable |
| `gst_number` | ✅ | Tax identity — locked |
| `dentist_name` | ✅ | Legal name — locked |
| `dentist_reg_id` | ✅ | Medical council reg — locked |
| `phone` | ❌ | Editable via settings |
| `email` | ❌ | Editable via settings |
| `address`, `city`, `state`, `pincode` | ❌ | Editable via settings |
| `operating_hours` | ❌ | Editable via settings |
| `latitude`, `longitude` | ❌ | Post-MVP maps feature |
| `subscription_plan` | — | Post-MVP billing — column exists now |

---

## 3. clinic_members

> Links a user to a clinic with a role.
> Replaces the separate doctors + staff tables — one clean join.
> One user can belong to one clinic in MVP. Post-MVP: multiple rows = multi-clinic.

```sql
CREATE TYPE member_role AS ENUM (
    'clinic_owner',
    'assistant',
    'receptionist',
    'helper',
    'compounder',
    'other'
);

CREATE TABLE clinic_members (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core relationships
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    clinic_id           UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,

    -- Identity (denormalized for fast access — avoids join to users for display)
    full_name           VARCHAR(120) NOT NULL,
    phone               VARCHAR(20),

    -- Role
    role                member_role NOT NULL,

    -- Clinic owner specific fields (null for staff)
    specialization      VARCHAR(100),                    -- dentist specialization
    experience_years    SMALLINT,                        -- dentist experience
    profile_bio         TEXT,                            -- post-MVP: public profile

    -- Status
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,   -- owner can deactivate staff

    -- Soft delete
    deleted_at          TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_clinic_members_user_clinic
    ON clinic_members(user_id, clinic_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_clinic_members_clinic_id   ON clinic_members(clinic_id);
CREATE INDEX idx_clinic_members_user_id     ON clinic_members(user_id);
CREATE INDEX idx_clinic_members_role        ON clinic_members(clinic_id, role);
CREATE INDEX idx_clinic_members_active      ON clinic_members(clinic_id, is_active)
    WHERE deleted_at IS NULL;
```

**Why denormalize `full_name` here?**
Every queue view, appointment list, and consultation form needs the member's name. Storing it here avoids joining `users` on every read. `users` table is auth-only — display name lives where the clinic context is.

**Column Notes**
| Column | Note |
|---|---|
| `user_id` | FK to users — the login identity |
| `clinic_id` | FK to clinics — which clinic they belong to |
| `full_name` | Display name within the clinic context |
| `role` | `clinic_owner` has all permissions; staff permissions are in user_permissions |
| `specialization`, `experience_years` | Only meaningful for clinic_owner/dentist |
| `is_active` | Owner can deactivate staff without deleting them |
| `deleted_at` | Soft delete — deactivated staff record preserved |

---

## 4. user_permissions

> Granular permission strings assigned to staff members.
> clinic_owner has a fixed full-access set loaded in code — not stored here.
> Only staff rows exist here.

```sql
CREATE TABLE user_permissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    clinic_member_id    UUID NOT NULL REFERENCES clinic_members(id) ON DELETE CASCADE,
    clinic_id           UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,

    -- Permission string: e.g. "appointment:write", "patient:read"
    permission          VARCHAR(100) NOT NULL,

    granted_by          UUID REFERENCES clinic_members(id) ON DELETE SET NULL,
    granted_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_user_permissions_member_perm
    ON user_permissions(clinic_member_id, permission);

CREATE INDEX idx_user_permissions_member     ON user_permissions(clinic_member_id);
CREATE INDEX idx_user_permissions_clinic     ON user_permissions(clinic_id);
```

**Valid Permission Strings**
```
appointment:read
appointment:write
appointment:cancel
appointment:complete
patient:read
patient:write
consultation:write
consultation:submit
analytics:read
clinic:settings:read
clinic:settings:write
clinic:staff:manage
```

**Column Notes**
| Column | Note |
|---|---|
| `clinic_member_id` | FK to clinic_members — whose permission this is |
| `clinic_id` | Denormalized for fast clinic-scoped queries |
| `permission` | Direct string — no lookup table needed at this scale |
| `granted_by` | Audit trail — which owner granted this permission |

---

## 5. patients

> Patients registered under a clinic.
> Soft deleted — never hard delete patient data.

```sql
CREATE TABLE patients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id           UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,

    -- Human-readable ID for display and search
    -- Format: PAT-YYYY-NNNNN  e.g. PAT-2024-00123
    patient_code        VARCHAR(20) NOT NULL,

    -- Core info
    full_name           VARCHAR(120) NOT NULL,
    age                 SMALLINT NOT NULL CHECK (age > 0 AND age < 121),
    gender              VARCHAR(10),                     -- optional: male/female/other

    -- Contact (all optional)
    phone               VARCHAR(20),
    email               VARCHAR(150),

    -- Notes
    general_notes       TEXT,                            -- permanent patient notes, allergies etc.

    -- Soft delete
    deleted_at          TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_patients_code_clinic
    ON patients(clinic_id, patient_code);

CREATE INDEX idx_patients_clinic_id         ON patients(clinic_id)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_patients_full_name         ON patients(clinic_id, full_name)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_patients_phone             ON patients(clinic_id, phone)
    WHERE deleted_at IS NULL;

-- Full-text search index for name search
CREATE INDEX idx_patients_name_fts
    ON patients USING gin(to_tsvector('english', full_name))
    WHERE deleted_at IS NULL;
```

**Column Notes**
| Column | Note |
|---|---|
| `patient_code` | Human-readable ID shown in UI: `PAT-2024-00123`. Generated by app. |
| `phone`, `email` | Both optional — patient may have neither |
| `general_notes` | Allergies, chronic conditions — persists across appointments |
| `deleted_at` | Soft delete only — patient data preserved for compliance |

---

## 6. appointments

> Every appointment ever booked in a clinic.
> The central table of the entire system.

```sql
CREATE TYPE appointment_type AS ENUM ('new', 'existing', 'follow_up');

CREATE TYPE appointment_status AS ENUM (
    'pending',
    'waiting',
    'cancelled',
    'no_show',
    'completed'
);

CREATE TABLE appointments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,
    patient_id              UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,

    -- Human-readable ID for display and search
    -- Format: APT-YYYY-NNNNN  e.g. APT-2024-00456
    appointment_code        VARCHAR(20) NOT NULL,

    -- Type and follow-up linkage
    appointment_type        appointment_type NOT NULL DEFAULT 'new',
    parent_appointment_id   UUID REFERENCES appointments(id) ON DELETE SET NULL,

    -- Status
    status                  appointment_status NOT NULL DEFAULT 'pending',
    queue_position          SMALLINT,                    -- set when status = waiting

    -- Scheduling
    scheduled_date          DATE NOT NULL,
    scheduled_time_slot     TIME NOT NULL,               -- e.g. 10:00

    -- Pre-consultation notes (set by assistant at booking)
    notes                   TEXT,

    -- Cancellation / no-show tracking
    cancelled_reason        TEXT,
    cancelled_at            TIMESTAMP WITH TIME ZONE,

    -- Action tracking
    created_by              UUID REFERENCES clinic_members(id) ON DELETE SET NULL,
    confirmed_by            UUID REFERENCES clinic_members(id) ON DELETE SET NULL,
    cancelled_by            UUID REFERENCES clinic_members(id) ON DELETE SET NULL,

    confirmed_at            TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_appointments_code_clinic
    ON appointments(clinic_id, appointment_code);

CREATE INDEX idx_appointments_clinic_date
    ON appointments(clinic_id, scheduled_date);

CREATE INDEX idx_appointments_patient
    ON appointments(patient_id, clinic_id);

CREATE INDEX idx_appointments_status
    ON appointments(clinic_id, status, scheduled_date);

CREATE INDEX idx_appointments_queue
    ON appointments(clinic_id, scheduled_date, queue_position)
    WHERE status = 'waiting';

CREATE INDEX idx_appointments_parent
    ON appointments(parent_appointment_id)
    WHERE parent_appointment_id IS NOT NULL;

-- Constraint: queue_position only set when status = waiting
-- (enforced at application layer)
```

**Status Transition Rules (enforced at app layer)**
```
pending   → waiting    (confirm)
pending   → cancelled  (cancel)
waiting   → completed  (dentist only — requires submitted consultation)
waiting   → cancelled  (cancel)
waiting   → no_show    (manual MVP / auto post-MVP)
completed → LOCKED
cancelled → LOCKED
no_show   → LOCKED
```

**Column Notes**
| Column | Note |
|---|---|
| `appointment_code` | Human-readable: `APT-2024-00456`. Generated by app. |
| `parent_appointment_id` | Self-referential FK — links follow-up to original |
| `queue_position` | Assigned when confirmed (status = waiting). Null otherwise. |
| `scheduled_time_slot` | TIME type — stores 10:00, not a full datetime |
| `created_by`, `confirmed_by`, `cancelled_by` | Audit trail — who did what |

---

## 7. consultations

> Clinical notes filled by dentist per appointment.
> Locked after submission — no edits allowed post-submit.

```sql
CREATE TABLE consultations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,
    appointment_id          UUID NOT NULL REFERENCES appointments(id) ON DELETE RESTRICT,
    patient_id              UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    dentist_id              UUID NOT NULL REFERENCES clinic_members(id) ON DELETE RESTRICT,

    -- Clinical data
    symptoms                TEXT,
    clinical_notes          TEXT,
    diagnosis               TEXT,                        -- post-MVP: structured diagnosis

    -- Financials
    fee_charged             DECIMAL(10, 2) DEFAULT 0.00,

    -- Follow-up
    is_follow_up_required   BOOLEAN NOT NULL DEFAULT FALSE,
    follow_up_notes         TEXT,
    follow_up_days          SMALLINT,                    -- suggested days until follow-up

    -- Form state
    is_submitted            BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at            TIMESTAMP WITH TIME ZONE,

    -- PDF report
    report_generated        BOOLEAN NOT NULL DEFAULT FALSE,
    report_path             VARCHAR(500),                -- local path or S3 key post-MVP
    report_generated_at     TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE UNIQUE INDEX uq_consultations_appointment
    ON consultations(appointment_id);               -- one consultation per appointment

CREATE INDEX idx_consultations_clinic          ON consultations(clinic_id);
CREATE INDEX idx_consultations_patient         ON consultations(patient_id, clinic_id);
CREATE INDEX idx_consultations_dentist         ON consultations(dentist_id);
CREATE INDEX idx_consultations_submitted       ON consultations(clinic_id, is_submitted);
CREATE INDEX idx_consultations_date
    ON consultations(clinic_id, created_at DESC);
```

**Column Notes**
| Column | Note |
|---|---|
| `appointment_id` | Unique — one consultation per appointment, enforced by DB |
| `dentist_id` | FK to clinic_members — who filled the form |
| `is_submitted` | False = draft (editable). True = locked forever. |
| `fee_charged` | DECIMAL(10,2) — supports up to 99,999,999.99 |
| `report_path` | Local path in MVP. S3 key in post-MVP. |
| `diagnosis` | Kept as TEXT now. Post-MVP: structured JSONB with ICD codes. |

---

## 8. medications

> Prescriptions within a consultation.
> Multiple medications per consultation allowed.

```sql
CREATE TABLE medications (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id         UUID NOT NULL REFERENCES consultations(id) ON DELETE CASCADE,
    clinic_id               UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,

    -- Prescription details
    name                    VARCHAR(200) NOT NULL,
    dosage                  VARCHAR(100),               -- e.g. "500mg"
    frequency               VARCHAR(100),               -- e.g. "3 times a day"
    duration                VARCHAR(100),               -- e.g. "5 days"
    instructions            TEXT,                       -- e.g. "After food"

    sort_order              SMALLINT DEFAULT 0,         -- display order on prescription

    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_medications_consultation   ON medications(consultation_id);
CREATE INDEX idx_medications_clinic         ON medications(clinic_id);
```

**Column Notes**
| Column | Note |
|---|---|
| `consultation_id` | CASCADE delete — medications deleted with consultation (only on hard delete, which shouldn't happen in prod) |
| `dosage`, `frequency`, `duration` | All free text — not enums. Dentist enters what they prescribe. |
| `sort_order` | Controls display order on PDF prescription |

---

## 9. follow_ups

> Tracks follow-up tasks created after consultation.
> In MVP: stored record only.
> Post-MVP: triggers Celery task for WhatsApp reminder.

```sql
CREATE TYPE follow_up_status AS ENUM (
    'scheduled',
    'sent',
    'completed',
    'cancelled'
);

CREATE TABLE follow_ups (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id               UUID NOT NULL REFERENCES clinics(id) ON DELETE RESTRICT,
    patient_id              UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    consultation_id         UUID NOT NULL REFERENCES consultations(id) ON DELETE RESTRICT,

    -- Linked new appointment (created when follow-up is booked)
    follow_up_appointment_id UUID REFERENCES appointments(id) ON DELETE SET NULL,

    -- Scheduling
    follow_up_date          DATE,                        -- suggested date
    notes                   TEXT,                        -- what to check at follow-up

    -- Status
    status                  follow_up_status NOT NULL DEFAULT 'scheduled',

    -- WhatsApp reminder (post-MVP — columns exist now)
    reminder_sent_at        TIMESTAMP WITH TIME ZONE,
    celery_task_id          VARCHAR(255),                -- post-MVP: Celery task ID

    -- Timestamps
    created_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_follow_ups_clinic          ON follow_ups(clinic_id);
CREATE INDEX idx_follow_ups_patient         ON follow_ups(patient_id, clinic_id);
CREATE INDEX idx_follow_ups_consultation    ON follow_ups(consultation_id);
CREATE INDEX idx_follow_ups_date            ON follow_ups(clinic_id, follow_up_date)
    WHERE status = 'scheduled';
```

---

## Relationships Map

```
clinics
  │
  ├──< clinic_members (role: clinic_owner, assistant, etc.)
  │         │
  │         └──< user_permissions (permission strings)
  │         │
  │         └── users (FK: user_id → login identity)
  │
  ├──< patients
  │         │
  │         └──< appointments
  │                   │
  │                   ├── appointments (self-ref: parent_appointment_id)
  │                   │
  │                   └──  consultations (1-to-1)
  │                               │
  │                               ├──< medications
  │                               │
  │                               └──  follow_ups
```

---

## Enum Summary

| Enum | Values |
|---|---|
| `clinic_status` | `active`, `suspended`, `inactive` |
| `member_role` | `clinic_owner`, `assistant`, `receptionist`, `helper`, `compounder`, `other` |
| `appointment_type` | `new`, `existing`, `follow_up` |
| `appointment_status` | `pending`, `waiting`, `cancelled`, `no_show`, `completed` |
| `follow_up_status` | `scheduled`, `sent`, `completed`, `cancelled` |

---

## Index Strategy Summary

| Table | Key Indexes | Why |
|---|---|---|
| `users` | `email` (unique) | Login lookup |
| `clinic_members` | `(user_id, clinic_id)` unique, `(clinic_id, role)` | Auth + staff list |
| `user_permissions` | `(clinic_member_id, permission)` unique | Permission check on every request |
| `patients` | `(clinic_id, full_name)`, `(clinic_id, phone)`, GIN full-text | Search |
| `appointments` | `(clinic_id, scheduled_date)`, `(clinic_id, status, date)`, queue partial | Date filter + queue |
| `consultations` | `appointment_id` unique, `(patient_id, clinic_id)` | One per appointment + history |
| `medications` | `consultation_id` | Prescription fetch |
| `follow_ups` | `(clinic_id, follow_up_date)` partial (scheduled only) | Reminder scheduling |

---

## Soft Delete Convention

Tables with soft delete (`deleted_at` column):
```
clinic_members    ← deactivated staff preserved
patients          ← patient data never lost
```

Tables without soft delete (append-only or system-managed):
```
appointments      ← status = cancelled/no_show is the "delete"
consultations     ← is_submitted lock is the protection
medications       ← cascade with consultation
user_permissions  ← hard delete on permission revoke is fine
follow_ups        ← status = cancelled is the "delete"
```

---

## Post-MVP Columns Already in Schema

These columns exist now but are unused in MVP. No migration needed later.

| Table | Column | Post-MVP Use |
|---|---|---|
| `users` | `is_verified` | Email verification flow |
| `clinics` | `latitude`, `longitude` | Maps / directions feature |
| `clinics` | `subscription_plan`, `subscription_expires_at` | Billing / plan management |
| `clinic_members` | `profile_bio` | Public dentist profile |
| `consultations` | `diagnosis` | Structured ICD diagnosis |
| `consultations` | `report_path` | S3 storage for PDF reports |
| `follow_ups` | `reminder_sent_at`, `celery_task_id` | Celery WhatsApp reminder |

---

## Alembic Migration Notes

```
1. All enums must be created BEFORE the tables that use them
2. Migration order:
   users → clinics → clinic_members → user_permissions
   → patients → appointments → consultations
   → medications → follow_ups

3. Never edit a committed migration file
4. Always generate: alembic revision --autogenerate -m "description"
5. Always review autogenerated file before applying
6. Apply: alembic upgrade head
7. Rollback: alembic downgrade -1
```
