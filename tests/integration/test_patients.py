"""
Integration tests for Phase 6 — Patient Module.
Run with: pytest tests/integration/test_patients.py -v
"""

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/patients"


class TestCreatePatient:

    async def test_create_patient_success(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(BASE, json={
            "full_name": "Rahul Sharma",
            "age": 35,
            "phone": "9876543210",
        }, headers=owner_headers)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["full_name"] == "Rahul Sharma"
        assert data["age"] == 35
        assert data["patient_code"].startswith("PAT-")
        assert data["total_appointments"] == 0
        assert data["last_visit"] is None

    async def test_patient_code_format(self, client: AsyncClient, owner_headers: dict):
        """Code must be PAT-YYYY-NNNNN"""
        r = await client.post(BASE, json={"full_name": "Code Test", "age": 25}, headers=owner_headers)
        code = r.json()["data"]["patient_code"]
        parts = code.split("-")
        assert len(parts) == 3
        assert parts[0] == "PAT"
        assert len(parts[1]) == 4  # year
        assert len(parts[2]) == 5  # sequence

    async def test_patient_code_is_sequential(self, client: AsyncClient, owner_headers: dict):
        """Second patient code should be one higher than first"""
        r1 = await client.post(BASE, json={"full_name": "First", "age": 30}, headers=owner_headers)
        r2 = await client.post(BASE, json={"full_name": "Second", "age": 31}, headers=owner_headers)
        seq1 = int(r1.json()["data"]["patient_code"].split("-")[2])
        seq2 = int(r2.json()["data"]["patient_code"].split("-")[2])
        assert seq2 == seq1 + 1

    async def test_create_patient_missing_required_fields(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(BASE, json={"phone": "9999999999"}, headers=owner_headers)
        assert r.status_code == 422

    async def test_create_patient_invalid_age(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(BASE, json={"full_name": "Test", "age": 0}, headers=owner_headers)
        assert r.status_code == 422

    async def test_create_patient_invalid_gender(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(BASE, json={"full_name": "Test", "age": 25, "gender": "unknown"}, headers=owner_headers)
        assert r.status_code == 422

    async def test_create_patient_requires_auth(self, client: AsyncClient):
        r = await client.post(BASE, json={"full_name": "No Auth", "age": 25})
        assert r.status_code == 401

    async def test_create_patient_requires_patient_write(self, client: AsyncClient, owner_headers: dict):
        """Staff without patient:write cannot create patients"""
        # Add staff with only appointment:read
        staff_r = await client.post("/api/v1/clinic/staff", json={
            "full_name": "ReadOnly Staff",
            "email": "readonly@test.com",
            "password": "StaffPass123",
            "role": "helper",
            "permissions": ["appointment:read"],
        }, headers=owner_headers)
        assert staff_r.status_code == 201
        login_r = await client.post("/api/v1/auth/login", json={"email": "readonly@test.com", "password": "StaffPass123"})
        token = login_r.json()["data"]["access_token"]
        r = await client.post(BASE, json={"full_name": "Blocked", "age": 25}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403


class TestListPatients:

    async def _create_patient(self, client, headers, name, phone=None, age=30):
        r = await client.post(BASE, json={"full_name": name, "age": age, "phone": phone}, headers=headers)
        assert r.status_code == 201
        return r.json()["data"]

    async def test_list_patients_empty(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(BASE, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"] == []
        assert r.json()["meta"]["total"] == 0

    async def test_list_patients_returns_all(self, client: AsyncClient, owner_headers: dict):
        await self._create_patient(client, owner_headers, "Priya Patel")
        await self._create_patient(client, owner_headers, "Raju Kumar")
        r = await client.get(BASE, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 2

    async def test_search_by_name(self, client: AsyncClient, owner_headers: dict):
        await self._create_patient(client, owner_headers, "Rahul Mehta")
        await self._create_patient(client, owner_headers, "Sita Devi")
        r = await client.get(f"{BASE}?search=Rahul", headers=owner_headers)
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1
        assert r.json()["data"][0]["full_name"] == "Rahul Mehta"

    async def test_search_by_phone(self, client: AsyncClient, owner_headers: dict):
        await self._create_patient(client, owner_headers, "Phone Patient", phone="9876543210")
        await self._create_patient(client, owner_headers, "Other Patient", phone="1111111111")
        r = await client.get(f"{BASE}?search=98765", headers=owner_headers)
        assert r.status_code == 200
        results = r.json()["data"]
        assert len(results) == 1
        assert results[0]["phone"] == "9876543210"

    async def test_search_by_patient_code(self, client: AsyncClient, owner_headers: dict):
        p = await self._create_patient(client, owner_headers, "Code Search Patient")
        code = p["patient_code"]
        r = await client.get(f"{BASE}?search={code}", headers=owner_headers)
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1

    async def test_search_no_results(self, client: AsyncClient, owner_headers: dict):
        await self._create_patient(client, owner_headers, "Someone")
        r = await client.get(f"{BASE}?search=ZZZNOMATCH", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["meta"]["total"] == 0

    async def test_pagination_meta(self, client: AsyncClient, owner_headers: dict):
        for i in range(5):
            await self._create_patient(client, owner_headers, f"Patient {i}")
        r = await client.get(f"{BASE}?page=1&per_page=2", headers=owner_headers)
        meta = r.json()["meta"]
        assert meta["total"] == 5
        assert meta["per_page"] == 2
        assert meta["pages"] == 3
        assert len(r.json()["data"]) == 2


class TestGetPatient:

    async def test_get_patient_success(self, client: AsyncClient, owner_headers: dict):
        r1 = await client.post(BASE, json={"full_name": "Detail Patient", "age": 40}, headers=owner_headers)
        pid = r1.json()["data"]["id"]
        r = await client.get(f"{BASE}/{pid}", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["id"] == pid

    async def test_get_nonexistent_patient_returns_404(self, client: AsyncClient, owner_headers: dict):
        import uuid
        r = await client.get(f"{BASE}/{uuid.uuid4()}", headers=owner_headers)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "PATIENT_NOT_FOUND"


class TestUpdatePatient:

    async def test_patch_patient_updates_fields(self, client: AsyncClient, owner_headers: dict):
        r1 = await client.post(BASE, json={"full_name": "Old Name", "age": 30}, headers=owner_headers)
        pid = r1.json()["data"]["id"]
        r = await client.patch(f"{BASE}/{pid}", json={"full_name": "New Name", "age": 31}, headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["data"]["full_name"] == "New Name"
        assert r.json()["data"]["age"] == 31

    async def test_patch_patient_partial_update(self, client: AsyncClient, owner_headers: dict):
        """Only provided fields should change"""
        r1 = await client.post(BASE, json={"full_name": "Stay Same", "age": 25, "phone": "9000000001"}, headers=owner_headers)
        pid = r1.json()["data"]["id"]
        r = await client.patch(f"{BASE}/{pid}", json={"age": 26}, headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["age"] == 26
        assert data["full_name"] == "Stay Same"    # unchanged
        assert data["phone"] == "9000000001"        # unchanged

    async def test_patch_nonexistent_patient(self, client: AsyncClient, owner_headers: dict):
        import uuid
        r = await client.patch(f"{BASE}/{uuid.uuid4()}", json={"age": 30}, headers=owner_headers)
        assert r.status_code == 404
