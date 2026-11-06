#!/usr/bin/env python3
"""Record a premise-check verdict, emit its OpenTelemetry span, and disarm the gate.

A verdict is one token (PASS, REVISE, FAIL) and the checker's reason. A PASS
reason must carry every keyed line of the skill's checker reason and pass
the mechanical cross-checks against the judged text the gate stored at arm
time; REVISE and FAIL need a failing step, an unanswered ask, or (REVISE only)
a ``Format:`` slip when their Valid lines all hold. The reason may come from a file or stdin
so that free text stays off the command line, where harness guards scan it.

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

import report_argument as ra
from premise_check_gate import disarm, get_judged, get_state, is_armed, mint_verification_id

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
) -> None:
    """Ship one TOOL span through claude_code_tracer's pipeline, or raise RuntimeError."""
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

    username = os.environ.get("USER") or os.environ.get("USERNAME") or None
    try:
        exported = tracer_mod._build_and_export_spans(
            config=config,
            session_id=phoenix_session_id,
            username=username,
            span_records=[record],
            service_name="aops-verdict-hooks",
            surface=surface,
        )
    except Exception as exc:
        raise RuntimeError(f"premise_check_verdict: OTel span export failed: {exc!r}") from exc
    if exported is not True:
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


def emit_claim_span(
    tracer_mod: Any,
    session_id: str,
    claim_id: str,
    argdown_text: str,
    title: str | None = None,
    config: dict[str, Any] | None = None,
    attributes: dict[str, Any] | None = None,
) -> bool:
    """Ship one TOOL span for filed claims via claude_code_tracer's pipeline.

    Returns True when the OTLP exporter reported SUCCESS for the span; raises
    RuntimeError when tracing is unconfigured or the export was not acknowledged.
    """
    vocab = ra.load_vocabulary()
    block_text = ra.extract_block(argdown_text)
    if block_text is None:
        block_text = argdown_text.strip()
    block = ra.parse_block(block_text, vocab)
    if block is None:
        raise ValueError("failed to parse argdown block")
    if not block.asks:
        raise ValueError("argdown block carries no ask ids")

    tool_input: dict[str, Any] = {
        "claim_id": claim_id,
        "status": "to_be_verified",
        "ask_ids": list(block.asks),
        "argdown": block_text,
    }
    if title:
        tool_input["title"] = title
    tool_response: dict[str, Any] = {
        "status": "filed",
        "claim_count": len(block.asks),
        "premise_count": len(block.premises),
        "inference_count": len(block.inferences),
    }

    attrs: dict[str, Any] = {
        "premise_check.claim_id": claim_id,
        "premise_check.status": "to_be_verified",
        "premise_check.ask_ids": list(block.asks),
        "premise_check.has_block": True,
        "premise_check.argdown_text": tracer_mod._truncate(block_text),
        "premise_check.argdown_sha256": hashlib.sha256(block_text.encode("utf-8")).hexdigest(),
        "premise_check.inference_count": len(block.inferences),
        "premise_check.premise_count": len(block.premises),
    }
    if title:
        attrs["premise_check.title"] = title
    if block.premises:
        weakest = block.weakest()
        if weakest is not None and weakest.basis is not None:
            attrs["premise_check.weakest_basis"] = weakest.basis.phrase
            attrs["premise_check.weakest_basis_term"] = weakest.basis.term
        elif weakest is not None:
            attrs["premise_check.weakest_basis"] = weakest.basis_text or ""
            attrs["premise_check.weakest_basis_term"] = "unmatched"
    attrs.update(attributes or {})

    _export_tool_span(
        tracer_mod,
        session_id,
        "premise_check_claim",
        tool_input,
        tool_response,
        attrs,
        config,
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
    )
    return True


def judge_reason(token: str, reason: str, judged_text: str | None) -> dict[str, Any]:
    """Parse the reason against the judged block; for PASS, refuse on any failed check.

    Returns the verdict's span attributes. Raises ValueError naming every
    failed check when a PASS reason is refused.
    """
    vocab = ra.load_vocabulary()
    parsed = ra.parse_reason(reason, vocab)
    block_text = _block_as_waived(ra.extract_block(judged_text), parsed, vocab)
    block_err: str | None = None
    if token == "PASS" and block_text is not None and not ra.is_null_form(block_text):
        if "block" not in parsed.waived_items(vocab):
            valid, parser_output, _ = ra.check_argdown_block(block_text)
            if not valid:
                block_err = parser_output

    block = (
        ra.parse_block(block_text, vocab)
        if (block_text is not None and block_err is None)
        else None
    )
    if token == "PASS":
        failures = ra.pass_failures(
            parsed,
            block,
            vocab,
            is_null=ra.is_null_form(block_text),
            block_text=block_text,
            block_error=block_err,
        )
        if failures:
            formatted = []
            for f in failures:
                remedy = ra.remediation_for_failure(f)
                if remedy:
                    formatted.append(f"{f}\n{remedy}")
                else:
                    formatted.append(f)
            raise ValueError(
                "PASS refused -- the reason fails the recorder's checks "
                "(see the premise-check skill's checker reason):\n- " + "\n- ".join(formatted)
            )
    elif token in ("REVISE", "FAIL"):
        valid_lines = parsed.get("Valid")
        if valid_lines:
            valid_entries = parsed.valid_entries()
            all_hold = all(m is not None and m.group("word") == "holds" for m in valid_entries)
            if all_hold:
                has_unanswered = False
                for ans in parsed.answered():
                    if ans is not None and ans[1] is None:
                        has_unanswered = True
                        break
                if not has_unanswered:
                    for entry in parsed.get("Answered"):
                        if "unanswered" in entry.lower():
                            has_unanswered = True
                            break
                if not has_unanswered:
                    for line in reason.splitlines():
                        if re.search(r"^\s*asks?\s*:.*?\bunanswered\b", line, re.IGNORECASE):
                            has_unanswered = True
                            break
                has_format = token == "REVISE" and bool(_format_items(reason, vocab))
                if not has_unanswered and not has_format:
                    raise ValueError(
                        f"{token} refused -- reason has Valid entries that all hold and no "
                        f"Ask: ... -> unanswered; {token} requires at least one failing "
                        f"inference step ('Valid: (n) fails -- <defect>') or unanswered ask"
                        + (", or a format defect to fix" if token == "REVISE" else "")
                        + ".\n"
                        f"Required remediation format: Reason must follow the schema in `ida:premise-check`. "
                        f"For {token}, record at least one of:\n"
                        f"  Valid: (n) fails #<defect-tag> -- <explanation of failure>\n"
                        f"  Answered: <ask_id> unanswered"
                        + (
                            f"\n  Format: <format item> -- <what to fix>   "
                            f"(format items: {', '.join(vocab.format_items)})"
                            if token == "REVISE"
                            else ""
                        )
                        + "\nLoad the premise-check skill (`ida:premise-check`) to inspect the required format before resubmitting."
                    )
    attrs = ra.span_attributes(parsed, block, vocab)
    if token == "REVISE" and (items := _format_items(reason, vocab)):
        attrs["premise_check.format_items"] = items
    return attrs


_FORMAT_LINE = re.compile(r"^\s*Format\s*:\s*(?P<value>.+)$")


def _format_items(reason: str, vocab: Any) -> list[str]:
    """Format items named by the reason's ``Format:`` lines (a REVISE for a format slip)."""
    entries = [
        m.group("value").strip() for ln in reason.splitlines() if (m := _FORMAT_LINE.match(ln))
    ]
    return ra._parse_waived_entries(entries, vocab)[0] if entries else []


def _block_as_waived(block_text: str | None, parsed: Any, vocab: Any) -> str | None:
    """The judged block with a waived ``numbering`` slip in ``answers`` normalised."""
    if block_text is not None and "numbering" in parsed.waived_items(vocab):
        return ra.unparenthesise_answers(block_text)
    return block_text


def record_verdict(
    session_id: str = "",
    claim_id: str = "",
    verdict: str = "",
    reason: str = "",
    title: str | None = None,
    tracer_mod: Any | None = None,
    machine: bool = False,
    judged_file: str | Path | None = None,
    judged_text: str | None = None,
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

    armed = is_armed(session_id)
    is_task_claim = is_task_id(cid)

    if not armed:
        if not is_task_claim and judged_file is None:
            raise ValueError(f"no premise check is currently armed for session {session_id!r}")
        state = get_state(session_id)
    else:
        state = get_state(session_id)
        expected_id = state.get("claim_id")
        valid_ids = state.get("claim_ids") or ([expected_id] if expected_id else [])
        if cid != expected_id and cid not in valid_ids:
            if not is_task_claim and judged_file is None:
                raise ValueError(
                    f"unknown or mismatched report id {cid!r}; gate is armed for {expected_id!r}"
                )

    if judged_file is not None:
        jf_path = Path(judged_file)
        if not jf_path.is_file():
            raise FileNotFoundError(f"judged file not found: {judged_file!r}")
        judged_text = jf_path.read_text(encoding="utf-8")
        judged_ref = str(judged_file)
    elif judged_text is None:
        judged_text, judged_ref = get_judged(session_id, cid)
        if is_task_claim and not judged_ref:
            judged_ref = cid

    block_text = ra.extract_block(judged_text)

    entry = (state.get("judged") or {}).get(cid, {})
    block_expected = bool(entry.get("block_expected") or state.get("block_expected"))
    is_peer = block_expected or any(
        str(judged_ref or "").startswith(prefix)
        for prefix in ("<cross-session-message", "<teammate-message", "<task-notification")
    )

    if token == "PASS":
        if (is_peer or is_task_claim) and judged_text is None:
            raise ValueError(
                f"PASS refused -- missing gate storage for claim {cid!r}: no judged text was stored "
                f"for this claim at arm time. Supply the report text using --judged-file <path>."
            )
        if is_peer and block_text is None:
            raise ValueError(
                "PASS refused -- no argument block in judged text: an absent block cannot pass; "
                "send the message back for revision\n"
                "Defect: The judged text does not contain a fenced ```argdown block.\n"
                "Required remediation: Return the message for revision and instruct the sender:\n"
                "  Load the premise-check skill (`ida:premise-check`) before writing your report; "
                "its Argdown dialect is a restricted subset of Argdown, so do not write the block from memory.\n"
                "  Command: verdict.py --claim <id> --verdict REVISE --reason-file <path>"
            )

    # Machine check on Argdown block for PASS verdicts unless block is waived
    if token == "PASS" and block_text is not None and not ra.is_null_form(block_text):
        vocab = ra.load_vocabulary()
        parsed_reason = ra.parse_reason(reason, vocab)
        if "block" not in parsed_reason.waived_items(vocab):
            valid, parser_output, _ = ra.check_argdown_block(
                _block_as_waived(block_text, parsed_reason, vocab) or block_text
            )
            if not valid:
                raise ValueError(
                    f"PASS verdict refused for {cid}: could not parse argdown block:\n{parser_output}\n"
                    f"Required remediation: The argdown block failed syntax validation. Return the message "
                    f"for revision and instruct the sender to load `ida:premise-check` before resending, "
                    f"or waive under `Waived: block -- <reason>` if format-only."
                )

    attributes = judge_reason(token, reason, judged_text)
    if machine:
        attributes["premise_check.machine"] = True
    attributes["premise_check.judged_ref"] = judged_ref or ""
    attributes["premise_check.judged_text_sha256"] = (
        hashlib.sha256(judged_text.encode("utf-8")).hexdigest() if judged_text is not None else ""
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
        attributes=attributes,
    )

    disarm(
        session_id,
        cid,
        token,
        reason,
        verification_id=verification_id,
        title=clean_title,
        machine=bool(attributes.get("premise_check.machine")),
    )

    result: dict[str, Any] = {
        "ok": True,
        "verification_id": verification_id,
        "claim_id": cid,
        "verdict": token,
        "reason": reason,
        "span_emitted": True,
        "span_error": None,
        "disarmed": True,
        "no_claim": bool(attributes.get("premise_check.no_claim")),
        "machine": bool(attributes.get("premise_check.machine")),
    }
    if clean_title:
        result["title"] = clean_title
    return result


def record_claims(
    session_id: str = "",
    claim_id: str = "",
    argdown_text: str = "",
    title: str | None = None,
    tracer_mod: Any | None = None,
) -> dict[str, Any]:
    """Validate argdown claims and emit the telemetry span to the OTel/Phoenix endpoint."""
    cid = (claim_id or "").strip()
    if not cid:
        raise ValueError("claims need a claim id (e.g. task id); got none")
    text = (argdown_text or "").strip()
    if not text:
        raise ValueError("claims need argdown content; got none")

    vocab = ra.load_vocabulary()
    block_text = ra.extract_block(text)
    if block_text is None:
        block_text = text
    block = ra.parse_block(block_text, vocab)
    if block is None:
        raise ValueError("failed to parse argdown block")
    if not block.asks:
        raise ValueError("argdown block carries no ask ids")

    if tracer_mod is None:
        tracer_mod = _import_claude_code_tracer()

    clean_title = (title or "").strip() or None
    emit_claim_span(
        tracer_mod,
        session_id,
        cid,
        block_text,
        title=clean_title,
    )

    result: dict[str, Any] = {
        "ok": True,
        "claim_id": cid,
        "status": "to_be_verified",
        "ask_ids": list(block.asks),
        "span_emitted": True,
        "span_error": None,
    }
    if clean_title:
        result["title"] = clean_title
    return result


def _read_reason(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def resolve_session_id(session_arg: str = "", claim_id: str = "") -> str:
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

    from premise_check_gate import _state_dir

    state_dir = _state_dir()
    if state_dir.is_dir():
        state_files = list(state_dir.glob("*.json"))
        # 1. Match claim_id in state
        if claim_id:
            for sfile in state_files:
                try:
                    data = json.loads(sfile.read_text(encoding="utf-8"))
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
                        return sfile.stem
                except (json.JSONDecodeError, OSError):
                    continue

    return ""


def main(argv: list[str] | None = None) -> int:
    # Support claim subcommand
    if argv and argv[0] in ("claim", "claims", "file-claims"):
        claim_parser = argparse.ArgumentParser(
            prog="premise_check_verdict.py claim",
            description="File premise-check argdown claims to OTEL / Phoenix.",
        )
        claim_parser.add_argument(
            "--claim",
            "--task",
            dest="claim",
            required=True,
            help="Identifier of the claim or task.",
        )
        claim_parser.add_argument(
            "--title",
            default=None,
            help="Optional short title for the claim or task.",
        )
        content_group = claim_parser.add_mutually_exclusive_group(required=True)
        content_group.add_argument("--argdown", help="The argdown block, inline.")
        content_group.add_argument(
            "--argdown-file",
            help="Read argdown from this file, or from stdin when '-'.",
        )
        claim_parser.add_argument(
            "--session",
            default=os.environ.get("AOPS_SESSION_ID", ""),
            help="Session id. Defaults to $AOPS_SESSION_ID.",
        )
        cargs = claim_parser.parse_args(argv[1:])
        session_id = resolve_session_id(cargs.session, cargs.claim)
        if not session_id:
            print(
                "premise_check_claim: no session id ($AOPS_SESSION_ID unset, --session not given, and no session state available)",
                file=sys.stderr,
            )
            return 1
        text = cargs.argdown if cargs.argdown is not None else _read_reason(cargs.argdown_file)
        try:
            result = record_claims(
                session_id=session_id,
                claim_id=cargs.claim,
                argdown_text=text,
                title=cargs.title,
            )
        except (OSError, ValueError, RuntimeError, ImportError) as exc:
            print(f"premise_check_claim: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result))
        return 0

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
        "--session",
        default=os.environ.get("AOPS_SESSION_ID", ""),
        help="Session id. Defaults to $AOPS_SESSION_ID.",
    )

    args = parser.parse_args(argv)

    session_id = resolve_session_id(args.session, args.claim)
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
            judged_file=args.judged_file,
        )
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"premise_check_verdict: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
