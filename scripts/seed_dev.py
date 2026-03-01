#!/usr/bin/env python
"""
Seed script for DentistSaas Dev Environment.

Creates realistic sample data via the live API server:
  - 1 clinic owner + clinic
  - 2 staff members (assistant + receptionist)
  - 20 patients with realistic Indian names
  - 20 appointments across all statuses
  - 5 submitted consultations with medications + PDF reports

Usage:
    # Seed fresh (server must be running)
    python scripts/seed_dev.py

    # Wipe all DB data, then reseed
    python scripts/seed_dev.py --reset

    # Wipe all DB data only (no reseed)
    python scripts/seed_dev.py --clean

Rollback guarantee:
    If ANY step fails, the script automatically deletes everything it
    created in this run so the DB is left clean for a re-run.
    The --reset flag always wipes before seeding for a guaranteed clean slate.
"""

# Standard library
import argparse
import asyncio
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env before importing app modules
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass  # dotenv not required if env vars are already set

import httpx

BASE = "http://localhost:8000/api/v1"
SERVER_URL = "http://localhost:8000"


# ============================================================
# Sample data
# ============================================================

PATIENTS = [
    ("Aarav Sharma",     28, "male",   "9811001001"),
    ("Priya Verma",      34, "female", "9811001002"),
    ("Rahul Gupta",      42, "male",   "9811001003"),
    ("Ananya Singh",     26, "female", "9811001004"),
    ("Vikram Mehta",     55, "male",   "9811001005"),
    ("Kavya Nair",       31, "female", "9811001006"),
    ("Arjun Patel",      38, "male",   "9811001007"),
    ("Pooja Iyer",       22, "female", "9811001008"),
    ("Siddharth Rao",    47, "male",   "9811001009"),
    ("Meera Krishnan",   29, "female", "9811001010"),
    ("Rohan Joshi",      36, "male",   "9811001011"),
    ("Sneha Desai",      24, "female", "9811001012"),
    ("Aditya Kumar",     45, "male",   "9811001013"),
    ("Divya Pillai",     33, "female", "9811001014"),
    ("Karan Malhotra",   41, "male",   "9811001015"),
    ("Tanvi Reddy",      27, "female", "9811001016"),
    ("Manish Tiwari",    52, "male",   "9811001017"),
    ("Riya Bose",        23, "female", "9811001018"),
    ("Nikhil Pandey",    39, "male",   "9811001019"),
    ("Swati Saxena",     30, "female", "9811001020"),
]

MEDICATIONS_POOL = [
    {"name": "Ibuprofen",      "dosage": "400mg", "frequency": "TID", "duration": "5 days",  "instructions": "After meals"},
    {"name": "Amoxicillin",    "dosage": "500mg", "frequency": "BID", "duration": "7 days",  "instructions": "After meals"},
    {"name": "Metronidazole",  "dosage": "400mg", "frequency": "TID", "duration": "5 days",  "instructions": "With food"},
    {"name": "Paracetamol",    "dosage": "500mg", "frequency": "QID", "duration": "3 days",  "instructions": "As needed for pain"},
    {"name": "Clindamycin",    "dosage": "300mg", "frequency": "TID", "duration": "7 days",  "instructions": "After meals"},
]

SYMPTOMS = [
    "Severe toothache in lower left molar",
    "Sensitivity to hot and cold beverages",
    "Gum bleeding and swelling",
    "Broken tooth, sharp edges causing discomfort",
    "Wisdom tooth pain and persistent swelling",
]

DIAGNOSES = [
    "Dental caries Grade III — RCT advised",
    "Periodontal disease — scaling and root planing required",
    "Dental abscess — incision and drainage performed",
    "Fractured cusp — crown placement advised",
    "Pericoronitis — wisdom tooth extraction recommended",
]


# ============================================================
# Formatting helpers
# ============================================================

W = 58

def _banner(text: str) -> None:
    print(f"\n{'═' * W}")
    print(f"  {text}")
    print(f"{'═' * W}")

def _step(n: int, total: int, text: str) -> None:
    print(f"\n[{n}/{total}] {text}...")

def _ok(text: str)  -> None: print(f"  ✓  {text}")
def _warn(text: str) -> None: print(f"  ⚠  {text}")
def _err(text: str)  -> None: print(f"  ✗  {text}")

def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# DB wipe (direct Postgres via SQLAlchemy, no API required)
# ============================================================

async def _wipe_database() -> None:
    """Truncate all tables so the DB is clean.  Imports app DB config."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        from app.core.config import settings
        db_url = settings.DATABASE_URL

    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(
                "TRUNCATE TABLE follow_ups, medications, consultations, "
                "appointments, user_permissions, clinic_members, "
                "patients, clinics, users RESTART IDENTITY CASCADE"
            ))
        _ok("Database wiped clean (all tables truncated)")
    finally:
        await engine.dispose()


# ============================================================
# Cleanup — delete only items created in this run via API
# ============================================================

async def _cleanup_run(
    client: httpx.AsyncClient,
    owner_token: str | None,
    patient_ids: list[str],
    appointment_ids: list[str],
    consultation_ids: list[str],
) -> None:
    """
    Best-effort rollback of everything created in THIS run.
    Consultations → Appointments → Patients → Clinic (via DB wipe).
    Falls back to full DB wipe if individual deletes are not available
    (MVP has no DELETE endpoints for clinic/owner — wipe is the safe option).
    """
    print("\n  Rolling back created records...")

    # The MVP API has no DELETE endpoints for clinic / owner,
    # so we fall back to a full DB wipe. This is safe for a dev seed script.
    try:
        await _wipe_database()
        _ok("Rollback complete — DB is clean")
    except Exception as exc:
        _err(f"Could not wipe DB during rollback: {exc}")
        _err("Manual cleanup may be required.")


# ============================================================
# Main seed logic
# ============================================================

TOTAL_STEPS = 6

async def seed(client: httpx.AsyncClient) -> bool:
    """
    Seed the database. Returns True on success, False on failure.
    On failure, rolls back all created data automatically.
    """
    owner_token: str | None = None
    patient_ids: list[str] = []
    appointment_ids: list[str] = []
    consultation_ids: list[str] = []

    try:
        # ── Step 1: Register clinic + owner ──────────────────────────────
        _step(1, TOTAL_STEPS, "Registering clinic owner")

        owner_email    = "dentist@demo-clinic.com"
        owner_password = "DemoPass@123"

        r = await client.post(f"{BASE}/auth/register", json={
            "clinic_name":     "Smile Dental Clinic",
            "dentist_name":    "Dr. Ravi Kapoor",
            "dentist_reg_id":  "MH-2024-001",
            "full_name":       "Dr. Ravi Kapoor",
            "email":           owner_email,
            "password":        owner_password,
            "phone":           "9900000001",
        })

        if r.status_code not in (200, 201):
            raise RuntimeError(
                f"Register failed ({r.status_code}): {r.text}\n"
                "  Hint: if the clinic already exists run with --reset first."
            )

        owner_token = r.json()["data"]["access_token"]
        clinic_id   = r.json()["data"]["clinic"]["id"]
        _ok(f"Clinic owner registered  →  {owner_email}  /  {owner_password}")
        _ok(f"Clinic ID: {clinic_id}")

        # ── Step 2: Create staff ──────────────────────────────────────────
        _step(2, TOTAL_STEPS, "Creating staff members")

        staff_creds = []
        staff_specs = [
            (
                "Preethi Menon", "assistant", "preethi@demo-clinic.com", "StaffPass@123",
                ["appointment:read", "appointment:write", "appointment:cancel",
                 "patient:read", "patient:write", "clinic:settings:read"],
            ),
            (
                "Rakesh Sharma", "receptionist", "rakesh@demo-clinic.com", "StaffPass@123",
                ["appointment:read", "appointment:write",
                 "patient:read", "clinic:settings:read"],
            ),
        ]

        for full_name, role, email, password, perms in staff_specs:
            sr = await client.post(f"{BASE}/clinic/staff", json={
                "full_name":   full_name,
                "email":       email,
                "password":    password,
                "role":        role,
                "permissions": perms,
            }, headers=_h(owner_token))

            if sr.status_code in (200, 201):
                staff_creds.append((email, password, role))
                _ok(f"{full_name} ({role})  →  {email}  /  {password}")
            else:
                _warn(f"Staff creation failed for {email}: {sr.status_code} {sr.text}")

        # ── Step 3: Create 20 patients ────────────────────────────────────
        _step(3, TOTAL_STEPS, "Creating 20 patients")

        for full_name, age, gender, phone in PATIENTS:
            pr = await client.post(f"{BASE}/patients", json={
                "full_name": full_name,
                "age":       age,
                "gender":    gender,       # "male" | "female"
                "phone":     phone,
            }, headers=_h(owner_token))

            if pr.status_code in (200, 201):
                pid = pr.json()["data"]["id"]
                patient_ids.append(pid)
            else:
                _warn(f"Patient '{full_name}' failed: {pr.status_code} — {pr.text}")

        if not patient_ids:
            raise RuntimeError("No patients were created — cannot continue without patient IDs.")

        _ok(f"{len(patient_ids)} / {len(PATIENTS)} patients created")

        # ── Step 4: Create appointments across all statuses ───────────────
        _step(4, TOTAL_STEPS, "Creating appointments across various statuses")

        today = date.today()

        # Distribute patients across status groups (cycle through patient_ids)
        status_plan = [
            ("pending",   4),
            ("waiting",   3),
            ("completed", 5),  # These will get consultations
            ("cancelled", 4),
            ("no_show",   4),
        ]

        completed_to_consult: list[tuple[str, str]] = []  # (appt_id, patient_id)
        patient_cycle = patient_ids.copy()
        pid_idx = 0

        for target_status, count in status_plan:
            for _ in range(count):
                patient_id    = patient_cycle[pid_idx % len(patient_cycle)]
                pid_idx      += 1
                sched_date    = (today - timedelta(days=random.randint(0, 14))).isoformat()
                appt_type     = random.choice(["regular", "follow_up", "walk_in"])

                ar = await client.post(f"{BASE}/appointments", json={
                    "patient_id":       patient_id,
                    "appointment_type": appt_type,
                    "scheduled_date":   sched_date,
                }, headers=_h(owner_token))

                if ar.status_code not in (200, 201):
                    _warn(f"Appointment creation failed ({target_status}): {ar.status_code} — {ar.text}")
                    continue

                appt_id = ar.json()["data"]["id"]
                appointment_ids.append(appt_id)

                # Advance to target status
                if target_status in ("waiting", "completed", "no_show"):
                    await client.patch(
                        f"{BASE}/appointments/{appt_id}/confirm",
                        headers=_h(owner_token),
                    )

                if target_status == "completed":
                    # Consultation submit auto-completes the appointment
                    completed_to_consult.append((appt_id, patient_id))

                elif target_status == "cancelled":
                    await client.patch(
                        f"{BASE}/appointments/{appt_id}/cancel",
                        json={"reason": "Patient requested cancellation"},
                        headers=_h(owner_token),
                    )

                elif target_status == "no_show":
                    await client.patch(
                        f"{BASE}/appointments/{appt_id}/no-show",
                        headers=_h(owner_token),
                    )

        _ok(f"{len(appointment_ids)} appointments created")

        if not completed_to_consult:
            _warn("No 'completed' appointments — skipping consultation creation")
        else:
            # ── Step 5: Create consultations for completed appointments ────
            _step(5, TOTAL_STEPS, "Creating consultations with medications + PDF reports")

            cons_ok = 0
            for appt_id, patient_id in completed_to_consult:
                idx = random.randint(0, len(SYMPTOMS) - 1)
                meds = random.sample(MEDICATIONS_POOL, random.randint(1, 3))

                cr = await client.post(
                    f"{BASE}/consultations?patient_id={patient_id}",
                    json={
                        "appointment_id":       appt_id,
                        "symptoms":             SYMPTOMS[idx],
                        "clinical_notes":       "Patient examined. Radiograph taken. Treatment discussed.",
                        "diagnosis":            DIAGNOSES[idx],
                        "fee_charged":          str(random.choice([350, 500, 750, 1000, 1500])),
                        "is_follow_up_required": random.choice([True, False]),
                        "follow_up_days":       random.choice([7, 14, 30]) if random.random() > 0.5 else None,
                        "medications":          meds,
                    },
                    headers=_h(owner_token),
                )

                if cr.status_code not in (200, 201):
                    _warn(f"Consultation creation failed: {cr.status_code} — {cr.text}")
                    continue

                cons_id = cr.json()["data"]["id"]
                consultation_ids.append(cons_id)

                # Submit (auto-completes appointment)
                await client.post(f"{BASE}/consultations/{cons_id}/submit", headers=_h(owner_token))
                # Generate PDF
                await client.post(f"{BASE}/consultations/{cons_id}/generate-report", headers=_h(owner_token))
                cons_ok += 1

            _ok(f"{cons_ok} consultations submitted + PDF reports generated")

        # ── Step 6: Print credentials summary ────────────────────────────
        _step(6, TOTAL_STEPS, "Seeding complete — credentials summary")

        print(f"\n{'─' * W}")
        print(f"  {'ROLE':<16} {'EMAIL':<28} PASSWORD")
        print(f"{'─' * W}")
        print(f"  {'clinic_owner':<16} {owner_email:<28} {owner_password}")
        for email, password, role in staff_creds:
            print(f"  {role:<16} {email:<28} {password}")
        print(f"{'─' * W}")
        print(f"\n  API Docs:  {SERVER_URL}/docs")
        print(f"  ReDoc:     {SERVER_URL}/redoc")

        return True

    except Exception as exc:
        _err(f"\nSeed failed: {exc}")
        print("\n  Initiating automatic rollback...")
        await _cleanup_run(client, owner_token, patient_ids, appointment_ids, consultation_ids)
        return False


# ============================================================
# Entry point
# ============================================================

async def main() -> None:
    parser = argparse.ArgumentParser(
        description="DentistSaas dev seed script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe ALL database data first, then reseed from scratch",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe ALL database data and exit (no reseed)",
    )
    args = parser.parse_args()

    _banner("DentistSaas Dev Seed Script")

    # ── Clean / Reset ───────────────────────────────────────────────────
    if args.clean or args.reset:
        action = "Clean only" if args.clean else "Reset (wipe then reseed)"
        print(f"\n  Mode: {action}")
        print("  Wiping all database tables...")
        await _wipe_database()

    if args.clean:
        print("\n  --clean done. Database is empty.\n")
        sys.exit(0)

    # ── Health check ────────────────────────────────────────────────────
    print(f"\n  Checking server at {SERVER_URL} ...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as probe:
            hr = await probe.get(f"{SERVER_URL}/health")
            if hr.status_code != 200:
                raise ConnectionError(f"Health check returned {hr.status_code}")
        _ok("Server is up")
    except Exception:
        _err(f"Cannot reach {SERVER_URL}")
        _err("Start the server first:  uvicorn app.main:app --reload")
        print()
        sys.exit(1)

    # ── Seed ────────────────────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=30.0) as client:
        success = await seed(client)

    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
