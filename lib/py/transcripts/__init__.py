"""Layer A: session-transcript parse/render adapters.

Each source (Claude Code, agy) gets a thin adapter delegating to a
maintained parser where one exists. Architecture: specs/transcript-pipeline.md.
"""

from transcripts.model import (
    NormalizedEvent,
    NormalizedRawEntry,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)

__all__ = [
    "NormalizedEvent",
    "NormalizedRawEntry",
    "NormalizedSession",
    "NormalizedToolCall",
    "SubagentTranscript",
]
