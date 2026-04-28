"""Tests for src.formatters helper functions."""

import pytest

from src.constants import Defaults
from src.formatters import format_interval, parse_interval


class TestParseInterval:
    """Tests for parse_interval()."""

    def test_bare_minutes(self):
        assert parse_interval("5") == 5
        assert parse_interval("90") == 90

    def test_zero_is_manual_only(self):
        assert parse_interval("0") == 0

    def test_minutes_suffix(self):
        assert parse_interval("5m") == 5
        assert parse_interval("90M") == 90

    def test_hours_suffix(self):
        assert parse_interval("1h") == 60
        assert parse_interval("4h") == 240
        assert parse_interval("4H") == 240

    def test_days_suffix(self):
        assert parse_interval("1d") == 1440
        assert parse_interval("7d") == 10080
        assert parse_interval("7D") == 10080

    def test_weeks_suffix(self):
        assert parse_interval("1w") == 10080
        assert parse_interval("2w") == 20160

    def test_strips_whitespace(self):
        assert parse_interval("  4h  ") == 240
        assert parse_interval("4 h") == 240

    def test_rejects_empty(self):
        with pytest.raises(ValueError, match="required"):
            parse_interval("")
        with pytest.raises(ValueError, match="required"):
            parse_interval("   ")

    def test_rejects_unknown_suffix(self):
        with pytest.raises(ValueError, match="Invalid interval suffix"):
            parse_interval("5x")
        with pytest.raises(ValueError, match="Invalid interval suffix"):
            parse_interval("5y")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="0 or higher"):
            parse_interval("-5")
        with pytest.raises(ValueError, match="0 or higher"):
            parse_interval("-1h")

    def test_rejects_combinations(self):
        # No combos: "1h30m" is malformed because the last char is the suffix
        # and the rest must be a plain integer.
        with pytest.raises(ValueError, match="Invalid interval"):
            parse_interval("1h30m")

    def test_rejects_fractional(self):
        with pytest.raises(ValueError, match="Invalid interval"):
            parse_interval("1.5h")

    def test_rejects_non_numeric(self):
        with pytest.raises(ValueError, match="Invalid interval"):
            parse_interval("abc")

    def test_rejects_suffix_only(self):
        with pytest.raises(ValueError, match="missing a number"):
            parse_interval("h")
        with pytest.raises(ValueError, match="missing a number"):
            parse_interval(" d ")

    def test_round_trip_with_format_interval(self):
        # parse_interval("7d") should produce minutes that format_interval
        # describes as "7 days"
        minutes = parse_interval("7d")
        assert "(7 days)" in format_interval(minutes)


class TestFormatInterval:
    """Tests for format_interval()."""

    def test_zero_returns_manual_only_label(self):
        assert format_interval(0) == Defaults.MANUAL_ONLY_LABEL

    def test_under_one_hour_no_humanization(self):
        assert format_interval(1) == "1 minute(s)"
        assert format_interval(5) == "5 minute(s)"
        assert format_interval(59) == "59 minute(s)"

    def test_exactly_one_hour(self):
        assert format_interval(60) == "60 minute(s) (1 hour)"

    def test_exactly_two_hours(self):
        assert format_interval(120) == "120 minute(s) (2 hours)"

    def test_one_hour_thirty_minutes(self):
        assert format_interval(90) == "90 minute(s) (1 hour, 30 minutes)"

    def test_exactly_one_day(self):
        assert format_interval(1440) == "1440 minute(s) (1 day)"

    def test_exactly_seven_days(self):
        assert format_interval(10080) == "10080 minute(s) (7 days)"

    def test_three_days_thirty_minutes(self):
        assert format_interval(4350) == "4350 minute(s) (3 days, 30 minutes)"

    def test_one_day_one_hour_thirty_minutes(self):
        assert format_interval(1530) == "1530 minute(s) (1 day, 1 hour, 30 minutes)"

    def test_one_day_one_hour(self):
        assert format_interval(1500) == "1500 minute(s) (1 day, 1 hour)"
