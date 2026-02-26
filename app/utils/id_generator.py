# Standard library
import uuid
from datetime import datetime, timezone

# Third-party
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.models.appointment import Appointment
from app.models.patient import Patient


async def generate_patient_code(clinic_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Generate a unique patient code in the format PAT-YYYY-NNNNN.
    Sequence is per-clinic per-year — resets on 1st Jan.
    Example: PAT-2026-00001, PAT-2026-00002, ...
    """
    year = datetime.now(timezone.utc).year

    # Count existing patients in this clinic this year (including soft-deleted)
    result = await db.execute(
        select(func.count(Patient.id)).where(
            Patient.clinic_id == clinic_id,
            func.extract("year", Patient.created_at) == year,
        )
    )
    count = result.scalar_one() or 0
    return f"PAT-{year}-{str(count + 1).zfill(5)}"


async def generate_appointment_code(clinic_id: uuid.UUID, db: AsyncSession) -> str:
    """
    Generate a unique appointment code in the format APT-YYYY-NNNNN.
    Sequence is per-clinic per-year.
    """
    year = datetime.now(timezone.utc).year

    result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.clinic_id == clinic_id,
            func.extract("year", Appointment.created_at) == year,
        )
    )
    count = result.scalar_one() or 0
    return f"APT-{year}-{str(count + 1).zfill(5)}"
