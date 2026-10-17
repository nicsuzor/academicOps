#!/usr/bin/env python3
"""Hook arm/disarm lifecycle for premise checking.

Enforces that a supervisor (Ida) evaluates incoming subagent reports against
logic-check doctrine before dispatching further subagents, contacting the user, or finishing tasks:

- ``premise_check_arm``: a ``UserPromptSubmit`` handler that arms the check when
  a peer's or worker's report arrives. The agent's own outgoing tool calls,
  subagent dispatches included, and the user's own messages never arm it.
- ``premise_check_handler``: a ``PreToolUse`` / ``Stop`` handler that refuses the
  supervisor's next subagent dispatch, communication, channel reply, or stop while armed.
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


def disarm(
    session_id: str,
    claim_id: str,
    verdict: str,
    reason: str,
    verification_id: str = "",
    title: str | None = None,
) -> None:
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
    state["last_verdict"] = last_verdict
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


def _prompt_text(ctx: HookContext) -> str:
    prompt = ctx.raw.get("prompt")
    if isinstance(prompt, dict):
        prompt = prompt.get("text") or prompt.get("content") or ""
    return str(prompt or "")


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


def is_peer_report(ctx: HookContext) -> bool:
    """True when an incoming prompt is another agent's report, not the user's message."""
    text = _strip_channel_wrapper(_prompt_text(ctx))
    return text.startswith(_PEER_ENVELOPES)


def is_foreground_dispatch(ctx: HookContext) -> bool:
    """True when a PostToolUse event is a foreground subagent dispatch."""
    if ctx.event != "PostToolUse" or ctx.tool not in _DISPATCH_TOOLS:
        return False
    tool_input = ctx.raw.get("tool_input") or ctx.raw.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return True
    bg = tool_input.get("run_in_background")
    if isinstance(bg, str):
        return bg.strip().lower() not in ("true", "1", "yes")
    return not bool(bg)


def _hooks_base(hooks_dir: Path | None = None) -> Path:
    if hooks_dir:
        if hooks_dir.is_absolute():
            return hooks_dir
        # If relative, resolve against the hook process's current working directory
        cand = (Path.cwd() / hooks_dir).resolve()
        if (cand.parent / "skills" / "premise-check" / "scripts" / "verdict.py").is_file() or (
            cand / "premise_check_verdict.py"
        ).is_file():
            return cand
        if cand.is_dir() and cand.name == "hooks":
            return cand
    # Check if cwd is the plugin root (the hook's working directory under Claude Code/agy)
    cwd = Path.cwd().resolve()
    if (cwd / "skills" / "premise-check" / "scripts" / "verdict.py").is_file():
        return cwd / "hooks"
    if (cwd / "premise_check_verdict.py").is_file():
        return cwd
    return Path(__file__).resolve().parent


def resolve_verdict_script(hooks_dir: Path | None = None) -> Path:
    base = _hooks_base(hooks_dir)
    plugin_dir = base.parent if base.name == "hooks" else base
    # 1. Skill script: <plugin-dir>/skills/premise-check/scripts/verdict.py
    skill_script = (plugin_dir / "skills" / "premise-check" / "scripts" / "verdict.py").resolve()
    if skill_script.is_file():
        return skill_script
    # 2. Hook script: <plugin-dir>/hooks/premise_check_verdict.py
    hook_script = (base / "premise_check_verdict.py").resolve()
    if hook_script.is_file():
        return hook_script
    return skill_script


def format_verdict_command(
    claim_id: str,
    hooks_dir: Path | None = None,
    session_id: str = "",
) -> str:
    base = _hooks_base(hooks_dir)
    plugin_dir = base.parent if base.name == "hooks" else base
    script_path = resolve_verdict_script(hooks_dir)
    # Run in the plugin's own environment, the same one the hooks use, so the
    # verdict span can import opentelemetry.
    quoted_project = shlex.quote(str(plugin_dir.resolve()))
    quoted_script = shlex.quote(str(script_path.resolve()))
    quoted_claim = shlex.quote(claim_id)
    cmd = (
        f"uv run --project {quoted_project} python3 {quoted_script}"
        f' --claim {quoted_claim} --verdict <PASS|REVISE|FAIL> --reason "<why>"'
    )
    if not os.environ.get("AOPS_SESSION_ID") and session_id:
        cmd += f" --session {shlex.quote(session_id)}"
    return cmd


def _derive_claim_id(ctx: HookContext) -> str:
    prompt = _strip_channel_wrapper(_prompt_text(ctx))
    match = re.match(
        r"<(cross-session-message|teammate-message|task-notification)([^>]*)>(.*?)(?:</\1>|$)",
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
            if cid and re.match(r"^[a-zA-Z0-9_\-\.:]+$", cid):
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
    """UserPromptSubmit handler: arm the premise check on an incoming report."""
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    if ctx.event != "UserPromptSubmit" or not is_peer_report(ctx):
        return None

    claim_id = _derive_claim_id(ctx)
    arm(ctx.session_id, claim_id=claim_id)
    inject = (
        f"Premise-check gate armed by {claim_id}; record a verdict per the `premise-check` skill.\n"
        f"{format_verdict_command(claim_id, ctx.hooks_dir, ctx.session_id)}"
    )
    user_msg = f"Premise-check gate armed by {claim_id}."
    return warn(inject, user_msg)


def premise_check_handler(ctx: HookContext) -> Result | None:
    """PreToolUse/Stop handler: refuse the next restricted action while armed."""
    if ctx.agent_type not in _GATED_AGENT_TYPES:
        return None

    if ctx.event == "PreToolUse" and not _is_blocked_tool(ctx.tool):
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
