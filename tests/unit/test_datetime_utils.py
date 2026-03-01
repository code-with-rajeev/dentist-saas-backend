"""
Unit tests for datetime_utils.resolve_date_range().
Tests all named periods, custom range, defaults, and error cases.
Pure Python, no DB.
"""

# Standard library
from datetime import date, timedelta

# Third-party
import pytest

# Internal
from app.utils.datetime_utils import resolve_date_range
from app.core.exceptions import ValidationException
from app.constants.messages import (
    INVALID_DATE_RANGE,
    INVALID_PERIOD,
    PERIOD_AND_RANGE_CONFLICT,
)

TODAY = date.today()


class TestNamedPeriods:
    def test_today(self):
        start, end = resolve_date_range("today", None, None)
        assert start == TODAY
        assert end == TODAY

    def test_yesterday(self):
        start, end = resolve_date_range("yesterday", None, None)
        yesterday = TODAY - timedelta(days=1)
        assert start == yesterday
        assert end == yesterday

    def test_this_week_starts_on_monday(self):
        start, end = resolve_date_range("this_week", None, None)
        monday = TODAY - timedelta(days=TODAY.weekday())
        assert start == monday
        assert end == TODAY

    def test_this_month_starts_on_first(self):
        start, end = resolve_date_range("this_month", None, None)
        first = TODAY.replace(day=1)
        assert start == first
        assert end == TODAY


class TestCustomDateRange:
    def test_valid_custom_range(self):
        d_from = date(2026, 1, 1)
        d_to = date(2026, 1, 31)
        start, end = resolve_date_range(None, d_from, d_to)
        assert start == d_from
        assert end == d_to

    def test_same_day_range(self):
        start, end = resolve_date_range(None, TODAY, TODAY)
        assert start == end == TODAY


class TestDefault:
    def test_no_params_defaults_to_today(self):
        start, end = resolve_date_range(None, None, None)
        assert start == TODAY
        assert end == TODAY


class TestValidationErrors:
    def test_period_and_date_from_conflicts(self):
        with pytest.raises(ValidationException) as exc_info:
            resolve_date_range("today", TODAY, TODAY)
        assert exc_info.value.code == PERIOD_AND_RANGE_CONFLICT

    def test_invalid_period_string(self):
        with pytest.raises(ValidationException) as exc_info:
            resolve_date_range("last_quarter", None, None)
        assert exc_info.value.code == INVALID_PERIOD

    def test_date_from_after_date_to(self):
        with pytest.raises(ValidationException) as exc_info:
            resolve_date_range(None, TODAY, TODAY - timedelta(days=1))
        assert exc_info.value.code == INVALID_DATE_RANGE

    def test_only_date_from_without_date_to(self):
        with pytest.raises(ValidationException) as exc_info:
            resolve_date_range(None, TODAY, None)
        assert exc_info.value.code == INVALID_DATE_RANGE

    def test_only_date_to_without_date_from(self):
        with pytest.raises(ValidationException) as exc_info:
            resolve_date_range(None, None, TODAY)
        assert exc_info.value.code == INVALID_DATE_RANGE
