# Standard library
import uuid

# Third-party
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

# Internal - dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_owner

# Internal - schemas + service
from app.schemas.med_library import MedLibraryCreate, MedLibraryResponse
from app.schemas.common import SuccessResponse
from app.services.med_library_service import MedLibraryService
from app.schemas.med_library import MedLibraryCreate, MedLibraryUpdate, MedLibraryResponse

router = APIRouter(prefix="/meds", tags=["Med Library"])


@router.get(
    "",
    response_model=SuccessResponse[list[MedLibraryResponse]],
    dependencies=[Depends(require_owner())],
)
async def get_meds(
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """
    Fetch all meds for this dentist.
    System meds + dentist's custom meds.
    Called once on consultation page mount. No pagination needed.
    """
    service = MedLibraryService(db)
    result = await service.get_meds_for_dentist(current_user.id)
    return JSONResponse(content={
        "success": True,
        "message": "Medications retrieved",
        "data": [r.model_dump(mode="json") for r in result],
    })


@router.post(
    "",
    response_model=SuccessResponse[MedLibraryResponse],
    status_code=201,
    dependencies=[Depends(require_owner())],
)
async def create_custom_med(
    body: MedLibraryCreate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """
    Add a new custom med to dentist's library.
    409 if name already exists for this dentist.
    """
    service = MedLibraryService(db)
    result = await service.create_custom_med(current_user.id, body)
    return JSONResponse(
        status_code=201,
        content={
            "success": True,
            "message": "Custom medication added",
            "data": result.model_dump(mode="json"),
        },
    )

@router.delete(
    "/{med_id}",
    response_model=SuccessResponse[MedLibraryResponse],
    dependencies=[Depends(require_owner())],
)
async def delete_custom_med(
    med_id: uuid.UUID,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Delete a custom med. Cannot delete system meds. Only owner dentist."""
    service = MedLibraryService(db)
    await service.delete_custom_med(med_id, current_user.id)
    return JSONResponse(content={
        "success": True,
        "message": "Medication deleted",
        "data": None,
    })

@router.patch(
    "/{med_id}",
    response_model=SuccessResponse[MedLibraryResponse],
    dependencies=[Depends(require_owner())],
)
async def update_custom_med(
    med_id: uuid.UUID,
    body: MedLibraryUpdate,
    current_user: AuthenticatedUser,
    db: DbSession,
) -> JSONResponse:
    """Update a custom med. Cannot edit system meds. Only owner dentist."""
    service = MedLibraryService(db)
    result = await service.update_custom_med(med_id, current_user.id, body)
    return JSONResponse(content={
        "success": True,
        "message": "Medication updated",
        "data": result.model_dump(mode="json"),
    })