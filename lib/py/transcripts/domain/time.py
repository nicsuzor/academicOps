"""Event-time timestamps extraction logic and Brisbane due-date bucketing utilities."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    BRISBANE_TZ: timezone | ZoneInfo = ZoneInfo("Australia/Brisbane")
except Exception:  # pragma: no cover
    BRISBANE_TZ = timezone(timedelta(hours=10))

from transcripts.model import NormalizedEvent


def format_iso_utc(at: datetime | date | str | None = None) -> str:
    """Format a datetime, date, or ISO string as a standardized ISO-8601 UTC timestamp string.

    Output format is strictly `YYYY-MM-DDTHH:MM:SS.ffffff+00:00`.
    Never uses filesystem mtime.
    """
    if at is None:
        dt = datetime.now(UTC)
    elif isinstance(at, datetime):
        dt = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
        dt = dt.astimezone(UTC)
    elif isinstance(at, date):
        dt = datetime.combine(at, datetime.min.time(), tzinfo=UTC)
    elif isinstance(at, str):
        parsed = parse_iso_utc(at)
        dt = parsed if parsed is not None else datetime.now(UTC)
    else:
        dt = datetime.now(UTC)

    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def parse_iso_utc(ts: str | datetime | date | None) -> datetime | None:
    """Parse an ISO-8601 string, date, or datetime into a UTC-aware datetime object.

    Never uses filesystem mtime or bogus fallback dates.
    Returns None if ts is None, empty, or invalid.
    """
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)
    if isinstance(ts, date):
        return datetime.combine(ts, datetime.min.time(), tzinfo=UTC)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        if "T" not in s and " " not in s:
            try:
                d = date.fromisoformat(s)
                return datetime.combine(d, datetime.min.time(), tzinfo=UTC)
            except ValueError:
                return None
        try:
            clean_ts = s.replace("Z", "+00:00")
            if "." in clean_ts:
                # Handle microsecond length if needed for fromisoformat
                parts = clean_ts.split(".", 1)
                base = parts[0]
                rest = parts[1]
                # Split rest into microseconds and tz offset if present
                tz_pos = max(rest.find("+"), rest.find("-"))
                if tz_pos != -1:
                    ms_part = rest[:tz_pos][:6]
                    tz_part = rest[tz_pos:]
                    clean_ts = f"{base}.{ms_part}{tz_part}"
                else:
                    clean_ts = f"{base}.{rest[:6]}"
            dt = datetime.fromisoformat(clean_ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            return None
    return None


def get_brisbane_today(at: datetime | date | str | None = None) -> date:
    """Get current date in Brisbane (UTC+10:00) timezone, or convert a timestamp/datetime/date to Brisbane date.

    If `at` is None, returns today's date in Brisbane local time.
    If `at` is a datetime, converts it to Brisbane timezone and returns its date.
    If `at` is a date object (and not datetime), returns it directly.
    If `at` is a string (ISO datetime or YYYY-MM-DD), parses and returns the Brisbane date.
    """
    if at is None:
        return datetime.now(BRISBANE_TZ).date()

    if isinstance(at, str):
        at_str = at.strip()
        if not at_str:
            return datetime.now(BRISBANE_TZ).date()
        if "T" not in at_str and " " not in at_str:
            try:
                return date.fromisoformat(at_str)
            except ValueError:
                return datetime.now(BRISBANE_TZ).date()
        parsed = parse_iso_utc(at_str)
        if parsed is not None:
            return parsed.astimezone(BRISBANE_TZ).date()
        return datetime.now(BRISBANE_TZ).date()

    if isinstance(at, datetime):
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        return at.astimezone(BRISBANE_TZ).date()

    if isinstance(at, date):
        return at

    raise TypeError(f"Unsupported type for at: {type(at)}")


def parse_due_date(due_date: str | date | datetime | None) -> date | None:
    """Parse a due date value into a date object, evaluating datetimes in Brisbane timezone context."""
    if due_date is None:
        return None
    if isinstance(due_date, str):
        s = due_date.strip()
        if not s:
            return None
        if "T" not in s and " " not in s:
            try:
                return date.fromisoformat(s)
            except ValueError:
                return None
        parsed = parse_iso_utc(s)
        if parsed is not None:
            return parsed.astimezone(BRISBANE_TZ).date()
        return None
    if isinstance(due_date, datetime):
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)
        return due_date.astimezone(BRISBANE_TZ).date()
    if isinstance(due_date, date):
        return due_date
    return None


def bucket_due_date(
    due_date: str | date | datetime | None,
    reference_time: datetime | date | str | None = None,
) -> str:
    """Categorize task due date against Brisbane local date (UTC+10:00).

    Returns one of: 'overdue', 'today', 'tomorrow', 'upcoming', or 'unscheduled'.
    Evaluating task due dates against Brisbane local time prevents mis-bucketing
    during the 10-hour window (14:00-24:00 UTC / 00:00-10:00 AEST).
    """
    parsed_due = parse_due_date(due_date)
    if parsed_due is None:
        return "unscheduled"

    ref_date = get_brisbane_today(reference_time)

    if parsed_due < ref_date:
        return "overdue"
    if parsed_due == ref_date:
        return "today"
    if parsed_due == ref_date + timedelta(days=1):
        return "tomorrow"
    return "upcoming"


def bucket_tasks_by_due_date(
    tasks: list[dict],
    reference_time: datetime | date | str | None = None,
    due_date_field: str = "due_date",
) -> dict[str, list[dict]]:
    """Group a list of task dicts by their due-date bucket in Brisbane timezone.

    Returns a dict with keys: 'overdue', 'today', 'tomorrow', 'upcoming', 'unscheduled'.
    """
    buckets: dict[str, list[dict]] = {
        "overdue": [],
        "today": [],
        "tomorrow": [],
        "upcoming": [],
        "unscheduled": [],
    }
    for task in tasks:
        due_val = task.get(due_date_field)
        bucket = bucket_due_date(due_val, reference_time=reference_time)
        buckets[bucket].append(task)
    return buckets


def get_event_timestamps(events: list[NormalizedEvent]) -> tuple[str, str, str]:
    """Extract started_at, last_modified, ended_at from event timestamps in the stream.

    Never uses file mtime. Returns ISO-8601 strings.
    """
    valid_times: list[tuple[datetime, str]] = []
    for event in events:
        ts = event.timestamp
        if ts:
            try:
                # Remove Z for parsing, but keep original for output
                clean_ts = ts.rstrip("Z")
                if "." in clean_ts:
                    base, ms = clean_ts.split(".")
                    ms = ms[:6]  # Limit to 6 digits for microseconds
                    dt = datetime.fromisoformat(f"{base}.{ms}").replace(tzinfo=UTC)
                else:
                    dt = datetime.fromisoformat(clean_ts).replace(tzinfo=UTC)
                valid_times.append((dt, ts))
            except ValueError:
                continue

    if not valid_times:
        now_str = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return now_str, now_str, now_str

    # Sort chronologically
    valid_times.sort(key=lambda x: x[0])

    started_at = valid_times[0][1]
    ended_at = valid_times[-1][1]
    last_modified = ended_at

    return started_at, last_modified, ended_at
