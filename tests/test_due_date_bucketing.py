"""Tests for Brisbane local date helper and due-date bucketing across timezones."""

from __future__ import annotations

from datetime import UTC, date, datetime

from transcripts.domain.time import (
    BRISBANE_TZ,
    bucket_due_date,
    bucket_tasks_by_due_date,
    get_brisbane_today,
    parse_due_date,
)


def test_get_brisbane_today_default() -> None:
    """Default call to get_brisbane_today returns today's date in Brisbane timezone."""
    today = get_brisbane_today()
    assert isinstance(today, date)
    expected = datetime.now(BRISBANE_TZ).date()
    assert today == expected


def test_get_brisbane_today_with_utc_datetime() -> None:
    """Test get_brisbane_today converts UTC datetime to Brisbane local date correctly."""
    # 05:00 UTC on Aug 6 -> 15:00 AEST on Aug 6
    dt_day = datetime(2026, 8, 6, 5, 0, 0, tzinfo=UTC)
    assert get_brisbane_today(dt_day) == date(2026, 8, 6)

    # 16:00 UTC on Aug 6 -> 02:00 AEST on Aug 7 (in the 10-hour boundary window)
    dt_night = datetime(2026, 8, 6, 16, 0, 0, tzinfo=UTC)
    assert get_brisbane_today(dt_night) == date(2026, 8, 7)


def test_10_hour_boundary_window_date_calculation() -> None:
    """Test date calculations across the 10-hour boundary (14:00-24:00 UTC / 00:00-10:00 AEST).

    During 14:00-24:00 UTC, the UTC date is D, but Brisbane local date is D+1.
    """
    # 14:00 UTC on Aug 6 -> 00:00 AEST on Aug 7
    dt_1400 = datetime(2026, 8, 6, 14, 0, 0, tzinfo=UTC)
    assert get_brisbane_today(dt_1400) == date(2026, 8, 7)

    # 18:30 UTC on Aug 6 -> 04:30 AEST on Aug 7
    dt_1830 = datetime(2026, 8, 6, 18, 30, 0, tzinfo=UTC)
    assert get_brisbane_today(dt_1830) == date(2026, 8, 7)

    # 23:59:59 UTC on Aug 6 -> 09:59:59 AEST on Aug 7
    dt_2359 = datetime(2026, 8, 6, 23, 59, 59, tzinfo=UTC)
    assert get_brisbane_today(dt_2359) == date(2026, 8, 7)

    # Outside the window: 13:59:59 UTC on Aug 6 -> 23:59:59 AEST on Aug 6
    dt_1359 = datetime(2026, 8, 6, 13, 59, 59, tzinfo=UTC)
    assert get_brisbane_today(dt_1359) == date(2026, 8, 6)


def test_due_date_bucketing_across_10hr_boundary() -> None:
    """Test due date bucketing when evaluated at 16:00 UTC (02:00 AEST next day).

    Reference time: 2026-08-06 16:00:00 UTC (Brisbane date: 2026-08-07).
    A naive UTC evaluator would see date 2026-08-06.
    Brisbane evaluator sees date 2026-08-07.
    """
    ref_utc_1600 = datetime(2026, 8, 6, 16, 0, 0, tzinfo=UTC)

    # Confirm Brisbane reference date is 2026-08-07
    assert get_brisbane_today(ref_utc_1600) == date(2026, 8, 7)

    # Task due 2026-08-06: In Brisbane (where today is Aug 7), Aug 6 is OVERDUE.
    # (If using UTC date Aug 6, this would incorrectly be "today")
    assert bucket_due_date("2026-08-06", reference_time=ref_utc_1600) == "overdue"

    # Task due 2026-08-07: In Brisbane (where today is Aug 7), Aug 7 is TODAY.
    # (If using UTC date Aug 6, this would incorrectly be "tomorrow")
    assert bucket_due_date("2026-08-07", reference_time=ref_utc_1600) == "today"

    # Task due 2026-08-08: In Brisbane (where today is Aug 7), Aug 8 is TOMORROW.
    # (If using UTC date Aug 6, this would incorrectly be "upcoming")
    assert bucket_due_date("2026-08-08", reference_time=ref_utc_1600) == "tomorrow"

    # Task due 2026-08-09: In Brisbane, Aug 9 is UPCOMING.
    assert bucket_due_date("2026-08-09", reference_time=ref_utc_1600) == "upcoming"

    # Task with no due date
    assert bucket_due_date(None, reference_time=ref_utc_1600) == "unscheduled"


def test_due_date_bucketing_daytime_utc() -> None:
    """Test due date bucketing when evaluated at 04:00 UTC (14:00 AEST same day).

    Reference time: 2026-08-06 04:00:00 UTC (Brisbane date: 2026-08-06).
    """
    ref_utc_0400 = datetime(2026, 8, 6, 4, 0, 0, tzinfo=UTC)

    assert get_brisbane_today(ref_utc_0400) == date(2026, 8, 6)

    assert bucket_due_date("2026-08-05", reference_time=ref_utc_0400) == "overdue"
    assert bucket_due_date("2026-08-06", reference_time=ref_utc_0400) == "today"
    assert bucket_due_date("2026-08-07", reference_time=ref_utc_0400) == "tomorrow"
    assert bucket_due_date("2026-08-08", reference_time=ref_utc_0400) == "upcoming"


def test_bucket_tasks_by_due_date() -> None:
    """Test grouping a collection of tasks into buckets in Brisbane timezone."""
    ref_time = datetime(2026, 8, 6, 20, 0, 0, tzinfo=UTC)  # 06:00 AEST Aug 7

    tasks = [
        {"id": "t1", "title": "Overdue task", "due_date": "2026-08-06"},
        {"id": "t2", "title": "Today's task", "due_date": "2026-08-07"},
        {"id": "t3", "title": "Tomorrow's task", "due_date": "2026-08-08"},
        {"id": "t4", "title": "Upcoming task", "due_date": "2026-08-10"},
        {"id": "t5", "title": "Unscheduled task", "due_date": None},
    ]

    result = bucket_tasks_by_due_date(tasks, reference_time=ref_time)

    assert len(result["overdue"]) == 1
    assert result["overdue"][0]["id"] == "t1"

    assert len(result["today"]) == 1
    assert result["today"][0]["id"] == "t2"

    assert len(result["tomorrow"]) == 1
    assert result["tomorrow"][0]["id"] == "t3"

    assert len(result["upcoming"]) == 1
    assert result["upcoming"][0]["id"] == "t4"

    assert len(result["unscheduled"]) == 1
    assert result["unscheduled"][0]["id"] == "t5"


def test_parse_due_date_variations() -> None:
    """Test parsing various due date input types."""
    assert parse_due_date(None) is None
    assert parse_due_date("") is None
    assert parse_due_date("  ") is None
    assert parse_due_date("invalid-date") is None

    # Plain date string
    assert parse_due_date("2026-08-06") == date(2026, 8, 6)

    # Date object
    assert parse_due_date(date(2026, 8, 6)) == date(2026, 8, 6)

    # ISO Datetime string in 10hr window
    # 2026-08-06T15:00:00Z -> 01:00 AEST 2026-08-07
    assert parse_due_date("2026-08-06T15:00:00Z") == date(2026, 8, 7)

    # ISO Datetime string with microseconds and explicit timezone offset (+10:00)
    # 2026-08-06T14:30:00.123456+10:00 is 14:30 AEST Aug 6 -> date 2026-08-06
    assert parse_due_date("2026-08-06T14:30:00.123456+10:00") == date(2026, 8, 6)


def test_get_brisbane_today_with_microseconds_and_tz_offset() -> None:
    """Test get_brisbane_today preserves timezone offsets when microseconds are present."""
    # 2026-08-06T14:30:00.123456+10:00 is 14:30 in Brisbane on Aug 6
    assert get_brisbane_today("2026-08-06T14:30:00.123456+10:00") == date(2026, 8, 6)

    # 2026-08-06T14:30:00.123456-05:00 is 19:30 UTC Aug 6 -> 05:30 AEST Aug 7
    assert get_brisbane_today("2026-08-06T14:30:00.123456-05:00") == date(2026, 8, 7)
