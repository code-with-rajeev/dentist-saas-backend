# Standard library
import uuid

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — core
from app.core.exceptions import NotFoundException
from app.constants.messages import PATIENT_NOT_FOUND

# Internal — repositories
from app.repositories.patient_repository import PatientRepository

# Internal — utils
from app.utils.id_generator import generate_patient_code
from app.utils.pagination import PaginatedResult

# Internal — schemas
from app.schemas.patient import PatientCreate, PatientListItem, PatientResponse, PatientUpdate


class PatientService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PatientRepository(db)

    async def create_patient(
        self, data: PatientCreate, clinic_id: uuid.UUID
    ) -> PatientResponse:
        # Generate unique patient code
        patient_code = await generate_patient_code(clinic_id, self.db)

        patient = await self.repo.create(
            clinic_id=clinic_id,
            patient_code=patient_code,
            full_name=data.full_name,
            age=data.age,
            gender=data.gender,
            phone=data.phone,
            email=data.email,
            general_notes=data.general_notes,
        )

        return await self._enrich(patient)

    async def list_patients(
        self,
        clinic_id: uuid.UUID,
        *,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> PaginatedResult:
        result = await self.repo.get_all_by_clinic(
            clinic_id, search=search, page=page, per_page=per_page
        )

        # Enrich each item with appointment counts + last visit
        enriched = []
        for patient in result.items:
            count = await self.repo.count_appointments(patient.id, clinic_id)
            last_visit = await self.repo.get_last_visit_date(patient.id, clinic_id)
            enriched.append(PatientListItem(
                id=patient.id,
                patient_code=patient.patient_code,
                full_name=patient.full_name,
                age=patient.age,
                phone=patient.phone,
                total_appointments=count,
                last_visit=last_visit,
            ))

        result.items = enriched
        return result

    async def get_patient(
        self, patient_id: uuid.UUID, clinic_id: uuid.UUID
    ) -> PatientResponse:
        patient = await self.repo.get_by_id(patient_id, clinic_id)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found")
        return await self._enrich(patient)

    async def update_patient(
        self, patient_id: uuid.UUID, clinic_id: uuid.UUID, data: PatientUpdate
    ) -> PatientResponse:
        update_data = data.model_dump(exclude_none=True)
        if not update_data:
            # Nothing to update — just return current state
            return await self.get_patient(patient_id, clinic_id)

        patient = await self.repo.update(patient_id, clinic_id, **update_data)
        if patient is None:
            raise NotFoundException(code=PATIENT_NOT_FOUND, message="Patient not found")

        return await self._enrich(patient)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    async def _enrich(self, patient) -> PatientResponse:
        """Add total_appointments and last_visit to a patient ORM object."""
        count = await self.repo.count_appointments(patient.id, patient.clinic_id)
        last_visit = await self.repo.get_last_visit_date(patient.id, patient.clinic_id)
        return PatientResponse(
            id=patient.id,
            clinic_id=patient.clinic_id,
            patient_code=patient.patient_code,
            full_name=patient.full_name,
            age=patient.age,
            gender=patient.gender,
            phone=patient.phone,
            email=patient.email,
            general_notes=patient.general_notes,
            total_appointments=count,
            last_visit=last_visit,
            created_at=patient.created_at,
        )
