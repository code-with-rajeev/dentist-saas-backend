# Standard library
import uuid

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal
from app.core.exceptions import ConflictException
from app.repositories.med_library_repository import MedLibraryRepository
from app.schemas.med_library import MedLibraryCreate, MedLibraryResponse
from app.core.exceptions import NotFoundException, ForbiddenException
from app.schemas.med_library import MedLibraryUpdate

class MedLibraryService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = MedLibraryRepository(db)

    async def get_meds_for_dentist(
        self, dentist_id: uuid.UUID
    ) -> list[MedLibraryResponse]:
        meds = await self.repo.get_all_for_dentist(dentist_id)
        return [MedLibraryResponse.model_validate(m) for m in meds]

    async def create_custom_med(
        self,
        dentist_id: uuid.UUID,
        data: MedLibraryCreate,
    ) -> MedLibraryResponse:
        existing = await self.repo.get_by_name_and_dosage_and_dentist(data.name, data.dosage, dentist_id)
        if existing is not None:
            raise ConflictException(
                code="MED_ALREADY_EXISTS",
                message=f"You already have a medication named '{data.name}'",
            )
        med = await self.repo.create_custom(
            dentist_id=dentist_id,
            name=data.name,
            dosage=data.dosage,
            frequency=data.frequency,
            duration=data.duration,
            instructions=data.instructions,
        )
        return MedLibraryResponse.model_validate(med)

    async def increment_usage(self, med_id: uuid.UUID) -> None:
        """
        Soft fail — if med was deleted after prescription,
        don't crash the finalise flow.
        """
        med = await self.repo.get_by_id(med_id)
        if med is None:
            return
        await self.repo.increment_usage(med_id)
    
    async def update_custom_med(
        self,
        med_id: uuid.UUID,
        dentist_id: uuid.UUID,
        data: MedLibraryUpdate,
    ) -> MedLibraryResponse:
        med = await self.repo.get_by_id(med_id)
        if med is None:
            raise NotFoundException(
                code="MED_NOT_FOUND",
                message="Medication not found",
            )
        # Guard — dentist can only edit their own custom meds
        if med.source != "custom" or med.dentist_id != dentist_id:
            raise ForbiddenException(
                code="MED_NOT_YOURS",
                message="You can only edit your own custom medications",
            )
        update_fields = data.model_dump(exclude_none=True)
        if update_fields:
            await self.repo.update(med, **update_fields)
        return MedLibraryResponse.model_validate(med)

    async def delete_custom_med(
        self,
        med_id: uuid.UUID,
        dentist_id: uuid.UUID,
    ) -> None:
        med = await self.repo.get_by_id(med_id)
        if med is None:
            raise NotFoundException(
                code="MED_NOT_FOUND",
                message="Medication not found",
            )
        # Guard — dentist can only delete their own custom meds
        if med.source != "custom" or med.dentist_id != dentist_id:
            raise ForbiddenException(
                code="MED_NOT_YOURS",
                message="You can only delete your own custom medications",
            )
        await self.repo.delete(med)