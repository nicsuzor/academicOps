
from transcripts.model import NormalizedSession


def get_session_timestamps(
    session: NormalizedSession,
) -> tuple[str | None, str | None, str | None]:
    """Extract started_at, last_modified, ended_at from event timestamps in the stream.

    This avoids file mtime fallbacks (academicops-d3b3b6ab).
    """
    ts_events = [e for e in session.events if e.timestamp]
    if not ts_events:
        return None, None, None

    ts_events_sorted = sorted(ts_events, key=lambda e: e.timestamp)
    started_at = ts_events_sorted[0].timestamp
    last_modified = ts_events_sorted[-1].timestamp

    # Check if the session is completed/terminated.
    # Look for exit/handover hooks or exit command events in the stream.
    ended_at = None
    is_completed = False
    for event in reversed(ts_events_sorted):
        # Look for user executing exit/handover commands
        if event.source == "user" and any(
            cmd in event.content for cmd in ("/handover", "/dump", "/end_session")
        ):
            is_completed = True
            break
        # Look for system SessionEnd hook execution
        if (
            event.source == "system"
            and "hookName" in event.meta
            and "SessionEnd" in event.meta.get("hookName", "")
        ):
            is_completed = True
            break

    if is_completed:
        ended_at = last_modified

    return started_at, last_modified, ended_at
