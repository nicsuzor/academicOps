#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for premise checking.

Enforces that a supervisor (Ida) evaluates incoming subagent reports against
logic-check doctrine before dispatching further subagents, contacting the user, or finishing tasks:

- ``premise_check_arm``: a ``PostToolBatch`` / ``PostToolUse`` / ``UserPromptSubmit`` handler that arms the check when
  an agent finishes calling tools (including subagents, before results return) or receives a peer's report.
  The user's own messages never arm it.
- ``premise_check_handler``: a ``PreToolUse`` / ``Stop`` handler that refuses the
  supervisor's next subagent dispatch, communication, or stop while armed.
- ``arm()`` / ``disarm()``: state management primitives. Calling ``disarm()``
  clears the check once a verdict is recorded.

Verdict recording and OpenTelemetry trace emission live separately in
``premise_check_verdict.py``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, block, refuse, warn


def _now() -> str:
    """Current time as an ISO-8601 string carrying the local system UTC offset."""
    return datetime.now().astimezone().isoformat()


# Agent profiles this check applies to: the manager (ida) and the dispatcher (sara)
_GATED_AGENT_TYPES = ["ida:ida", "ida", "ida:sara", "sara"]

# Envelopes the harness wraps around a report from another agent. Anything
# else arriving on UserPromptSubmit -- a channel message or a typed prompt -- is
# the user's own message, which is an ask, not a claim to check.
_PEER_ENVELOPES = ("<cross-session-message", "<teammate-message", "<task-notification")

# Tools that dispatch subagents (arming the check)
_DISPATCH_TOOLS = ["Agent", "Task", "invoke_subagent"]

# Tools that are blocked while the check is armed
_BLOCKED_TOOLS = ["Agent", "Task", "invoke_subagent", "SendMessage", "AskUserQuestion", "Dump"]


# ---------------------------------------------------------------------------
# State: is the premise check armed (awaiting verdict) or disarmed?
# ---------------------------------------------------------------------------


def _state_dir() -> Path:
    override = os.environ.get("AOPS_PREMISE_CHECK_DIR") or os.environ.get("AOPS_PREMISE_GATE_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_premise_check"
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
    """Reset premise check state for a session. Used by tests."""
    target = _state_path(session_id)
    if target.exists():
        try:
            target.unlink()
        except OSError:
            pass


def get_state(session_id: str) -> dict[str, Any]:
    return _load_state(session_id)


def arm(session_id: str, claim_id: str | None = None) -> None:
    """Arm the premise check for a session until a verdict disarms it."""
    state = _load_state(session_id)
    cid = claim_id or state.get("claim_id") or "unnamed-claim"
    state["armed"] = True
    state["pending"] = True  # backward compat
    state["claim_id"] = cid
    claim_ids = state.get("claim_ids") or []
    if cid not in claim_ids:
        claim_ids.append(cid)
    state["claim_ids"] = claim_ids
    state["armed_at"] = _now()
    _save_state(session_id, state)


def disarm(session_id: str, claim_id: str, verdict: str, reason: str) -> None:
    """Disarm the premise check after a verdict is recorded."""
    state = _load_state(session_id)
    claim_ids = state.get("claim_ids") or []
    if claim_id in claim_ids:
        claim_ids.remove(claim_id)
    state["claim_ids"] = claim_ids

    if claim_ids:
        state["armed"] = True
        state["pending"] = True
        state["claim_id"] = claim_ids[-1]
    else:
        state["armed"] = False
        state["pending"] = False
        state["claim_id"] = claim_id

    state["last_verdict"] = {
        "claim_id": claim_id,
        "verdict": verdict,
        "reason": reason,
        "recorded_at": _now(),
    }
    _save_state(session_id, state)


def is_armed(session_id: str) -> bool:
    """Return True if the premise check is armed (awaiting verdict)."""
    state = _load_state(session_id)
    return bool(state.get("armed") or state.get("pending"))


def is_disarmed(session_id: str) -> bool:
    """Return True if the premise check is disarmed (cleared to proceed)."""
    return not is_armed(session_id)


# Aliases for terminology clarity:
# "open" = disarmed (free to proceed), "closed" = armed (blocking dispatch)
close_gate = arm
open_gate = disarm
is_gate_open = is_disarmed


def _prompt_text(ctx: HookContext | Any) -> str:
    if isinstance(ctx, str):
        return ctx
    raw = getattr(ctx, "raw", {}) if ctx is not None else {}
    prompt = raw.get("prompt") if isinstance(raw, dict) else None
    if prompt is None and hasattr(ctx, "prompt"):
        prompt = ctx.prompt
    if isinstance(prompt, dict):
        prompt = prompt.get("text") or prompt.get("content") or ""
    return str(prompt or "")


# Envelopes the harness wraps around a report from a peer agent.
_PEER_MESSAGE_ENVELOPES = ("<cross-session-message", "<teammate-message")

# For backward compatibility with imports
_PEER_ENVELOPES = ("<cross-session-message", "<teammate-message", "<task-notification")

# Prefixes identifying /loop autonomous loop ticks or preamble injections.
_LOOP_WAKEUP_PREFIXES = (
    "# Autonomous loop tick",
    "# /loop tick",
    "# /loop",
    "/loop tick",
    "<<loop.md>>",
    "<<loop.md-dynamic>>",
    "__autonomous_preamble__",
)

# Prefixes identifying /goal evaluations or auto-continuation notices.
_GOAL_WAKEUP_PREFIXES = (
    "/goal ",
    "Goal active:",
    "Goal set:",
    "<goal-notification",
    "<goal-wakeup",
)

# Automated lifecycle and environment notices.
_OTHER_HARNESS_ENVELOPES = (
    "<mcp-resource-update",
    "<mcp-polling-update",
)


def is_background_task_notice(text: str) -> bool:
    """True when an incoming prompt is an automated background task completion notice.

    Recognized by:
    1. <task-notification> containing explicit background command/task summaries:
       '<summary>Background command ...' or '<summary>Background task ...'
    2. <task-notification> containing monitor events or artifact lifecycle events:
       '<task-type>artifact-' or '<summary>Monitor event:'
    3. <task-notification> containing an '<output-file>' without an agent '<result>'
       block or worker/agent completion signature.
    """
    stripped = text.strip()
    if not stripped.startswith("<task-notification"):
        return False
    if re.search(
        r"<summary>\s*(?:Background (?:command|task)|Remote task|Monitor event:|\d+\s+background\s+tasks)",
        stripped,
        re.IGNORECASE,
    ):
        return True
    if "<task-type>artifact-" in stripped:
        return True
    if "<output-file>" in stripped and "<result>" not in stripped:
        if not re.search(r'<summary>\s*Agent\s+"', stripped) and "worker finished" not in stripped:
            return True
    return False


def is_loop_wakeup(text: str) -> bool:
    """True when an incoming prompt is an automated /loop or autonomous loop tick wakeup.

    Recognized by prompt text or inner <system-reminder> content starting with:
    - '# Autonomous loop tick'
    - '# /loop tick'
    - '# /loop'
    - '/loop tick'
    - '<<loop.md>>' / '<<loop.md-dynamic>>'
    - '__autonomous_preamble__'
    """
    stripped = text.strip()
    if stripped.startswith(_LOOP_WAKEUP_PREFIXES):
        return True
    if stripped.startswith("<system-reminder>"):
        inner = re.sub(r"^<system-reminder>\s*", "", stripped)
        if inner.startswith(_LOOP_WAKEUP_PREFIXES):
            return True
    return False


def is_goal_wakeup(text: str) -> bool:
    """True when an incoming prompt is an automated /goal evaluation or continuation notice.

    Recognized by prompt text starting with:
    - '/goal '
    - 'Goal active:'
    - 'Goal set:'
    - '<goal-notification'
    - '<goal-wakeup'
    """
    stripped = text.strip()
    if stripped.startswith(_GOAL_WAKEUP_PREFIXES):
        return True
    if stripped.startswith("<system-reminder>"):
        inner = re.sub(r"^<system-reminder>\s*", "", stripped)
        if inner.startswith(_GOAL_WAKEUP_PREFIXES):
            return True
    return False


def is_other_harness_notice(text: str) -> bool:
    """True when an incoming prompt is an automated environment or lifecycle notice."""
    stripped = text.strip()
    return stripped.startswith(_OTHER_HARNESS_ENVELOPES)


def is_harness_notice(ctx_or_text: HookContext | str) -> bool:
    """True when an incoming prompt is an automated in-session notice injected by the harness.

    Harness notices include:
    1. Background-task completion notices (e.g. background bash command completions)
    2. /loop wakeups (e.g. # Autonomous loop tick, # /loop tick)
    3. /goal wakeups (e.g. Goal active:, Goal set:, /goal)
    4. Environment/lifecycle notices (e.g. <mcp-resource-update>, monitor events)
    """
    text = ctx_or_text if isinstance(ctx_or_text, str) else _prompt_text(ctx_or_text)
    return (
        is_background_task_notice(text)
        or is_loop_wakeup(text)
        or is_goal_wakeup(text)
        or is_other_harness_notice(text)
    )


def is_worker_report(text: str) -> bool:
    """True when a <task-notification> represents a worker or subagent report with findings.

    Recognized by:
    - <task-notification> that is not a background task notice, and carries:
      1. '<result>...</result>' block with the subagent's final output
      2. '<summary>Agent "..." finished' (or similar Agent summary)
      3. 'worker finished' or subagent token metrics
    """
    stripped = text.strip()
    if not stripped.startswith("<task-notification"):
        return False
    if is_background_task_notice(stripped):
        return False
    if "<result>" in stripped:
        return True
    if re.search(r'<summary>\s*Agent\s+"', stripped):
        return True
    if "worker finished" in stripped:
        return True
    if "<subagent_tokens>" in stripped:
        return True
    return False


def is_peer_report(ctx: HookContext | str) -> bool:
    """True when an incoming prompt is another agent's or worker's report, not a harness notice or user ask."""
    text = ctx if isinstance(ctx, str) else _prompt_text(ctx)
    stripped = text.lstrip()
    if is_harness_notice(stripped):
        return False
    if stripped.startswith(_PEER_MESSAGE_ENVELOPES):
        return True
    if stripped.startswith("<system-reminder>"):
        m = re.search(r"<system-reminder\b[^>]*>(.*?)</system-reminder>", stripped, re.DOTALL)
        if m:
            inner = m.group(1).strip()
            if is_harness_notice(inner):
                return False
            if inner.startswith(_PEER_MESSAGE_ENVELOPES):
                return True
            return is_worker_report(inner)
    return is_worker_report(stripped)


def resolve_verdict_script(hooks_dir: Path | None = None) -> Path:
    if hooks_dir and hooks_dir.is_absolute():
        base = hooks_dir
    else:
        base = Path(__file__).resolve().parent
    # 1. Skill script: <plugin-dir>/skills/premise-check/scripts/verdict.py
    skill_script = base.parent / "skills" / "premise-check" / "scripts" / "verdict.py"
    if skill_script.is_file():
        return skill_script
    # 2. Hook script: <plugin-dir>/hooks/premise_check_verdict.py
    hook_script = base / "premise_check_verdict.py"
    if hook_script.is_file():
        return hook_script
    return skill_script


def format_verdict_command(
    claim_id: str,
    hooks_dir: Path | None = None,
    session_id: str = "",
) -> str:
    script_path = resolve_verdict_script(hooks_dir)
    quoted_script = shlex.quote(str(script_path))
    quoted_claim = shlex.quote(claim_id)
    cmd = f'python3 {quoted_script} --report {quoted_claim} --verdict PASS --reason "<why>"'
    if not os.environ.get("AOPS_SESSION_ID") and session_id:
        cmd += f" --session {shlex.quote(session_id)}"
    return cmd


def _derive_claim_id(ctx: HookContext) -> str:
    if ctx.event == "UserPromptSubmit":
        prompt = _prompt_text(ctx).strip()
        match = re.search(r"<([a-zA-Z0-9_\-]+)([^>]*)>(.*?)(?:</\1>|$)", prompt, re.DOTALL)
        if match:
            attrs = match.group(2)
            id_match = re.search(r'\b(?:id|report_id|task_id)=["\']([^"\']+)["\']', attrs)
            if id_match:
                cid = id_match.group(1).strip()
                if cid and re.match(r"^[a-zA-Z0-9_\-\.:]+$", cid):
                    return cid

            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
            return f"report-{digest}"

        prompt_snippet = prompt.strip()
        if prompt_snippet:
            digest = hashlib.sha256(prompt_snippet.encode("utf-8")).hexdigest()[:8]
            return f"report-{digest}"
        return f"report-{uuid.uuid4().hex[:8]}"

    for call in ctx.tool_calls:
        if call.get("tool_name") in _DISPATCH_TOOLS:
            tool_input = call.get("tool_input") or {}
            desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
            if desc:
                return desc[:80]
            call_id = call.get("tool_use_id") or ""
            if call_id:
                return str(call_id)

    if ctx.tool in _DISPATCH_TOOLS:
        tool_input = ctx.raw.get("tool_input") or {}
        if isinstance(tool_input, dict):
            desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
            if desc:
                return desc[:80]
        call_id = (
            ctx.raw.get("tool_call_id") or ctx.raw.get("id") or ctx.raw.get("tool_use_id") or ""
        )
        if call_id:
            return str(call_id)

    return "report-unnamed"


def _is_override_active() -> bool:
    for var in (
        "PREMISE_CHECK_OVERRIDE",
        "PREMISE_CHECK_GATE_OVERRIDE",
        "AOP_FORCE",
        "AOP_OVERRIDE",
    ):
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return True
    return False


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def premise_check_arm(ctx: HookContext) -> Result | None:
    """PostToolBatch/PostToolUse/UserPromptSubmit handler: arm the premise check."""
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    if ctx.event == "UserPromptSubmit":
        if is_peer_report(ctx):
            claim_id = _derive_claim_id(ctx)
            arm(ctx.session_id, claim_id=claim_id)
            cmd = format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id)
            inject = (
                f"A peer report arrived and armed the premise-check gate: {claim_id}.\n"
                f"The premise-check gate blocks until a verdict is recorded.\n"
                f"To record a verdict and clear the gate, run:\n"
                f"{cmd}"
            )
            user_msg = (
                f"Premise-check gate armed by: {claim_id}. "
                f"The gate blocks until a verdict is recorded. Run:\n{cmd}"
            )
            return warn(inject, user_msg)
        return None

    has_dispatch = any(call.get("tool_name") in _DISPATCH_TOOLS for call in ctx.tool_calls)
    if not has_dispatch and ctx.tool in _DISPATCH_TOOLS:
        has_dispatch = True

    if not has_dispatch:
        return None

    arm(ctx.session_id, claim_id=_derive_claim_id(ctx))
    return None


def premise_check_handler(ctx: HookContext) -> Result | None:
    """PreToolUse/Stop handler: refuse the next restricted action while armed."""
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    if ctx.event == "PreToolUse" and ctx.tool not in _BLOCKED_TOOLS:
        return None

    mode = (
        os.environ.get("PREMISE_CHECK_GATE_MODE", os.environ.get("PREMISE_CHECK_MODE", "block"))
        .strip()
        .lower()
    )
    if mode == "off":
        return None
    if _is_override_active():
        return None
    if not is_armed(ctx.session_id):
        return None

    claim_id = get_state(ctx.session_id).get("claim_id", "the pending report")
    action_desc = (
        "finishing the task or contacting the user/teammates"
        if ctx.event == "Stop"
        else "dispatching another subagent or message"
    )

    cmd = format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id)
    reason = (
        f"The premise-check gate was armed by: {claim_id}.\n"
        f"The gate blocks until a verdict is recorded before {action_desc}.\n"
        f"To record a verdict and clear the gate, run:\n"
        f"{cmd}"
    )
    user_msg = (
        f"Blocked: premise check pending on {claim_id}. "
        f"The gate blocks until a verdict is recorded. Run:\n{cmd}"
    )

    if mode == "warn":
        return warn(reason, user_msg)

    if ctx.event == "Stop":
        return block(reason, user_msg)

    return refuse(reason, user_msg)
