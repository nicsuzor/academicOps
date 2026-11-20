#!/usr/bin/env python3
"""Record a premise-check verdict, emit its OpenTelemetry span, and disarm the gate.

A verdict is one token (PASS, REVISE, FAIL) and a non-empty natural-language
reason. The reason may come from a file or stdin so that free text stays off
the command line, where harness guards scan it. Substantive review of reports
and reasons belongs to checking agents; this recorder enforces only gate slot
integrity, token validity, non-empty reasons, and fail-closed OTel emission.

A verdict is recorded only once its span is exported: an unconfigured tracer or
an unacknowledged export raises, and the gate stays armed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from premise_check_gate import (
    _canonical_agent_id,
    _normalized_body_hash,
    _safe_token,
    _state_dir,
    disarm,
    find_armed_owner,
    get_judged,
    get_state,
    is_armed,
    mint_verification_id,
)

_GATE_MINTED_ID_RE = re.compile(r"^(?:claim-[0-9a-f]{8}(?:-|$)|toolu_)", re.IGNORECASE)


def is_gate_minted_id(identifier: str) -> bool:
    """True for gate-generated claim-<8hex> or tool_use_id claim identifiers."""
    return bool(_GATE_MINTED_ID_RE.match((identifier or "").strip()))


VERDICTS: tuple[str, ...] = ("PASS", "REVISE", "FAIL")

_TASK_ID_RE = re.compile(
    r"^(?:task|epic|aops|wf)[_-][a-zA-Z0-9_-]+$"
    r"|^(?:[a-z][a-z0-9-]*[_-])?[0-9a-f]{8}$"
    r"|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    r"|^(?:engine-)?task-\d+$",
    re.IGNORECASE,
)
_NON_TASK_PREFIXES = ("claim-", "verdict-", "report-", "toolu_")
_KNOWN_NON_TASK_IDS = {"ns", "default", "academicops", "aops"}


def is_task_id(identifier: str) -> bool:
    """Return True if identifier resembles a task or epic ID."""
    if not identifier:
        return False
    tid = identifier.strip()
    low = tid.lower()
    if low in _KNOWN_NON_TASK_IDS:
        return False
    if any(low.startswith(p) for p in _NON_TASK_PREFIXES):
        return False
    if _TASK_ID_RE.match(tid):
        return True
    if re.match(r"^[a-z][a-z0-9_.-]*[_-][0-9a-f]{6,}$", tid, re.IGNORECASE):
        return True
    return False


def _import_claude_code_tracer() -> Any:
    import claude_code_tracer  # type: ignore[import-not-found]

    return claude_code_tracer


def _surface(state: dict[str, Any] | None) -> str:
    if os.environ.get("GITHUB_ACTIONS"):
        return "github-actions"
    if state and state.get("surface") == "agy":
        return "agy"
    if os.environ.get("ANTIGRAVITY_CLI") or os.environ.get("GEMINI_CLI"):
        return "agy"
    return "claude-code"


def _export_tool_span(
    tracer_mod: Any,
    session_id: str,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_response: dict[str, Any],
    attributes: dict[str, Any],
    config: dict[str, Any] | None,
    agent_id: str | None = None,
) -> None:
    """Ship one TOOL span through claude_code_tracer's pipeline, or raise RuntimeError."""
    if config is None:
        config = tracer_mod.discover_config()
    if config is None:
        err_msg = (
            "ERROR: Premise-check verdict cannot be recorded: OpenTelemetry tracing unconfigured (no endpoint). "
            "Gate remains armed."
        )
        print(err_msg, file=sys.stderr)
        raise RuntimeError("premise_check_verdict: tracing is not configured (no OTel endpoint)")

    now_ns = time.time_ns()
    trace_id = tracer_mod._new_trace_id()
    parent_span_id = tracer_mod._new_span_id()

    env_session_id = os.environ.get("AOPS_SESSION_ID")
    canon_agent = _canonical_agent_id(session_id, agent_id)
    state = (tracer_mod._load_state(canon_agent) if canon_agent else None) or (
        tracer_mod._load_state(session_id) if session_id else {}
    )
    if not state and env_session_id and env_session_id != session_id:
        state = tracer_mod._load_state(env_session_id)

    resolved_agent_id: str | None = None
    parent_session_id = None
    if state and hasattr(tracer_mod, "_resolve_agent_and_parent_ids"):
        phoenix_session_id, resolved_agent_id, parent_session_id = (
            tracer_mod._resolve_agent_and_parent_ids(state)
        )
    else:
        raw_phx = (
            (state.get("phoenix_session_id") if state else None) or env_session_id or session_id
        )
        phoenix_session_id = str(raw_phx).split("/", 1)[0]
        if session_id and session_id != phoenix_session_id:
            resolved_agent_id = session_id.split("/", 1)[1] if "/" in session_id else session_id
            parent_session_id = (
                state.get("parent_session_id") if state else None
            ) or phoenix_session_id

    if canon_agent:
        resolved_agent_id = canon_agent
        if not parent_session_id and phoenix_session_id and canon_agent != phoenix_session_id:
            parent_session_id = phoenix_session_id

    current_trace = state.get("current_trace") if state else None
    if current_trace:
        trace_id = current_trace["trace_id"]
        parent_span_id = current_trace["root_span_id"]

    record = tracer_mod._build_tool_span_record(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=now_ns,
        end_ns=now_ns + 1_000_000,
        trace_id=trace_id,
        root_span_id=parent_span_id,
    )
    surface = _surface(state)
    record["attributes"].update(attributes)
    record["attributes"]["service.name"] = "aops-verdict-hooks"
    record["attributes"]["aops.surface"] = surface
    if resolved_agent_id:
        record["attributes"]["premise_check.recipient_agent_id"] = resolved_agent_id

    username = os.environ.get("USER") or os.environ.get("USERNAME") or None
    export_kwargs: dict[str, Any] = {
        "config": config,
        "session_id": phoenix_session_id,
        "username": username,
        "span_records": [record],
        "service_name": "aops-verdict-hooks",
        "surface": surface,
    }
    if resolved_agent_id:
        export_kwargs["agent_id"] = resolved_agent_id
    if parent_session_id:
        export_kwargs["parent_session_id"] = parent_session_id
    try:
        exported = tracer_mod._build_and_export_spans(**export_kwargs)
    except Exception as exc:
        err_msg = (
            f"ERROR: Premise-check verdict cannot be recorded: OpenTelemetry export failed ({exc!r}). "
            "Gate remains armed."
        )
        print(err_msg, file=sys.stderr)
        raise RuntimeError(f"premise_check_verdict: OTel span export failed: {exc!r}") from exc
    if exported is not True:
        err_msg = (
            "ERROR: Premise-check verdict cannot be recorded: OpenTelemetry span export was not acknowledged. "
            "Gate remains armed."
        )
        print(err_msg, file=sys.stderr)
        raise RuntimeError("premise_check_verdict: OTel span export failed")


def emit_verdict_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
    config: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> bool:
    """Ship one TOOL span for this verdict via claude_code_tracer's pipeline.

    Returns True when the OTLP exporter reported SUCCESS for the span; raises
    RuntimeError when tracing is unconfigured or the export was not acknowledged.
    """
    tool_input: dict[str, Any] = {"claim_id": claim_id, "verdict": verdict, "reason": reason}
    if title:
        tool_input["title"] = title
    tool_response: dict[str, Any] = {"status": "recorded"}
    if verification_id:
        tool_response["verification_id"] = verification_id

    attrs: dict[str, Any] = {
        "premise_check.claim_id": claim_id,
        "premise_check.verdict": verdict,
        "premise_check.reason_text": tracer_mod._truncate(reason),
    }
    if verification_id:
        attrs["premise_check.verification_id"] = verification_id
    if title:
        attrs["premise_check.title"] = title
    attrs.update(attributes or {})

    _export_tool_span(
        tracer_mod,
        session_id,
        "premise_check_verdict",
        tool_input,
        tool_response,
        attrs,
        config,
        agent_id=agent_id,
    )
    return True


def emit_override_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    tool: str,
    event: str,
    variable: str,
    override_count: int,
) -> bool:
    """Ship one ``premise_check_override`` span; raises like ``emit_verdict_span``."""
    attrs = {
        "premise_check.claim_id": claim_id,
        "premise_check.override_var": variable,
        "premise_check.override_tool": tool,
        "premise_check.override_event": event,
        "premise_check.override_count": override_count,
    }
    _export_tool_span(
        tracer_mod,
        session_id,
        "premise_check_override",
        {"claim_id": claim_id, "tool": tool, "event": event, "variable": variable},
        {"status": "passed"},
        attrs,
        None,
    )
    return True


def emit_hearsay_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    event: str,
    judged_ref: str | None = None,
    attributes: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> bool:
    """Ship one TOOL span for this hearsay check via claude_code_tracer's pipeline."""
    attrs: dict[str, Any] = {
        "hearsay.claim_id": claim_id,
        "hearsay.event": event,
        "hearsay.status": "armed",
        "premise_check.claim_id": claim_id,
    }
    if judged_ref:
        attrs["hearsay.judged_ref"] = judged_ref
        attrs["premise_check.judged_ref"] = judged_ref
    if attributes:
        attrs.update(attributes)

    _export_tool_span(
        tracer_mod,
        session_id,
        "hearsay_check",
        {"claim_id": claim_id, "event": event},
        {"status": "armed"},
        attrs,
        config,
        agent_id=agent_id,
    )
    return True


def _judged_matches_stored(jf_text: str, stored_text: str) -> bool:
    if _normalized_body_hash(jf_text) == _normalized_body_hash(stored_text):
        return True
    # Also accept unwrapped inner text if stored_text carries an outer XML envelope
    stripped = re.sub(
        r"^\s*<(?:cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)\b[^>]*>(.*?)</(?:cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)>\s*$",
        r"\1",
        stored_text,
        flags=re.DOTALL,
    )
    if stripped != stored_text and _normalized_body_hash(jf_text) == _normalized_body_hash(
        stripped
    ):
        return True
    return False


def record_verdict(
    session_id: str = "",
    claim_id: str = "",
    verdict: str = "",
    reason: str = "",
    title: str | None = None,
    tracer_mod: Any | None = None,
    machine: bool = False,
    no_claim: bool = False,
    judged_file: str | Path | None = None,
    judged_text: str | None = None,
    agent_id: str | None = None,
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

    target_agent = _canonical_agent_id(session_id, agent_id)
    armed = is_armed(session_id, agent_id=target_agent)
    is_task_claim = is_task_id(cid)
    state = get_state(session_id, agent_id=target_agent)
    judged_map = state.get("judged") or {}
    disarmed_map = state.get("disarmed_claims") or {}
    expected_id = state.get("claim_id")
    valid_ids = state.get("claim_ids") or ([expected_id] if expected_id else [])

    # Check if this claim belongs to a DIFFERENT active agent slot in this session
    foreign_owner = find_armed_owner(session_id, cid, exclude_agent=target_agent)
    if foreign_owner is not None and cid not in valid_ids:
        caller_label = target_agent or "main"
        raise ValueError(
            f"claim {cid!r} is armed for agent {foreign_owner!r}, not {caller_label!r}"
        )

    is_active_in_slot = armed and (cid == expected_id or cid in valid_ids)
    if not is_active_in_slot:
        if not is_task_claim and cid in disarmed_map:
            prev_verdict = (disarmed_map.get(cid) or {}).get("verdict") or "recorded"
            raise ValueError(
                f"claim {cid!r} is already disarmed in gate state (last verdict: {prev_verdict}); not armed"
            )
        if not armed:
            if not is_task_claim and (judged_file is None or is_gate_minted_id(cid)):
                raise ValueError(
                    f"no premise check is currently armed for session {session_id!r}"
                    + (f" (agent {target_agent!r})" if target_agent else "")
                )
        else:
            if not is_task_claim and (judged_file is None or is_gate_minted_id(cid)):
                raise ValueError(
                    f"unknown or mismatched report id {cid!r}; gate is armed for {expected_id!r}"
                )

    if judged_file is not None:
        jf_path = Path(judged_file)
        if not jf_path.is_file():
            raise FileNotFoundError(f"judged file not found: {judged_file!r}")
        jf_text = jf_path.read_text(encoding="utf-8")
        if is_active_in_slot and cid in judged_map:
            stored_text, _ = get_judged(session_id, cid, agent_id=target_agent)
            if stored_text is not None and not _judged_matches_stored(jf_text, stored_text):
                raise ValueError(
                    f"--judged-file content mismatch: {str(judged_file)!r} does not match the report that armed {cid!r}"
                )
        judged_text = jf_text
        judged_ref = str(judged_file)
    elif judged_text is None:
        judged_text, judged_ref = get_judged(session_id, cid, agent_id=target_agent)
        if is_task_claim and not judged_ref:
            judged_ref = cid
    else:
        judged_ref = cid if is_task_claim else ""

    attributes: dict[str, Any] = {
        "premise_check.no_claim": bool(no_claim),
        "premise_check.judged_ref": judged_ref or "",
        "premise_check.judged_text_sha256": (
            hashlib.sha256(judged_text.encode("utf-8")).hexdigest()
            if judged_text is not None
            else ""
        ),
    }
    if machine:
        attributes["premise_check.machine"] = True

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
        attributes=attributes,
        agent_id=target_agent or None,
    )

    disarm(
        session_id,
        cid,
        token,
        reason,
        verification_id=verification_id,
        title=clean_title,
        machine=bool(attributes.get("premise_check.machine")),
        no_claim=bool(no_claim),
        agent_id=target_agent,
    )

    result: dict[str, Any] = {
        "ok": True,
        "verification_id": verification_id,
        "claim_id": cid,
        "verdict": token,
        "reason": reason,
        "span_emitted": True,
        "disarmed": True,
        "no_claim": bool(attributes.get("premise_check.no_claim")),
        "machine": bool(attributes.get("premise_check.machine")),
    }
    if clean_title:
        result["title"] = clean_title
    return result


def _read_reason(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def resolve_session_id(session_arg: str = "", claim_id: str = "", agent_id: str = "") -> str:
    """Resolve active session ID from CLI arg, environment, or on-disk session state."""
    if session_arg and session_arg.strip():
        return session_arg.strip()

    for var in (
        "AOPS_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "SESSION_ID",
        "ANTIGRAVITY_SESSION_ID",
        "GEMINI_SESSION_ID",
    ):
        val = os.environ.get(var, "").strip()
        if val:
            return val

    claude_env = os.environ.get("CLAUDE_ENV_FILE")
    if claude_env and Path(claude_env).is_file():
        try:
            content = Path(claude_env).read_text(encoding="utf-8")
            for line in content.splitlines():
                if "AOPS_SESSION_ID=" in line:
                    match = re.search(r'AOPS_SESSION_ID=["\']?([^"\'\s]+)', line)
                    if match:
                        return match.group(1).strip()
        except OSError:
            pass

    state_dir = _state_dir()
    if state_dir.is_dir() and claim_id:
        canon_agent = _canonical_agent_id("", agent_id)
        if canon_agent:
            suffix = f".agent-{_safe_token(canon_agent, 'agent')}.json"
            state_files = [p for p in state_dir.glob(f"*{suffix}") if p.is_file()]
        else:
            # Strict scoping: omitted --agent checks ONLY root slot files (never .agent-* or .parents.json)
            state_files = [
                p
                for p in state_dir.glob("*.json")
                if p.is_file() and not p.name.endswith(".parents.json") and ".agent-" not in p.name
            ]
        for sfile in state_files:
            data = json.loads(sfile.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"corrupt gate state in {sfile}: expected JSON object")
            cid = data.get("claim_id")
            cids = data.get("claim_ids") or []
            judged = data.get("judged") or {}
            last_verdict = data.get("last_verdict") or {}
            if (
                claim_id == cid
                or claim_id in cids
                or claim_id in judged
                or claim_id == last_verdict.get("claim_id")
            ):
                explicit_sid = str(data.get("session_id") or "").strip()
                if explicit_sid:
                    return explicit_sid
                stem = sfile.stem
                if ".agent-" in stem:
                    return stem.split(".agent-", 1)[0]
                return stem

    return ""


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
        type=str.upper,
        choices=VERDICTS,
        help="PASS, REVISE or FAIL.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional short title for the verification.",
    )
    parser.add_argument(
        "--judged-file",
        dest="judged_file",
        default=None,
        help="Read the judged report or text from this file.",
    )
    reason = parser.add_mutually_exclusive_group()
    reason.add_argument("--reason", help="The checker's reason, inline.")
    reason.add_argument(
        "--reason-file",
        help="Read the reason from this file, or from stdin when '-'.",
    )
    parser.add_argument(
        "--no-claim",
        action="store_true",
        default=False,
        help="Mark this verdict as covering a claim-free notice or armed direction brief (sets premise_check.no_claim=true).",
    )
    parser.add_argument(
        "--session",
        default=os.environ.get("AOPS_SESSION_ID", ""),
        help="Session id. Defaults to $AOPS_SESSION_ID.",
    )
    parser.add_argument(
        "--agent",
        "--recipient",
        dest="agent_id",
        default="",
        help="Recipient agent_id owning the armed gate slot (empty for root coordinator).",
    )

    args = parser.parse_args(argv)

    session_id = resolve_session_id(args.session, args.claim, args.agent_id)
    if not session_id:
        print(
            "premise_check_verdict: no session id ($AOPS_SESSION_ID unset, --session not given, and no session state available)",
            file=sys.stderr,
        )
        return 1

    if not args.verdict:
        print(
            "premise_check_verdict: error: the following arguments are required: --verdict",
            file=sys.stderr,
        )
        return 2

    if not args.reason and not args.reason_file:
        print(
            "premise_check_verdict: error: one of --reason or --reason-file is required",
            file=sys.stderr,
        )
        return 2

    try:
        text = args.reason if args.reason is not None else _read_reason(args.reason_file)
        result = record_verdict(
            session_id=session_id,
            claim_id=args.claim,
            verdict=args.verdict,
            reason=text,
            title=args.title,
            no_claim=args.no_claim,
            judged_file=args.judged_file,
            agent_id=args.agent_id or None,
        )
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"premise_check_verdict: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
