from transcripts.model import NormalizedSession


def has_user_context(session: NormalizedSession) -> bool:
    """Determine if a session has interactive user context.

    This is human-vs-automated classification based on event semantics
    rather than a surface whitelist (academicops-739d95be).
    """
    user_events = [e for e in session.events if e.source == "user"]
    if not user_events:
        return False

    for event in user_events:
        content = event.content.strip()

        # If it has automated XML wrapper, it is automated/harness-dispatched
        if "<USER_REQUEST>" in content:
            continue

        # Pre-dispatch safety checks are automated
        if "You are a pre-dispatch safety check" in content:
            continue

        # Typical automated instructions
        if (
            content.startswith("You are an automated")
            or "Verify that a code change actually does" in content
        ):
            continue

        # Claude-code logs: userType of "external" indicates automated/harness run
        if event.meta.get("user_type") == "external":
            continue

        # Otherwise, if we have any user input, it's genuine interactive human activity
        return True

    return False
