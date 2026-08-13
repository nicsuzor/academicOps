"""Compaction/truncation checkpoint identification predicate."""

from __future__ import annotations

from transcripts.model import NormalizedEvent

# Markers present in compaction/truncation checkpoints injected by harnesses/clients.
COMPACTION_CHECKPOINT_MARKERS = (
    "USER Objective:",
    "Conversation Logs",
    "{{ CHECKPOINT",
    "truncated due to its long length",
)


def is_compaction_checkpoint(event: NormalizedEvent) -> bool:
    """Return True if event is a conversation compaction/truncation checkpoint.

    Compaction checkpoints are system-injected summary blocks created when a long
    conversation is truncated. They contain boilerplate context (e.g. 'USER Objective:',
    'Conversation Logs', or '{{ CHECKPOINT') rather than human input, assistant messages,
    or true outcome signals.
    """
    if event.type != "checkpoint" or not event.content:
        return False

    return any(marker in event.content for marker in COMPACTION_CHECKPOINT_MARKERS)
