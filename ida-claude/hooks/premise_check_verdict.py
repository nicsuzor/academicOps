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

from premise_check_gate import disarm, get_state, is_armed, mint_verification_id

VERDICTS: tuple[str, ...] = ("PASS", "REVISE", "FAIL")


def _import_claude_code_tracer() -> Any:
    import claude_code_tracer  # type: ignore[import-not-found]

    return claude_code_tracer


def emit_verdict_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
    config: dict[str, Any] | None = None,
) -> bool:
    """Ship one TOOL span for this verdict via claude_code_tracer's pipeline.

    Returns True only when the OTLP exporter reported SUCCESS for the span;
    raises RuntimeError when tracing is unconfigured or the export was not acknowledged.
    """
    if config is None:
        config = tracer_mod.discover_config()
    if config is None:
        raise RuntimeError("premise_check_verdict: tracing is not configured (no OTel endpoint)")

    now_ns = time.time_ns()
    trace_id = tracer_mod._new_trace_id()
    parent_span_id = tracer_mod._new_span_id()

    phoenix_session_id = os.environ.get("AOPS_SESSION_ID") or session_id
    state = tracer_mod._load_state(phoenix_session_id)
    current_trace = state.get("current_trace") if state else None
    if current_trace:
        trace_id = current_trace["trace_id"]
        parent_span_id = current_trace["root_span_id"]

    tool_input: dict[str, Any] = {"claim_id": claim_id, "verdict": verdict, "reason": reason}
    if title:
        tool_input["title"] = title
    tool_response: dict[str, Any] = {"status": "recorded"}
    if verification_id:
        tool_response["verification_id"] = verification_id

    record = tracer_mod._build_tool_span_record(
        tool_name="premise_check_verdict",
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=now_ns,
        end_ns=now_ns + 1_000_000,
        trace_id=trace_id,
        root_span_id=parent_span_id,
    )
    record["attributes"]["premise_check.claim_id"] = claim_id
    record["attributes"]["premise_check.verdict"] = verdict
    record["attributes"]["premise_check.reason"] = tracer_mod._truncate(reason)
    if verification_id:
        record["attributes"]["premise_check.verification_id"] = verification_id
    if title:
        record["attributes"]["premise_check.title"] = title

    surface = "claude-code"
    if os.environ.get("GITHUB_ACTIONS"):
        surface = "github-actions"
    elif state and state.get("surface") == "agy":
        surface = "agy"
    elif os.environ.get("ANTIGRAVITY_CLI") or os.environ.get("GEMINI_CLI"):
        surface = "agy"

    record["attributes"]["service.name"] = "aops-verdict-hooks"
    record["attributes"]["aops.surface"] = surface

    username = os.environ.get("USER") or os.environ.get("USERNAME") or None
    exported = tracer_mod._build_and_export_spans(
        config=config,
        session_id=phoenix_session_id,
        username=username,
        span_records=[record],
        service_name="aops-verdict-hooks",
        surface=surface,
    )
    if exported is not True:
        raise RuntimeError("premise_check_verdict: OTel span export failed")
    return True


def record_verdict(
    session_id: str = "",
    claim_id: str = "",
    verdict: str = "",
    reason: str = "",
    title: str | None = None,
    tracer_mod: Any | None = None,
) -> dict[str, Any]:
    """Validate, emit the span, and disarm the premise check."""
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

    clean_title = (title or "").strip() or None
    verification_id = mint_verification_id(cid, token, reason, title=clean_title)

    if tracer_mod is None:
        tracer_mod = _import_claude_code_tracer()

    emit_verdict_span(
        tracer_mod,
        session_id,
        cid,
        token,
        reason,
        verification_id=verification_id,
        title=clean_title,
    )

    disarm(
        session_id,
        cid,
        token,
        reason,
        verification_id=verification_id,
        title=clean_title,
    )

    result: dict[str, Any] = {
        "ok": True,
        "verification_id": verification_id,
        "claim_id": cid,
        "verdict": token,
        "span_emitted": True,
        "span_error": None,
        "disarmed": True,
    }
    if clean_title:
        result["title"] = clean_title
    return result


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
    parser.add_argument(
        "--title",
        default=None,
        help="Optional short title for the verification.",
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
            title=args.title,
        )
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"premise_check_verdict: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
