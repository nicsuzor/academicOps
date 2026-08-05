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
    call_id: str | None = None


@dataclass(frozen=True)
class NormalizedEvent:
    """A single normalized step or event within a transcript session."""

    event_id: str
    timestamp: str  # ISO-8601 string
    source: str  # "user", "model", "system", "tool"
    type: str  # "message", "tool_output", "checkpoint", "system", "unknown"
    content: str
    thinking: str | None = None
    # True when this event carried an extended-thinking block whose content
    # came back empty — Claude Code ships the block's `signature` field but
    # not recoverable text. Distinct from `thinking is None` (no thinking
    # block at all): this event *did* think, but that reasoning cannot be
    # shown. See specs/transcript-pipeline.md, On-disk trace convention.
    thinking_opaque: bool = False
    tool_calls: list[NormalizedToolCall] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedRawEntry:
    """An unrecognized or unparseable line from the raw log preserved for logging."""

    line_no: int
    type: str | None
    raw: dict[str, Any]


@dataclass
class SubagentTranscript:
    """A sidechain conversation run by a subagent on behalf of a parent session.

    Subagent logs carry the *parent's* `session_id`, so they are never sessions
    in their own right: they are branches of one session, and belong inside the
    parent's record.
    """

    agent_id: str
    source_file: Path
    events: list[NormalizedEvent] = field(default_factory=list)
    agent_type: str | None = None
    name: str | None = None
    description: str | None = None
    parent_tool_use_id: str | None = None
    parent_agent_id: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0
    # From the `agent-<id>.meta.json` sidecar. `spawn_depth` is NOT reliably
    # parent+1 for team-mode spawns (a mailbox/named spawn) — `parent_agent_id`
    # is the field that stays correct there; treat spawn_depth as a rendering
    # hint, not ground truth for tree structure. `is_fork` marks a `fork`-type
    # spawn (inherits the parent's context) rather than a fresh subagent.
    spawn_depth: int | None = None
    is_fork: bool = False
    model: str | None = None
    degraded: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        """A human-readable identifier, preferring the most specific name available."""
        return self.name or self.agent_type or self.agent_id


@dataclass
class NormalizedSession:
    """A complete session transcript, containing the list of events and raw entries.

    `events` is the trunk (main-thread) conversation. Work delegated to
    subagents lives in `subagents`, one entry per sidechain transcript.
    """

    session_id: str
    source_file: Path
    events: list[NormalizedEvent] = field(default_factory=list)
    raw_events: list[NormalizedRawEntry] = field(default_factory=list)
    tokens_used: int = 0
    cost_usd: float = 0.0
    subagents: list[SubagentTranscript] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    @property
    def source_files(self) -> list[Path]:
        """Every file on disk this session was reconstructed from."""
        return [self.source_file, *(sub.source_file for sub in self.subagents)]

    @property
    def total_event_count(self) -> int:
        """Trunk events plus every subagent event."""
        return len(self.events) + sum(len(sub.events) for sub in self.subagents)

    @property
    def total_tokens_used(self) -> int:
        """Trunk tokens plus every subagent's tokens — the session's real spend."""
        return self.tokens_used + sum(sub.tokens_used for sub in self.subagents)

    @property
    def total_cost_usd(self) -> float:
        """Trunk cost plus every subagent's cost — the session's real spend."""
        return self.cost_usd + sum(sub.cost_usd for sub in self.subagents)
