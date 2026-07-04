"""Completion-claim evidence contract (epic aops-262def9f, WI2).

The invariant being wired: no completion claim (task → merge_ready/done,
PR → ready, artifact handed over) without attached independent-verification
evidence bound to final artifact state.

Evidence contract (three fields, all required on a completion claim):

- ``verified_by``  — reviewer identity; the reviewer must NOT be the
  producer. "self"/"me"/"producer" and friends are rejected outright.
- ``verified_sha`` — artifact-state identifier (git SHA / content hash)
  the review was performed against. A later state change voids the
  evidence — live verification against the PR head is the tool
  boundary's job (polecat/validation.py).
- ``findings``     — concrete findings with file:line references, OR a
  method-named null result ("no defects found via pytest tests/hooks +
  read of lib/gates/definitions.py:294-398"). Attestation-only strings
  ("clean", "verified", "LGTM") are NOT evidence — they count as NOT RUN.

Evidence rides either as explicit fields (``release_task`` /
``complete_task`` kwargs at the polecat bridge) or as git-trailer-style
lines embedded in the summary / completion_evidence text — the only
channel available to agents calling the PKB MCP tools directly:

    Verified-By: marsha (session 9f3e3217)
    Verified-SHA: 51ed2fff
    Findings: no defects found via pytest tests/hooks + read of
      aops-core/lib/gates/definitions.py:294-398

All checks here are deterministic string/state checks — no LLM call per
fire (CBA §4.1 item 4; see the epic's root-cause/CBA document). Consumers:

- hooks/router.py — records completion claims on the session state at
  PostToolUse time (works in is_subagent sessions, where gate dispatch
  skips tool-call events).
- lib/gates/custom_conditions.py — handover-gate evidence predicate at
  Stop, and the qa gate's verifier-verdict satisfier.
- polecat/pkb_bridge.py — the release_task/complete_task tool boundary.
"""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lib.hook_context import HookContext
    from lib.session_state import SessionState

EVIDENCE_FIELDS = ("verified_by", "verified_sha", "findings")

# Statuses that constitute a completion claim at a task tool boundary.
COMPLETION_CLAIM_STATUSES = frozenset({"merge_ready", "done"})

# Task tools that can carry a completion claim. Matches both the bare tool
# name (bridge/tests) and MCP-prefixed forms (mcp__pkb__release_task,
# mcp__plugin_aops-core_pkb__update_task, ...). claim_task deliberately
# does NOT match.
_COMPLETION_TOOL_RE = re.compile(r"(?:^|__)(release_task|complete_task|update_task)$")

# Canonical trailer block, quoted verbatim in actionable error messages so
# a blocked agent knows the exact re-issue format.
TRAILER_FORMAT_HELP = (
    "Attach evidence trailers (three lines) to the summary/evidence text:\n"
    "  Verified-By: <reviewer identity — NOT the producer>\n"
    "  Verified-SHA: <git head SHA / content hash the review ran against>\n"
    "  Findings: <findings with file:line refs, or a method-named null result,\n"
    "    e.g. 'no defects found via pytest tests/hooks + read of "
    "lib/gates/definitions.py:294-398'>"
)

# Git-trailer-style evidence lines. Findings supports folded continuation
# lines (subsequent lines indented, git-trailer convention).
_TRAILER_RES = {
    "verified_by": re.compile(r"(?im)^[ \t]*verified-by[ \t]*:[ \t]*(.+?)[ \t]*$"),
    "verified_sha": re.compile(r"(?im)^[ \t]*verified-sha[ \t]*:[ \t]*(.+?)[ \t]*$"),
    "findings": re.compile(r"(?im)^[ \t]*findings[ \t]*:[ \t]*(.+(?:\n[ \t]+.+)*)"),
}

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")

# A file:line reference — the minimum shape of a concrete finding.
_FILE_LINE_RE = re.compile(r"[\w./\\-]+\.[A-Za-z0-9_]+:\d+")

# Method-named null result: a "no defects/findings/..." claim that also
# names HOW the reviewer looked (via/using/ran/`cmd`). Either half alone is
# attestation, not evidence.
_NULL_RESULT_RE = re.compile(
    r"(?i)\bno\s+(?:defects?|findings?|issues?|regressions?|problems?|failures?|failing)\b"
)
_METHOD_MARKER_RE = re.compile(r"(?i)\b(?:via|using|by running|ran|through|per|with)\b|`[^`]+`")

# Identities that can never satisfy reviewer-independence.
_SELF_IDENTITIES = frozenset(
    {"self", "me", "producer", "author", "same", "unknown", "n/a", "none", "-", "worker"}
)

# Verifier verdict channel (WI3): labelled form first ("**Verdict:** PASS",
# any case), then a bare UPPERCASE token — lowercase "pass" in prose must
# not count.
_VERDICT_LABELED_RE = re.compile(r"(?i)\bverdict\b[^A-Za-z0-9\r\n]{0,20}(PASS|FAIL|REVISE)\b")
_VERDICT_BARE_RE = re.compile(r"\b(PASS|FAIL|REVISE)\b")


class EvidenceValidationError(ValueError):
    """Raised when a completion claim lacks contract-conformant evidence.

    The message is actionable by construction: it lists every problem and
    quotes the exact trailer format needed to re-issue the call.
    """

    def __init__(self, action: str, task_id: str, problems: list[str]):
        self.action = action
        self.task_id = task_id
        self.problems = list(problems)
        bullet_list = "\n".join(f"  - {p}" for p in problems)
        super().__init__(
            f"{action}({task_id}) is a completion claim but the "
            f"independent-verification evidence contract is not met:\n{bullet_list}\n"
            f"{TRAILER_FORMAT_HELP}\n"
            "Attestation-only evidence ('clean'/'verified' with no findings or "
            "method) counts as NOT RUN. If the work is not verified, release "
            "with a non-terminal status (blocked/partial) instead."
        )


def parse_evidence_trailers(text: str | None) -> dict[str, str]:
    """Extract Verified-By / Verified-SHA / Findings trailer lines from text.

    Returns only the fields found; folded continuation lines on Findings are
    joined with single spaces.
    """
    if not isinstance(text, str) or not text:
        return {}
    out: dict[str, str] = {}
    for field, pattern in _TRAILER_RES.items():
        m = pattern.search(text)
        if m:
            value = re.sub(r"\s*\n[ \t]+", " ", m.group(1)).strip()
            if value:
                out[field] = value
    return out


def extract_evidence(tool_input: dict[str, Any]) -> dict[str, str]:
    """Pull evidence fields from a task-tool call's input.

    Explicit fields win; missing ones fall back to trailer lines embedded in
    the ``summary`` / ``completion_evidence`` text (the only channel agents
    calling the PKB MCP tools directly have). Always returns all three keys
    ("" when absent) so validation reports each gap by name.
    """
    evidence: dict[str, str] = {}
    for field in EVIDENCE_FIELDS:
        value = tool_input.get(field)
        if isinstance(value, str) and value.strip():
            evidence[field] = value.strip()
    if len(evidence) < len(EVIDENCE_FIELDS):
        text = "\n".join(
            part
            for part in (tool_input.get("summary"), tool_input.get("completion_evidence"))
            if isinstance(part, str)
        )
        trailers = parse_evidence_trailers(text)
        for field in EVIDENCE_FIELDS:
            evidence.setdefault(
                field, trailers.get(field, "")
            )  # allow-fallback: "" reported as a named problem by validation
    return evidence


def validate_completion_evidence(
    evidence: dict[str, str], producer: str | None = None
) -> list[str]:
    """Validate the evidence contract; returns a list of problems (empty = ok).

    ``producer`` is the producer identity when the caller knows it (PR
    author, worker assignee); reviewer == producer is rejected. Structural
    checks only — the live PR-head/author checks live in polecat/validation.
    """
    problems: list[str] = []

    verified_by = (
        evidence.get("verified_by") or ""
    ).strip()  # allow-fallback: "" -> named problem below
    if not verified_by:
        problems.append("missing Verified-By (independent reviewer identity)")
    elif verified_by.lower() in _SELF_IDENTITIES:
        problems.append(
            f"Verified-By={verified_by!r} is not an independent reviewer "
            "(reviewer must not be the producer)"
        )
    elif producer and verified_by.lower() == producer.strip().lower():
        problems.append(
            f"Verified-By={verified_by!r} equals the producer identity "
            f"({producer!r}) — reviewer must not be the producer"
        )

    verified_sha = (
        evidence.get("verified_sha") or ""
    ).strip()  # allow-fallback: "" -> named problem below
    if not verified_sha:
        problems.append("missing Verified-SHA (artifact-state identifier the review ran against)")
    elif not _SHA_RE.match(verified_sha):
        problems.append(
            f"Verified-SHA={verified_sha!r} is not a git SHA / content hash "
            "(expected 7-64 hex chars)"
        )

    findings = (evidence.get("findings") or "").strip()  # allow-fallback: "" -> named problem below
    if not findings:
        problems.append("missing Findings (file:line findings or a method-named null result)")
    elif not (
        _FILE_LINE_RE.search(findings)
        or (_NULL_RESULT_RE.search(findings) and _METHOD_MARKER_RE.search(findings))
    ):
        problems.append(
            f"Findings={findings!r} is attestation-only — needs file:line "
            "references or a null result that names the method used "
            "(attestation-only counts as NOT RUN)"
        )

    return problems


def detect_completion_claim(
    tool_name: str | None, tool_input: dict[str, Any]
) -> tuple[str, str] | None:
    """Return ``(task_id, status)`` when a tool call claims completion, else None.

    complete_task always claims done; release_task/update_task only when the
    requested status is merge_ready/done (flat or nested-``updates`` shape).
    """
    if not tool_name:
        return None
    m = _COMPLETION_TOOL_RE.search(tool_name)
    if not m:
        return None
    base = m.group(1)
    if base == "complete_task":
        status = "done"
    else:
        status = tool_input.get("status")
        if not isinstance(status, str):
            updates = tool_input.get("updates")
            status = updates.get("status") if isinstance(updates, dict) else None
        if not isinstance(status, str) or status not in COMPLETION_CLAIM_STATUSES:
            return None
    task_id = tool_input.get("id") or tool_input.get("task_id")
    if not isinstance(task_id, str) or not task_id:
        task_id = "unknown"
    return task_id, status


def record_completion_claim(ctx: HookContext, session_state: SessionState) -> None:
    """Record a completion claim on the session state at PostToolUse time.

    Called from the router's execute_hooks() — NOT from gate dispatch —
    because _dispatch_gates skips PostToolUse wholesale for is_subagent
    sessions, while the handover gate's Stop-time evidence predicate must
    see claims made in exactly that session class (Stop/SessionEnd are
    exempt from the skip). Bookkeeping only: never emits a verdict, never
    touches the router's skip lists (that routing decision is reserved —
    epic WI6).

    An unevidenced claim additionally force-closes the handover gate
    (clearing any post-skill sticky latch) so a claim made AFTER
    /end-session or /dump already opened the gate cannot launder the exit —
    and so the gate is armed in is_subagent sessions where the PostToolUse
    close triggers never run. A conformant claim leaves gate state alone.
    """
    tool_input = ctx.tool_input if isinstance(ctx.tool_input, dict) else {}
    claim = detect_completion_claim(ctx.tool_name, tool_input)
    if claim is None:
        return
    task_id, status = claim
    problems = validate_completion_evidence(extract_evidence(tool_input))
    ledger = session_state.state.setdefault("completion_claims", {})
    ledger[task_id] = {
        "tool": ctx.tool_name,
        "status": status,
        "evidence_ok": not problems,
        "problems": problems,
        "ts": time.time(),
    }
    if problems:
        session_state.close_gate("handover")
        gate = session_state.get_gate("handover")
        gate.sticky = False
        gate.sticky_until_events = []


def has_unevidenced_completion_claim(session_state: SessionState) -> bool:
    """True when any recorded completion claim lacks conformant evidence.

    Claims are keyed by task id: a later conformant re-release of the same
    task clears its earlier unevidenced record; a later /dump does NOT
    (nothing removes ledger entries within a session).
    """
    ledger = (
        session_state.state.get("completion_claims") or {}
    )  # allow-fallback: no claims recorded is a valid state
    return any(
        isinstance(record, dict) and not record.get("evidence_ok") for record in ledger.values()
    )


def verifier_result_text(ctx: HookContext) -> str:
    """Collect the verifier subagent's OWN result-channel text.

    Channels (verified against captured DEBUG_HOOKS payloads, see
    tests/test_subagent_gates.py): ``last_assistant_message`` on
    SubagentStop, and the Agent tool_response ``content`` blocks on
    PostToolUse. Producer prose is not in these channels, so a producer
    echoing "PASS" cannot satisfy the qa verdict check.
    """
    parts: list[str] = []
    last_message = ctx.raw_input.get("last_assistant_message")
    if isinstance(last_message, str):
        parts.append(last_message)
    output = ctx.tool_output
    if isinstance(output, str):
        parts.append(output)
    elif isinstance(output, dict):
        content = output.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and isinstance(block.get("text"), str):
                    parts.append(block["text"])
        for key in ("output", "result", "text", "message"):
            value = output.get(key)
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def parse_verifier_verdict(text: str | None) -> str | None:
    """Parse a PASS/FAIL/REVISE verdict from verifier output, or None.

    Labelled form ("**Verdict:** PASS", the verify-skill/marsha output
    contract) matches any case; a bare token counts only in UPPERCASE so
    prose ("tests pass") cannot fake a verdict.
    """
    if not isinstance(text, str) or not text:
        return None
    m = _VERDICT_LABELED_RE.search(text)
    if m:
        return m.group(1).upper()
    m = _VERDICT_BARE_RE.search(text)
    if m:
        return m.group(1)
    return None
