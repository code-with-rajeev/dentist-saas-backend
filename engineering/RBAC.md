# RBAC.md
# Dentist AI SaaS — Role Based Access Control
> Every role. Every permission. Every rule. One source of truth.

---

## Design Philosophy

- **Roles define who you are** inside a clinic
- **Permissions define what you can do** inside a clinic
- **clinic_id defines where your access ends** — always
- `clinic_owner` has a fixed, hardcoded permission set — never stored in DB, never editable
- Staff permissions are stored in `user_permissions` table — assigned by owner, loaded at login
- Every permission check happens in a FastAPI `Depends()` — never inside business logic
- No permission = `403 FORBIDDEN` — always, no exceptions

---

## Role Hierarchy

```
SYSTEM
  └── clinic_owner  (top — fixed full access, can't be edited)
          │
          └── staff (bottom — permissions granted explicitly by owner)
                ├── assistant
                ├── receptionist
                ├── helper
                ├── compounder
                └── other
```

**Key Rules**
- `clinic_owner` is always one per clinic — the person who registered
- `clinic_owner` permissions are hardcoded in `app/rbac/roles.py` — not in DB
- Staff roles are just labels — permissions are what actually controls access
- Two `assistant` roles in the same clinic can have completely different permissions
- A staff member with zero permissions can log in but cannot do anything

---

## Permission Registry

All valid permission strings. Defined as constants in `app/rbac/permissions.py`.
No permission outside this list is valid. Any unknown string is rejected.

```
Category: Appointments
─────────────────────────────────────────────
appointment:read          View appointments, queue, history
appointment:write         Create, confirm, reschedule appointments
appointment:cancel        Cancel appointments
appointment:complete      Mark appointment as completed (dentist only)

Category: Patients
─────────────────────────────────────────────
patient:read              View patient records, history, consultations
patient:write             Create and edit patient records

Category: Consultations
─────────────────────────────────────────────
consultation:write        Create and update draft consultation form
consultation:submit       Submit and lock consultation (dentist only)

Category: Analytics
─────────────────────────────────────────────
analytics:read            View analytics dashboard and all reports

Category: Clinic
─────────────────────────────────────────────
clinic:settings:read      View clinic settings
clinic:settings:write     Edit allowed clinic settings (hours, contact)
clinic:staff:manage       Add, edit permissions, deactivate staff
```

**Total: 12 permission strings**

---

## Role → Permission Matrix

### clinic_owner (Hardcoded — NOT in DB)

```
appointment:read          ✅
appointment:write         ✅
appointment:cancel        ✅
appointment:complete      ✅  ← EXCLUSIVE to clinic_owner
patient:read              ✅
patient:write             ✅
consultation:write        ✅  ← EXCLUSIVE to clinic_owner
consultation:submit       ✅  ← EXCLUSIVE to clinic_owner
analytics:read            ✅  ← EXCLUSIVE to clinic_owner
clinic:settings:read      ✅
clinic:settings:write     ✅  ← EXCLUSIVE to clinic_owner
clinic:staff:manage       ✅  ← EXCLUSIVE to clinic_owner
```

**clinic_owner has all 12 permissions. No exceptions. Not configurable.**

---

### Staff Roles (Stored in DB — Assigned by Owner)

Staff roles carry **no default permissions**. Every permission must be explicitly granted.
Below is the **recommended starter set** per role — owner can customize freely.

#### assistant (Recommended Starter Set)
```
appointment:read          ✅ recommended
appointment:write         ✅ recommended
appointment:cancel        ✅ recommended
appointment:complete      ❌ never (owner exclusive)
patient:read              ✅ recommended
patient:write             ✅ recommended
consultation:write        ❌ never (owner exclusive)
consultation:submit       ❌ never (owner exclusive)
analytics:read            ❌ not recommended
clinic:settings:read      ❌ not recommended
clinic:settings:write     ❌ never (owner exclusive)
clinic:staff:manage       ❌ never (owner exclusive)
```

#### receptionist (Recommended Starter Set)
```
appointment:read          ✅ recommended
appointment:write         ✅ recommended
appointment:cancel        ✅ recommended
appointment:complete      ❌ never
patient:read              ✅ recommended
patient:write             ✅ recommended
consultation:write        ❌ never
consultation:submit       ❌ never
analytics:read            ❌ not recommended
clinic:settings:read      ❌ not recommended
clinic:settings:write     ❌ never
clinic:staff:manage       ❌ never
```

#### helper / compounder / other (Recommended Starter Set)
```
appointment:read          ✅ recommended
appointment:write         ❌ not recommended
appointment:cancel        ❌ not recommended
appointment:complete      ❌ never
patient:read              ✅ recommended
patient:write             ❌ not recommended
consultation:write        ❌ never
consultation:submit       ❌ never
analytics:read            ❌ never
clinic:settings:read      ❌ never
clinic:settings:write     ❌ never
clinic:staff:manage       ❌ never
```

---

## Owner-Exclusive Permissions

These 6 permissions can **never** be assigned to any staff member.
Enforced at two levels: API validation on staff permission assignment + RBAC dependency check.

```
appointment:complete      Only dentist can mark a consultation done
consultation:write        Only dentist fills the clinical form
consultation:submit       Only dentist locks and submits
analytics:read            Revenue and patient data — owner only
clinic:settings:write     Clinic config — owner only
clinic:staff:manage       Staff management — owner only
```

**Implementation Note:** When owner assigns permissions to staff, the API rejects
any payload containing these 6 strings with `400 OWNER_EXCLUSIVE_PERMISSION`.

---

## Clinic Scope Enforcement

Every permission check also validates clinic scope.
A user authenticated with `clinic_id = A` can **never** access resources of `clinic_id = B`.
This is the second layer of every RBAC dependency check.

```
Check 1: Is the user authenticated?           → 401 if not
Check 2: Does the user have the permission?   → 403 if not
Check 3: Does the resource belong to their clinic_id? → 403 if not
```

All three checks happen on every protected request. No exceptions.

---

## FastAPI Dependency Implementation Pattern

Defined in `app/rbac/dependencies.py`.

### How Routes Use It

```python
# Single permission required
@router.get("/appointments")
async def list_appointments(
    current_user: CurrentUser = Depends(require_permission("appointment:read"))
):
    ...

# Multiple permissions required (user must have ALL)
@router.post("/appointments/{id}/complete")
async def complete_appointment(
    current_user: CurrentUser = Depends(
        require_permissions(["appointment:complete", "consultation:submit"])
    )
):
    ...

# Owner-only route (role check, not just permission)
@router.get("/analytics/overview")
async def analytics_overview(
    current_user: CurrentUser = Depends(require_role("clinic_owner"))
):
    ...
```

### Dependency Chain

```
require_permission("appointment:write")
        │
        ▼
get_current_user()          ← validates JWT, loads user + clinic_id + permissions
        │
        ▼
check_permission()          ← is "appointment:write" in user.permissions?
        │
        ▼
inject CurrentUser          ← user object available in route handler
```

### CurrentUser Object (injected into every protected route)

```python
class CurrentUser:
    id: UUID                  # clinic_member id
    user_id: UUID             # users table id (auth identity)
    clinic_id: UUID           # which clinic they belong to
    full_name: str
    role: MemberRole          # clinic_owner | assistant | etc.
    permissions: list[str]    # ["appointment:read", "patient:write", ...]
    is_active: bool
```

---

## Permission Loading Strategy

### clinic_owner
Permissions are **never loaded from DB**. At JWT creation:
```python
if member.role == "clinic_owner":
    permissions = OWNER_PERMISSIONS  # hardcoded full list from roles.py
```

### Staff
Permissions are **loaded from `user_permissions` table** at login and baked into JWT:
```python
if member.role != "clinic_owner":
    permissions = load_from_db(clinic_member_id)  # query user_permissions
```

### Why bake into JWT?
- Zero DB hit on every request for permission check
- Trade-off: permission changes take effect on next login (or token refresh)
- Acceptable for MVP — post-MVP can add Redis cache invalidation

### Permission Change Propagation (MVP)
```
Owner updates staff permissions
        │
        ▼
DB updated immediately
        │
        ▼
Staff must log out + log in again
to get new permissions in token
```

**Post-MVP:** Redis pub/sub invalidates active tokens immediately on permission change.

---

## Route Permission Map

Full reference. Every protected route and its required permission.

### Auth
```
POST /auth/register          Public
POST /auth/login             Public
POST /auth/refresh           Public (refresh cookie)
POST /auth/logout            Protected (any authenticated user)
GET  /auth/me                Protected (any authenticated user)
```

### Clinic
```
GET    /clinic/settings                          clinic:settings:read
PATCH  /clinic/settings                          clinic:settings:write  + role:clinic_owner
GET    /clinic/staff                             clinic:staff:manage    + role:clinic_owner
POST   /clinic/staff                             clinic:staff:manage    + role:clinic_owner
PATCH  /clinic/staff/{id}/permissions            clinic:staff:manage    + role:clinic_owner
DELETE /clinic/staff/{id}                        clinic:staff:manage    + role:clinic_owner
```

### Appointments
```
POST   /appointments/                            appointment:write
GET    /appointments/                            appointment:read
GET    /appointments/queue                       appointment:read
GET    /appointments/{id}                        appointment:read
PATCH  /appointments/{id}/confirm                appointment:write
PATCH  /appointments/{id}/cancel                 appointment:cancel
PATCH  /appointments/{id}/reschedule             appointment:write
PATCH  /appointments/{id}/no-show                appointment:write
PATCH  /appointments/{id}/complete               appointment:complete   + role:clinic_owner
```

### Patients
```
POST   /patients/                                patient:write
GET    /patients/                                patient:read
GET    /patients/{id}                            patient:read
PATCH  /patients/{id}                            patient:write
GET    /patients/{id}/appointments               patient:read
GET    /patients/{id}/consultations              patient:read
```

### Consultations
```
POST   /patients/{id}/consultations/             consultation:write     + role:clinic_owner
PATCH  /patients/{id}/consultations/{cid}        consultation:write     + role:clinic_owner
POST   /patients/{id}/consultations/{cid}/submit consultation:submit    + role:clinic_owner
GET    /patients/{id}/consultations/{cid}        patient:read
GET    /patients/{id}/consultations/{cid}/report patient:read
```

### Analytics
```
GET    /analytics/overview                       analytics:read         + role:clinic_owner
GET    /analytics/appointments                   analytics:read         + role:clinic_owner
GET    /analytics/revenue                        analytics:read         + role:clinic_owner
GET    /analytics/patients                       analytics:read         + role:clinic_owner
```

### Stub Routes (POST-MVP)
```
POST   /patients/{id}/consultations/{cid}/send-report   consultation:submit + role:clinic_owner
POST   /patients/{id}/follow-up                         consultation:submit + role:clinic_owner
```

---

## Error Responses

| Scenario | HTTP | Error Code |
|---|---|---|
| No token / invalid token | 401 | `UNAUTHORIZED` |
| Token expired | 401 | `TOKEN_EXPIRED` |
| Valid token, missing permission | 403 | `FORBIDDEN` |
| Valid token, wrong clinic resource | 403 | `FORBIDDEN` |
| Staff assigned owner-exclusive permission | 400 | `OWNER_EXCLUSIVE_PERMISSION` |
| Inactive user attempts login | 403 | `ACCOUNT_INACTIVE` |

---

## Constants File Reference

### `app/rbac/permissions.py`
```python
# All permission strings as constants
APPOINTMENT_READ     = "appointment:read"
APPOINTMENT_WRITE    = "appointment:write"
APPOINTMENT_CANCEL   = "appointment:cancel"
APPOINTMENT_COMPLETE = "appointment:complete"
PATIENT_READ         = "patient:read"
PATIENT_WRITE        = "patient:write"
CONSULTATION_WRITE   = "consultation:write"
CONSULTATION_SUBMIT  = "consultation:submit"
ANALYTICS_READ       = "analytics:read"
CLINIC_SETTINGS_READ = "clinic:settings:read"
CLINIC_SETTINGS_WRITE= "clinic:settings:write"
CLINIC_STAFF_MANAGE  = "clinic:staff:manage"

# Owner-exclusive — never assignable to staff
OWNER_EXCLUSIVE_PERMISSIONS = [
    APPOINTMENT_COMPLETE,
    CONSULTATION_WRITE,
    CONSULTATION_SUBMIT,
    ANALYTICS_READ,
    CLINIC_SETTINGS_WRITE,
    CLINIC_STAFF_MANAGE,
]

# All valid permission strings
ALL_PERMISSIONS = [
    APPOINTMENT_READ, APPOINTMENT_WRITE, APPOINTMENT_CANCEL, APPOINTMENT_COMPLETE,
    PATIENT_READ, PATIENT_WRITE,
    CONSULTATION_WRITE, CONSULTATION_SUBMIT,
    ANALYTICS_READ,
    CLINIC_SETTINGS_READ, CLINIC_SETTINGS_WRITE, CLINIC_STAFF_MANAGE,
]
```

### `app/rbac/roles.py`
```python
# Hardcoded owner permission set — never from DB
OWNER_PERMISSIONS = [
    "appointment:read", "appointment:write",
    "appointment:cancel", "appointment:complete",
    "patient:read", "patient:write",
    "consultation:write", "consultation:submit",
    "analytics:read",
    "clinic:settings:read", "clinic:settings:write",
    "clinic:staff:manage",
]

# Recommended starter sets (used when owner adds staff — not enforced)
RECOMMENDED_PERMISSIONS = {
    "assistant":    ["appointment:read", "appointment:write",
                     "appointment:cancel", "patient:read", "patient:write"],
    "receptionist": ["appointment:read", "appointment:write",
                     "appointment:cancel", "patient:read", "patient:write"],
    "helper":       ["appointment:read", "patient:read"],
    "compounder":   ["appointment:read", "patient:read"],
    "other":        ["appointment:read", "patient:read"],
}
```

---

## Security Notes

- JWT payload includes `permissions` array — no DB hit on every request
- Permissions in JWT are treated as read-only — cannot be self-modified
- Token tampering → `401 UNAUTHORIZED` (signature fails)
- Staff permission changes take effect on next login in MVP
- `clinic_id` in JWT is set at login — cannot be changed mid-session
- All RBAC checks log the user_id, clinic_id, and permission attempted on failure

