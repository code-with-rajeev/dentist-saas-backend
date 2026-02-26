"""
Integration tests for the Auth module.
Each test runs in an isolated, rolled-back DB transaction.
Run with: pytest tests/integration/test_auth.py -v
"""

# Third-party
import pytest
from httpx import AsyncClient

BASE = "/api/v1/auth"


class TestRegister:

    async def test_register_success(self, client: AsyncClient):
        r = await client.post(f"{BASE}/register", json={
            "clinic_name": "Happy Teeth Clinic",
            "dentist_name": "Dr. Alice",
            "full_name": "Dr. Alice",
            "email": "alice@happyteeth.com",
            "password": "StrongPass123",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["success"] is True
        assert data["data"]["clinic"]["name"] == "Happy Teeth Clinic"
        assert data["data"]["user"]["role"] == "clinic_owner"
        assert len(data["data"]["user"]["permissions"]) == 12
        assert "access_token" in data["data"]

    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {
            "clinic_name": "Clinic A",
            "dentist_name": "Dr. Bob",
            "full_name": "Dr. Bob",
            "email": "bob@clinic.com",
            "password": "StrongPass123",
        }
        await client.post(f"{BASE}/register", json=payload)
        r = await client.post(f"{BASE}/register", json=payload)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    async def test_register_missing_required_fields(self, client: AsyncClient):
        r = await client.post(f"{BASE}/register", json={"email": "x@x.com"})
        assert r.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        r = await client.post(f"{BASE}/register", json={
            "clinic_name": "C", "dentist_name": "D",
            "full_name": "D", "email": "d@d.com", "password": "short",
        })
        assert r.status_code == 422


class TestLogin:

    async def test_login_success(self, client: AsyncClient, registered_owner: dict):
        r = await client.post(f"{BASE}/login", json={
            "email": "owner@testclinic.com",
            "password": "TestPass123",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, registered_owner: dict):
        r = await client.post(f"{BASE}/login", json={
            "email": "owner@testclinic.com",
            "password": "WrongPassword",
        })
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"

    async def test_login_nonexistent_email(self, client: AsyncClient):
        r = await client.post(f"{BASE}/login", json={
            "email": "nobody@nowhere.com",
            "password": "SomePass123",
        })
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


class TestMe:

    async def test_me_returns_full_profile(self, client: AsyncClient, owner_headers: dict):
        r = await client.get(f"{BASE}/me", headers=owner_headers)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["clinic_name"] == "Test Dental Clinic"
        assert data["role"] == "clinic_owner"
        assert len(data["permissions"]) == 12

    async def test_me_without_token_returns_401(self, client: AsyncClient):
        r = await client.get(f"{BASE}/me")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHORIZED"

    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient):
        r = await client.get(f"{BASE}/me", headers={"Authorization": "Bearer invalid"})
        assert r.status_code == 401


class TestLogout:

    async def test_logout_success(self, client: AsyncClient):
        r = await client.post(f"{BASE}/logout")
        assert r.status_code == 200
        assert r.json()["success"] is True