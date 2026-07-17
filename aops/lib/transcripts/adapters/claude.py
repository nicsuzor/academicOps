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

logger = logging.getLogger(__name__)

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
