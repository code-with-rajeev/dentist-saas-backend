from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

router = APIRouter()

# Override Clinic Learning Data (Post-MVP), will implement later
@router.get("/overrides")
async def get_clinic_learning_data():
    return JSONResponse(content={"success": True, "message": "Learning data retrieved", "data": {}})

@router.post("/overrides")
async def update_clinic_learning_data(payload: dict = Body(default={})):
    return JSONResponse(content={"success": True, "message": "Learning data updated", "data": None})  # Implement logic here