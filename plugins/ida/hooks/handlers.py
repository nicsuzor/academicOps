from __future__ import annotations

"""ida hook handlers (premise-check, hearsay_gate, and handback reminders)."""

import json
import logging
import os
import re
import shlex
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from dispatch import (
    HookContext,
    Kind,
    Result,
    _merge,
    _run_handler,
    _tracer_state_dir,
    load_message_pair,
    warn,
)
from hearsay_gate import (
    _is_subagent_conversation,
    hearsay_arm,
    hearsay_handler,
    record_pre_dispatch,
    should_arm_hearsay,
    subagent_start_gate_notice,
)
from hearsay_gate import (
    is_peer_report as is_peer_report,
)

premise_check_arm = hearsay_arm
premise_check_handler = hearsay_handler

Handler = Callable[[HookContext], Result | None]

log = logging.getLogger("aops.ida.handlers")

PREMISE_CHECK_POINTER = (
    "All agent-to-agent communication follows `premise-check` (`ida:premise-check`)."
    " Write inter-agent messages in unfenced prose Argdown blocks stating the ask upfront"
    " and sourcing load-bearing premises proportionately (or bare `[no claim]` when claim-free)."
    " Run judicial review on the message alone -- zero substantive checking outside it --"
    " scaling effort and reasons to what turns on it and remanding only material defects."
)


def _read_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        k, sep, v = line.partition("=")
        if not sep:
            continue
        k = k.strip()
        v = v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[k] = v
    return out


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"export {k}={shlex.quote(v)}" for k, v in sorted(values.items())]
    content = "\n".join(lines) + ("\n" if lines else "")
    path.write_text(content, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _export_session_id(ctx: HookContext) -> bool:
    """Write this session's id to CLAUDE_ENV_FILE as AOPS_SESSION_ID."""
    env_file_str = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file_str or not ctx.session_id:
        return False
    env_file = Path(env_file_str)
    values = _read_env_file(env_file)
    values["AOPS_SESSION_ID"] = ctx.session_id
    _write_env_file(env_file, values)
    return True


def _session_pointer_dir() -> Path:
    import tempfile

    override = os.environ.get("AOPS_SESSION_POINTER_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_session_pointer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def honest_output(ctx: HookContext) -> Result | None:
    """Remind subagents on SubagentStart to write reports in premise-check shape."""
    if ctx.event != "SubagentStart" or ctx.raw.get("background_tasks"):
        return None
    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


honesty_on_peer_message = honest_output


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind agents that an incoming peer report or foreground subagent return is hearsay."""
    if not should_arm_hearsay(ctx):
        return None
    return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


def session_start(ctx: HookContext) -> Result | None:
    """Inject ida CORE.md and PREMISE_CHECK_POINTER on SessionStart."""
    parts = [PREMISE_CHECK_POINTER]
    core_path = (
        ctx.hooks_dir.parent
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent.parent
    ) / "CORE.md"
    if core_path.is_file():
        core_text = core_path.read_text(encoding="utf-8").strip()
        if core_text:
            parts.append(core_text)

    _export_session_id(ctx)

    if ctx.session_id:
        safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
        marker = _session_pointer_dir() / f"{safe_session}.ida.delivered"
        try:
            with marker.open("w", encoding="utf-8") as f:
                f.write(datetime.now().astimezone().isoformat())
        except OSError as exc:
            log.warning("Could not write session pointer marker %s: %s", marker, exc)

    return warn("\n\n".join(parts))


def agy_session_pointer(ctx: HookContext) -> Result | None:
    """Deliver PREMISE_CHECK_POINTER (and honesty notice for subagents) on agy once."""
    if ctx.client != "agy" or not ctx.session_id:
        return None
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
    marker = _session_pointer_dir() / f"{safe_session}.ida.delivered"
    if marker.exists():
        return None
    try:
        with marker.open("x", encoding="utf-8") as f:
            f.write(datetime.now().astimezone().isoformat())
    except (FileExistsError, OSError):
        return None

    pointer_text = PREMISE_CHECK_POINTER
    try:
        tracer_file = _tracer_state_dir() / f"{ctx.session_id}.json"
        if tracer_file.is_file():
            tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
            phx_sid = tdata.get("phoenix_session_id")
            if phx_sid:
                phx_root = str(phx_sid).split("/", 1)[0]
                if phx_root and phx_root != ctx.session_id:
                    pointer_text = (
                        f"{PREMISE_CHECK_POINTER}\n"
                        f"caller_session: {phx_root} | agent_id: {ctx.session_id}"
                    )
    except Exception:
        pass

    if _is_subagent_conversation(ctx):
        hooks_dir = (
            ctx.hooks_dir
            if ctx.hooks_dir and str(ctx.hooks_dir) != "."
            else Path(__file__).resolve().parent
        )
        honesty_agent, honesty_user = load_message_pair(hooks_dir, "honesty")
        if honesty_agent:
            pointer_text = f"{honesty_agent}\n\n{pointer_text}"
        return warn(pointer_text, honesty_user or pointer_text)

    return warn(pointer_text)


def user_prompt_submit(ctx: HookContext) -> Result | None:
    """Handle UserPromptSubmit / PreInvocation for hearsay arming."""
    steps = (
        agy_session_pointer,
        rule_against_hearsay,
        hearsay_arm,
    )
    return _merge([_run_handler(step, ctx) for step in steps])


def pre_tool(ctx: HookContext) -> Result | None:
    """Enforce hearsay gate on PreToolUse and record subagent dispatch."""
    gate_res = _run_handler(hearsay_handler, ctx)
    if gate_res is not None and gate_res.kind == Kind.REFUSE:
        return gate_res
    record_pre_dispatch(ctx)
    return gate_res


def post_tool(ctx: HookContext) -> Result | None:
    """Arm hearsay gate on PostToolUse."""
    return _run_handler(hearsay_arm, ctx)


def post_tool_batch(ctx: HookContext) -> Result | None:
    """Arm hearsay gate on PostToolBatch."""
    steps = (rule_against_hearsay, hearsay_arm)
    return _merge([_run_handler(step, ctx) for step in steps])


def subagent_start(ctx: HookContext) -> Result | None:
    """Emit honesty reminder and active gate notice on SubagentStart."""
    steps = (honest_output, subagent_start_gate_notice)
    return _merge([_run_handler(step, ctx) for step in steps])


def stop(ctx: HookContext) -> Result | None:
    """Enforce hearsay gate on Stop."""
    return _run_handler(hearsay_handler, ctx)


def subagent_stop(ctx: HookContext) -> Result | None:
    """Arm hearsay gate on SubagentStop."""
    return _run_handler(hearsay_arm, ctx)


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [user_prompt_submit],
    "PreToolUse": [pre_tool],
    "PostToolUse": [post_tool],
    "PostToolBatch": [post_tool_batch],
    "SubagentStart": [subagent_start],
    "Stop": [stop],
    "SubagentStop": [subagent_stop],
}
