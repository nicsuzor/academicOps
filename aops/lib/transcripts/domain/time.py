"""Event-time timestamps extraction logic."""

from __future__ import annotations

from datetime import UTC, datetime

from transcripts.model import NormalizedEvent


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
