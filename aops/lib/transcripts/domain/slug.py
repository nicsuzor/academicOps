import re


def get_session_slug(session_id: str) -> str:
    """Get a stable, deterministic slug derived ONLY from the session_id.

    This guards against content-derived churn or self-delete (aops-e6dd60cf).
    """
    cleaned = re.sub(r"[^a-zA-Z0-9\-]", "", session_id).lower()
    return cleaned if cleaned else "unknown-session"
