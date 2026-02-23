# Standard library
from collections.abc import AsyncGenerator

# Third-party
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Internal
from app.core.config import settings

# ============================================================
# Async engine
# ============================================================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,   # log SQL in development only
    pool_pre_ping=True,             # verify connections before use
    pool_size=10,
    max_overflow=20,
)

# ============================================================
# Session factory
# ============================================================
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,         # objects accessible after commit without re-query
    autocommit=False,
    autoflush=False,
)


# ============================================================
# FastAPI dependency
# ============================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async DB session for use in FastAPI route dependencies.

    Usage:
        async def my_route(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
