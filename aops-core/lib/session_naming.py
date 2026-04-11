"""Session naming utilities for unified session identification."""

from datetime import datetime

from .session_paths import get_session_short_hash


def generate_session_filename(session_id: str, date: datetime | str | None = None) -> str:
    """Generate a unified session filename base.

    Format: YYYYMMDD-HH-shorthash

    Args:
        session_id: Full session ID (UUID or Gemini timestamp-hash)
        date: Session start date (datetime or ISO 8601 string)

    Returns:
        Unified filename base (e.g., 20260411-14-abc12345)
    """
    if date is None:
        now = datetime.now().astimezone()
    elif isinstance(date, str):
        if "T" in date:
            now = datetime.fromisoformat(date)
        else:
            # Assume YYYY-MM-DD
            now = datetime.strptime(date, "%Y-%m-%d").astimezone()
    elif isinstance(date, datetime):
        now = date
        if now.tzinfo is None:
            now = now.astimezone()
    else:
        raise TypeError(f"date must be datetime, str, or None; got {type(date)}")

    date_compact = now.strftime("%Y%m%d")
    hour = now.strftime("%H")
    short_hash = get_session_short_hash(session_id)

    return f"{date_compact}-{hour}-{short_hash}"
