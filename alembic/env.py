# Standard library
import asyncio
from logging.config import fileConfig

# Third-party
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Internal — must import settings and Base before models
from app.core.config import settings
from app.database.base import Base

# Import ALL models here so Alembic can discover them for autogenerate.
# Add each model as it is created in Phase 2.
# from app.models.user import User
# from app.models.clinic import Clinic
# from app.models.clinic_member import ClinicMember
# from app.models.user_permission import UserPermission
# from app.models.patient import Patient
# from app.models.appointment import Appointment
# from app.models.consultation import Consultation
# from app.models.medication import Medication
# from app.models.follow_up import FollowUp

# Alembic Config object
config = context.config

# Set the database URL from our settings (not from alembic.ini)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata — Alembic uses this to detect schema changes
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    async_engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with async_engine.begin() as conn:
        await conn.run_sync(do_run_migrations)
    await async_engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async SQLAlchemy)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
