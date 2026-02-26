"""
Date/period resolution utilities for the Analytics module.
`resolve_date_range(period, date_from, date_to)` is the main public function.
"""

# Standard library
from datetime import date, timedelta

# Internal
from app.core.exceptions import ValidationException
from app.constants.messages import (
    INVALID_DATE_RANGE,
    INVALID_PERIOD,
    PERIOD_AND_RANGE_CONFLICT,
)

_VALID_PERIODS = {"today", "yesterday", "this_week", "this_month"}


def resolve_date_range(
    period: str | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date, date]:
    """
    Resolve analytics date range from either a named period or explicit dates.

    Rules:
    - Exactly one of (period, date_from/date_to) must be supplied.
    - If neither is provided, defaults to 'today'.
    - Raises ValidationException for conflicts, bad periods, or invalid ranges.

    Returns:
        (start_date, end_date) both inclusive.
    """
    has_period = period is not None
    has_range = date_from is not None or date_to is not None

    if has_period and has_range:
        raise ValidationException(
            code=PERIOD_AND_RANGE_CONFLICT,
            message="Provide either 'period' or 'date_from'/'date_to', not both",
        )

    if has_period:
        return _resolve_period(period)

    if has_range:
        # Both must be present
        if date_from is None or date_to is None:
            raise ValidationException(
                code=INVALID_DATE_RANGE,
                message="Both 'date_from' and 'date_to' must be provided together",
            )
        if date_from > date_to:
            raise ValidationException(
                code=INVALID_DATE_RANGE,
                message="'date_from' must be on or before 'date_to'",
            )
        return date_from, date_to

    # Default: today
    today = date.today()
    return today, today


def _resolve_period(period: str) -> tuple[date, date]:
    today = date.today()

    if period == "today":
        return today, today
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    elif period == "this_week":
        # Monday-based week
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == "this_month":
        start = today.replace(day=1)
        return start, today
    else:
        raise ValidationException(
            code=INVALID_PERIOD,
            message=f"Unknown period '{period}'. Valid values: {', '.join(_VALID_PERIODS)}",
        )
