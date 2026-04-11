# Standard library
import uuid
from datetime import datetime, timezone
from typing import Any

# Third-party
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.models.user import User


class UserRepository:
    """Data access layer for the users table."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str) -> User:
        user = User(email=email, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.flush()   # get the auto-generated id
        return user
    
    async def update_password(self, user_id: uuid.UUID, new_hashed_password: str) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=new_hashed_password)
        )

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )

    async def exists_by_email(self, email: str) -> bool:
        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )
        return result.scalar_one_or_none() is not None
