# Standard library
from datetime import date

# Third-party
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

# Internal — dependencies
from app.dependencies import DbSession
from app.rbac.dependencies import AuthenticatedUser, require_owner, require_permission
from app.rbac.permissions import ANALYTICS_READ

# Internal — schemas + service
from app.schemas.analytics import AnalyticsFilter
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_OWNER_DEPS = [Depends(require_permission(ANALYTICS_READ)), Depends(require_owner())]


@router.get(
    "/overview",
    dependencies=_OWNER_DEPS,
)
async def analytics_overview(
    current_user: AuthenticatedUser,
    db: DbSession,
    period: str | None = Query(None, description="today|yesterday|this_week|this_month"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> JSONResponse:
    """Dashboard overview: revenue, appointments, patient counts, completion rate. Owner only."""
    f = AnalyticsFilter(period=period, date_from=date_from, date_to=date_to)
    svc = AnalyticsService(db)
    result = await svc.get_overview(current_user.clinic_id, f)
    return JSONResponse(content={"success": True, "message": "Overview retrieved", "data": result.model_dump(mode="json")})


@router.get(
    "/appointments",
    dependencies=_OWNER_DEPS,
)
async def analytics_appointments(
    current_user: AuthenticatedUser,
    db: DbSession,
    period: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> JSONResponse:
    """Appointment breakdown by status, type and daily count. Owner only."""
    f = AnalyticsFilter(period=period, date_from=date_from, date_to=date_to)
    svc = AnalyticsService(db)
    result = await svc.get_appointment_analytics(current_user.clinic_id, f)
    return JSONResponse(content={"success": True, "message": "Appointment analytics retrieved", "data": result.model_dump(mode="json")})


@router.get(
    "/revenue",
    dependencies=_OWNER_DEPS,
)
async def analytics_revenue(
    current_user: AuthenticatedUser,
    db: DbSession,
    period: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> JSONResponse:
    """Revenue totals + daily breakdown from submitted consultations. Owner only."""
    f = AnalyticsFilter(period=period, date_from=date_from, date_to=date_to)
    svc = AnalyticsService(db)
    result = await svc.get_revenue_analytics(current_user.clinic_id, f)
    return JSONResponse(content={"success": True, "message": "Revenue analytics retrieved", "data": result.model_dump(mode="json")})


@router.get(
    "/patients",
    dependencies=_OWNER_DEPS,
)
async def analytics_patients(
    current_user: AuthenticatedUser,
    db: DbSession,
    period: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
) -> JSONResponse:
    """Unique / new / returning patient counts and retention rate. Owner only."""
    f = AnalyticsFilter(period=period, date_from=date_from, date_to=date_to)
    svc = AnalyticsService(db)
    result = await svc.get_patient_analytics(current_user.clinic_id, f)
    return JSONResponse(content={"success": True, "message": "Patient analytics retrieved", "data": result.model_dump(mode="json")})
