"""
Integration tests for Phase 7 — Appointment Module.
Covers: create, list+filters, queue, confirm, cancel, reschedule, no-show, complete,
        state machine enforcement, RBAC, patient sub-route.
Run with: pytest tests/integration/test_appointments.py -v
"""

# Standard library
import uuid
from datetime import date, timedelta

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/appointments"
PATIENTS = "/api/v1/patients"
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
TODAY = date.today().isoformat()


# ============================================================
# Helpers
# ============================================================

async def create_patient(client, headers) -> dict:
    r = await client.post(PATIENTS, json={"full_name": "Test Patient", "age": 30}, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


async def create_appointment(client, headers, patient_id: str, appt_date: str = TOMORROW) -> dict:
    r = await client.post(BASE, json={
        "patient_id": patient_id,
        "appointment_type": "regular",
        "scheduled_date": appt_date,
        "scheduled_time_slot": "10:00",
    }, headers=headers)
    assert r.status_code == 201, f"Create appointment failed: {r.text}"
    return r.json()["data"]


async def confirm_appointment(client, headers, appt_id: str) -> dict:
    r = await client.patch(f"{BASE}/{appt_id}/confirm", headers=headers)
    assert r.status_code == 200, f"Confirm failed: {r.text}"
    return r.json()["data"]


# ============================================================
# Create
# ============================================================

class TestCreateAppointment:

    async def test_create_appointment_success(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        r = await client.post(BASE, json={
            "patient_id": patient["id"],
            "appointment_type": "regular",
            "scheduled_date": TOMORROW,
            "scheduled_time_slot": "10:00",
        }, headers=owner_headers)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["status"] == "pending"
        assert data["appointment_code"].startswith("APT-")
        assert data["patient_id"] == patient["id"]

    async def test_appointment_code_format(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        data = await create_appointment(client, owner_headers, patient["id"])
        code = data["appointment_code"]
        parts = code.split("-")
        assert parts[0] == "APT"
        assert len(parts[1]) == 4   # year
        assert len(parts[2]) == 5   # sequence

    async def test_create_appointment_for_missing_patient_404(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(BASE, json={
            "patient_id": str(uuid.uuid4()),
            "appointment_type": "regular",
            "scheduled_date": TOMORROW,
        }, headers=owner_headers)
        assert r.status_code == 404

    async def test_create_appointment_requires_auth(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        r = await client.post(BASE, json={
            "patient_id": patient["id"],
            "appointment_type": "regular",
            "scheduled_date": TOMORROW,
        })
        assert r.status_code == 401

    async def test_create_appointment_invalid_type(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        r = await client.post(BASE, json={
            "patient_id": patient["id"],
            "appointment_type": "xyz_invalid",
            "scheduled_date": TOMORROW,
        }, headers=owner_headers)
        assert r.status_code == 422


# ============================================================
# List + Filters
# ============================================================

class TestListAppointments:

    async def test_list_all(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        await create_appointment(client, owner_headers, patient["id"])
        await create_appointment(client, owner_headers, patient["id"])
        r = await client.get(BASE, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 2

    async def test_filter_by_status(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        await create_appointment(client, owner_headers, patient["id"])   # stays pending

        r = await client.get(f"{BASE}?status=waiting", headers=owner_headers)
        assert r.json()["meta"]["total"] == 1
        assert r.json()["data"][0]["status"] == "waiting"

    async def test_filter_by_date(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        r1 = await client.post(BASE, json={
            "patient_id": patient["id"],
            "appointment_type": "regular",
            "scheduled_date": TOMORROW,
        }, headers=owner_headers)
        assert r1.status_code == 201

        r = await client.get(f"{BASE}?date={TOMORROW}", headers=owner_headers)
        assert r.json()["meta"]["total"] == 1

    async def test_search_by_appointment_code(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        code = appt["appointment_code"]
        r = await client.get(f"{BASE}?search={code}", headers=owner_headers)
        assert r.json()["meta"]["total"] == 1
        assert r.json()["data"][0]["appointment_code"] == code


# ============================================================
# Queue
# ============================================================

class TestQueue:

    async def test_queue_returns_today_waiting(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"], TODAY)
        await confirm_appointment(client, owner_headers, appt["id"])

        r = await client.get(f"{BASE}/queue", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total_waiting"] == 1
        assert data["items"][0]["id"] == appt["id"]

    async def test_queue_assigns_sequential_positions(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        a1 = await create_appointment(client, owner_headers, patient["id"], TODAY)
        a2 = await create_appointment(client, owner_headers, patient["id"], TODAY)
        await confirm_appointment(client, owner_headers, a1["id"])
        confirmed2 = await confirm_appointment(client, owner_headers, a2["id"])
        assert confirmed2["queue_position"] == 2


# ============================================================
# State Machine
# ============================================================

class TestStateMachine:

    async def test_confirm_pending_to_waiting(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/confirm", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "waiting"
        assert r.json()["data"]["queue_position"] is not None

    async def test_double_confirm_returns_409(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/confirm", headers=owner_headers)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "APPOINTMENT_ALREADY_CONFIRMED"

    async def test_cancel_pending_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/cancel", json={"reason": "Patient request"}, headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] == "cancelled"
        assert data["cancelled_reason"] == "Patient request"

    async def test_cancel_waiting_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/cancel", json={}, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "cancelled"

    async def test_cannot_cancel_completed_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        await client.patch(f"{BASE}/{appt['id']}/complete", headers=owner_headers)
        r = await client.patch(f"{BASE}/{appt['id']}/cancel", json={}, headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    async def test_reschedule_pending_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        new_date = (date.today() + timedelta(days=3)).isoformat()
        r = await client.patch(f"{BASE}/{appt['id']}/reschedule", json={
            "scheduled_date": new_date, "scheduled_time_slot": "14:00"
        }, headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["scheduled_date"] == new_date
        assert data["status"] == "pending"

    async def test_reschedule_waiting_resets_to_pending(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        new_date = (date.today() + timedelta(days=5)).isoformat()
        r = await client.patch(f"{BASE}/{appt['id']}/reschedule", json={
            "scheduled_date": new_date
        }, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "pending"
        assert r.json()["data"]["queue_position"] is None

    async def test_mark_no_show(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"], TODAY)
        await confirm_appointment(client, owner_headers, appt["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/no-show", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "no_show"

    async def test_cannot_no_show_pending_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/no-show", headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"

    async def test_complete_waiting_appointment(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        appt = await create_appointment(client, owner_headers, patient["id"])
        await confirm_appointment(client, owner_headers, appt["id"])
        r = await client.patch(f"{BASE}/{appt['id']}/complete", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "completed"


# ============================================================
# Patient sub-route
# ============================================================

class TestPatientAppointments:

    async def test_get_patient_appointments(self, client: AsyncClient, owner_headers: dict):
        patient = await create_patient(client, owner_headers)
        await create_appointment(client, owner_headers, patient["id"])
        await create_appointment(client, owner_headers, patient["id"])
        r = await client.get(f"{PATIENTS}/{patient['id']}/appointments", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 2

    async def test_patient_cannot_see_other_patient_appointments(self, client: AsyncClient, owner_headers: dict):
        p1 = await create_patient(client, owner_headers)
        p2 = await create_patient(client, owner_headers)
        await create_appointment(client, owner_headers, p1["id"])
        r = await client.get(f"{PATIENTS}/{p2['id']}/appointments", headers=owner_headers)
        assert r.json()["meta"]["total"] == 0
