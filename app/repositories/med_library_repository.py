# Standard library
import uuid

# Third-party
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.models.med_library import MedLibrary


class MedLibraryRepository:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_all_for_dentist(self, dentist_id: uuid.UUID) -> list[MedLibrary]:
        """
        Returns system meds + this dentist's custom meds.
        Custom meds first, then system. Both sorted by usage_count DESC.
        """
        result = await self.db.execute(
            select(MedLibrary)
            .where(
                (MedLibrary.source == "system") |
                (MedLibrary.dentist_id == dentist_id)
            )
            .order_by(
                MedLibrary.source.asc(),          # 'custom' sorts before 'system'
                MedLibrary.usage_count.desc(),
                MedLibrary.name.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_id(self, med_id: uuid.UUID) -> MedLibrary | None:
        result = await self.db.execute(
            select(MedLibrary).where(MedLibrary.id == med_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name_and_dosage_and_dentist(
        self,
        name: str,
        dosage: str | None,
        dentist_id: uuid.UUID,
    ) -> MedLibrary | None:
        if dosage is None:
            # If no dosage — match any entry with same name regardless of dosage
            result = await self.db.execute(
                select(MedLibrary).where(
                    MedLibrary.name == name,
                    MedLibrary.dentist_id == dentist_id,
                )    
            )
        else:
            # If dosage provided — exact match on name + dosage
            result = await self.db.execute(
                select(MedLibrary).where(
                    MedLibrary.name == name,
                    MedLibrary.dosage == dosage,
                    MedLibrary.dentist_id == dentist_id,
                )
            )
        return result.scalar_one_or_none()

    async def create_custom(
        self,
        dentist_id: uuid.UUID,
        name: str,
        dosage: str | None,
        frequency: str | None,
        duration: str | None,
        instructions: str | None,
    ) -> MedLibrary:
        med = MedLibrary(
            name=name,
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            instructions=instructions,
            source="custom",
            dentist_id=dentist_id,
            usage_count=0,
        )
        self.db.add(med)
        await self.db.flush()
        return med

    async def increment_usage(self, med_id: uuid.UUID) -> None:
        """Atomic increment. Called on consultation finalise."""
        await self.db.execute(
            update(MedLibrary)
            .where(MedLibrary.id == med_id)
            .values(usage_count=MedLibrary.usage_count + 1)
        )

    async def update(
        self, med: MedLibrary, **kwargs
    ) -> MedLibrary:
        for field, value in kwargs.items():
            setattr(med, field, value)
        await self.db.flush()
        return med
    
    async def delete(self, med: MedLibrary) -> None:
        await self.db.delete(med)
        await self.db.flush()