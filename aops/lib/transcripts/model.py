"""Normalized Session/Event data models for session transcripts.

This module defines the single, stable target schema that downstream domain code
(Layer B) consumes, decoupling it from the raw schemas of Claude Code and agy logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NormalizedToolCall:
    """A normalized representation of an agent's tool invocation."""

    name: str
    args: dict[str, Any]


@dataclass(frozen=True)
class NormalizedEvent:
    """A single normalized step or event within a transcript session."""

    event_id: str
    timestamp: str  # ISO-8601 string
    source: str  # "user", "model", "system", "tool"
    type: str  # "message", "tool_output", "checkpoint", "system", "unknown"
    content: str
    thinking: str | None = None
    tool_calls: list[NormalizedToolCall] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedRawEntry:
    """An unrecognized or unparseable line from the raw log preserved for logging."""

    line_no: int
    type: str | None
    raw: dict[str, Any]


@dataclass
class NormalizedSession:
    """A complete session transcript, containing the list of events and raw entries."""

    session_id: str
    source_file: Path
    events: list[NormalizedEvent] = field(default_factory=list)
    raw_events: list[NormalizedRawEntry] = field(default_factory=list)
