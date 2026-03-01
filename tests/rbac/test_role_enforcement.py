"""
RBAC Integration Tests — Role enforcement and clinic isolation.
10.4.1 test_role_enforcement.py — every owner-exclusive route returns 403 for staff.
10.4.2 test_clinic_isolation.py — Clinic A token cannot read Clinic B data.

Both use separate test classes and share the client/clean_db fixtures from conftest.
"""

# Standard library
import uuid
from datetime import date

# Third-party
import pytest
from httpx import AsyncClient

TODAY = date.today().isoformat()

# ============================================================
# Helpers
# ============================================================

async def _register_and_login(client: AsyncClient, email: str, suffix: str) -> tuple[str, str]:
    """Register a new clinic+owner and return (access_token, clinic_id)."""
    r = await client.post("/api/v1/auth/register", json={
        "clinic_name": f"Clinic {suffix}",
        "dentist_name": f"Dr {suffix}",
        "dentist_reg_id": f"REG-{suffix}",
        "full_name": f"Dr {suffix}",
        "email": email,
        "password": "TestPass123!",
        "phone": f"900000{suffix[:4].replace('-', '')}",
    })
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    return data["access_token"], data["clinic"]["id"]


async def _make_staff(client: AsyncClient, owner_headers: dict, email: str) -> str:
    """Create an assistant staff member and return their token."""
    r = await client.post("/api/v1/clinic/staff", json={
        "full_name": "Staff Member",
        "email": email,
        "password": "StaffPass123",
        "role": "assistant",
        "permissions": ["patient:read", "appointment:read", "appointment:write", "appointment:cancel"],
    }, headers=owner_headers)
    assert r.status_code == 201, r.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "StaffPass123"})
    return login.json()["data"]["access_token"]


async def _make_patient(client: AsyncClient, headers: dict) -> str:
    r = await client.post("/api/v1/patients", json={"full_name": "Test Patient", "age": 30}, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]["id"]


# ============================================================
# 10.4.1 — Role Enforcement
# ============================================================

class TestRoleEnforcement:
    """Every owner-exclusive endpoint must return 403 for staff."""

    async def test_analytics_overview_staff_gets_403(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_analytics@test.com")
        r = await client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_analytics_revenue_staff_gets_403(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_rev@test.com")
        r = await client.get("/api/v1/analytics/revenue", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_analytics_patients_staff_gets_403(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_pat@test.com")
        r = await client.get("/api/v1/analytics/patients", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_analytics_appointments_staff_gets_403(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_appts@test.com")
        r = await client.get("/api/v1/analytics/appointments", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    async def test_create_consultation_staff_gets_403(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_cons@test.com")
        patient_id = await _make_patient(client, owner_headers)
        appt_r = await client.post("/api/v1/appointments", json={
            "patient_id": patient_id,
            "appointment_type": "regular",
            "scheduled_date": TODAY,
        }, headers=owner_headers)
        appt_id = appt_r.json()["data"]["id"]
        await client.patch(f"/api/v1/appointments/{appt_id}/confirm", headers=owner_headers)
        r = await client.post(
            f"/api/v1/consultations?patient_id={patient_id}",
            json={"appointment_id": appt_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    async def test_clinic_staff_listing_requires_owner(self, client: AsyncClient, owner_headers: dict):
        token = await _make_staff(client, owner_headers, "staff_list@test.com")
        r = await client.get("/api/v1/clinic/staff", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


# ============================================================
# 10.4.2 — Clinic Isolation
# ============================================================

class TestClinicIsolation:
    """Clinic A token cannot read or modify Clinic B's resources."""

    async def test_clinic_a_cannot_read_clinic_b_patients(self, client: AsyncClient):
        # Register two separate clinics
        token_a, clinic_a_id = await _register_and_login(client, "ownerA@isolation.com", "A0001")
        token_b, clinic_b_id = await _register_and_login(client, "ownerB@isolation.com", "B0001")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create patient in Clinic B
        patient_b = await _make_patient(client, headers_b)

        # Clinic A tries to access it
        r = await client.get(f"/api/v1/patients/{patient_b}", headers=headers_a)
        assert r.status_code == 404  # not visible to Clinic A

    async def test_clinic_a_cannot_list_clinic_b_patients(self, client: AsyncClient):
        token_a, _ = await _register_and_login(client, "ownerAlist@isolation.com", "AL001")
        token_b, _ = await _register_and_login(client, "ownerBlist@isolation.com", "BL001")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create 3 patients in Clinic B
        for i in range(3):
            await _make_patient(client, headers_b)

        # Clinic A should see 0 patients
        r = await client.get("/api/v1/patients", headers=headers_a)
        assert r.json()["meta"]["total"] == 0

    async def test_clinic_a_cannot_read_clinic_b_appointments(self, client: AsyncClient):
        token_a, _ = await _register_and_login(client, "ownerAappt@isolation.com", "AA001")
        token_b, _ = await _register_and_login(client, "ownerBappt@isolation.com", "BA001")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create appointment in clinic B
        patient_b = await _make_patient(client, headers_b)
        appt_r = await client.post("/api/v1/appointments", json={
            "patient_id": patient_b,
            "appointment_type": "regular",
            "scheduled_date": TODAY,
        }, headers=headers_b)
        appt_id = appt_r.json()["data"]["id"]

        # Clinic A tries
        r = await client.get(f"/api/v1/appointments/{appt_id}", headers=headers_a)
        assert r.status_code == 404

    async def test_clinic_a_analytics_only_sees_own_data(self, client: AsyncClient):
        token_a, _ = await _register_and_login(client, "ownerAana@isolation.com", "ANA1")
        token_b, _ = await _register_and_login(client, "ownerBana@isolation.com", "ANB1")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Create 5 patients + appointments in Clinic B only
        for i in range(5):
            patient_b = await _make_patient(client, headers_b)
            await client.post("/api/v1/appointments", json={
                "patient_id": patient_b,
                "appointment_type": "regular",
                "scheduled_date": TODAY,
            }, headers=headers_b)

        # Clinic A analytics should show 0
        r = await client.get("/api/v1/analytics/overview?period=today", headers=headers_a)
        assert r.json()["data"]["total_appointments"] == 0
        assert r.json()["data"]["unique_patients"] == 0
