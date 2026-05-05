# Standard library
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

# Third-party
from pydantic import BaseModel, Field, field_validator, model_validator

# Internal
from app.constants.messages import PERIOD_AND_RANGE_CONFLICT
from app.core.exceptions import ValidationException


# ============================================================
# Shared config mixin
# ============================================================

class _Base(BaseModel):
    model_config = {"populate_by_name": True}


# ============================================================
# Query filter
# ============================================================

_VALID_PERIODS = frozenset({"today", "yesterday", "this_week", "this_month", "last_month"})
_MAX_RANGE_DAYS = 366


class AnalyticsFilter(_Base):
    period: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    # New: triggers comparison block in every endpoint
    compare: bool = False
    # New: IANA timezone string — defaults to clinic TZ server-side
    timezone: str | None = None

    @field_validator("period")
    @classmethod
    def _valid_period(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_PERIODS:
            raise ValueError(
                f"Invalid period '{v}'. Must be one of: {', '.join(sorted(_VALID_PERIODS))}"
            )
        return v

    @model_validator(mode="after")
    def _validate_range(self) -> "AnalyticsFilter":
        has_period = self.period is not None
        has_range  = self.date_from is not None or self.date_to is not None

        # Mutual exclusion
        if has_period and has_range:
            raise ValidationException(
                code=PERIOD_AND_RANGE_CONFLICT,
                message="Provide either 'period' or 'date_from'/'date_to', not both.",
            )

        # date_to without date_from is ambiguous
        if self.date_to is not None and self.date_from is None:
            raise ValueError("'date_to' requires 'date_from'.")

        # Chronological order
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("'date_from' must not be after 'date_to'.")

        # Max range guard — prevents huge daily_breakdown payloads
        if self.date_from and self.date_to:
            span = (self.date_to - self.date_from).days + 1
            if span > _MAX_RANGE_DAYS:
                raise ValueError(
                    f"Date range may not exceed {_MAX_RANGE_DAYS} days (got {span})."
                )

        return self


# ============================================================
# Shared leaf models
# ============================================================

class GeneratedMeta(_Base):
    """Top-level envelope meta — present on every response."""
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when this response was computed.",
    )


class ComparisonPeriod(_Base):
    """Shared date-range header for comparison blocks."""
    period_from: date
    period_to: date


# ============================================================
# Daily data points
# Two distinct shapes — the old single DailyDataPoint tried to
# serve both appointments and revenue with stub zero fields.
# ============================================================

class AppointmentDailyPoint(_Base):
    """One calendar day in an appointment daily_breakdown."""
    date: date
    appointment_count: int = 0


class RevenueDailyPoint(_Base):
    """One calendar day in a revenue daily_breakdown."""
    date: date
    appointment_count: int = 0       # completed appts that generated revenue
    revenue: Decimal = Decimal("0.00")


# ============================================================
# Slot heatmap models  (NEW)
# ============================================================

class SlotHourPoint(_Base):
    """One hour cell within a weekday row of the heatmap."""
    hour: str                         # "09:00", "10:00" …
    appointment_count: int = 0
    utilisation_rate: Decimal = Decimal("0.00")   # relative: 100 = busiest cell


class SlotDayRow(_Base):
    """One weekday row in the heatmap."""
    day: str                          # "Monday" … "Sunday"
    slots: list[SlotHourPoint]


# ============================================================
# Procedure summary  (NEW — used in patient response)
# ============================================================

class ProcedureSummary(_Base):
    procedure: str
    count: int
    revenue: Decimal


# ============================================================
# Comparison blocks — one per endpoint
# delta_pct fields are None when prior period had zero (undefined, not 0%)
# ============================================================

class OverviewComparison(ComparisonPeriod):
    total_revenue_delta_pct: Decimal | None = None
    total_appointments_delta_pct: Decimal | None = None
    new_patients_delta_pct: Decimal | None = None
    # Absolute percentage-point change, not relative
    completion_rate_delta: Decimal = Decimal("0.00")


class AppointmentComparison(ComparisonPeriod):
    total_appointments_delta_pct: Decimal | None = None
    completion_rate_delta: Decimal = Decimal("0.00")
    no_show_rate_delta: Decimal = Decimal("0.00")


class RevenueComparison(ComparisonPeriod):
    total_revenue: Decimal
    delta_pct: Decimal | None = None
    average_per_appointment: Decimal


class PatientComparison(ComparisonPeriod):
    new_patients_delta_pct: Decimal | None = None
    # Absolute pp change
    retention_rate_delta: Decimal = Decimal("0.00")


# ============================================================
# Response models
# ============================================================

class AnalyticsOverviewResponse(GeneratedMeta):
    period_from: date
    period_to: date

    # Appointment counts
    total_appointments: int
    completed: int
    cancelled: int
    no_show: int
    pending: int                    # fix: was missing
    waiting: int                    # fix: was missing
    walk_ins: int
    follow_ups: int

    # Rates — fix: all Decimal, not float
    completion_rate: Decimal
    cancellation_rate: Decimal      # fix: was missing
    no_show_rate: Decimal           # fix: was missing

    # Revenue
    total_revenue: Decimal
    average_fee: Decimal            # fix: rounded to 2 dp, completed appts only
    peak_day: date | None = None    # new: highest revenue calendar day
    peak_day_revenue: Decimal = Decimal("0.00")   # new

    # Patients
    unique_patients: int
    new_patients: int
    returning_patients: int
    retention_rate: Decimal         # fix: was missing from overview, now Decimal

    # Optional comparison block
    comparison: OverviewComparison | None = None


# ----------------------------------------------------------------

class AppointmentBreakdown(_Base):
    by_status: dict[str, int]
    by_type: dict[str, int]
    # fix: was list[DailyDataPoint] with stub revenue field
    daily_breakdown: list[AppointmentDailyPoint]


class AppointmentAnalyticsResponse(GeneratedMeta):
    period_from: date
    period_to: date

    # fix: was "total" — renamed to match overview and repo
    total_appointments: int
    completion_rate: Decimal        # fix: was missing
    cancellation_rate: Decimal      # new
    no_show_rate: Decimal           # new

    breakdown: AppointmentBreakdown
    comparison: AppointmentComparison | None = None


# ----------------------------------------------------------------

class RevenueAnalyticsResponse(GeneratedMeta):
    period_from: date
    period_to: date

    total_revenue: Decimal
    # fix: was 16 dp raw avg — now 2 dp Decimal
    average_per_appointment: Decimal
    outstanding_amount: Decimal     # new: billed but not yet collected
    collection_rate: Decimal        # new: collected / (collected + outstanding)

    # fix: was list[DailyDataPoint] with stub count=0
    daily_breakdown: list[RevenueDailyPoint]
    comparison: RevenueComparison | None = None


# ----------------------------------------------------------------

class PatientAnalyticsResponse(GeneratedMeta):
    period_from: date
    period_to: date

    unique_patients: int
    new_patients: int
    returning_patients: int
    # fix: was float — now Decimal; fix: was missing from old schema entirely
    retention_rate: Decimal

    top_procedures: list[ProcedureSummary]   # new
    comparison: PatientComparison | None = None


# ----------------------------------------------------------------

class SlotAnalyticsResponse(GeneratedMeta):   # new: entire model
    period_from: date
    period_to: date

    total_booked_slots: int
    busiest_slot: str | None = None     # e.g. "Tuesday 10:00"
    quietest_slot: str | None = None
    heatmap: list[SlotDayRow]


# ============================================================
# Resolved date range helper
# Used by the service/router layer to turn AnalyticsFilter
# into concrete (date_from, date_to) before hitting the repo.
# ============================================================

from datetime import timedelta   # noqa: E402  (kept local — only used here)


def resolve_date_range(f: AnalyticsFilter) -> tuple[date, date]:
    """
    Translate AnalyticsFilter into a concrete (date_from, date_to) pair.

    Period shortcuts:
        today        → today … today
        yesterday    → yesterday … yesterday
        this_week    → Monday of current ISO week … today
        this_month   → 1st of current month … today
        last_month   → 1st … last day of previous month

    If neither period nor dates provided, defaults to today.
    date_from without date_to defaults to date_from … today.
    """
    today = date.today()

    if f.period:
        match f.period:
            case "today":
                return today, today
            case "yesterday":
                yesterday = today - timedelta(days=1)
                return yesterday, yesterday
            case "this_week":
                # ISO week starts Monday (weekday() == 0)
                monday = today - timedelta(days=today.weekday())
                return monday, today
            case "this_month":
                return today.replace(day=1), today
            case "last_month":
                first_this = today.replace(day=1)
                last_prev  = first_this - timedelta(days=1)
                first_prev = last_prev.replace(day=1)
                return first_prev, last_prev
            case _:
                # _valid_period validator already caught this — unreachable
                return today, today

    if f.date_from:
        return f.date_from, (f.date_to or today)

    # Default
    return today, today