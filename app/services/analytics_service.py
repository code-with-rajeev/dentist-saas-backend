# Standard library
import uuid
from datetime import date

# Third-party
from sqlalchemy.ext.asyncio import AsyncSession

# Internal — repository
from app.repositories.analytics_repository import AnalyticsRepository

# Internal — schemas
from app.schemas.analytics import (
    AnalyticsFilter,
    AnalyticsOverviewResponse,
    AppointmentAnalyticsResponse,
    AppointmentBreakdown,
    DailyDataPoint,
    PatientAnalyticsResponse,
    RevenueAnalyticsResponse,
)

# Internal — utils
from app.utils.datetime_utils import resolve_date_range


class AnalyticsService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)

    async def get_overview(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> AnalyticsOverviewResponse:
        start, end = resolve_date_range(f.period, f.date_from, f.date_to)
        data = await self.repo.get_overview_metrics(clinic_id, start, end)
        return AnalyticsOverviewResponse(
            period_from=start,
            period_to=end,
            **data,
        )

    async def get_appointment_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> AppointmentAnalyticsResponse:
        start, end = resolve_date_range(f.period, f.date_from, f.date_to)
        data = await self.repo.get_appointment_stats(clinic_id, start, end)
        return AppointmentAnalyticsResponse(
            period_from=start,
            period_to=end,
            total=data["total"],
            breakdown=AppointmentBreakdown(
                by_status=data["by_status"],
                by_type=data["by_type"],
                daily_breakdown=[DailyDataPoint(**d) for d in data["daily_breakdown"]],
            ),
        )

    async def get_revenue_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> RevenueAnalyticsResponse:
        start, end = resolve_date_range(f.period, f.date_from, f.date_to)
        data = await self.repo.get_revenue_stats(clinic_id, start, end)
        return RevenueAnalyticsResponse(
            period_from=start,
            period_to=end,
            daily_breakdown=[DailyDataPoint(**d) for d in data["daily_breakdown"]],
            **{k: v for k, v in data.items() if k != "daily_breakdown"},
        )

    async def get_patient_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> PatientAnalyticsResponse:
        start, end = resolve_date_range(f.period, f.date_from, f.date_to)
        data = await self.repo.get_patient_stats(clinic_id, start, end)
        return PatientAnalyticsResponse(period_from=start, period_to=end, **data)
