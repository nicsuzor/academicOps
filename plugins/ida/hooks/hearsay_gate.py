#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for hearsay checking.

Enforces that an agent evaluates incoming subagent reports and peer messages
against logic-check doctrine before dispatching further subagents, contacting the
user, or finishing tasks:

- ``hearsay_arm``: a ``UserPromptSubmit`` / ``PostToolUse`` handler that arms
  the check when a report or direction arrives: a peer or worker message, or a
  foreground subagent's returned result. A spawn acknowledgement, any other of the
  agent's own tool results, a notice with no report in it, and the user's own
  messages never arm it.
- ``hearsay_handler``: a ``PreToolUse`` / ``Stop`` handler that refuses the
  agent's next subagent dispatch, communication, channel reply, or stop while armed.
- ``arm()`` / ``disarm()``: state management primitives. Calling ``disarm()``
  clears the check once a verdict is recorded.

Verdict recording and OpenTelemetry trace emission live in ``premise_check_verdict.py``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shlex
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import report_argument as ra
from dispatch import HookContext, Result, block, refuse, warn

try:
    import claude_code_tracer
except ImportError:
    claude_code_tracer = None

log = logging.getLogger("aops.hearsay_gate")


def _now() -> str:
    """Current time as an ISO-8601 string carrying the local system UTC offset."""
    return datetime.now().astimezone().isoformat()


# Envelopes the harness wraps around a report or direction from another agent. Anything
# else arriving on UserPromptSubmit -- a channel message or a typed prompt -- is
# the user's own message, which is an ask, not a claim to check.
_PEER_ENVELOPES = (
    "<cross-session-message",
    "<teammate-message",
    "<task-notification",
    "<subagent-handback",
    "<agent-message",
)


# Tools that dispatch subagents
_DISPATCH_TOOLS = ["Agent", "Task", "invoke_subagent"]

# Tools that reach the user directly. Matched on the full name or the last
# ``__`` segment, case-insensitively.
_CHANNEL_REPLY_TOOLS = frozenset(
    name.lower()
    for name in (
        "AskUserQuestion",
        "AskQuestion",
        "ask_user_question",
        "ask_question",
        "ask_user",
        "reply",
        "telegram_reply",
        "telegram_send_message",
        "discord_reply",
        "discord_send_message",
    )
)

# Non-channel tools blocked while the check is armed
_GATED_TOOLS = frozenset([*_DISPATCH_TOOLS, "SendMessage", "Dump"])


def is_channel_reply_tool(tool_name: str) -> bool:
    """True when a tool sends a message to the user over a channel or prompt."""
    if not tool_name:
        return False
    tool_lower = tool_name.lower()
    if tool_lower in _CHANNEL_REPLY_TOOLS or tool_lower.split("__")[-1] in _CHANNEL_REPLY_TOOLS:
        return True
    return ("telegram" in tool_lower or "discord" in tool_lower) and (
        "reply" in tool_lower or "send" in tool_lower or "ask_user" in tool_lower
    )


def _is_blocked_tool(tool_name: str) -> bool:
    if not tool_name:
        return False
    if tool_name in _GATED_TOOLS or tool_name.split("__")[-1] in _GATED_TOOLS:
        return True
    return is_channel_reply_tool(tool_name)


ID_PATTERN = re.compile(
    r"^(?P<kind>claim|verdict|report)-(?P<hash>[0-9a-f]{8})(?:-(?P<title>[a-z0-9]+(?:-[a-z0-9]+)*))?$"
)


def slugify_title(title: str | None) -> str:
    """Convert an arbitrary title string into a lowercase kebab-case slug."""
    if not title:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return slug[:40]


def build_id(kind: str, content: str, title: str | None = None) -> str:
    """Build a short id in the shared format: <kind>-<hash>[-<title>]."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:8]
    slug = slugify_title(title)
    if slug:
        return f"{kind}-{digest}-{slug}"
    return f"{kind}-{digest}"


def is_valid_id(identifier: str) -> bool:
    """Return True if identifier conforms to the shared id format."""
    return bool(ID_PATTERN.match(identifier.strip()))


def parse_id(identifier: str) -> dict[str, str | None] | None:
    """Parse an id into its components: kind, hash, and optional title slug."""
    match = ID_PATTERN.match(identifier.strip())
    if not match:
        return None
    return match.groupdict()


def mint_verification_id(
    claim_id: str,
    verdict: str,
    reason: str,
    title: str | None = None,
) -> str:
    """Mint a verification id in the shared format referencing the verified content."""
    content = f"{claim_id}:{verdict}:{reason}"
    return build_id("verdict", content, title=title)


# ---------------------------------------------------------------------------
# State: is the hearsay check armed (awaiting verdict) or disarmed?
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
        return json.loads(target.read_text(encoding="utf-8"))
    return {}


def _save_state(session_id: str, state: dict[str, Any]) -> None:
    _state_path(session_id).write_text(json.dumps(state, indent=2), encoding="utf-8")


def clear_state(session_id: str) -> None:
    """Reset hearsay check state for a session. Used by tests."""
    target = _state_path(session_id)
    target.unlink(missing_ok=True)


def get_state(session_id: str) -> dict[str, Any]:
    return _load_state(session_id)


def _judged_path(session_id: str, claim_id: str) -> Path:
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    safe_claim = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", claim_id)[:60]
    digest = hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:8]
    return _state_dir() / f"{safe_session}.{safe_claim}-{digest}.judged.txt"


def arm(
    session_id: str,
    claim_id: str | None = None,
    judged_text: str | None = None,
    judged_ref: str | None = None,
    block_expected: bool = False,
) -> None:
    """Arm the hearsay check for a session until a verdict disarms it.

    ``judged_text`` is the report the verdict will judge; it is stored beside
    the state file so the recorder can cross-check the reason against its
    ``argument`` block. ``judged_ref`` names where that text came from: the
    tool-use id of a subagent result, the id of a peer envelope, or a task id.
    ``block_expected`` records whether an Argdown block was required on this report.
    """
    state = _load_state(session_id)
    cid = claim_id or state.get("claim_id") or "unnamed-claim"
    state["armed"] = True
    state["pending"] = True  # backward compat
    state["claim_id"] = cid
    if block_expected:
        state["block_expected"] = True
    claim_ids = state.get("claim_ids") or []
    if cid not in claim_ids:
        claim_ids.append(cid)
    state["claim_ids"] = claim_ids
    state["armed_at"] = _now()
    if judged_text is not None or judged_ref or block_expected:
        judged = state.get("judged") or {}
        entry: dict[str, Any] = {"ref": judged_ref or cid}
        if block_expected:
            entry["block_expected"] = True
        if judged_text is not None:
            path = _judged_path(session_id, cid)
            path.write_text(judged_text, encoding="utf-8")
            entry["file"] = path.name
        judged[cid] = entry
        state["judged"] = judged
    _save_state(session_id, state)


def get_judged(session_id: str, claim_id: str) -> tuple[str | None, str | None]:
    """The judged text and its reference stored when ``claim_id`` armed the gate.

    (None, None) when the arm stored nothing; an entry naming a file that is
    gone raises FileNotFoundError.
    """
    entry = (_load_state(session_id).get("judged") or {}).get(claim_id)
    if not entry:
        return None, None
    text = None
    if entry.get("file"):
        text = (_state_dir() / entry["file"]).read_text(encoding="utf-8")
    return text, entry.get("ref")


def disarm(
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
    machine: bool = False,
) -> None:
    """Disarm the hearsay check after a verdict is recorded."""
    state = _load_state(session_id)
    claim_ids = state.get("claim_ids") or []
    if claim_id in claim_ids:
        claim_ids.remove(claim_id)
    state["claim_ids"] = claim_ids
    judged = state.get("judged") or {}
    entry = judged.pop(claim_id, None)
    if entry and entry.get("file"):
        (_state_dir() / entry["file"]).unlink()
    state["judged"] = judged

    if claim_ids:
        state["armed"] = True
        state["pending"] = True
        state["claim_id"] = claim_ids[-1]
    else:
        state["armed"] = False
        state["pending"] = False
        state["claim_id"] = claim_id

    last_verdict: dict[str, Any] = {
        "claim_id": claim_id,
        "verdict": verdict,
        "reason": reason,
        "recorded_at": _now(),
    }
    if verification_id:
        last_verdict["verification_id"] = verification_id
    if title:
        last_verdict["title"] = title
    if machine:
        last_verdict["machine"] = True
    if verdict == "no-claim":
        last_verdict["no_claim"] = True
    state["last_verdict"] = last_verdict
    _save_state(session_id, state)


def is_armed(session_id: str) -> bool:
    """Return True if the hearsay check is armed (awaiting verdict)."""
    state = _load_state(session_id)
    return bool(state.get("armed") or state.get("pending"))


def is_disarmed(session_id: str) -> bool:
    """Return True if the hearsay check is disarmed (cleared to proceed)."""
    return not is_armed(session_id)


# Aliases for terminology clarity:
# "open" = disarmed (free to proceed), "closed" = armed (blocking dispatch)
close_gate = arm
open_gate = disarm
is_gate_open = is_disarmed


_AGY_USER_REQUEST = re.compile(r"<USER_REQUEST>\s*(.*)\s*</USER_REQUEST>", re.DOTALL)


def _agy_turn_start(ctx: HookContext) -> dict[str, Any] | None:
    if ctx.raw.get("invocationNum", 0) != 0:
        return None
    path = ctx.transcript_path or ctx.raw.get("transcriptPath")
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and entry.get("type") in (
            "USER_INPUT",
            "SYSTEM_MESSAGE",
        ):
            return entry
    return None


_AGY_MESSAGE = re.compile(
    r"\[Message\][^\n]*?\bsender=(\S+)[^\n]*?\bcontent=(.*?)\s*(?:</SYSTEM_MESSAGE>\s*)?$",
    re.DOTALL,
)
_AGY_IDLE_RESPONSE = re.compile(
    r"^Subagent \S+ has gone idle\. This was the subagent's most recent response:\s*(\S.*)$",
    re.DOTALL,
)


def agy_arrival(content: str) -> str:
    """The report or direction an agy SYSTEM_MESSAGE delivers, or "" when it delivers none.

    agy starts a SYSTEM_MESSAGE turn for every wake: the session's own command
    tasks and timers finishing (sender ``<conversation>/task-N``), system
    notices, stop-hook refusals, and messages from other agents. Only a message
    whose sender is another agent's conversation, or a system notice quoting an
    idle subagent's last response, carries a report or direction.
    """
    m = _AGY_MESSAGE.search(content)
    if not m:
        return ""
    sender, body = m.group(1), m.group(2).strip()
    if sender == "system":
        idle = _AGY_IDLE_RESPONSE.match(body)
        return body if idle else ""
    if "/" in sender:
        return ""
    return body


def _agy_user_prompt(ctx: HookContext) -> str:
    """The user's text for an agy turn, read from the turn's transcript."""
    turn_start = _agy_turn_start(ctx)
    if not turn_start or turn_start.get("type") != "USER_INPUT":
        return ""
    content = str(turn_start.get("content") or "").strip()
    m = _AGY_USER_REQUEST.search(content)
    return (m.group(1) if m else content).strip()


def prompt_text(ctx: HookContext) -> str:
    """Extract prompt text canonically across Claude Code and agy."""
    prompt = ctx.raw.get("prompt")
    if prompt is None and hasattr(ctx, "prompt"):
        prompt = ctx.prompt
    if isinstance(prompt, dict):
        prompt = prompt.get("text") or prompt.get("content") or ""
    text = str(prompt or "").strip()
    if not text and ctx.client == "agy":
        text = _agy_user_prompt(ctx)
    return text


_prompt_text = prompt_text


def _strip_channel_wrapper(text: str) -> str:
    """Unwrap outer or leading <channel> envelope if present."""
    s = text.strip()
    m = re.match(r"^<channel\b[^>]*>(.*)</channel>$", s, re.DOTALL)
    if m:
        s = m.group(1).strip()
    m = re.match(r"^<channel\b[^>]*>.*?</channel>\s*(.*)$", s, re.DOTALL)
    if m and m.group(1):
        s = m.group(1).strip()
    return s


_PEER_PREAMBLE = re.compile(
    r"^(?:Another Claude session sent a message:\s*)+",
    re.IGNORECASE,
)


def _strip_peer_wrapper(text: str) -> str:
    """Unwrap channel envelopes and Claude Code teammate/peer preambles."""
    s = _strip_channel_wrapper(text).strip()
    m = _PEER_PREAMBLE.match(s)
    if m:
        s = s[m.end() :].strip()
    s = _strip_channel_wrapper(s).strip()
    return s


def is_peer_report(ctx: HookContext) -> bool:
    """True when an incoming prompt is another agent's report or direction, not the user's message."""
    if ctx.client == "agy":
        turn_start = _agy_turn_start(ctx)
        if turn_start and turn_start.get("type") == "SYSTEM_MESSAGE":
            return bool(agy_arrival(str(turn_start.get("content") or "")))
    raw = _prompt_text(ctx)
    text = _strip_peer_wrapper(raw).lstrip()
    if not text:
        return False
    return text.startswith(_PEER_ENVELOPES)


def is_foreground_dispatch(ctx: HookContext) -> bool:
    """True when a PostToolUse event returns a foreground subagent's result."""
    if ctx.event != "PostToolUse" or ctx.tool not in _DISPATCH_TOOLS:
        return False
    if ctx.client == "agy":
        return False
    response = _tool_response(ctx)
    return isinstance(response, dict) and response.get("status") == "completed"


def _hooks_base(hooks_dir: Path | None = None) -> Path:
    if hooks_dir:
        if hooks_dir.is_absolute():
            return hooks_dir
        cand = (Path.cwd() / hooks_dir).resolve()
        if (cand.parent / "skills" / "premise-check" / "scripts" / "verdict.py").is_file() or (
            cand / "premise_check_verdict.py"
        ).is_file():
            return cand
        if cand.is_dir() and cand.name == "hooks":
            return cand
    cwd = Path.cwd().resolve()
    if (cwd / "skills" / "premise-check" / "scripts" / "verdict.py").is_file():
        return cwd / "hooks"
    if (cwd / "premise_check_verdict.py").is_file():
        return cwd
    return Path(__file__).resolve().parent


def resolve_verdict_script(hooks_dir: Path | None = None) -> Path:
    base = _hooks_base(hooks_dir)
    plugin_dir = base.parent if base.name == "hooks" else base
    skill_script = (plugin_dir / "skills" / "premise-check" / "scripts" / "verdict.py").resolve()
    if skill_script.is_file():
        return skill_script
    hook_script = (base / "premise_check_verdict.py").resolve()
    if hook_script.is_file():
        return hook_script
    return skill_script


def format_verdict_command(
    claim_id: str,
    hooks_dir: Path | None = None,
    session_id: str = "",
    verdict: str = "<PASS|REVISE|FAIL>",
    reason: str | None = None,
) -> str:
    base = _hooks_base(hooks_dir)
    plugin_dir = base.parent if base.name == "hooks" else base
    script_path = resolve_verdict_script(hooks_dir)
    quoted_project = shlex.quote(str(plugin_dir.resolve()))
    quoted_script = shlex.quote(str(script_path.resolve()))
    quoted_claim = shlex.quote(claim_id)
    cmd = (
        f"uv run --project {quoted_project} python {quoted_script}"
        f" --claim {quoted_claim} --verdict {verdict}"
    )
    if reason is not None:
        cmd += f" --reason {shlex.quote(reason)}"
    else:
        cmd += " --reason-file <path>"
    if not os.environ.get("AOPS_SESSION_ID") and session_id:
        cmd += f" --session {shlex.quote(session_id)}"
    return cmd


def _derive_claim_id(ctx: HookContext) -> str:
    if ctx.event == "PostToolUse":
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
            tool_input = ctx.raw.get("tool_input") or ctx.raw.get("toolInput") or {}
            if isinstance(tool_input, dict):
                desc = str(tool_input.get("description") or tool_input.get("prompt") or "").strip()
                if desc:
                    return desc[:80]
            call_id = (
                ctx.raw.get("tool_call_id") or ctx.raw.get("id") or ctx.raw.get("tool_use_id") or ""
            )
            if call_id:
                return str(call_id)
        raise RuntimeError("Dispatch tool call lacks identifier and description metadata")

    if ctx.event == "UserPromptSubmit":
        prompt = _strip_peer_wrapper(_prompt_text(ctx)).strip()
        if not prompt and ctx.client == "agy":
            turn_start = _agy_turn_start(ctx)
            if turn_start:
                prompt = str(turn_start.get("content") or "").strip()
        match = re.match(
            r"<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)([^>]*)>(.*?)(?:</\1>|$)",
            prompt,
            re.DOTALL,
        )
        if match:
            attrs = match.group(2)
            id_match = re.search(
                r'\b(?:id|report_id|claim_id|verification_id|task_id)=["\']([^"\']+)["\']',
                attrs,
            )
            if id_match:
                cid = id_match.group(1).strip()
                if cid and re.match(r"^[a-zA-Z0-9_\-\.:@]+$", cid):
                    return cid

            title_match = re.search(
                r'\b(?:title|short_title|slug)=["\']([^"\']+)["\']',
                attrs,
            )
            title = title_match.group(1).strip() if title_match else None
            return build_id("claim", prompt, title=title)

        if prompt:
            return build_id("claim", prompt)
        return build_id("claim", uuid.uuid4().hex)

    raise RuntimeError(f"Cannot derive claim_id for event {ctx.event}")


_OVERRIDE_VARS = (
    "PREMISE_CHECK_OVERRIDE",
    "PREMISE_CHECK_GATE_OVERRIDE",
    "AOP_FORCE",
    "AOP_OVERRIDE",
)


def _active_override() -> str | None:
    """The first override variable set truthy, or None."""
    for var in _OVERRIDE_VARS:
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return var
    return None


def _is_override_active() -> bool:
    return _active_override() is not None


def _count_override(ctx: HookContext, variable: str) -> None:
    """Count an override that let an armed gate pass a blocked action."""
    import premise_check_verdict as pcv

    state = _load_state(ctx.session_id)
    count = int(state.get("override_count") or 0) + 1
    pcv.emit_override_span(
        pcv._import_claude_code_tracer(),
        ctx.session_id,
        str(state.get("claim_id") or ""),
        ctx.tool or "",
        ctx.event,
        variable,
        count,
    )
    state["override_count"] = count
    _save_state(ctx.session_id, state)


# ---------------------------------------------------------------------------
# What arrived: the judged text and its reference
# ---------------------------------------------------------------------------

_TASK_READ_TOOL = "get_task"
_REPORT_HEADING = re.compile(r"^##\s+Report\s*$", re.MULTILINE)
_VERDICT_HEADING = re.compile(r"^##\s+Premise-Check Verdict\s*$", re.MULTILINE)


def is_task_read_tool(tool_name: str) -> bool:
    """True for the PKB task-read tool under any MCP server prefix."""
    if not tool_name:
        return False
    if tool_name.split("__")[-1] == _TASK_READ_TOOL:
        return True
    return tool_name == _TASK_READ_TOOL or tool_name.endswith(
        (f"_{_TASK_READ_TOOL}", f".{_TASK_READ_TOOL}")
    )


def _tool_input(ctx: HookContext) -> dict[str, Any]:
    tool_input = ctx.raw.get("tool_input") or ctx.raw.get("toolInput") or {}
    return tool_input if isinstance(tool_input, dict) else {}


def _tool_response(ctx: HookContext) -> Any:
    return ctx.raw.get("tool_response", ctx.raw.get("toolResponse"))


def _response_text(value: Any) -> str:
    """Plain text of a tool response: a string, content blocks, or a result mapping."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(t for t in (_response_text(v) for v in value) if t)
    if isinstance(value, dict):
        for key in ("content", "text", "result", "output"):
            if key in value:
                return _response_text(value[key])
    return json.dumps(value)


def _task_record(value: Any) -> dict[str, Any] | None:
    """The task mapping (one with a ``body``) inside a task-read response."""
    if isinstance(value, dict):
        if isinstance(value.get("body"), str):
            return value
        for key in ("structuredContent", "result", "task", "content", "text"):
            if key in value:
                found = _task_record(value[key])
                if found:
                    return found
        return None
    if isinstance(value, list):
        for item in value:
            found = _task_record(item)
            if found:
                return found
        return None
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return {"body": value}
        return _task_record(parsed) if isinstance(parsed, (dict, list)) else None
    return None


def unverdicted_task_report(ctx: HookContext) -> tuple[str, str] | None:
    """(task id, body) when a PKB task read returned a report with no verdict section."""
    if ctx.event != "PostToolUse" or not is_task_read_tool(ctx.tool):
        return None
    record = _task_record(_tool_response(ctx))
    if not record:
        return None
    body = record["body"]
    if not _REPORT_HEADING.search(body) or _VERDICT_HEADING.search(body):
        return None
    tool_input = _tool_input(ctx)
    task_id = str(record.get("id") or tool_input.get("id") or tool_input.get("task_id") or "")
    if not task_id:
        return None
    return task_id, body


def _tool_use_id(ctx: HookContext) -> str:
    return str(ctx.raw.get("tool_use_id") or ctx.raw.get("tool_call_id") or ctx.raw.get("id") or "")


def _envelope_id(prompt: str) -> str | None:
    stripped = _strip_peer_wrapper(prompt)
    match = re.search(r"<([a-zA-Z0-9_\-]+)([^>]*)>", stripped)
    if not match:
        return None
    id_match = re.search(
        r'\b(?:id|report_id|claim_id|verification_id|task_id)=["\']([^"\']+)["\']',
        match.group(2),
    )
    if id_match:
        cid = id_match.group(1).strip()
        if cid and re.match(r"^[a-zA-Z0-9_\-\.:@]+$", cid):
            return cid
    return None


_NOTIFICATION_RESULT = re.compile(r"<result>(.*?)</result>", re.DOTALL)
_HANDBACK_POINTER = re.compile(
    r"report was delivered to you as a message from .{0,120}\(its SubagentHandback call\)",
    re.DOTALL,
)


def carries_report(text: str) -> bool:
    """False when an arrival only announces or points at a report.

    A task notification carries a report in its ``<result>``; one without (a
    background command finishing) carries none. A hand-back pointer names the
    message that carries the report, which arms the gate when it arrives.
    """
    body = _strip_peer_wrapper(text).lstrip()
    if not body:
        return False
    if body.startswith("<task-notification"):
        result = _NOTIFICATION_RESULT.search(body)
        if not result or not result.group(1).strip():
            return False
    return not _HANDBACK_POINTER.search(body)


def _extract_judged_text(prompt: str) -> str:
    """Extract report content from an incoming peer prompt.

    For an idle_notification JSON inside a <teammate-message> envelope,
    the teammate's final report is the JSON `result` string; returning that
    unpacks the unescaped markdown (including any fenced argdown blocks).
    For other peer messages, returns the prompt text.
    """
    stripped = _strip_peer_wrapper(prompt)
    match = re.search(
        r"<(cross-session-message|teammate-message|task-notification|subagent-handback|agent-message)([^>]*)>(.*?)(?:</\1>|$)",
        stripped,
        re.DOTALL,
    )
    if match and match.group(1) == "teammate-message":
        inner = match.group(3).strip()
        if inner.startswith("{") and inner.endswith("}"):
            try:
                data = json.loads(inner)
                if (
                    isinstance(data, dict)
                    and data.get("type") == "idle_notification"
                    and "result" in data
                ):
                    return str(data["result"])
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return prompt


# ---------------------------------------------------------------------------
# Shared trigger predicate and OTel emission
# ---------------------------------------------------------------------------


def extract_judged_content(ctx: HookContext) -> tuple[str, str] | None:
    """Extract (judged_text, judged_ref) if this event is a hearsay candidate, else None."""
    if ctx.event == "UserPromptSubmit":
        if not is_peer_report(ctx):
            return None
        text = _prompt_text(ctx)
        if not text and ctx.client == "agy":
            turn_start = _agy_turn_start(ctx)
            if turn_start:
                text = agy_arrival(str(turn_start.get("content") or ""))
        raw_prompt = text
        judged_text = _extract_judged_text(raw_prompt)
        if not carries_report(judged_text):
            return None
        judged_ref = _envelope_id(raw_prompt.strip()) or _derive_claim_id(ctx)
        return judged_text, judged_ref

    if ctx.event == "PostToolUse":
        if not is_foreground_dispatch(ctx):
            return None
        judged_text = _response_text(_tool_response(ctx))
        if not carries_report(judged_text):
            return None
        judged_ref = _tool_use_id(ctx) or _derive_claim_id(ctx)
        return judged_text, judged_ref

    return None


def should_arm_hearsay(ctx: HookContext) -> bool:
    """Shared trigger predicate: True when an incoming event arms the hearsay gate."""
    content = extract_judged_content(ctx)
    if not content:
        return False
    judged_text, _ = content
    if ctx.event == "UserPromptSubmit":
        block_text = ra.extract_block(judged_text)
        if block_text is not None and ra.is_null_form(block_text):
            return False
    return True


is_hearsay_trigger = should_arm_hearsay


def emit_hearsay_span(*args: Any, **kwargs: Any) -> bool:
    """Forward hearsay span emission to premise_check_verdict."""
    import premise_check_verdict as pcv

    return pcv.emit_hearsay_span(*args, **kwargs)


def _emit_hearsay_trace(ctx: HookContext, claim_id: str, judged_ref: str | None) -> None:
    """Emit an OTel span for a hearsay check if tracing is configured."""
    tracer = claude_code_tracer
    if tracer is None:
        return
    try:
        config = tracer.discover_config()
        if config is not None:
            emit_hearsay_span(
                tracer,
                session_id=ctx.session_id,
                claim_id=claim_id,
                event=ctx.event,
                judged_ref=judged_ref,
                config=config,
            )
    except Exception as exc:
        log.debug("Hearsay span export skipped: %s", exc)


# ---------------------------------------------------------------------------
# Hook handlers
# ---------------------------------------------------------------------------


def hearsay_arm(ctx: HookContext) -> Result | None:
    """UserPromptSubmit or PostToolUse handler: arm the hearsay gate on an incoming report or direction."""
    content = extract_judged_content(ctx)
    if not content:
        return None
    judged_text, judged_ref = content

    claim_id = _derive_claim_id(ctx)

    if ctx.event == "UserPromptSubmit":
        block_text = ra.extract_block(judged_text)

        # 1. Null form: clears the gate with no agent action
        if block_text is not None and ra.is_null_form(block_text):
            disarm(
                ctx.session_id,
                claim_id=claim_id,
                verdict="no-claim",
                reason="null form",
                machine=True,
            )
            return None

        # 2. Absent block: keep gate shut, agent must send it back for resending
        if block_text is None:
            arm(
                ctx.session_id,
                claim_id=claim_id,
                judged_text=judged_text,
                judged_ref=judged_ref,
                block_expected=True,
            )
            _emit_hearsay_trace(ctx, claim_id, judged_ref)
            inject = (
                f"Premise-check gate armed by {claim_id}: no argument block supplied; "
                f"send the message back for revision per the `premise-check` skill "
                f"(an absent block cannot pass).\n"
                f"{format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id, verdict='REVISE', reason='no argument supplied')}"
            )
            user_msg = f"Premise-check gate armed by {claim_id} (no argument block supplied; send back for revision)."
            return warn(inject, user_msg)

        # 3. Substantive argument block: arm the gate awaiting agent verdict
        arm(
            ctx.session_id,
            claim_id=claim_id,
            judged_text=judged_text,
            judged_ref=judged_ref,
            block_expected=True,
        )
        _emit_hearsay_trace(ctx, claim_id, judged_ref)
    else:
        # PostToolUse
        arm(
            ctx.session_id,
            claim_id=claim_id,
            judged_text=judged_text,
            judged_ref=judged_ref,
        )
        _emit_hearsay_trace(ctx, claim_id, judged_ref)

    inject = (
        f"Premise-check gate armed by {claim_id}; if this is a direction, summarise it stating deliverables and log as a frozen acceptance checklist on a PKB task; record a verdict per the `premise-check` skill.\n"
        f"{format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id)}"
    )
    user_msg = f"Premise-check gate armed by {claim_id}."
    return warn(inject, user_msg)


def hearsay_handler(ctx: HookContext) -> Result | None:
    """PreToolUse/Stop handler: refuse the next restricted action while armed."""
    if ctx.event == "PreToolUse" and not _is_blocked_tool(ctx.tool):
        return None

    mode = (
        os.environ.get("PREMISE_CHECK_GATE_MODE", os.environ.get("PREMISE_CHECK_MODE", "block"))
        .strip()
        .lower()
    )
    if mode == "off":
        return None
    if not is_armed(ctx.session_id):
        return None
    if _active_override():
        return None

    claim_id = get_state(ctx.session_id).get("claim_id", "the pending report")
    action_desc = (
        "finishing the task or contacting the user/teammates"
        if ctx.event == "Stop"
        else "dispatching another subagent or message"
    )

    reason = (
        f"Premise-check gate armed by {claim_id} blocks {action_desc}; "
        f"record a verdict per the `premise-check` skill.\n"
        f"{format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id)}"
    )
    user_msg = f"Blocked: premise-check verdict pending on {claim_id}."

    if mode == "warn":
        return warn(reason, user_msg)

    if ctx.event == "Stop":
        return block(reason, user_msg)

    return refuse(reason, user_msg)


# Backward compatibility aliases
premise_check_arm = hearsay_arm
premise_check_handler = hearsay_handler
