"""aops hook handlers."""

from __future__ import annotations

import json
import logging
import os
import shlex
import socket
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, block, load_message_pair, warn

log = logging.getLogger("aops.handlers")

try:
    import claude_code_tracer
except ImportError as exc:
    claude_code_tracer = None
    log.warning(
        "claude_code_tracer did not import (%s) — OTel tracing is disabled for every hook",
        exc,
    )

try:
    import agy_tracer
except ImportError as exc:
    agy_tracer = None
    log.warning("agy_tracer did not import (%s)", exc)

try:
    from premise_check_gate import (
        premise_check_arm,
        premise_check_handler,
    )
except ImportError:
    premise_check_arm = None
    premise_check_handler = None
    premise_check_handler = None
    premise_check_arm = None

Handler = Callable[[HookContext], Result | None]

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


def _scrub(value: object) -> str:
    """Neutralise characters that let a client-supplied value forge a field."""
    return " ".join(str(value).split()).replace("|", "")


def _get_plugin_version_metadata(ctx: HookContext) -> str | None:
    # 1. Check direct environment variable
    if os.environ.get("AOPS_IMAGE_PLUGINS_VERSION"):
        return os.environ["AOPS_IMAGE_PLUGINS_VERSION"]
    # 2. Check ctx.raw
    if ctx.raw.get("plugins"):
        return str(ctx.raw["plugins"])
    if ctx.raw.get("plugins_version"):
        return str(ctx.raw["plugins_version"])
    # 3. Check /home/worker/.aops-image-metadata.json
    metadata_path = Path("/home/worker/.aops-image-metadata.json")
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            version = data.get("aops_version") or "0.9.1"
            dist_source = data.get("dist_source") or "local"
            return f"{version} ({dist_source}:match)"
        except Exception:
            pass
    return None


def _format_session_metadata(ctx: HookContext) -> str:
    # ``%z`` (``+1000``), never ``%Z``. The abbreviation is not unique — ``IST``
    # is both Asia/Kolkata (+05:30) and Europe/Dublin (+01:00) — so a reader
    # cannot recover an offset from it, which is the whole point of naming the
    # zone. ``astimezone()`` guarantees an aware datetime, so ``%z`` is never empty.
    now = datetime.now().astimezone()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S %z")

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    session_id = ctx.session_id or ctx.raw.get("session_id") or ctx.raw.get("conversationId") or ""
    cwd = ctx.cwd or ctx.raw.get("cwd") or ""

    plugins_meta = _get_plugin_version_metadata(ctx)

    pkb_version = os.environ.get("PKB_VERSION") or ctx.raw.get("pkb_version") or "unknown"

    parts = [
        f"session: {_scrub(session_id)}" if session_id else "session: unknown",
        f"time: {time_str}",
        f"host: {_scrub(hostname)}" if hostname else "host: unknown",
        f"cwd: {_scrub(cwd)}" if cwd else "cwd: unknown",
    ]
    if plugins_meta:
        parts.append(f"plugins: {_scrub(plugins_meta)}")
    parts.append(f"pkb: {_scrub(pkb_version)}")

    otel_endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("BETA_TRACING_ENDPOINT")
        or os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")
    )
    if otel_endpoint:
        service_name = os.environ.get("OTEL_SERVICE_NAME") or "unknown"
        parts.append(f"tracing: {_scrub(otel_endpoint)} (service: {_scrub(service_name)})")
    else:
        parts.append("tracing: unconfigured")

    return " | ".join(parts)


def _get_injected_files(ctx: HookContext) -> list[str]:
    injected_str = os.environ.get("AOPS_INJECT_FILES", "").strip()
    if not injected_str:
        return []

    lines = []
    base_dir = ctx.cwd
    for p_str in injected_str.split(","):
        p_str = p_str.strip()
        if not p_str:
            continue
        p = Path(p_str)
        if not p.is_absolute():
            p = base_dir / p

        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                lines.append(f"--- START: {p_str} ---\n{content}\n--- END: {p_str} ---")
            except Exception as e:
                lines.append(f"--- ERROR reading {p_str}: {e} ---")
        else:
            lines.append(f"--- MISSING: {p_str} ---")
    return lines


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


def _isolate_credentials(ctx: HookContext) -> bool:
    env_file_str = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file_str:
        return False
    env_file = Path(env_file_str)

    existing = _read_env_file(env_file)
    moved: dict[str, str] = {}

    for var in _BASIC_VARS:
        val = os.environ.get(var)
        if val is not None:
            moved[var] = val

    if not moved:
        return False

    existing.update(moved)
    _write_env_file(env_file, existing)

    for var in moved:
        os.environ.pop(var, None)

    return True


def _check_stale_baked_plugins() -> str | None:
    metadata_path = Path("/home/worker/.aops-image-metadata.json")
    if not metadata_path.exists():
        return None
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        if data.get("dist_source") == "stale":
            built = data.get("built_at", "unknown")
            host_commit = data.get("host_commit", "unknown")
            built_commit = data.get("built_commit", "unknown")
            return (
                f"[WARNING: STALE BAKED PLUGINS DETECTED]\n"
                f"The plugins baked into this container image do not match the current commit on the host.\n"
                f"Image built at: {built}\n"
                f"Baked commit:   {built_commit}\n"
                f"Host commit:    {host_commit}\n"
                f"Behavior of skills/hooks may diverge from host edits. Run 'polecat build' to refresh."
            )
    except Exception:
        pass
    return None


def session_start(ctx: HookContext) -> Result | None:
    """Handle SessionStart for Claude Code and SessionStart for agy."""
    metadata = _format_session_metadata(ctx)
    parts = ["aops hook: Session started.", metadata]
    user_parts = [metadata]

    stale_warning = os.environ.get("AOPS_IMAGE_STALENESS_WARNING") or ctx.raw.get(
        "image_staleness_warning"
    )
    if not stale_warning and (
        os.environ.get("AOPS_IMAGE_STALE") == "1" or ctx.raw.get("image_stale")
    ):
        stale_warning = (
            "[SYSTEM WARNING: RUNNING WITH STALE BAKED PLUGINS]\n"
            "Container plugin payload lags workspace under test.\n"
            "Any skill, hook, or MCP behavior verified in this session reflects the BAKED payload, NOT workspace edits."
        )

    if stale_warning:
        parts.append(stale_warning)
        user_parts.append(stale_warning)

    if _isolate_credentials(ctx):
        parts.append("Credentials have been isolated in CLAUDE_ENV_FILE.")
        user_parts.insert(0, "Credentials isolated.")

    injected = _get_injected_files(ctx)
    if injected:
        files_str = "Injected context files:\n" + "\n".join(injected)
        parts.append(files_str)
        user_parts.append(files_str)

    return warn("\n\n".join(parts), "\n\n".join(user_parts))


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind the dispatcher that a subagent's report is not evidence."""
    # Only fire on supervisor profiles
    if ctx.agent_type in ("aops:ida", "aops:james", "orchestrate:james"):
        if any(call.get("tool_name") == "Agent" for call in ctx.tool_calls):
            return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))

    return None


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims."""
    # Do not fire on supervisor profiles (Ida and James)
    if ctx.agent_type in (
        "aops:ida",
        "aops:james",
        "orchestrate:james",
        "pkb:ida",
    ) or (ctx.agent_type and ctx.agent_type.endswith((":ida", ":james"))):
        return None

    if ctx.raw.get("background_tasks"):
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind the face to strip its reply down to what is load-bearing."""
    # Only fire on Ida
    if ctx.agent_type == "aops:ida":
        if ctx.raw.get("background_tasks"):
            return None
        return warn(*load_message_pair(ctx.hooks_dir, "quiet"))

    return None


def _is_james(ctx: HookContext) -> bool:
    """Is this session the worker persona the handover gate belongs to?

    Two sources, because the persona reaches a hook two different ways.
    ``agent_type`` is populated when james runs as a dispatched subagent and is
    empty for a top-level session, which is exactly the shape a sandboxed
    worker has; ``AOPS_AGENT_NAME`` is the environment's name for the persona a
    session booted into, already the tracers' fallback for the same question
    (``claude_code_tracer.py``, ``agy_tracer.py``).

    Both are affirmative tests. An unlabelled session is not james, so the gate
    stays off for ida, sara, and a person's own session rather than holding
    every stop in the fleet.
    """
    agent_type = ctx.agent_type or ""
    if agent_type.endswith(":james"):
        return True
    return (os.environ.get("AOPS_AGENT_NAME") or "").strip().lower().endswith("james")


def dump_before_stopping(ctx: HookContext) -> Result | None:
    """Withhold james' stop until the work is committed and handed over.

    Blocking, and the only handler here that is. A worker's commits and its
    report are the only things that survive an ephemeral container, and a stop
    is the last moment either can still be produced.

    Once per stop-chain, and that guard is dispatch.py's, not this handler's:
    the block gives the session another turn, and the re-entry carries
    ``stop_hook_active``, which ``is_continuation`` drops before any handler
    loads. So a worker that has already run ``dump`` stops on its next attempt.

    ``background_tasks`` holds it silent while work is still running: nothing is
    being handed back yet, so there is nothing to hand over, and firing here
    would spend the chain's one block on a turn that is not the handback.
    """
    if not _is_james(ctx):
        return None
    if ctx.raw.get("background_tasks"):
        return None

    reason, user_text = load_message_pair(ctx.hooks_dir, "dump-gate")
    if not reason:
        # A block is an instruction to do something. With no text there is no
        # instruction, and blocking would cost the agent a turn to be told
        # nothing — worse than not blocking. Fail open and say why.
        print(
            "DEGRADED: aops: hooks/messages/dump-gate.md is missing or empty, so the handover "
            "gate cannot be asked for; letting the stop through",
            file=sys.stderr,
        )
        return None
    return block(reason, user_text)


def _prepare_tracer_data(ctx: HookContext) -> dict[str, Any]:
    """Extract and normalize payload dictionary for claude_code_tracer."""
    data = dict(ctx.raw)
    if ctx.session_id:
        data.setdefault("session_id", ctx.session_id)
    if ctx.tool:
        data.setdefault("tool_name", ctx.tool)
    if "toolName" in data and "tool_name" not in data:
        data["tool_name"] = data["toolName"]
    if "toolInput" in data and "tool_input" not in data:
        data["tool_input"] = data["toolInput"]
    if "toolResponse" in data and "tool_response" not in data:
        data["tool_response"] = data["toolResponse"]
    return data


def user_prompt_submit(ctx: HookContext) -> Result | None:
    """Tracer hook handler for canonical UserPromptSubmit, Claude Code side."""
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_user_prompt_submit(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer user_prompt_submit failed: %s", exc)
    return None


def pre_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer pre_tool failed: %s", exc)
    return None


def post_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool failed: %s", exc)
    return None


def post_tool_failure(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool_failure(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool_failure failed: %s", exc)
    return None


def stop(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer stop failed: %s", exc)
    return None


def agy_user_prompt_submit(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_pre_invocation(data, config)
    except Exception as exc:
        log.warning("agy_user_prompt_submit tracer failed: %s", exc)
    return None


def agy_pre_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("agy_pre_tool tracer failed: %s", exc)
    return None


def agy_post_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("agy_post_tool tracer failed: %s", exc)
    return None


def agy_stop(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        config = agy_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            agy_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("agy_stop tracer failed: %s", exc)
    return None


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [user_prompt_submit, agy_user_prompt_submit, honest_output],
    "PreToolUse": [h for h in (pre_tool, agy_pre_tool, premise_check_handler) if h is not None],
    "PostToolUse": [post_tool, agy_post_tool],
    "PostToolUseFailure": [post_tool_failure],
    "Stop": [stop, agy_stop, dump_before_stopping],
    "PostToolBatch": [
        h for h in (rule_against_hearsay, premise_check_arm, be_quiet) if h is not None
    ],
    "SubagentStart": [honest_output],
}
