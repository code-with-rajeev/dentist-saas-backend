# Standard library
from collections.abc import AsyncGenerator

# Third-party
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Internal
from app.core.config import settings
from app.main import app

# ============================================================
# Two separate engines:
#   - test_engine: NullPool so every get_db call is a fresh connection
#     (no pool contention between the app's DB operations and fixtures)
#   - cleanup_engine: NullPool for TRUNCATE between tests
# Using NullPool avoids the asyncpg "another operation is in progress"
# error that occurs when sharing pooled connections across async contexts.
# ============================================================

app_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
AppSessionLocal = async_sessionmaker(
    bind=app_engine, class_=AsyncSession, expire_on_commit=False
)

cleanup_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)

_TRUNCATE_SQL = (
    "TRUNCATE TABLE follow_ups, medications, consultations, appointments, "
    "user_permissions, clinic_members, patients, clinics, users "
    "RESTART IDENTITY CASCADE"
)


async def _truncate_all() -> None:
    async with cleanup_engine.begin() as conn:
        await conn.execute(text(_TRUNCATE_SQL))


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db():
    """Truncate all tables before each test for clean isolation."""
    await _truncate_all()
    yield


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired to a NullPool engine (fresh connection per request)."""
    async def override_get_db():
        async with AppSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from app.database.session import get_db
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ============================================================
# Reusable data fixtures
# ============================================================
OWNER_REGISTER_PAYLOAD = {
    "clinic_name": "Test Dental Clinic",
    "dentist_name": "Dr. Test Owner",
    "dentist_reg_id": "TEST-REG-001",
    "full_name": "Dr. Test Owner",
    "email": "owner@testclinic.com",
    "password": "TestPass123",
    "phone": "9000000001",
}


@pytest_asyncio.fixture
async def registered_owner(client: AsyncClient) -> dict:
    r = await client.post("/api/v1/auth/register", json=OWNER_REGISTER_PAYLOAD)
    assert r.status_code == 201, f"Register failed: {r.text}"
    return r.json()["data"]


@pytest_asyncio.fixture
async def owner_token(registered_owner: dict) -> str:
    return registered_owner["access_token"]


@pytest_asyncio.fixture
async def owner_headers(owner_token: str) -> dict:
    return {"Authorization": f"Bearer {owner_token}"}


@pytest_asyncio.fixture
async def clinic_id(registered_owner: dict) -> str:
    return registered_owner["clinic"]["id"]