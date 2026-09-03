#!/usr/bin/env python3
"""Record and emit logic-check verdicts and OpenTelemetry spans.

Validates evaluation answers against the six-question logic-check sequence
extracted from hearsay doctrine, emits a TOOL span via claude_code_tracer,
and disarms the premise check hook.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    from datetime import UTC
except ImportError:
    UTC = UTC  # type: ignore[assignment]

from premise_check_gate import disarm

# Matches numbered, bold-led items in hearsay.md's logic-check list
_QUESTION_RE = re.compile(r"^\d+\.\s+\*\*(.+?)\*\*", re.MULTILINE)

# The canonical six-question logic-check sequence extracted from hearsay.md.
# Baked at build/test time to prevent runtime path resolution errors and
# filesystem permissions issues in client sandboxes.
LOGIC_CHECK_QUESTIONS: tuple[str, ...] = (
    "What is the subject of this claim, independent of what you're being told about it?",
    "Does the evidence admit more than one explanation?",
    "Is the evidence sufficient? Is the methodology sound and exhaustive? Are the inferences warranted for the conclusion as stated?",
    "Is anything presented as an observed fact actually an inference, and is the certainty expressed proportionate to what the evidence supports?",
    "Does the conclusion generalise beyond what a representative, sufficient sample of the evidence supports?",
    "What does the conclusion depend on that the report never states?",
)


def load_logic_check_questions(hooks_dir: Path | None = None) -> list[str]:
    """Return the numbered logic-check sequence.

    Returns the build-time baked LOGIC_CHECK_QUESTIONS, avoiding runtime
    filesystem lookups and permissions issues in sandboxes.
    """
    return list(LOGIC_CHECK_QUESTIONS)


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
    """Ship one TOOL span for this verdict via claude_code_tracer's pipeline."""
    if config is None:
        config = tracer_mod.discover_config()
    if config is None:
        return False

    now_ns = time.time_ns()
    trace_id = tracer_mod._new_trace_id()
    parent_span_id = tracer_mod._new_span_id()

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
    hooks_dir: Path | None = None,
    session_id: str = "",
    claim_id: str = "",
    answers: list[str] | None = None,
    tracer_mod: Any | None = None,
) -> dict[str, Any]:
    """Validate, emit the span (best-effort), and disarm the premise check."""
    if answers is None:
        answers = []
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
        except Exception as exc:
            span_error = repr(exc)
            print(f"premise_check_verdict: span emission failed: {exc!r}", file=sys.stderr)

    disarm(session_id, claim_id, questions, answers)

    return {
        "ok": True,
        "claim_id": claim_id,
        "question_count": len(questions),
        "span_emitted": span_emitted,
        "span_error": span_error,
        "disarmed": True,
        "gate_closed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="premise_check_verdict.py",
        description="Record a per-claim logic-check verdict and disarm the premise check.",
    )
    # Support both direct flags and optional 'verdict' subcommand
    if argv and argv[0] == "verdict":
        argv = argv[1:]

    parser.add_argument(
        "--claim",
        "--report",
        dest="claim",
        required=True,
        help="Identifier or short description of the claim or report.",
    )
    parser.add_argument(
        "--answer",
        "--verdict",
        action="append",
        dest="answers",
        required=True,
        help="Answer per logic-check question, in order. Repeat flag once per question.",
    )
    parser.add_argument(
        "--session",
        default=os.environ.get("AOPS_SESSION_ID", ""),
        help="Session id. Defaults to $AOPS_SESSION_ID.",
    )

    args = parser.parse_args(argv)

    if not args.session:
        print(
            "premise_check_verdict: no session id ($AOPS_SESSION_ID unset and --session not given)",
            file=sys.stderr,
        )
        return 1

    try:
        result = record_verdict(
            session_id=args.session,
            claim_id=args.claim,
            answers=args.answers,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"premise_check_verdict: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    if not result["span_emitted"]:
        detail = f": {result['span_error']}" if result.get("span_error") else ""
        print(
            "premise_check_verdict: verdict recorded locally (premise check disarmed) but no "
            f"OTel span was emitted -- tracing endpoint not configured or export failed{detail}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
