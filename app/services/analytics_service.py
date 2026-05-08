# Standard library
import uuid

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
    AppointmentDailyPoint,       # fix: was DailyDataPoint (removed)
    PatientAnalyticsResponse,
    ProcedureSummary,
    RevenueAnalyticsResponse,
    RevenueDailyPoint,            # fix: was DailyDataPoint (removed)
    SlotAnalyticsResponse,        # new
    SlotDayRow,                   # new
    SlotHourPoint,                # new
    resolve_date_range,           # fix: moved from app.utils.datetime_utils; signature changed
)


class AnalyticsService:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AnalyticsRepository(db)

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def get_overview(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> AnalyticsOverviewResponse:
        start, end = resolve_date_range(f)   # fix: was resolve_date_range(f.period, f.date_from, f.date_to)
        data = await self.repo.get_overview_metrics(
            clinic_id, start, end,
            compare=f.compare,               # fix: was never forwarded
        )
        return AnalyticsOverviewResponse(
            period_from=start,
            period_to=end,
            **data,
        )

    # ------------------------------------------------------------------
    # Appointments
    # ------------------------------------------------------------------

    async def get_appointment_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> AppointmentAnalyticsResponse:
        start, end = resolve_date_range(f)
        data = await self.repo.get_appointment_stats(
            clinic_id, start, end,
            compare=f.compare,
        )

        breakdown = data["breakdown"]
        return AppointmentAnalyticsResponse(
            period_from=start,
            period_to=end,
            # fix: was "total" — field renamed to total_appointments in schema
            total_appointments=data["total_appointments"],
            completion_rate=data["completion_rate"],
            cancellation_rate=data["cancellation_rate"],
            no_show_rate=data["no_show_rate"],
            breakdown=AppointmentBreakdown(
                by_status=breakdown["by_status"],
                by_type=breakdown["by_type"],
                # fix: was DailyDataPoint — now AppointmentDailyPoint (no revenue field)
                daily_breakdown=[
                    AppointmentDailyPoint(**d) for d in breakdown["daily_breakdown"]
                ],
            ),
            # fix: comparison was never wired up
            comparison=data.get("comparison"),
        )

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------

    async def get_revenue_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> RevenueAnalyticsResponse:
        start, end = resolve_date_range(f)
        data = await self.repo.get_revenue_stats(
            clinic_id, start, end,
            compare=f.compare,
        )
        return RevenueAnalyticsResponse(
            period_from=start,
            period_to=end,
            total_revenue=data["total_revenue"],
            average_per_appointment=data["average_per_appointment"],
            outstanding_amount=data["outstanding_amount"],
            collection_rate=data["collection_rate"],
            # fix: was DailyDataPoint — now RevenueDailyPoint (has real appointment_count)
            daily_breakdown=[
                RevenueDailyPoint(**d) for d in data["daily_breakdown"]
            ],
            # fix: was never wired up
            comparison=data.get("comparison"),
        )

    # ------------------------------------------------------------------
    # Patients
    # ------------------------------------------------------------------

    async def get_patient_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> PatientAnalyticsResponse:
        start, end = resolve_date_range(f)
        data = await self.repo.get_patient_stats(
            clinic_id, start, end,
            compare=f.compare,
        )
        return PatientAnalyticsResponse(
            period_from=start,
            period_to=end,
            unique_patients=data["unique_patients"],
            new_patients=data["new_patients"],
            returning_patients=data["returning_patients"],
            retention_rate=data["retention_rate"],
            # new: top_procedures is list[dict] from repo — hydrate into typed models
            top_procedures=[
                ProcedureSummary(**p) for p in data["top_procedures"]
            ],
            comparison=data.get("comparison"),
        )

    # ------------------------------------------------------------------
    # Slots  (new)
    # ------------------------------------------------------------------

    async def get_slot_analytics(
        self, clinic_id: uuid.UUID, f: AnalyticsFilter
    ) -> SlotAnalyticsResponse:
        start, end = resolve_date_range(f)
        # compare not supported for slots — heatmap has no meaningful prior-period diff
        data = await self.repo.get_slot_stats(clinic_id, start, end)
        return SlotAnalyticsResponse(
            period_from=start,
            period_to=end,
            total_booked_slots=data["total_booked_slots"],
            busiest_slot=data["busiest_slot"],
            quietest_slot=data["quietest_slot"],
            heatmap=[
                SlotDayRow(
                    day=row["day"],
                    slots=[SlotHourPoint(**s) for s in row["slots"]],
                )
                for row in data["heatmap"]
            ],
        )