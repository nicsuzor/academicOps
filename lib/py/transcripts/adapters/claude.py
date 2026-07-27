"""Claude Code parse/render adapter, wrapping the live `claude-code-log` library.

`claude-code-log` owns the Claude Code JSONL schema (Pydantic discriminated
union) and rendering (markdown/HTML/JSON) so we stop hand-maintaining a
parser against a schema we don't control. This module is the single seam
academicOps code should import through — nothing else should import
`claude_code_log` directly.

Tolerant loading: `claude_code_log.converter.load_transcript` already
guards against crashes on malformed lines, but a top-level `type` it
doesn't recognize is either silently dropped or only ever `print()`-ed to
stdout (easy to miss, not machine-actionable). We independently scan the
raw JSONL lines and preserve every unrecognized-type line as a `RawEntry`,
logged via the standard `logging` module, so upstream schema drift shows
up as visible degraded data rather than a silent loss.

Subagents: a session's delegated work is written to separate sidechain logs
that reuse the parent's `sessionId`. `load_claude_session` is the entry point
that reconstructs a whole session — trunk plus sidechains — and it refuses a
sidechain log handed to it directly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_code_log.converter import load_transcript
from claude_code_log.models import TranscriptEntry
from claude_code_log.renderer import get_renderer

from transcripts.model import (
    NormalizedEvent,
    NormalizedRawEntry,
    NormalizedSession,
    NormalizedToolCall,
    SubagentTranscript,
)

logger = logging.getLogger(__name__)

# Claude Code writes each subagent's sidechain conversation to
# `<project>/<session-id>/subagents/**/agent-<agentId>.jsonl`, with an
# `agent-<agentId>.meta.json` sidecar describing what it was asked to do.
# Every record in those files carries the *parent's* `sessionId`, so they are
# branches of one session, never sessions of their own.
SUBAGENT_DIR_NAME = "subagents"
SUBAGENT_FILE_PREFIX = "agent-"

# The top-level `type` values claude_code_log parses into typed Pydantic
# models (see claude_code_log.converter.load_transcript). Anything else is
# preserved as a RawEntry instead of being dropped.
KNOWN_ENTRY_TYPES = frozenset(
    {
        "user",
        "assistant",
        "summary",
        "ai-title",
        "system",
        "queue-operation",
        "attachment",
    }
)


@dataclass(frozen=True)
class RawEntry:
    """A JSONL line whose top-level `type` claude-code-log doesn't parse into a typed model."""

    line_no: int
    type: str | None
    raw: dict[str, Any]


@dataclass
class ClaudeTranscript:
    """Result of tolerantly loading a Claude Code JSONL transcript."""

    source: Path
    entries: list[TranscriptEntry] = field(default_factory=list)
    raw_entries: list[RawEntry] = field(default_factory=list)


def _scan_raw_entries(jsonl_path: Path) -> list[RawEntry]:
    """Preserve every line whose `type` claude-code-log won't turn into a typed model."""
    raw_entries: list[RawEntry] = []
    try:
        text = jsonl_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        logger.warning("could not read %s for raw-entry scan", jsonl_path, exc_info=True)
        return raw_entries

    for line_no, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("%s:%d is not valid JSON, skipping", jsonl_path, line_no)
            continue
        if not isinstance(obj, dict):
            continue
        entry_type = obj.get("type")
        if entry_type not in KNOWN_ENTRY_TYPES:
            logger.warning(
                "%s:%d: unrecognized transcript entry type %r, preserving as raw",
                jsonl_path,
                line_no,
                entry_type,
            )
            raw_entries.append(RawEntry(line_no=line_no, type=entry_type, raw=obj))
    return raw_entries


def load_claude_transcript(jsonl_path: Path, *, silent: bool = True) -> ClaudeTranscript:
    """Tolerantly parse a Claude Code JSONL transcript.

    Never raises: a claude-code-log failure degrades to an empty `entries`
    list (logged) rather than propagating, and unrecognized-type lines are
    always captured in `raw_entries` regardless of what claude-code-log
    itself decides to do with them internally.
    """
    raw_entries = _scan_raw_entries(jsonl_path)

    try:
        entries = load_transcript(jsonl_path, silent=silent)
    except Exception:
        logger.exception(
            "claude-code-log failed to parse %s; degrading to raw entries only", jsonl_path
        )
        entries = []

    return ClaudeTranscript(source=jsonl_path, entries=entries, raw_entries=raw_entries)


def render_claude_session(
    entries: list[TranscriptEntry],
    session_id: str,
    *,
    format: str = "markdown",
    title: str | None = None,
) -> str:
    """Render already-parsed entries via claude-code-log's renderer.

    Delegates all format-specific rendering (markdown/html/json) to
    claude-code-log — this adapter does not maintain its own renderer.
    """
    renderer = get_renderer(format)
    # generate_session returns Optional[str] (None for an empty session); we
    # always hand back a str so callers get a predictable, never-None contract.
    return renderer.generate_session(entries, session_id, title=title) or ""


def is_sidechain_file(jsonl_path: Path) -> bool:
    """True when this *file* is a subagent's sidechain log rather than a trunk.

    Judged from the file's own records, never from a loaded entry list:
    claude-code-log inlines a subagent's records into the trunk it can link
    them to, so a trunk's entries routinely include sidechain ones. Only the
    file on disk says what the file is.
    """
    if SUBAGENT_DIR_NAME in jsonl_path.parts:
        return True
    try:
        with jsonl_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    return bool(obj.get("isSidechain"))
    except OSError:
        logger.warning("could not read %s to classify it", jsonl_path, exc_info=True)
    return False


def find_subagent_files(jsonl_path: Path) -> list[Path]:
    """Sidechain transcripts belonging to the Claude trunk transcript at `jsonl_path`."""
    subagent_dir = jsonl_path.parent / jsonl_path.stem / SUBAGENT_DIR_NAME
    if not subagent_dir.is_dir():
        return []
    return sorted(
        p
        for p in subagent_dir.glob("**/*.jsonl")
        if p.is_file() and p.name.startswith(SUBAGENT_FILE_PREFIX)
    )


def _accumulate_usage(entries: list[TranscriptEntry]) -> tuple[int, float]:
    """Total tokens and estimated USD cost across every entry carrying usage data."""
    total_input = 0
    total_cache_creation = 0
    total_cache_read = 0
    total_output = 0

    for entry in entries:
        if (
            hasattr(entry, "message")
            and entry.message
            and hasattr(entry.message, "usage")
            and entry.message.usage
        ):
            u = entry.message.usage
            total_input += getattr(u, "input_tokens", 0) or 0
            total_cache_creation += getattr(u, "cache_creation_input_tokens", 0) or 0
            total_cache_read += getattr(u, "cache_read_input_tokens", 0) or 0
            total_output += getattr(u, "output_tokens", 0) or 0

    tokens_used = total_input + total_cache_creation + total_cache_read + total_output
    cost_usd = (
        total_input * 3.0
        + total_cache_creation * 3.75
        + total_cache_read * 0.3
        + total_output * 15.0
    ) / 1_000_000

    return tokens_used, cost_usd


def _entries_to_events(entries: list[TranscriptEntry]) -> list[NormalizedEvent]:
    """Map parsed Claude Code entries onto the common NormalizedEvent model."""
    events: list[NormalizedEvent] = []
    for entry in entries:
        entry_type = entry.type
        if entry_type == "user":
            content_parts = []
            if entry.message and entry.message.content:
                for block in entry.message.content:
                    if hasattr(block, "text") and block.text:
                        content_parts.append(block.text)
                    elif getattr(block, "type", None) == "tool_result":
                        # Extract and format tool result content
                        result_content = ""
                        if hasattr(block, "content") and block.content is not None:
                            if isinstance(block.content, str):
                                result_content = block.content
                            elif isinstance(block.content, list):
                                text_parts = []
                                for item in block.content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_parts.append(str(item.get("text", "")))
                                    else:
                                        text_parts.append(json.dumps(item, ensure_ascii=False))
                                result_content = "\n".join(text_parts)
                            else:
                                result_content = str(block.content)

                        # Truncate to prevent bloat (keep file sizes efficient)
                        limit = 4000
                        if len(result_content) > limit:
                            truncated_part = len(result_content) - limit
                            result_content = (
                                result_content[:limit]
                                + f"\n\n... [TRUNCATED - {truncated_part} chars of tool result output omitted]"
                            )

                        tool_use_id = getattr(block, "tool_use_id", "unknown")
                        is_error = getattr(block, "is_error", False)
                        events.append(
                            NormalizedEvent(
                                event_id=f"{entry.uuid}_tool_{tool_use_id}",
                                timestamp=entry.timestamp,
                                source="tool",
                                type="tool_output",
                                content=result_content,
                                meta={
                                    "tool_use_id": tool_use_id,
                                    "is_error": is_error,
                                    "cwd": entry.cwd,
                                },
                            )
                        )
            content = "".join(content_parts).strip()
            if content:
                events.append(
                    NormalizedEvent(
                        event_id=entry.uuid,
                        timestamp=entry.timestamp,
                        source="user",
                        type="message",
                        content=content,
                        meta={"user_type": entry.userType, "cwd": entry.cwd},
                    )
                )
        elif entry_type == "assistant":
            content_parts = []
            thinking_parts = []
            tool_calls = []
            if entry.message and entry.message.content:
                for block in entry.message.content:
                    if block.type == "text" and hasattr(block, "text") and block.text:
                        content_parts.append(block.text)
                    elif block.type == "thinking" and hasattr(block, "thinking") and block.thinking:
                        thinking_parts.append(block.thinking)
                    elif block.type == "tool_use":
                        tool_calls.append(
                            NormalizedToolCall(
                                name=block.name,
                                args=block.input if isinstance(block.input, dict) else {},
                                call_id=getattr(block, "id", None),
                            )
                        )
            content = "".join(content_parts)
            thinking = "".join(thinking_parts) if thinking_parts else None
            events.append(
                NormalizedEvent(
                    event_id=entry.uuid,
                    timestamp=entry.timestamp,
                    source="model",
                    type="message",
                    content=content,
                    thinking=thinking,
                    tool_calls=tool_calls if tool_calls else None,
                    meta={"cwd": entry.cwd},
                )
            )
        elif entry_type == "attachment":
            att = entry.attachment or {}
            content = att.get("content") or att.get("stdout") or att.get("stderr") or ""
            events.append(
                NormalizedEvent(
                    event_id=entry.uuid,
                    timestamp=entry.timestamp,
                    source="tool",
                    type="tool_output",
                    content=content,
                    meta={"attachment": att, "cwd": entry.cwd},
                )
            )
        elif entry_type == "queue-operation":
            op = getattr(entry, "operation", "")
            content = getattr(entry, "content", "") or ""
            events.append(
                NormalizedEvent(
                    event_id=f"queue_{entry.timestamp}",
                    timestamp=entry.timestamp,
                    source="system",
                    type="checkpoint",
                    content=f"Queue operation: {op}" + (f"\nContent: {content}" if content else ""),
                    meta={"operation": op},
                )
            )
        elif entry_type == "summary":
            events.append(
                NormalizedEvent(
                    event_id=entry.leafUuid or "",
                    timestamp="",
                    source="system",
                    type="checkpoint",
                    content=entry.summary,
                    meta={"cwd": entry.cwd},
                )
            )
        elif entry_type == "system":
            sys_content = entry.content or ""
            if isinstance(sys_content, list):
                sys_content = "".join(getattr(b, "text", str(b)) for b in sys_content)
            else:
                sys_content = str(sys_content)
            events.append(
                NormalizedEvent(
                    event_id=entry.uuid,
                    timestamp=entry.timestamp,
                    source="system",
                    type="system",
                    content=sys_content,
                    meta={"subtype": getattr(entry, "subtype", None), "cwd": entry.cwd},
                )
            )
        elif entry_type == "ai-title":
            events.append(
                NormalizedEvent(
                    event_id=f"title_{entry.sessionId}",
                    timestamp="",
                    source="system",
                    type="system",
                    content=entry.aiTitle or "",
                )
            )

    return events


def _is_sidechain_entry(entry: TranscriptEntry) -> bool:
    """True for a record belonging to a subagent's conversation.

    `isSidechain` alone: claude-code-log also copies a spawning tool_result's
    `agentId` onto trunk entries, so `agentId` does not imply sidechain.
    """
    return bool(getattr(entry, "isSidechain", False))


def normalize_claude_transcript(transcript: ClaudeTranscript) -> NormalizedSession:
    """Map a ClaudeTranscript into the common NormalizedSession model.

    Only the main thread becomes `events`. claude-code-log inlines the records
    of every subagent it can link back to its spawning tool call, and counting
    those as trunk events overstates both the conversation and its cost;
    `load_claude_session` is what turns them into `subagents`.
    """
    # Every entry model carries `sessionId`, but a summary record types it as
    # None, so bind it before testing to keep the narrowing.
    session_id = "unknown"
    for entry in transcript.entries:
        entry_session_id = entry.sessionId
        if entry_session_id:
            session_id = entry_session_id
            break

    trunk_entries = [entry for entry in transcript.entries if not _is_sidechain_entry(entry)]
    tokens_used, cost_usd = _accumulate_usage(trunk_entries)

    raw_events = [
        NormalizedRawEntry(line_no=raw.line_no, type=raw.type, raw=raw.raw)
        for raw in transcript.raw_entries
    ]

    return NormalizedSession(
        session_id=session_id,
        source_file=transcript.source,
        events=_entries_to_events(trunk_entries),
        raw_events=raw_events,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )


def _read_subagent_meta(jsonl_path: Path) -> dict[str, Any]:
    """Read the `agent-<id>.meta.json` sidecar Claude Code writes next to a sidechain log."""
    meta_path = jsonl_path.with_suffix(".meta.json")
    if not meta_path.is_file():
        return {}
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("could not read subagent metadata %s", meta_path, exc_info=True)
        return {}
    return meta if isinstance(meta, dict) else {}


def _agent_id_from_path(jsonl_path: Path) -> str:
    """The subagent's id, which Claude Code encodes in the log's filename."""
    return jsonl_path.stem.removeprefix(SUBAGENT_FILE_PREFIX)


def _describe_from_parent(
    parent_events: list[NormalizedEvent], tool_use_id: str | None
) -> str | None:
    """Recover a subagent's brief from the parent's spawning tool call.

    The parent's `Task`/`Agent` tool_use block carries the description that
    commissioned the subagent; the sidecar's `toolUseId` points back at it.
    """
    if not tool_use_id:
        return None
    for event in parent_events:
        for call in event.tool_calls or ():
            if call.call_id == tool_use_id:
                args = call.args or {}
                description = args.get("description") or args.get("prompt")
                return str(description) if description else None
    return None


def _build_subagent(
    agent_id: str,
    source_file: Path,
    entries: list[TranscriptEntry],
    parent_events: list[NormalizedEvent],
) -> SubagentTranscript:
    meta = _read_subagent_meta(source_file)
    tokens_used, cost_usd = _accumulate_usage(entries)
    tool_use_id = meta.get("toolUseId")
    return SubagentTranscript(
        agent_id=agent_id,
        source_file=source_file,
        events=_entries_to_events(entries),
        agent_type=meta.get("agentType"),
        name=meta.get("name"),
        description=meta.get("description") or _describe_from_parent(parent_events, tool_use_id),
        parent_tool_use_id=tool_use_id,
        parent_agent_id=meta.get("parentAgentId"),
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )


def load_subagent_transcripts(
    jsonl_path: Path,
    parent_events: list[NormalizedEvent],
    inlined: list[TranscriptEntry] | None = None,
) -> list[SubagentTranscript]:
    """Every sidechain conversation belonging to the trunk log at `jsonl_path`.

    Two paths reach the same place. Subagents claude-code-log could link to
    their spawning tool call arrive already inlined in the trunk's entries and
    are regrouped by `agentId` from `inlined`; subagents it could not link —
    in-process teammates carry no `toolUseId`, and a nested spawn's id lives in
    another subagent's log rather than the trunk's — are read from their files.
    Each agent is built once, whichever path found it.

    Ordered by first event time so the parent's record reads chronologically.
    """
    subagents: list[SubagentTranscript] = []
    seen: set[str] = set()
    subagent_files = {_agent_id_from_path(path): path for path in find_subagent_files(jsonl_path)}

    grouped: dict[str, list[TranscriptEntry]] = {}
    for entry in inlined or ():
        agent_id = getattr(entry, "agentId", None)
        if agent_id:
            grouped.setdefault(str(agent_id), []).append(entry)

    for agent_id, entries in grouped.items():
        source_file = subagent_files.get(agent_id, jsonl_path)
        subagents.append(_build_subagent(agent_id, source_file, entries, parent_events))
        seen.add(agent_id)

    for agent_id, path in subagent_files.items():
        if agent_id in seen:
            continue
        transcript = load_claude_transcript(path)
        if not transcript.entries:
            continue
        # A subagent may itself have spawned others, whose records
        # claude-code-log inlines here in turn. Keep this agent's own records.
        own = [
            entry
            for entry in transcript.entries
            if str(getattr(entry, "agentId", "") or agent_id) == agent_id
        ]
        subagents.append(_build_subagent(agent_id, path, own, parent_events))
        seen.add(agent_id)

    subagents.sort(key=lambda sub: sub.events[0].timestamp if sub.events else "")
    return subagents


def load_claude_session(jsonl_path: Path) -> NormalizedSession | None:
    """Load a Claude Code trunk transcript together with its subagent sidechains.

    Returns None for an unreadable file, and for a sidechain log handed in
    directly: those carry the parent's `session_id`, so processing one as a
    session in its own right overwrites the parent's record.
    """
    if is_sidechain_file(jsonl_path):
        logger.error(
            "%s is a subagent sidechain carrying its parent's session id; "
            "process the parent transcript instead",
            jsonl_path,
        )
        return None

    transcript = load_claude_transcript(jsonl_path)
    if not transcript.entries and not transcript.raw_entries:
        return None

    session = normalize_claude_transcript(transcript)
    session.subagents = load_subagent_transcripts(
        jsonl_path,
        session.events,
        [entry for entry in transcript.entries if _is_sidechain_entry(entry)],
    )
    if session.subagents:
        logger.info(
            "session %s: attached %d subagent transcript(s), %d extra events",
            session.session_id,
            len(session.subagents),
            session.total_event_count - len(session.events),
        )
    return session
