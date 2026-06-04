"""Parse reviewer verdicts and issue counts from subagent invocations.

Build B of Safeguard ROI v0 (epic aops-85b082c5). Emits one row per subagent
invocation with the verdict token (APPROVE/REVISE/PASS/FAIL/ESCALATE) and an
issues count, both read from a structured trailer the agent emits at the end
of its review.

## Contract — what reviewers must emit

The reviewer agent ends its message with HTML-comment markers on their own
lines. These are invisible in rendered markdown but trivial to parse:

    <!-- aops-verdict: APPROVE -->
    <!-- aops-issues: 0 -->

`aops-verdict` value MUST be one of ``VERDICT_TOKENS`` (uppercase, exact).
`aops-issues` value MUST be a non-negative integer. Either marker may be
omitted; the corresponding field then resolves to ``None``.

This is a structured field with a fixed syntax — the parser does no
inference about agent intent. Anything that doesn't match the marker is
ignored. Agents that don't emit the trailer yield ``verdict=None`` and
``issues_count=None``.

## Why structured markers, not regex over prose

Earlier iterations tried to extract verdicts via regex permutations over
markdown (`# Verdict: TOKEN`, `**Verdict:** TOKEN`, em-dash variants…).
That is "shitty NLP": offloading a semantic question — *what did this
reviewer conclude?* — to a deterministic heuristic that compensates for
inconsistent agent output. The fix is to make the contract strict at the
source. Reviewers declare the verdict in a fixed-syntax field; we read
the field. No semantic extraction is performed.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .transcript_parser import Entry


VERDICT_TOKENS: tuple[str, ...] = ("APPROVE", "REVISE", "PASS", "FAIL", "ESCALATE")
_ALLOWED_TOKENS = frozenset(VERDICT_TOKENS)

# Structured trailer markers. Each occupies its own line; surrounding whitespace
# is permitted but no markdown decoration is. The values are pure data: a
# canonical token (verdict) or a non-negative integer (issues).
_VERDICT_MARKER = re.compile(r"^\s*<!--\s*aops-verdict:\s*([A-Za-z]+)\s*-->\s*$")
_ISSUES_MARKER = re.compile(r"^\s*<!--\s*aops-issues:\s*(\d+)\s*-->\s*$")


def extract_verdict(text: str) -> str | None:
    """Return the canonical verdict token from the structured trailer, or None.

    Walks the text for the first ``<!-- aops-verdict: TOKEN -->`` line whose
    TOKEN is one of ``VERDICT_TOKENS``. No fuzzy matching, no markdown
    permutations — agents must emit the marker verbatim or the field
    resolves to ``None`` (fail-open).
    """
    if not text:
        return None
    for line in text.splitlines():
        m = _VERDICT_MARKER.match(line)
        if not m:
            continue
        token = m.group(1).upper()
        if token in _ALLOWED_TOKENS:
            return token
    return None


def extract_issues_count(text: str) -> int | None:
    """Return the issues count from the structured trailer, or None.

    Walks the text for the first ``<!-- aops-issues: N -->`` line, where
    N is a non-negative integer. Returns ``None`` when no marker is found,
    which downstream rollups treat as "unknown" (distinct from "0 issues").
    """
    if not text:
        return None
    for line in text.splitlines():
        m = _ISSUES_MARKER.match(line)
        if m:
            return int(m.group(1))
    return None


def last_assistant_text(entries: list[Entry]) -> str:
    """Return the concatenated text of the last assistant entry, or "".

    Skips ``thinking`` / ``redacted_thinking`` blocks; only ``text`` blocks
    are included. If the message ``content`` is a bare string, returns that.
    """
    for entry in reversed(entries):
        if entry.type != "assistant" or not entry.message:
            continue
        content = entry.message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        parts.append(text)
            if parts:
                return "\n".join(parts)
    return ""


def _build_subagent_type_index(main_entries: list[Entry]) -> dict[str, str]:
    """Map agent file id (the file-stem after ``agent-``) to its subagent_type.

    Walks main session entries pairing Task/Agent tool_use blocks with their
    tool_result. The result's ``tool_use_result.agentId`` is the file id; the
    tool_use's ``input.subagent_type`` is the human-readable type
    (e.g. ``rbg``, ``aops-core:pauli``).
    """
    type_by_tool_id: dict[str, str] = {}
    for entry in main_entries:
        if entry.type != "assistant" or not entry.message:
            continue
        content = entry.message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            if block.get("name") not in ("Task", "Agent"):
                continue
            tool_id = block.get("id")
            if not tool_id:
                continue
            tool_input = block.get("input") or {}
            subagent_type = tool_input.get("subagent_type")
            if subagent_type:
                type_by_tool_id[tool_id] = subagent_type

    index: dict[str, str] = {}
    for entry in main_entries:
        if entry.type != "user":
            continue
        message = entry.message or {}
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            tool_id = block.get("tool_use_id")
            if not tool_id or tool_id not in type_by_tool_id:
                continue
            result = entry.tool_use_result
            agent_file_id = None
            if isinstance(result, dict):
                agent_file_id = result.get("agentId")
            if agent_file_id:
                index[agent_file_id] = type_by_tool_id[tool_id]
    return index


def build_subagent_verdicts(
    main_entries: list[Entry],
    agent_entries: dict[str, list[Entry]] | None,
    by_agent: dict[str, dict[str, int]] | None,
) -> list[dict[str, Any]]:
    """Build the per-invocation verdict rows for the per-session summary.

    Args:
        main_entries: Main session entries (used to resolve ``subagent_type``).
        agent_entries: Mapping of agent file id -> entries from the subagent
            JSONL file. Each key represents one Task invocation.
        by_agent: ``UsageStats.by_agent`` mapping for token accounting.

    Returns:
        A list of dicts, one per subagent invocation, with keys
        ``invocation_id``, ``agent_id``, ``verdict``, ``issues_count``,
        ``tokens``. Order follows ``agent_entries`` insertion order.
        ``verdict`` and ``issues_count`` are ``None`` when the agent did
        not emit the structured trailer.
    """
    if not agent_entries:
        return []

    type_index = _build_subagent_type_index(main_entries)
    rows: list[dict[str, Any]] = []
    for invocation_id, entries in agent_entries.items():
        text = last_assistant_text(entries)
        agent_stats = (by_agent or {}).get(invocation_id) or {}
        rows.append(
            {
                "invocation_id": invocation_id,
                "agent_id": type_index.get(invocation_id),
                "verdict": extract_verdict(text),
                "issues_count": extract_issues_count(text),
                "tokens": int(agent_stats.get("input", 0)) + int(agent_stats.get("output", 0)),
            }
        )
    return rows
