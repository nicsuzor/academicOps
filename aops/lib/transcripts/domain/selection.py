
from transcripts.domain.classification import has_user_context
from transcripts.domain.timestamps import get_session_timestamps
from transcripts.model import NormalizedSession


def select_recent_interactive_sessions(
    sessions: list[NormalizedSession],
) -> list[NormalizedSession]:
    """Select interactive sessions (having user context) sorted by last_modified descending.

    Used to populate the primary interactive-only nav surface (task_5dd6cc88).
    """
    interactive = []
    for session in sessions:
        if has_user_context(session):
            interactive.append(session)

    def sort_key(s: NormalizedSession):
        _, last_modified, _ = get_session_timestamps(s)
        return last_modified or ""

    return sorted(interactive, key=sort_key, reverse=True)
