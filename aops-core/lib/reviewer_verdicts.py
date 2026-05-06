"""Parse reviewer verdicts and issue counts from subagent invocations.

Build B of Safeguard ROI v0 (epic aops-85b082c5). Emits one row per subagent
invocation with the verdict token (APPROVE/REVISE/PASS/FAIL/ESCALATE) and a
crude count of bullet/numbered list items in the final assistant message.

Failure mode is "fail open": unparseable messages yield ``verdict=None``,
``issues_count=0``. The downstream cost/benefit join treats those as
unclassified rather than aborting the rollup.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .transcript_parser import Entry


VERDICT_TOKENS: tuple[str, ...] = ("APPROVE", "REVISE", "PASS", "FAIL", "ESCALATE")

# Match a verdict token preceded only by markdown decoration (#, *, _, whitespace,
# optional "Verdict:" label). Word boundary on the trailing side so APPROVED etc.
# don't false-match.
_VERDICT_RE = re.compile(
    r"^[\s#*_>`]*"
    r"(?:\*+\s*)?"
    r"(?:verdict\s*[:\-—–]\s*)?"
    r"(?:\*+\s*)?"
    r"(APPROVE|REVISE|PASS|FAIL|ESCALATE)\b",
    re.IGNORECASE,
)

_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*]\s+|\d+\.\s+)")

# How many leading lines of the final message we scan for a verdict. Verdicts
# in practice appear at the very top; scanning the whole message increases the
# chance of a false-positive from quoted code or examples.
_VERDICT_SCAN_LINES = 30


def extract_verdict(text: str) -> str | None:
    """Return the canonical verdict token from the text, or None.

    Scans the first ``_VERDICT_SCAN_LINES`` non-empty lines for a match.
    Recognises bare tokens, markdown-header tokens, and ``Verdict: TOKEN``
    style labels, case-insensitively.
    """
    if not text:
        return None
    seen = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        seen += 1
        if seen > _VERDICT_SCAN_LINES:
            break
        m = _VERDICT_RE.match(line)
        if m:
            return m.group(1).upper()
    return None


def count_issues(text: str) -> int:
    """Count bullet/numbered list items in the text.

    Each line matching ``- ``, ``* ``, or ``<n>.`` (with optional leading
    whitespace) counts as one issue. Min 0.
    """
    if not text:
        return 0
    return sum(1 for line in text.splitlines() if _LIST_ITEM_RE.match(line))


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
                "issues_count": count_issues(text),
                "tokens": int(agent_stats.get("input", 0)) + int(agent_stats.get("output", 0)),
            }
        )
    return rows
