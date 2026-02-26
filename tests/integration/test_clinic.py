"""
Integration tests for the Clinic module (Phase 5).
Covers: settings GET/PATCH, staff CRUD, permission management, RBAC enforcement.
Run with: pytest tests/integration/test_clinic.py -v
"""

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/clinic"
AUTH = "/api/v1/auth"

STAFF_PAYLOAD = {
    "full_name": "Assistant Maya",
    "email": "maya@testclinic.com",
    "password": "StaffPass123",
    "role": "assistant",
    "phone": "9000000002",
}


# ============================================================
# Helpers
# ============================================================

async def add_staff(client: AsyncClient, owner_headers: dict, payload: dict | None = None) -> dict:
    r = await client.post(f"{BASE}/staff", json=payload or STAFF_PAYLOAD, headers=owner_headers)
    assert r.status_code == 201, f"Add staff failed: {r.text}"
    return r.json()["data"]


async def get_staff_token(client: AsyncClient, email: str, password: str) -> dict:
    r = await client.post(f"{AUTH}/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Staff login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


# ============================================================
# Clinic Settings
# ============================================================

class TestClinicSettings:

    async def test_get_settings_as_owner(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/settings", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["name"] == "Test Dental Clinic"
        assert "locked_fields" in data
        assert "name" in data["locked_fields"]

    async def test_get_settings_without_auth(self, client: AsyncClient):
        r = await client.get(f"{BASE}/settings")
        assert r.status_code == 401

    async def test_patch_settings_editable_fields(self, client: AsyncClient, owner_headers: dict):
        r = await client.patch(f"{BASE}/settings", json={
            "phone": "9999999999",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001",
        }, headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["phone"] == "9999999999"
        assert data["city"] == "Mumbai"

    async def test_patch_settings_with_operating_hours(self, client: AsyncClient, owner_headers: dict):
        r = await client.patch(f"{BASE}/settings", json={
            "operating_hours": {
                "monday": {"open": "09:00", "close": "18:00", "is_closed": False},
                "sunday": {"is_closed": True},
            }
        }, headers=owner_headers)
        assert r.status_code == 200
        hours = r.json()["data"]["operating_hours"]
        assert hours["monday"]["open"] == "09:00"
        assert hours["sunday"]["is_closed"] is True

    async def test_patch_settings_invalid_time_format(self, client: AsyncClient, owner_headers: dict):
        r = await client.patch(f"{BASE}/settings", json={
            "operating_hours": {
                "monday": {"open": "9am", "close": "18:00", "is_closed": False}
            }
        }, headers=owner_headers)
        assert r.status_code == 422

    async def test_patch_settings_missing_open_time(self, client: AsyncClient, owner_headers: dict):
        """Day not closed but missing open time → 400"""
        r = await client.patch(f"{BASE}/settings", json={
            "operating_hours": {
                "monday": {"close": "18:00", "is_closed": False}
            }
        }, headers=owner_headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_OPERATING_HOURS"

    async def test_staff_cannot_patch_settings(self, client: AsyncClient, owner_headers: dict):
        """Staff with only settings:read cannot PATCH settings"""
        staff = await add_staff(client, owner_headers)
        staff_headers = await get_staff_token(client, STAFF_PAYLOAD["email"], STAFF_PAYLOAD["password"])
        r = await client.patch(f"{BASE}/settings", json={"city": "Delhi"}, headers=staff_headers)
        assert r.status_code == 403

    async def test_staff_can_read_settings(self, client: AsyncClient, owner_headers: dict):
        """Assistant has clinic:settings:read by default → can GET settings"""
        await add_staff(client, owner_headers)
        staff_headers = await get_staff_token(client, STAFF_PAYLOAD["email"], STAFF_PAYLOAD["password"])
        r = await client.get(f"{BASE}/settings", headers=staff_headers)
        assert r.status_code == 200


# ============================================================
# Staff Management
# ============================================================

class TestStaffManagement:

    async def test_add_staff_success(self, client: AsyncClient, owner_headers: dict):
        r = await client.post(f"{BASE}/staff", json=STAFF_PAYLOAD, headers=owner_headers)
        assert r.status_code == 201
        data = r.json()["data"]
        assert data["full_name"] == "Assistant Maya"
        assert data["role"] == "assistant"
        assert isinstance(data["permissions"], list)

    async def test_add_staff_default_permissions_applied(self, client: AsyncClient, owner_headers: dict):
        """No permissions in payload → recommended defaults applied"""
        payload = {**STAFF_PAYLOAD, "email": "receptionist@testclinic.com",
                   "role": "receptionist", "full_name": "Receptionist Priya"}
        r = await client.post(f"{BASE}/staff", json=payload, headers=owner_headers)
        assert r.status_code == 201
        # Receptionist defaults include appointment:read
        permissions = r.json()["data"]["permissions"]
        assert "appointment:read" in permissions

    async def test_add_staff_duplicate_email_fails(self, client: AsyncClient, owner_headers: dict):
        await add_staff(client, owner_headers)
        r = await client.post(f"{BASE}/staff", json=STAFF_PAYLOAD, headers=owner_headers)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    async def test_add_staff_with_owner_exclusive_permission_fails(
        self, client: AsyncClient, owner_headers: dict
    ):
        payload = {**STAFF_PAYLOAD, "permissions": ["clinic:settings:write"]}  # owner-exclusive
        r = await client.post(f"{BASE}/staff", json=payload, headers=owner_headers)
        assert r.status_code in (400, 403, 422)

    async def test_list_staff(self, client: AsyncClient, owner_headers: dict):
        await add_staff(client, owner_headers)
        r = await client.get(f"{BASE}/staff", headers=owner_headers)
        assert r.status_code == 200
        members = r.json()["data"]
        # At least the owner + 1 staff
        assert len(members) >= 2

    async def test_update_staff_permissions(self, client: AsyncClient, owner_headers: dict):
        staff = await add_staff(client, owner_headers)
        staff_id = staff["id"]
        r = await client.patch(
            f"{BASE}/staff/{staff_id}/permissions",
            json={"permissions": ["appointment:read", "patient:read"]},
            headers=owner_headers,
        )
        assert r.status_code == 200
        perms = r.json()["data"]["permissions"]
        assert set(perms) == {"appointment:read", "patient:read"}

    async def test_update_staff_permissions_with_owner_exclusive_fails(
        self, client: AsyncClient, owner_headers: dict
    ):
        staff = await add_staff(client, owner_headers)
        r = await client.patch(
            f"{BASE}/staff/{staff["id"]}/permissions",
            json={"permissions": ["analytics:read"]},  # owner-exclusive
            headers=owner_headers,
        )
        assert r.status_code in (400, 403, 422)

    async def test_remove_staff_success(self, client: AsyncClient, owner_headers: dict):
        staff = await add_staff(client, owner_headers)
        r = await client.delete(f"{BASE}/staff/{staff['id']}", headers=owner_headers)
        assert r.status_code == 200
        assert r.json()["success"] is True

    async def test_cannot_remove_owner(self, client: AsyncClient, owner_headers: dict, registered_owner: dict):
        owner_member_id = registered_owner["user"]["id"]
        r = await client.delete(f"{BASE}/staff/{owner_member_id}", headers=owner_headers)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "CANNOT_REMOVE_OWNER"

    async def test_non_owner_cannot_list_staff(self, client: AsyncClient, owner_headers: dict):
        await add_staff(client, owner_headers)
        staff_headers = await get_staff_token(client, STAFF_PAYLOAD["email"], STAFF_PAYLOAD["password"])
        r = await client.get(f"{BASE}/staff", headers=staff_headers)
        assert r.status_code == 403
