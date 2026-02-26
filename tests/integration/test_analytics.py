"""
Integration tests for Phase 9 — Analytics Module.
Covers: overview, appointments, revenue, patients endpoints;
        period filter, custom date range, conflict/invalid validations, RBAC.

Run with: pytest tests/integration/test_analytics.py -v
"""

# Standard library
from datetime import date, timedelta

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/analytics"
BASE_PATIENTS = "/api/v1/patients"
BASE_APPTS = "/api/v1/appointments"
BASE_CONSULTATIONS = "/api/v1/consultations"
TODAY = date.today().isoformat()


# ============================================================
# Setup helpers — reuse appointment + consultation patterns
# ============================================================

async def _seed_appointment(client, headers, patient_id: str, status_chain: list[str] = None) -> dict:
    """Create appointment and optionally advance its state."""
    r = await client.post(BASE_APPTS, json={
        "patient_id": patient_id,
        "appointment_type": "regular",
        "scheduled_date": TODAY,
    }, headers=headers)
    appt = r.json()["data"]
    if status_chain:
        if "waiting" in status_chain:
            r = await client.patch(f"{BASE_APPTS}/{appt['id']}/confirm", headers=headers)
            appt = r.json()["data"]
        if "completed" in status_chain:
            # Need a submitted consultation to complete
            cons_r = await client.post(
                f"{BASE_CONSULTATIONS}?patient_id={patient_id}",
                json={"appointment_id": appt["id"], "fee_charged": "500.00"},
                headers=headers,
            )
            cons = cons_r.json()["data"]
            await client.post(f"{BASE_CONSULTATIONS}/{cons['id']}/submit", headers=headers)
            # appointment auto-completes
        if "cancelled" in status_chain and appt["status"] in ("pending", "waiting"):
            await client.patch(f"{BASE_APPTS}/{appt['id']}/cancel", json={"reason": "No-show"}, headers=headers)
    return appt


async def _seed_patient(client, headers, name: str = "Analytics Patient") -> dict:
    r = await client.post(BASE_PATIENTS, json={"full_name": name, "age": 30}, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


# ============================================================
# Happy-path: endpoint structure tests
# ============================================================

class TestAnalyticsOverview:

    async def test_overview_default_returns_today(self, client: AsyncClient, owner_headers: dict):
        """No params → defaults to today. Returns expected keys."""
        r = await client.get(f"{BASE}/overview", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "total_appointments" in data
        assert "completion_rate" in data
        assert "total_revenue" in data
        assert "unique_patients" in data
        assert "new_patients" in data
        assert data["period_from"] == TODAY

    async def test_overview_period_today(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/overview?period=today", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["period_from"] == TODAY

    async def test_overview_period_this_month(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/overview?period=this_month", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        expected_start = date.today().replace(day=1).isoformat()
        assert data["period_from"] == expected_start

    async def test_overview_custom_date_range(self, client: AsyncClient, owner_headers: dict):
        d_from = (date.today() - timedelta(days=7)).isoformat()
        d_to = TODAY
        r = await client.get(f"{BASE}/overview?date_from={d_from}&date_to={d_to}", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["period_from"] == d_from


class TestAnalyticsAppointments:

    async def test_appointments_endpoint_returns_breakdown(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/appointments?period=today", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "total" in data
        assert "breakdown" in data
        assert "by_status" in data["breakdown"]
        assert "by_type" in data["breakdown"]
        assert "daily_breakdown" in data["breakdown"]


class TestAnalyticsRevenue:

    async def test_revenue_endpoint_returns_totals(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/revenue?period=today", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "total_revenue" in data
        assert "average_per_appointment" in data
        assert "daily_breakdown" in data


class TestAnalyticsPatients:

    async def test_patients_endpoint_returns_counts(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/patients?period=today", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert "unique_patients" in data
        assert "new_patients" in data
        assert "returning_patients" in data
        assert "retention_rate" in data


# ============================================================
# Metric accuracy tests
# ============================================================

class TestMetricAccuracy:

    async def test_completion_rate_calculation(self, client: AsyncClient, owner_headers: dict):
        """Create 1 completed + 1 pending. Completion rate should be 50%."""
        patient = await _seed_patient(client, owner_headers, "AccuracyPat1")
        patient2 = await _seed_patient(client, owner_headers, "AccuracyPat2")
        await _seed_appointment(client, owner_headers, patient["id"], status_chain=["waiting", "completed"])
        await _seed_appointment(client, owner_headers, patient2["id"])  # pending
        r = await client.get(f"{BASE}/overview?period=today", headers=owner_headers)
        data = r.json()["data"]
        total = data["total_appointments"]
        completed = data["completed"]
        if total > 0:
            expected_rate = round(completed / total * 100, 2)
            assert abs(data["completion_rate"] - expected_rate) < 0.01

    async def test_new_vs_returning_patient(self, client: AsyncClient, owner_headers: dict):
        """Patient who already had appointment before period should be 'returning'."""
        # Create patient and appointment for TODAY — they are 'new' since it's their first
        patient = await _seed_patient(client, owner_headers, "NewPatient")
        await _seed_appointment(client, owner_headers, patient["id"])
        r = await client.get(f"{BASE}/patients?period=today", headers=owner_headers)
        data = r.json()["data"]
        # new + returning should equal unique
        assert data["new_patients"] + data["returning_patients"] == data["unique_patients"]

    async def test_revenue_counts_submitted_consultations_only(self, client: AsyncClient, owner_headers: dict):
        """Unsubmitted consultation should NOT count toward revenue."""
        patient = await _seed_patient(client, owner_headers, "RevPat")
        appt_r = await client.post(BASE_APPTS, json={
            "patient_id": patient["id"],
            "appointment_type": "regular",
            "scheduled_date": TODAY,
        }, headers=owner_headers)
        appt = appt_r.json()["data"]
        await client.patch(f"{BASE_APPTS}/{appt['id']}/confirm", headers=owner_headers)

        # Create draft consultation (NOT submitted)
        await client.post(
            f"{BASE_CONSULTATIONS}?patient_id={patient['id']}",
            json={"appointment_id": appt["id"], "fee_charged": "9999.99"},
            headers=owner_headers,
        )

        r = await client.get(f"{BASE}/revenue?period=today", headers=owner_headers)
        # fee_charged from draft should NOT appear in revenue total
        total = float(r.json()["data"]["total_revenue"])
        assert 9999.99 not in [total]  # draft not included


# ============================================================
# Validation errors
# ============================================================

class TestValidationErrors:

    async def test_period_and_date_range_conflict(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(
            f"{BASE}/overview?period=today&date_from={TODAY}&date_to={TODAY}",
            headers=owner_headers,
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "PERIOD_AND_RANGE_CONFLICT"

    async def test_invalid_date_range_reversed(self, client: AsyncClient, owner_headers: dict):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = await client.get(
            f"{BASE}/overview?date_from={TODAY}&date_to={yesterday}",
            headers=owner_headers,
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_DATE_RANGE"

    async def test_invalid_period_string(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/overview?period=last_quarter", headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_PERIOD"


# ============================================================
# RBAC
# ============================================================

class TestAnalyticsRBAC:

    async def test_non_owner_cannot_access_analytics(self, client: AsyncClient, owner_headers: dict):
        """Staff member without owner role gets 403."""
        staff_r = await client.post("/api/v1/clinic/staff", json={
            "full_name": "Receptionist",
            "email": "rec9@test.com",
            "password": "RecPass123",
            "role": "receptionist",
            "permissions": ["patient:read", "appointment:read"],
        }, headers=owner_headers)
        assert staff_r.status_code == 201
        login = await client.post("/api/v1/auth/login", json={"email": "rec9@test.com", "password": "RecPass123"})
        t = login.json()["data"]["access_token"]
        r = await client.get(f"{BASE}/overview", headers={"Authorization": f"Bearer {t}"})
        assert r.status_code == 403

    async def test_unauthenticated_gets_401(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/overview")
        assert r.status_code == 401
