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
from app.schemas.analytics2 import AnalyticsFilter
from app.services.analytics_service2 import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_OWNER_DEPS = [Depends(require_permission(ANALYTICS_READ)), Depends(require_owner())]

# ------------------------------------------------------------------
# Shared query param descriptions (DRY — avoids copy-paste drift)
# ------------------------------------------------------------------

_PERIOD_DESC   = "Shorthand period: today | yesterday | this_week | this_month | last_month"
_FROM_DESC     = "Range start (YYYY-MM-DD). Mutually exclusive with 'period'."
_TO_DESC       = "Range end (YYYY-MM-DD). Requires date_from. Defaults to today if omitted."
_COMPARE_DESC  = "Include a comparison block for the equivalent prior period."
_TIMEZONE_DESC = "IANA timezone string (e.g. Asia/Kolkata). Defaults to clinic's registered timezone."


# ------------------------------------------------------------------
# Helper — builds AnalyticsFilter from raw query params
# ------------------------------------------------------------------

def _filter(
    period: str | None,
    date_from: date | None,
    date_to: date | None,
    compare: bool,
    timezone: str | None,
) -> AnalyticsFilter:
    """Construct and validate AnalyticsFilter from query params."""
    return AnalyticsFilter(
        period=period,
        date_from=date_from,
        date_to=date_to,
        compare=compare,
        timezone=timezone,
    )


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@router.get("/overview", dependencies=_OWNER_DEPS)
async def analytics_overview(
    current_user: AuthenticatedUser,
    db: DbSession,
    period:    str | None  = Query(None,  description=_PERIOD_DESC),
    date_from: date | None = Query(None,  description=_FROM_DESC),
    date_to:   date | None = Query(None,  description=_TO_DESC),
    compare:   bool        = Query(False, description=_COMPARE_DESC),
    timezone:  str | None  = Query(None,  description=_TIMEZONE_DESC),
) -> JSONResponse:
    """
    Dashboard overview: revenue, appointments, patient counts, completion rate.
    Owner only.
    """
    f = _filter(period, date_from, date_to, compare, timezone)
    result = await AnalyticsService(db).get_overview(current_user.clinic_id, f)
    return JSONResponse(content={
        "success": True,
        "message": "Overview retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.get("/appointments", dependencies=_OWNER_DEPS)
async def analytics_appointments(
    current_user: AuthenticatedUser,
    db: DbSession,
    period:    str | None  = Query(None,  description=_PERIOD_DESC),
    date_from: date | None = Query(None,  description=_FROM_DESC),
    date_to:   date | None = Query(None,  description=_TO_DESC),
    compare:   bool        = Query(False, description=_COMPARE_DESC),
    timezone:  str | None  = Query(None,  description=_TIMEZONE_DESC),
) -> JSONResponse:
    """
    Appointment volume + status/type breakdown with zero-filled daily counts.
    Owner only.
    """
    f = _filter(period, date_from, date_to, compare, timezone)
    result = await AnalyticsService(db).get_appointment_analytics(current_user.clinic_id, f)
    return JSONResponse(content={
        "success": True,
        "message": "Appointment analytics retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.get("/revenue", dependencies=_OWNER_DEPS)
async def analytics_revenue(
    current_user: AuthenticatedUser,
    db: DbSession,
    period:    str | None  = Query(None,  description=_PERIOD_DESC),
    date_from: date | None = Query(None,  description=_FROM_DESC),
    date_to:   date | None = Query(None,  description=_TO_DESC),
    compare:   bool        = Query(False, description=_COMPARE_DESC),
    timezone:  str | None  = Query(None,  description=_TIMEZONE_DESC),
) -> JSONResponse:
    """
    Revenue totals, daily breakdown, outstanding amount and collection rate.
    Covers submitted consultations only. Owner only.
    """
    f = _filter(period, date_from, date_to, compare, timezone)
    result = await AnalyticsService(db).get_revenue_analytics(current_user.clinic_id, f)
    return JSONResponse(content={
        "success": True,
        "message": "Revenue analytics retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.get("/patients", dependencies=_OWNER_DEPS)
async def analytics_patients(
    current_user: AuthenticatedUser,
    db: DbSession,
    period:    str | None  = Query(None,  description=_PERIOD_DESC),
    date_from: date | None = Query(None,  description=_FROM_DESC),
    date_to:   date | None = Query(None,  description=_TO_DESC),
    compare:   bool        = Query(False, description=_COMPARE_DESC),
    timezone:  str | None  = Query(None,  description=_TIMEZONE_DESC),
) -> JSONResponse:
    """
    Unique / new / returning patient counts, retention rate, and top procedures.
    Owner only.
    """
    f = _filter(period, date_from, date_to, compare, timezone)
    result = await AnalyticsService(db).get_patient_analytics(current_user.clinic_id, f)
    return JSONResponse(content={
        "success": True,
        "message": "Patient analytics retrieved",
        "data": result.model_dump(mode="json"),
    })


@router.get("/slots", dependencies=_OWNER_DEPS)
async def analytics_slots(
    current_user: AuthenticatedUser,
    db: DbSession,
    period:    str | None  = Query(None, description=_PERIOD_DESC),
    date_from: date | None = Query(None, description=_FROM_DESC),
    date_to:   date | None = Query(None, description=_TO_DESC),
    timezone:  str | None  = Query(None, description=_TIMEZONE_DESC),
) -> JSONResponse:
    """
    Slot utilisation heatmap by weekday and hour.
    Shows busiest and quietest booking windows to help optimise the schedule.
    Owner only. Compare not supported for heatmaps.
    """
    # compare intentionally omitted — no meaningful prior-period diff for a heatmap
    f = _filter(period, date_from, date_to, compare=False, timezone=timezone)
    result = await AnalyticsService(db).get_slot_analytics(current_user.clinic_id, f)
    return JSONResponse(content={
        "success": True,
        "message": "Slot analytics retrieved",
        "data": result.model_dump(mode="json"),
    })