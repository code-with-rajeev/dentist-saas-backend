"""
Integration tests for Phase 8 — Consultation Module.
Covers: create, update, submit (lock + auto-complete appointment),
        get, patient list, PDF generate + download, stubs, RBAC.

API layout:
  POST   /api/v1/consultations?patient_id=...
  PATCH  /api/v1/consultations/{id}
  POST   /api/v1/consultations/{id}/submit
  GET    /api/v1/consultations/{id}
  GET    /api/v1/consultations?patient_id=...
  POST   /api/v1/consultations/{id}/generate-report
  GET    /api/v1/consultations/{id}/report
  POST   /api/v1/consultations/{id}/send-report   (stub)

Run with: pytest tests/integration/test_consultations.py -v
"""

# Standard library
import uuid
from datetime import date, timedelta

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/consultations"
BASE_PATIENTS = "/api/v1/patients"
BASE_APPTS = "/api/v1/appointments"
TODAY = date.today().isoformat()


# ============================================================
# Shared setup helpers
# ============================================================

async def _create_patient(client, headers) -> dict:
    r = await client.post(BASE_PATIENTS, json={"full_name": "Consultation Patient", "age": 35}, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


async def _create_appointment(client, headers, patient_id: str) -> dict:
    r = await client.post(BASE_APPTS, json={
        "patient_id": patient_id,
        "appointment_type": "regular",
        "scheduled_date": TODAY,
    }, headers=headers)
    assert r.status_code == 201
    return r.json()["data"]


async def _confirm_appointment(client, headers, appt_id: str) -> dict:
    r = await client.patch(f"{BASE_APPTS}/{appt_id}/confirm", headers=headers)
    assert r.status_code == 200
    return r.json()["data"]


async def _get_waiting_appt(client, headers):
    """Create patient → appointment → confirm → return both."""
    patient = await _create_patient(client, headers)
    appt = await _create_appointment(client, headers, patient["id"])
    appt = await _confirm_appointment(client, headers, appt["id"])
    return patient, appt


async def _create_consultation(client, headers, patient_id: str, appt_id: str, **extra) -> dict:
    payload = {
        "appointment_id": appt_id,
        "symptoms": "Toothache upper left",
        "clinical_notes": "Cavity detected",
        "fee_charged": "500.00",
        **extra,
    }
    r = await client.post(f"{BASE}?patient_id={patient_id}", json=payload, headers=headers)
    assert r.status_code == 201, f"Create consultation failed: {r.text}"
    return r.json()["data"]


# ============================================================
# Create Consultation
# ============================================================

class TestCreateConsultation:

    async def test_create_consultation_success(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        r = await client.post(
            f"{BASE}?patient_id={patient['id']}",
            json={
                "appointment_id": appt["id"],
                "symptoms": "Toothache",
                "fee_charged": "300.00",
                "medications": [{"name": "Ibuprofen", "dosage": "400mg", "frequency": "TID"}],
            },
            headers=owner_headers,
        )
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["symptoms"] == "Toothache"
        assert data["is_submitted"] is False
        assert len(data["medications"]) == 1
        assert data["medications"][0]["name"] == "Ibuprofen"

    async def test_create_consultation_pending_appointment_rejected(self, client: AsyncClient, owner_headers: dict):
        patient = await _create_patient(client, owner_headers)
        appt = await _create_appointment(client, owner_headers, patient["id"])  # still pending
        r = await client.post(
            f"{BASE}?patient_id={patient['id']}",
            json={"appointment_id": appt["id"]},
            headers=owner_headers,
        )
        assert r.status_code == 400
        assert "waiting" in r.json()["message"].lower()

    async def test_cannot_create_duplicate_consultation(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.post(
            f"{BASE}?patient_id={patient['id']}",
            json={"appointment_id": appt["id"]},
            headers=owner_headers,
        )
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "CONSULTATION_ALREADY_EXISTS"

    async def test_create_consultation_requires_owner(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        # consultation:write is owner-exclusive; give staff only appointment/patient read
        staff_r = await client.post("/api/v1/clinic/staff", json={
            "full_name": "Staff Member",
            "email": "staff8@test.com",
            "password": "StaffPass123",
            "role": "assistant",
            "permissions": ["patient:read", "appointment:write", "appointment:read"],
        }, headers=owner_headers)
        assert staff_r.status_code == 201
        login = await client.post("/api/v1/auth/login", json={"email": "staff8@test.com", "password": "StaffPass123"})
        staff_token = login.json()["data"]["access_token"]
        r = await client.post(
            f"{BASE}?patient_id={patient['id']}",
            json={"appointment_id": appt["id"]},
            headers={"Authorization": f"Bearer {staff_token}"},
        )
        # Staff without owner role get 403 from require_owner()
        assert r.status_code == 403


# ============================================================
# Update Consultation
# ============================================================

class TestUpdateConsultation:

    async def test_update_draft_consultation(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.patch(
            f"{BASE}/{c['id']}",
            json={"diagnosis": "Caries Grade II", "fee_charged": "750.00"},
            headers=owner_headers,
        )
        assert r.status_code == 200
        assert r.json()["data"]["diagnosis"] == "Caries Grade II"
        assert float(r.json()["data"]["fee_charged"]) == 750.00

    async def test_update_replaces_medications(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"],
                                       medications=[{"name": "OldMed"}])
        r = await client.patch(
            f"{BASE}/{c['id']}",
            json={"medications": [{"name": "NewMed1"}, {"name": "NewMed2"}]},
            headers=owner_headers,
        )
        assert r.status_code == 200
        names = {m["name"] for m in r.json()["data"]["medications"]}
        assert names == {"NewMed1", "NewMed2"}

    async def test_update_medications_empty_clears_all(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"],
                                       medications=[{"name": "SomeMed"}])
        r = await client.patch(
            f"{BASE}/{c['id']}",
            json={"medications": []},
            headers=owner_headers,
        )
        assert r.status_code == 200
        assert r.json()["data"]["medications"] == []


# ============================================================
# Submit Consultation
# ============================================================

class TestSubmitConsultation:

    async def test_submit_locks_form(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["is_submitted"] is True
        assert r.json()["data"]["submitted_at"] is not None

    async def test_submit_auto_completes_appointment(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        appt_r = await client.get(f"{BASE_APPTS}/{appt['id']}", headers=owner_headers)
        assert appt_r.json()["data"]["status"] == "completed"

    async def test_double_submit_returns_400(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        r = await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "CONSULTATION_LOCKED"

    async def test_update_submitted_consultation_returns_400(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        r = await client.patch(
            f"{BASE}/{c['id']}",
            json={"clinical_notes": "Should fail"},
            headers=owner_headers,
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "CONSULTATION_LOCKED"


# ============================================================
# Get Consultation
# ============================================================

class TestGetConsultation:

    async def test_get_consultation_returns_full_detail(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"],
                                       medications=[{"name": "Paracetamol"}])
        r = await client.get(f"{BASE}/{c['id']}", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["id"] == c["id"]
        assert len(data["medications"]) == 1

    async def test_get_nonexistent_consultation_returns_404(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=owner_headers)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "CONSULTATION_NOT_FOUND"


# ============================================================
# Patient consultation list
# ============================================================

class TestPatientConsultations:

    async def test_patient_consultation_list(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.get(f"{BASE}?patient_id={patient['id']}", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 1


# ============================================================
# PDF Generation
# ============================================================

class TestPDFReport:

    async def test_generate_pdf_for_submitted_consultation(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"],
                                       medications=[{"name": "Ibuprofen", "dosage": "400mg"}])
        await client.post(f"{BASE}/{c['id']}/submit", headers=owner_headers)
        r = await client.post(f"{BASE}/{c['id']}/generate-report", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["report_generated"] is True
        assert data["report_path"] is not None
        assert data["report_path"].endswith(".pdf")

    async def test_generate_pdf_draft_rejected(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.post(f"{BASE}/{c['id']}/generate-report", headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "CONSULTATION_NOT_SUBMITTED"


# ============================================================
# Stub Routes
# ============================================================

class TestStubRoutes:

    async def test_send_report_stub_returns_success(self, client: AsyncClient, owner_headers: dict):
        patient, appt = await _get_waiting_appt(client, owner_headers)
        c = await _create_consultation(client, owner_headers, patient["id"], appt["id"])
        r = await client.post(f"{BASE}/{c['id']}/send-report", headers=owner_headers)
        assert r.status_code == 200
        assert "STUB" in r.json()["message"]
