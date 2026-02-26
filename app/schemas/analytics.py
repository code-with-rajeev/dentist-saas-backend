# Standard library
import uuid
from datetime import date
from decimal import Decimal

# Third-party
from pydantic import BaseModel, Field, model_validator


# ============================================================
# Query filter model
# ============================================================

class AnalyticsFilter(BaseModel):
    period: str | None = None           # today|yesterday|this_week|this_month
    date_from: date | None = None
    date_to: date | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _validate_mutual_exclusion(self):
        has_period = self.period is not None
        has_range = self.date_from is not None or self.date_to is not None
        if has_period and has_range:
            from app.core.exceptions import ValidationException
            from app.constants.messages import PERIOD_AND_RANGE_CONFLICT
            raise ValidationException(
                code=PERIOD_AND_RANGE_CONFLICT,
                message="Provide either 'period' or 'date_from'/'date_to', not both",
            )
        return self


# ============================================================
# Response models
# ============================================================

class DailyDataPoint(BaseModel):
    date_label: str          # e.g. "2026-02-26"
    count: int = 0
    revenue: Decimal = Decimal("0")


class AnalyticsOverviewResponse(BaseModel):
    period_from: date
    period_to: date
    total_appointments: int
    completed: int
    cancelled: int
    no_show: int
    walk_ins: int
    follow_ups: int
    completion_rate: float           # completed / total * 100
    total_revenue: Decimal
    average_fee: Decimal
    unique_patients: int
    new_patients: int
    returning_patients: int


class AppointmentBreakdown(BaseModel):
    by_status: dict[str, int]
    by_type: dict[str, int]
    daily_breakdown: list[DailyDataPoint]


class AppointmentAnalyticsResponse(BaseModel):
    period_from: date
    period_to: date
    total: int
    breakdown: AppointmentBreakdown


class RevenueAnalyticsResponse(BaseModel):
    period_from: date
    period_to: date
    total_revenue: Decimal
    average_per_appointment: Decimal
    daily_breakdown: list[DailyDataPoint]


class PatientAnalyticsResponse(BaseModel):
    period_from: date
    period_to: date
    unique_patients: int
    new_patients: int
    returning_patients: int
    retention_rate: float            # returning / unique * 100
