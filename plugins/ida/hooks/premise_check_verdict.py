#!/usr/bin/env python3
"""Record a premise-check verdict, emit its OpenTelemetry span, and disarm the gate.

A verdict is one token (PASS, REVISE, FAIL) and a free-text reason. The reason
may come from a file or stdin so that free text stays off the command line,
where harness guards scan it.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from premise_check_gate import disarm, get_state, is_armed

VERDICTS: tuple[str, ...] = ("PASS", "REVISE", "FAIL")


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
    verdict: str,
    reason: str,
    config: dict[str, Any] | None = None,
) -> bool:
    """Ship one TOOL span for this verdict via claude_code_tracer's pipeline.

    Returns True only when the OTLP exporter reported SUCCESS for the span;
    False when tracing is unconfigured or the export was not acknowledged.
    """
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
        tool_input={"claim_id": claim_id, "verdict": verdict, "reason": reason},
        tool_response={"status": "recorded"},
        start_ns=now_ns,
        end_ns=now_ns + 1_000_000,
        trace_id=trace_id,
        root_span_id=parent_span_id,
    )
    record["attributes"]["premise_check.claim_id"] = claim_id
    record["attributes"]["premise_check.verdict"] = verdict
    record["attributes"]["premise_check.reason"] = tracer_mod._truncate(reason)

    username = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))
    exported = tracer_mod._build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[record],
    )
    return exported is True


def record_verdict(
    session_id: str = "",
    claim_id: str = "",
    verdict: str = "",
    reason: str = "",
    tracer_mod: Any | None = None,
) -> dict[str, Any]:
    """Validate, emit the span (best-effort), and disarm the premise check."""
    cid = (claim_id or "").strip()
    if not cid:
        raise ValueError("a verdict needs a report id; got none")

    token = (verdict or "").strip().upper()
    if token not in VERDICTS:
        raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}; got {verdict!r}")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("a verdict needs a reason; got none")

    if not is_armed(session_id):
        raise ValueError(f"no premise check is currently armed for session {session_id!r}")

    state = get_state(session_id)
    expected_id = state.get("claim_id")
    valid_ids = state.get("claim_ids") or ([expected_id] if expected_id else [])
    if cid != expected_id and cid not in valid_ids:
        raise ValueError(
            f"unknown or mismatched report id {cid!r}; gate is armed for {expected_id!r}"
        )

    if tracer_mod is None:
        tracer_mod = _import_claude_code_tracer()

    span_emitted = False
    span_error: str | None = None
    if tracer_mod is not None:
        try:
            span_emitted = emit_verdict_span(tracer_mod, session_id, cid, token, reason)
        except Exception as exc:
            span_error = repr(exc)
            print(f"premise_check_verdict: span emission failed: {exc!r}", file=sys.stderr)

    disarm(session_id, cid, token, reason)

    return {
        "ok": True,
        "claim_id": claim_id,
        "verdict": token,
        "span_emitted": span_emitted,
        "span_error": span_error,
        "disarmed": True,
    }


def _read_reason(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="premise_check_verdict.py",
        description="Record a premise-check verdict and disarm the premise check.",
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
        "--verdict",
        required=True,
        type=str.upper,
        choices=VERDICTS,
        help="PASS, REVISE or FAIL.",
    )
    reason = parser.add_mutually_exclusive_group(required=True)
    reason.add_argument("--reason", help="Why, in free text.")
    reason.add_argument(
        "--reason-file",
        help="Read the reason from this file, or from stdin when '-'.",
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
        text = args.reason if args.reason is not None else _read_reason(args.reason_file)
        result = record_verdict(
            session_id=args.session,
            claim_id=args.claim,
            verdict=args.verdict,
            reason=text,
        )
    except (OSError, ValueError) as exc:
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
