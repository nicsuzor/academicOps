from __future__ import annotations

"""james hook handlers."""


import json
import logging
import os
import re
import secrets
import shlex
import socket
import sys
import tempfile
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_IDA_HOOKS_DIR = _HOOKS_DIR.parent.parent / "ida" / "hooks"
if _IDA_HOOKS_DIR.is_dir() and str(_IDA_HOOKS_DIR) not in sys.path:
    sys.path.append(str(_IDA_HOOKS_DIR))

from dispatch import (
    HookContext,
    Result,
    _run_handler,
    refuse,
    warn,
)

Handler = Callable[[HookContext], Result | None]

log = logging.getLogger("aops.handlers")

try:
    import claude_code_tracer
except ImportError as exc:
    claude_code_tracer = None
    log.warning(
        "claude_code_tracer did not import (%s) -- OTel tracing is disabled for every hook",
        exc,
    )

try:
    import agy_tracer
except ImportError as exc:
    agy_tracer = None
    log.warning("agy_tracer did not import (%s)", exc)

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_NOSYSTEM",
)


def _tracer_state_dir() -> Path:
    env_dir = (
        os.environ.get("AOPS_TRACER_STATE_DIR")
        or os.environ.get("TRACER_STATE_DIR")
        or os.environ.get("AOPS_TRACER_DIR")
    )
    if env_dir:
        return Path(env_dir)
    if claude_code_tracer is not None and hasattr(claude_code_tracer, "_tracer_state_dir"):
        return claude_code_tracer._tracer_state_dir()
    if claude_code_tracer is not None and hasattr(claude_code_tracer, "STATE_DIR"):
        return Path(claude_code_tracer.STATE_DIR)
    return Path.home() / ".claude" / "tracer"


def _scrub(value: object) -> str:
    """Neutralise characters that let a client-supplied value forge a field."""
    return " ".join(str(value).split()).replace("|", "")


def _resolve_plugin_version(ctx: HookContext) -> str | None:
    """Resolve the installed plugin version from env or manifest."""
    if ver := os.environ.get("AOPS_IMAGE_PLUGINS_VERSION"):
        return ver.strip()
    plugin_dir = (
        ctx.hooks_dir.parent
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent.parent
    )
    for candidate in (
        plugin_dir / ".claude-plugin" / "plugin.json",
        plugin_dir / "plugin.json",
    ):
        if candidate.is_file():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if v := data.get("version"):
                return str(v).strip()
    return None


def _format_session_metadata(ctx: HookContext) -> str:
    now = datetime.now().astimezone()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S %z")

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    session_id = ctx.session_id or ctx.raw.get("session_id") or ctx.raw.get("conversationId") or ""
    cwd = ctx.cwd or ctx.raw.get("cwd") or ""

    parts = [
        f"session: {_scrub(session_id)}" if session_id else "session: unknown",
        f"time: {time_str}",
        f"host: {_scrub(hostname)}" if hostname else "host: unknown",
        f"cwd: {_scrub(cwd)}" if cwd else "cwd: unknown",
    ]

    pkb_url = os.environ.get("PKB_MCP_URL")
    if not pkb_url:
        raise RuntimeError("PKB_MCP_URL is not set; SessionStart requires it")
    parts.append(f"pkb: {_scrub(pkb_url)}")

    plugin_ver = _resolve_plugin_version(ctx)
    if plugin_ver:
        parts.append(f"plugins: {_scrub(plugin_ver)}")

    otel_endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or os.environ.get("BETA_TRACING_ENDPOINT")
        or os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")
    )
    if otel_endpoint:
        service_name = os.environ.get("OTEL_SERVICE_NAME", "").strip()
        if service_name:
            parts.append(f"tracing: {_scrub(otel_endpoint)} (service: {_scrub(service_name)})")
        else:
            parts.append(f"tracing: {_scrub(otel_endpoint)}")
    else:
        parts.append("tracing: unconfigured")

    return " | ".join(parts)


def _get_workspace_core_md(ctx: HookContext) -> str | None:
    """Read the project-local .agents/CORE.md if present in target workspace."""
    if not ctx.cwd:
        return None
    workspace_core = Path(ctx.cwd) / ".agents" / "CORE.md"
    if workspace_core.is_file():
        try:
            content = workspace_core.read_text(encoding="utf-8").strip()
            return content or None
        except Exception as exc:
            log.warning("Could not read workspace .agents/CORE.md: %s", exc)
    return None


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

    aops_gitconfig = os.environ.get("AOPS_GIT_CONFIG_GLOBAL")
    added_git_isolation = False
    if "GIT_CONFIG_GLOBAL" not in existing and "GIT_CONFIG_GLOBAL" not in moved and aops_gitconfig:
        existing["GIT_CONFIG_GLOBAL"] = str(Path(aops_gitconfig).expanduser())
        existing.setdefault("GIT_CONFIG_NOSYSTEM", "1")
        added_git_isolation = True

    if not moved and not added_git_isolation:
        return False

    existing.update(moved)
    _write_env_file(env_file, existing)

    for var in moved:
        os.environ.pop(var, None)

    return True


def _export_session_id(ctx: HookContext) -> bool:
    """Write this session's id to CLAUDE_ENV_FILE as AOPS_SESSION_ID.

    CLAUDE_ENV_FILE is sourced before every shell command, so each session's
    own file carries its own session id for verdict and claim scripts.
    """
    env_file_str = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file_str or not ctx.session_id:
        return False
    env_file = Path(env_file_str)
    values = _read_env_file(env_file)
    values["AOPS_SESSION_ID"] = ctx.session_id
    _write_env_file(env_file, values)
    return True


PREMISE_CHECK_POINTER = (
    "Reports follow `premise-check`: written in its shape and checked on receipt."
    " Load the skill (`james:premise-check`) before writing or checking one;"
    " its form is a restricted subset of Argdown."
    " Every `send_message` / `SendMessage` report to a calling/peer agent"
    " (and every foreground subagent return) must end with a fenced `argdown` block or `[no claim]`."
)


def session_start(ctx: HookContext) -> Result | None:
    """Handle SessionStart for Claude Code and Antigravity (agy)."""
    emit_debug_span(ctx)
    metadata = _format_session_metadata(ctx)
    parts = [
        metadata,
        PREMISE_CHECK_POINTER,
    ]
    core_path = (
        ctx.hooks_dir.parent
        if ctx.hooks_dir and str(ctx.hooks_dir) != "."
        else Path(__file__).resolve().parent.parent
    ) / "CORE.md"
    if core_path.is_file():
        core_text = core_path.read_text(encoding="utf-8").strip()
        if core_text:
            parts.append(core_text)
    user_parts = [metadata]

    is_telemetry_ok = True
    if claude_code_tracer is not None:
        is_telemetry_ok = claude_code_tracer.is_telemetry_configured()
    else:
        is_telemetry_ok = bool(
            os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            or os.environ.get("BETA_TRACING_ENDPOINT")
            or os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")
        )

    mode = "warn"
    if claude_code_tracer is not None:
        mode = claude_code_tracer.get_telemetry_failure_mode()
    elif os.environ.get("AOPS_TELEMETRY_FAILURE_MODE") == "block":
        mode = "block"

    if not is_telemetry_ok:
        unconfigured_err = (
            "WARNING: OpenTelemetry tracing unconfigured (endpoint or credentials unset). "
            "Telemetry will NOT be exported."
        )
        print(unconfigured_err, file=sys.stderr)
        unconfigured_ctx = "WARNING: OpenTelemetry tracing is unconfigured. Spans and metrics for this session are dropped."
        parts.append(unconfigured_ctx)
        user_parts.append(unconfigured_ctx)
        if mode == "block":
            return refuse("\n\n".join(parts), "\n\n".join(user_parts))

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
    _export_session_id(ctx)

    if ctx.session_id:
        safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
        marker = _session_pointer_dir() / f"{safe_session}.delivered"
        try:
            with marker.open("w", encoding="utf-8") as f:
                f.write(datetime.now().astimezone().isoformat())
        except OSError as exc:
            log.warning("Could not write session pointer marker %s: %s", marker, exc)

    if ws_core := _get_workspace_core_md(ctx):
        parts.append(ws_core)

    return warn("\n\n".join(parts), "\n\n".join(user_parts))


def _session_pointer_dir() -> Path:
    override = os.environ.get("AOPS_SESSION_POINTER_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_session_pointer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def agy_session_pointer(ctx: HookContext) -> Result | None:
    """Deliver the session-start pointer on agy once per conversation if SessionStart did not."""
    if ctx.client != "agy" or not ctx.session_id:
        return None
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
    marker = _session_pointer_dir() / f"{safe_session}.delivered"
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
    return warn(pointer_text)


def _prepare_tracer_data(ctx: HookContext) -> dict[str, Any]:
    """Extract and normalize payload dictionary for claude_code_tracer."""
    data = dict(ctx.raw)
    if ctx.session_id:
        data.setdefault("session_id", ctx.session_id)
        data.setdefault("conversationId", ctx.session_id)
    if ctx.cwd:
        data.setdefault("cwd", ctx.cwd)
    if ctx.agent_type:
        data.setdefault("agent_type", ctx.agent_type)
    if ctx.agent_id:
        data.setdefault("agent_id", ctx.agent_id)
    if getattr(ctx, "prompt_id", None):
        data.setdefault("prompt_id", ctx.prompt_id)
    if ctx.tool:
        data.setdefault("tool_name", ctx.tool)
    if "toolName" in data and "tool_name" not in data:
        data["tool_name"] = data["toolName"]
    if "toolInput" in data and "tool_input" not in data:
        data["tool_input"] = data["toolInput"]
    if "toolResponse" in data and "tool_response" not in data:
        data["tool_response"] = data["toolResponse"]
    return data


def _run_claude_tracer(ctx: HookContext, handler_name: str) -> None:
    if claude_code_tracer is None or ctx.client != "claude":
        return
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            getattr(claude_code_tracer, handler_name)(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer %s failed: %s", handler_name, exc)


def agy_user_prompt_submit(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = agy_tracer.discover_config(data)
        if config is not None:
            agy_tracer.handle_pre_invocation(data, config)
    except Exception as exc:
        log.warning("agy_user_prompt_submit tracer failed: %s", exc)
    return None


def agy_pre_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = agy_tracer.discover_config(data)
        if config is not None:
            agy_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("agy_pre_tool tracer failed: %s", exc)
    return None


def agy_post_tool(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = agy_tracer.discover_config(data)
        if config is not None:
            agy_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("agy_post_tool tracer failed: %s", exc)
    return None


def agy_stop(ctx: HookContext) -> Result | None:
    if agy_tracer is None or ctx.client != "agy":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = agy_tracer.discover_config(data)
        if config is not None:
            agy_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("agy_stop tracer failed: %s", exc)
    return None


def telemetry_diagnostic_handler(ctx: HookContext) -> Result | None:
    """Inspect tracer state for telemetry errors and inject diagnostic notice into turn context."""
    sess_id = (
        ctx.session_id
        or ctx.raw.get("session_id")
        or ctx.raw.get("conversationId")
        or os.environ.get("AOPS_SESSION_ID")
    )
    if not sess_id:
        return None
    tracer_file = _tracer_state_dir() / f"{sess_id}.json"
    if not tracer_file.is_file():
        return None
    try:
        tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    err = tdata.get("telemetry_error")
    if not err or err.get("reported_to_session"):
        return None

    err_type = err.get("type")
    endpoint = err.get("endpoint", "unknown")

    if err_type == "auth_refusal":
        code = err.get("status_code", 401)
        diag = (
            f"ERROR: OpenTelemetry export refused by collector (HTTP {code}) at {endpoint}. "
            "Authentication invalid or expired. Telemetry spans are being dropped."
        )
    elif err_type == "server_error":
        code = err.get("status_code", 500)
        diag = (
            f"ERROR: OpenTelemetry collector returned HTTP {code} at {endpoint}. "
            "Collector is failing to ingest spans."
        )
    elif err_type == "network_error":
        net_err = err.get("error_type", "Timeout/ConnectionError")
        diag = (
            f"ERROR: OpenTelemetry export failed ({net_err}) connecting to {endpoint}. "
            "Check network route or collector health."
        )
    else:
        msg = err.get("message", "export failure")
        diag = f"ERROR: OpenTelemetry export failed at {endpoint}: {msg}"

    err["reported_to_session"] = True
    try:
        tracer_file.write_text(json.dumps(tdata), encoding="utf-8")
    except Exception:
        pass

    mode = "warn"
    if claude_code_tracer is not None:
        mode = claude_code_tracer.get_telemetry_failure_mode()
    elif os.environ.get("AOPS_TELEMETRY_FAILURE_MODE") == "block":
        mode = "block"

    if mode == "block":
        return refuse(diag, user_text=diag)
    return warn(diag, user_text=diag)


def user_prompt_submit(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical UserPromptSubmit."""
    prompt_id = (
        getattr(ctx, "prompt_id", None) or ctx.raw.get("prompt_id") or ctx.raw.get("promptId")
    )
    if not prompt_id:
        sess_id = (
            ctx.session_id
            or ctx.raw.get("session_id")
            or ctx.raw.get("conversationId")
            or os.environ.get("AOPS_SESSION_ID")
        )
        if sess_id:
            tracer_file = _tracer_state_dir() / f"{sess_id}.json"
            if tracer_file.is_file():
                try:
                    tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
                    prompt_id = (tdata.get("current_trace") or {}).get("prompt_id")
                except Exception:
                    pass
    if not prompt_id:
        prompt_id = secrets.token_hex(8)

    ctx = replace(ctx, prompt_id=prompt_id)

    _run_claude_tracer(ctx, "handle_user_prompt_submit")
    agy_user_prompt_submit(ctx)
    emit_debug_span(ctx)
    return _run_handler(agy_session_pointer, ctx)


def pre_tool(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PreToolUse."""
    _run_claude_tracer(ctx, "handle_pre_tool")
    agy_pre_tool(ctx)
    emit_debug_span(ctx)
    return None


def post_tool(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PostToolUse."""
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_post_tool")
    agy_post_tool(ctx)
    return _run_handler(telemetry_diagnostic_handler, ctx)


def post_tool_batch(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PostToolBatch."""
    emit_debug_span(ctx)
    return None


def post_tool_failure(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_post_tool_failure")
    return _run_handler(telemetry_diagnostic_handler, ctx)


def subagent_start(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical SubagentStart."""
    emit_debug_span(ctx)
    return None


def stop(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical Stop."""
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_stop")
    agy_stop(ctx)
    return _run_handler(telemetry_diagnostic_handler, ctx)


def subagent_stop(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_subagent_stop")
    return None


def stop_failure(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_stop_failure")
    return None


def permission_request(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_permission_request")
    return None


def permission_denied(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_permission_denied")
    return None


def notification(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_notification")
    return None


def pre_compact(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_pre_compact")
    return None


def post_compact(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_post_compact")
    return None


def session_end(ctx: HookContext) -> Result | None:
    emit_debug_span(ctx)
    _run_claude_tracer(ctx, "handle_session_end")
    return None


def emit_debug_span(ctx: HookContext) -> Result | None:
    """Export an aops-debug span for any hook event on every surface the hook tracer runs on."""
    if claude_code_tracer is None:
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.emit_debug_hook_span(
                data,
                config,
                client=ctx.client,
                event=ctx.event,
                raw_payload=ctx.raw,
            )
    except Exception as exc:
        log.debug("Debug hook span export failed (%s): %s", ctx.event, exc)
    return None


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [user_prompt_submit],
    "PreToolUse": [pre_tool],
    "PostToolUse": [post_tool],
    "PostToolUseFailure": [post_tool_failure],
    "PostToolBatch": [post_tool_batch],
    "SubagentStart": [subagent_start],
    "Stop": [stop],
    "SubagentStop": [subagent_stop],
    "StopFailure": [stop_failure],
    "PermissionRequest": [permission_request],
    "PermissionDenied": [permission_denied],
    "Notification": [notification],
    "PreCompact": [pre_compact],
    "PostCompact": [post_compact],
    "SessionEnd": [session_end],
}
