"""Semantic user context classification (human-vs-automated by event semantics)."""

from __future__ import annotations

from transcripts.domain.checkpoint import is_compaction_checkpoint
from transcripts.model import NormalizedSession


def has_user_context(session: NormalizedSession) -> bool:
    """Classify if a session is interactive/human vs automated/cron.

    This is based on event semantics (e.g. prompt wrappers, entrypoints,
    presence of automated hooks/headers), rather than simple title whitelists.
    """
    if not session.events:
        return False

    for event in session.events:
        meta = event.meta or {}
        # Claude Code metadata
        if meta.get("entrypoint") == "sdk-cli":
            return False

        # Check if the user prompt is wrapped in XML tags typical of automated runs
        if event.source == "user" and event.type == "message":
            content = event.content or ""
            if "<USER_REQUEST>" in content and "<ADDITIONAL_METADATA>" in content:
                return False
            # Check if prompt looks like a standard automated safety check/prompt
            if "You are a pre-dispatch safety check" in content:
                return False
            if "Choose a worker client" in content or "Answer these two questions" in content:
                return False

    # Check if the session contains system events typical of automated cron/harnesses
    for event in session.events:
        if is_compaction_checkpoint(event):
            # Compaction checkpoints occur when long sessions are truncated;
            # they carry context summaries but do not mean the session was automated.
            continue
        if event.type == "tool_output" and event.content:
            if "tailscale-up.sh" in event.content or "session-end-sync.sh" in event.content:
                return False

    return True
