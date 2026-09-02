#!/usr/bin/env python3
"""Forced per-claim logic-check verdict (epic aops_premise_check_gate).

``hooks/messages/hearsay.md`` instructs a supervisor (Ida) to run a six-step
logic-check before accepting any subagent report. An instruction alone is not
a forcing mechanism: a verdict emitted without the check actually running
defeats the purpose (Nic, task_db1da567). This module supplies both halves,
mirroring the shape of ``task_body_gate.py``:

- ``record_verdict()`` -- called by this file's own CLI (``verdict``
  subcommand), which is the script a supervisor invokes per incoming claim.
  It validates the answer count against the logic-check sequence parsed
  live from ``hearsay.md`` (so the two can never drift apart), closes the
  local gate, and rides ``claude_code_tracer``'s own span-building/export
  functions -- unmodified -- to ship a TOOL span carrying one attribute per
  question. No separate telemetry plumbing is built.
- ``premise_check_open_gate`` -- a ``PostToolBatch`` handler that opens the
  gate the moment a subagent report lands (an ``Agent`` call completes),
  so the obligation exists before the supervisor has any chance to act on
  it.
- ``premise_check_gate_handler`` -- a ``PreToolUse`` handler that refuses
  the supervisor's *next subagent dispatch* (``Agent``/``Task``) while the
  gate is open, i.e. while the most recent subagent report is unverdicted.
  Dispatching further work on the back of an unchecked claim is the
  narrowest concrete action available to gate from inside a hook: it is the
  one avenue for the "I read it, verdict pending" state to have visible
  downstream consequences.

Both handlers are scoped to ``_GATED_AGENT_TYPES`` (Ida's profiles) -- this
task is specifically about Ida, not every supervisor persona.

Gating mode is controlled via $PREMISE_CHECK_GATE_MODE:
- "off"   : gate never refuses (verdicts are still recorded).
- "warn"  : advisory only.
- "block" : refuses the next Agent/Task dispatch until verdicted (default --
  unlike task_body_gate's opt-in "off" default, this gate exists specifically
  to be non-optional).

Overrides: $PREMISE_CHECK_GATE_OVERRIDE=1 (or true/yes), $AOP_FORCE=1,
$AOP_OVERRIDE=1 -- same override contract as task_body_gate.py, for the same
reason: a human operator must always be able to get out of the way of an
automated gate.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, refuse, warn

# Agent profiles this gate applies to. Narrower than rule_against_hearsay's
# scope (which also covers orchestrate:james) because this task
# (task_db1da567) is specifically about Ida.
_GATED_AGENT_TYPES = ("aops:ida", "pkb:ida")
_GATED_TOOLS = ("Agent", "Task")

# Matches the numbered, bold-led items in hearsay.md's logic-check list, e.g.
# "1. **What is the subject of this claim...**". The bold span is the
# question text; anything after it (worked examples, sub-clauses) is not
# captured.
_QUESTION_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)


# ---------------------------------------------------------------------------
# State: has the gate been opened by a claim, and closed by a verdict?
# ---------------------------------------------------------------------------


def _state_dir() -> Path:
    override = os.environ.get("AOPS_PREMISE_GATE_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_premise_gate"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(session_id: str) -> Path:
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    return _state_dir() / f"{safe_session}.json"


def _load_state(session_id: str) -> dict[str, Any]:
    target = _state_path(session_id)
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_state(session_id: str, state: dict[str, Any]) -> None:
    _state_path(session_id).write_text(json.dumps(state, indent=2), encoding="utf-8")


def clear_state(session_id: str) -> None:
    """Reset gate state for a session. Used by tests."""
    target = _state_path(session_id)
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass


def get_state(session_id: str) -> dict[str, Any]:
    return _load_state(session_id)


def open_gate(session_id: str, claim_id: str | None = None) -> None:
    """Record that a claim has arrived and is awaiting its logic-check verdict."""
    state = _load_state(session_id)
    state["pending"] = True
    state["claim_id"] = claim_id or state.get("claim_id") or "unnamed-claim"
    state["opened_at"] = datetime.now(UTC).isoformat()
    _save_state(session_id, state)


def is_gate_open(session_id: str) -> bool:
    return bool(_load_state(session_id).get("pending"))


def close_gate(
    session_id: str,
    claim_id: str,
    questions: list[str],
    answers: list[str],
) -> None:
    """Record that a claim's verdict was recorded, satisfying the gate."""
    state = _load_state(session_id)
    state["pending"] = False
    state["claim_id"] = claim_id
    state["last_verdict"] = {
        "claim_id": claim_id,
        "questions": list(questions),
        "answers": list(answers),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    _save_state(session_id, state)


def _derive_claim_id(ctx: HookContext) -> str:
    for call in ctx.tool_calls:
        if call.get("tool_name") == "Agent":
            tool_input = call.get("tool_input") or {}
            desc = str(tool_input.get("description") or "").strip()
            if desc:
                return desc[:80]
            call_id = call.get("tool_use_id") or ""
            if call_id:
                return str(call_id)
    return "unnamed-claim"


def _is_override_active() -> bool:
    for var in ("PREMISE_CHECK_GATE_OVERRIDE", "AOP_FORCE", "AOP_OVERRIDE"):
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return True
    return False


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def premise_check_open_gate(ctx: HookContext) -> Result | None:
    """PostToolBatch handler: open the gate when a subagent report lands."""
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None
    if not any(call.get("tool_name") == "Agent" for call in ctx.tool_calls):
        return None
    open_gate(ctx.session_id, claim_id=_derive_claim_id(ctx))
    return None


def premise_check_gate_handler(ctx: HookContext) -> Result | None:
    """PreToolUse handler: refuse the next subagent dispatch while unverdicted."""
    if ctx.tool not in _GATED_TOOLS:
        return None
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    mode = os.environ.get("PREMISE_CHECK_GATE_MODE", "block").strip().lower()
    if mode == "off":
        return None
    if _is_override_active():
        return None
    if not is_gate_open(ctx.session_id):
        return None

    claim_id = get_state(ctx.session_id).get("claim_id", "the pending subagent report")
    reason = (
        f"A subagent report ({claim_id!r}) is pending its logic-check verdict for session "
        f"'{ctx.session_id or 'current'}'. Run this file's 'verdict' subcommand "
        "(hearsay.md's six-question sequence, one --answer per question, in order) before "
        "dispatching another subagent."
    )
    user_msg = (
        "Blocked: record the logic-check verdict on the last subagent report before "
        "dispatching another."
    )
    if mode == "warn":
        return warn(reason, user_msg)
    return refuse(reason, user_msg)


# ---------------------------------------------------------------------------
# The verdict itself: validate against hearsay.md, close the gate, and ride
# claude_code_tracer's own export pipeline to ship a TOOL span.
# ---------------------------------------------------------------------------


def load_logic_check_questions(hooks_dir: Path) -> list[str]:
    """Parse the numbered logic-check sequence straight out of hearsay.md.

    Reading the questions live (rather than duplicating them here) is what
    keeps "same number of questions, same order" true by construction: there
    is exactly one place the sequence is written down.
    """
    path = hooks_dir / "messages" / "hearsay.md"
    if not path.exists():
        raise FileNotFoundError(f"logic-check source not found: {path}")
    text = path.read_text(encoding="utf-8")
    questions = _QUESTION_RE.findall(text)
    if not questions:
        raise ValueError(f"no numbered logic-check questions parsed from {path}")
    return questions


def _import_claude_code_tracer() -> Any | None:
    try:
        import claude_code_tracer  # type: ignore[import-not-found]

        return claude_code_tracer
    except ImportError:
        return None


def emit_verdict_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    questions: list[str],
    answers: list[str],
    config: dict[str, Any] | None = None,
) -> bool:
    """Ship one TOOL span for this verdict via claude_code_tracer's own pipeline.

    Reuses ``_build_tool_span_record``/``_build_and_export_spans`` exactly as
    an ordinary captured tool call would -- no parallel exporter, no new
    OTLP wiring. Returns False on the tracer's own "silent no-op if nothing
    configured" contract (``discover_config()`` returned None); never raises
    for that case, matching every other call site in claude_code_tracer.py.
    """
    if config is None:
        config = tracer_mod.discover_config()
    if config is None:
        return False

    now_ns = time.time_ns()
    trace_id = tracer_mod._new_trace_id()
    parent_span_id = tracer_mod._new_span_id()

    # Nest under the session's current turn when the tracer already has one
    # in flight, so this reads as an ordinary tool call inside the live
    # trace instead of a disconnected one-off.
    phoenix_session_id = os.environ.get("AOPS_SESSION_ID") or session_id
    state = tracer_mod._load_state(phoenix_session_id)
    current_trace = state.get("current_trace") if state else None
    if current_trace:
        trace_id = current_trace["trace_id"]
        parent_span_id = current_trace["root_span_id"]

    record = tracer_mod._build_tool_span_record(
        tool_name="premise_check_verdict",
        tool_input={"claim_id": claim_id, "answers": answers},
        tool_response={"status": "recorded", "question_count": len(questions)},
        start_ns=now_ns,
        end_ns=now_ns + 1_000_000,
        trace_id=trace_id,
        root_span_id=parent_span_id,
    )
    record["attributes"]["premise_check.claim_id"] = claim_id
    record["attributes"]["premise_check.question_count"] = len(questions)
    for i, (question, answer) in enumerate(zip(questions, answers, strict=True), start=1):
        record["attributes"][f"premise_check.q{i}.question"] = tracer_mod._truncate(question)
        record["attributes"][f"premise_check.q{i}.answer"] = tracer_mod._truncate(answer)

    username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    tracer_mod._build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[record],
    )
    return True


def record_verdict(
    hooks_dir: Path,
    session_id: str,
    claim_id: str,
    answers: list[str],
    tracer_mod: Any | None = None,
) -> dict[str, Any]:
    """Validate, emit the span (best-effort), and close the gate.

    Raises ``ValueError`` if ``answers`` does not have exactly one entry per
    question in hearsay.md's logic-check sequence -- the script refuses to
    close the gate on a malformed verdict rather than accept a partial one.
    """
    questions = load_logic_check_questions(hooks_dir)
    if len(answers) != len(questions):
        raise ValueError(
            f"expected {len(questions)} answers (one per hearsay.md logic-check question), "
            f"got {len(answers)}"
        )

    if tracer_mod is None:
        tracer_mod = _import_claude_code_tracer()

    span_emitted = False
    span_error: str | None = None
    if tracer_mod is not None:
        try:
            span_emitted = emit_verdict_span(tracer_mod, session_id, claim_id, questions, answers)
        except Exception as exc:  # mirrors claude_code_tracer's own fail-safe style
            span_error = repr(exc)
            print(f"premise_check_gate: span emission failed: {exc!r}", file=sys.stderr)

    close_gate(session_id, claim_id, questions, answers)

    return {
        "ok": True,
        "claim_id": claim_id,
        "question_count": len(questions),
        "span_emitted": span_emitted,
        "span_error": span_error,
        "gate_closed": True,
    }


# ---------------------------------------------------------------------------
# CLI: the script a supervisor invokes per incoming claim.
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="premise_check_gate.py",
        description="Record a per-claim logic-check verdict and clear the dispatch gate.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser(
        "verdict",
        help="Record one answer per hearsay.md logic-check question, in order.",
    )
    v.add_argument("--claim", required=True, help="Identifier or short description of the claim.")
    v.add_argument(
        "--answer",
        action="append",
        required=True,
        dest="answers",
        help="One per logic-check question, in order. Repeat this flag once per question.",
    )
    v.add_argument(
        "--session",
        default=os.environ.get("AOPS_SESSION_ID", ""),
        help="Session id. Defaults to $AOPS_SESSION_ID.",
    )

    args = parser.parse_args(argv)

    if args.command == "verdict":
        if not args.session:
            print(
                "premise_check_gate: no session id ($AOPS_SESSION_ID unset and --session not given)",
                file=sys.stderr,
            )
            return 1
        hooks_dir = Path(__file__).resolve().parent
        try:
            result = record_verdict(hooks_dir, args.session, args.claim, args.answers)
        except (FileNotFoundError, ValueError) as exc:
            print(f"premise_check_gate: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result))
        if not result["span_emitted"]:
            detail = f": {result['span_error']}" if result.get("span_error") else ""
            print(
                "premise_check_gate: verdict recorded locally (dispatch gate cleared) but no "
                f"OTel span was emitted -- tracing endpoint not configured or export failed{detail}",
                file=sys.stderr,
            )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
