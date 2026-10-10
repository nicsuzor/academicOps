from __future__ import annotations

"""ida hook handlers."""


import asyncio
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, block, load_message_pair, refuse, warn
from premise_check_gate import is_peer_report, premise_check_arm, premise_check_handler

Handler = Callable[[HookContext], Result | None]

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

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_NOSYSTEM",
)


# Measured 2026-09-12 (scripts/measure_pkb_injection.py, n=30 live fires
# across two prompt families): backend search latency p95 ~1.35s, median
# ~1.29s. 5s clears that with >3x margin while cutting the worst-case block
# on a stalled backend from 15s to 5s -- this hook is synchronous ahead of
# every prompt, so a hang here is a hang for the whole turn.
_SEARCH_TIMEOUT_SECONDS = 5

# Same measurement run: payload size for 5 results was 3.5-6.4KB (p95). This
# hook fires on every single UserPromptSubmit -- the highest-frequency
# injection point in the framework -- and had no ceiling of its own,
# inheriting whatever the `pkb` CLI's default result count/format produced.
# Set well above the measured p95 so normal output is never touched; it only
# bites if the backend's output grows unexpectedly large.
_MAX_INJECT_CHARS = 8000
_TRUNCATION_MARKER = "\n[...truncated, output exceeded injection budget...]"


def is_agent(ctx: HookContext | str | None, *targets: str) -> bool:
    """Check if the context or agent string matches any target agent names.

    Matches bare names (e.g. 'ida', 'james'), namespaced forms (e.g. 'ida:ida',
    'aops:james', 'plugin:ida'), prime variants (e.g. 'ida-prime',
    'ida_prime'), and colon-delimited components.
    """
    if ctx is None:
        return False
    agent = ctx.agent_type if hasattr(ctx, "agent_type") else str(ctx)
    agent = (agent or "").strip().lower()
    if not agent:
        return False
    for target in targets:
        target = target.strip().lower()
        if not target:
            continue
        if (
            agent == target
            or agent.endswith(f":{target}")
            or agent in (f"{target}-prime", f"{target}_prime")
            or f":{target}:" in agent
        ):
            return True
    return False


def is_ida(ctx: HookContext | str | None, *extra_targets: str) -> bool:
    """Check if the agent is Ida or matches any additional target names."""
    return is_agent(ctx, "ida", *extra_targets)


_is_ida = is_ida
_is_agent = is_agent


_CHANNEL_REPLY_TOOLS = {
    "telegram_reply",
    "discord_reply",
    "AskUserQuestion",
    "ask_user_question",
    "ask_question",
}


def _is_channel_reply_tool(tool_name: str) -> bool:
    if not tool_name:
        return False
    if tool_name in _CHANNEL_REPLY_TOOLS:
        return True
    name = tool_name.split("__")[-1]
    if name in _CHANNEL_REPLY_TOOLS:
        return True
    tool_lower = tool_name.lower()
    name_lower = name.lower()
    if tool_lower in (
        "telegram_reply",
        "discord_reply",
        "askuserquestion",
        "ask_user_question",
        "ask_question",
        "askquestion",
    ) or name_lower in (
        "telegram_reply",
        "discord_reply",
        "askuserquestion",
        "ask_user_question",
        "ask_question",
        "askquestion",
    ):
        return True
    if ("telegram" in tool_lower or "discord" in tool_lower) and (
        "reply" in tool_lower or "send" in tool_lower
    ):
        return True
    return False


def _channel_gate_state_dir() -> Path:
    override = os.environ.get("AOPS_CHANNEL_GATE_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_channel_gate"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _channel_gate_state_path(session_id: str) -> Path:
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", session_id or "default")
    return _channel_gate_state_dir() / f"{safe_session}.json"


def clear_channel_gate_state(session_id: str | None = None) -> None:
    if session_id:
        target = _channel_gate_state_path(session_id)
        if target.exists():
            try:
                target.unlink()
            except OSError:
                pass
    else:
        state_dir = _channel_gate_state_dir()
        if state_dir.exists():
            for p in state_dir.glob("*.json"):
                try:
                    p.unlink()
                except OSError:
                    pass


def honest_output(ctx: HookContext) -> Result | None:
    """Remind all agents to present substantiating evidence on stop, blocking once."""
    if ctx.raw.get("background_tasks"):
        return None

    return block(*load_message_pair(ctx.hooks_dir, "honesty"))


def _cap_output(out: str) -> str:
    """Bound injected payload size, independent of what the backend returns.

    A per-turn hook has no natural upper limit from its caller -- the CLI's
    own result count and formatting decide payload size today. This is the
    hook's own ceiling, not a substitute for the backend returning a
    reasonable number of results.
    """
    if len(out) <= _MAX_INJECT_CHARS:
        return out
    cutoff = _MAX_INJECT_CHARS - len(_TRUNCATION_MARKER)
    return out[:cutoff].rstrip() + _TRUNCATION_MARKER


def extract_prompt_query(prompt: str) -> str:
    """Extract the searchable user text from a prompt, unwrapping channel envelopes.

    A prompt that begins with a `<channel ...>` envelope (Telegram or another
    channel) is unwrapped to its body; any other prompt is used as typed. ANSI
    escape codes are removed and surrounding whitespace stripped.
    """
    if not prompt:
        return ""
    m = re.match(r"\s*<channel\b[^>]*>(.*?)(?:</channel>|$)", prompt, flags=re.DOTALL)
    text = m.group(1) if m else prompt
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()


def _resolve_mcp_headers() -> dict[str, str]:
    """HTTP headers for the PKB endpoint, from the environment only.

    `PKB_MCP_HEADERS` is a JSON object of header name to value.
    `CF_ACCESS_CLIENT_ID` and `CF_ACCESS_CLIENT_SECRET` together supply the
    Cloudflare Access service-token headers. A malformed `PKB_MCP_HEADERS` is
    logged and ignored, never silently swallowed.
    """
    headers: dict[str, str] = {}

    env_headers = os.environ.get("PKB_MCP_HEADERS")
    if env_headers:
        try:
            parsed = json.loads(env_headers)
        except json.JSONDecodeError as exc:
            log.warning("PKB_MCP_HEADERS is not valid JSON, ignoring it: %s", exc)
        else:
            if isinstance(parsed, dict):
                headers.update({str(k): str(v) for k, v in parsed.items()})
            else:
                log.warning("PKB_MCP_HEADERS is not a JSON object, ignoring it")

    cf_id = os.environ.get("CF_ACCESS_CLIENT_ID")
    cf_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET")
    if cf_id and cf_secret:
        headers.setdefault("CF-Access-Client-Id", cf_id)
        headers.setdefault("CF-Access-Client-Secret", cf_secret)

    return headers


async def _call_pkb_search(mcp_url: str, query: str, headers: dict[str, str]) -> str | None:
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    transport = StreamableHttpTransport(mcp_url, headers=headers)
    async with Client(transport=transport) as client:
        res = await client.call_tool("pkb_search", {"query": query})
    texts = [item.text if hasattr(item, "text") else str(item) for item in res.content]
    out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", "\n".join(texts)).strip()
    return _cap_output(out) if out else None


def _search_via_fastmcp_client(mcp_url: str, query: str, headers: dict[str, str]) -> str | None:
    """Search the PKB in-process over streamable HTTP with the given headers.

    The whole connect-and-call is bounded by `_SEARCH_TIMEOUT_SECONDS`. Any
    failure is logged and returns None; there is no second transport to try.
    """
    try:
        return asyncio.run(
            asyncio.wait_for(
                _call_pkb_search(mcp_url, query, headers), timeout=_SEARCH_TIMEOUT_SECONDS
            )
        )
    except Exception as exc:
        log.warning("PKB search over HTTP failed: %r", exc)
        return None


def _run_pkb_search(prompt: str, cwd: str | Path | None = None) -> str | None:
    query = extract_prompt_query(prompt)[:200]
    if not query:
        return None

    mcp_url = os.environ.get("PKB_MCP_URL")
    if not mcp_url:
        log.warning("PKB_MCP_URL not found for UserPromptSubmit hook")
        return None

    headers = _resolve_mcp_headers()
    if headers:
        return _search_via_fastmcp_client(mcp_url, query, headers)

    mcp_bin = shutil.which("fastmcp") or shutil.which("mcp")
    if not mcp_bin:
        log.warning("fastmcp/mcp binary not found for UserPromptSubmit hook")
        return None

    try:
        env = dict(os.environ)
        env["NO_COLOR"] = "1"
        env["AOPS_OFFLINE"] = "true"

        cmd = [
            mcp_bin,
            "call",
            mcp_url,
            "pkb__search",
            "--input-json",
            json.dumps({"query": query}),
        ]

        mcp_token = os.environ.get("PKB_MCP_TOKEN")
        if mcp_token:
            cmd.extend(["--auth", mcp_token])
        else:
            cmd.extend(["--auth", "none"])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_SEARCH_TIMEOUT_SECONDS,
            cwd=str(cwd) if cwd and Path(cwd).is_dir() else None,
            env=env,
        )
        if proc.returncode == 0:
            out = proc.stdout.strip()
            out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", out).strip()
            if out:
                return _cap_output(out)
        else:
            log.warning("mcp search exited with returncode %s: %s", proc.returncode, proc.stderr)
    except Exception as exc:
        log.warning("mcp search execution failed: %s", exc)
    return None


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    Tries first to return the output of `pkb search {prompt:200}` wrapped in
    `<academicOps PKB search results>` tags; if that fails, returns the
    existing messages. Peer reports are skipped so they trigger hearsay
    and premise check gates instead of hydrating from the PKB.
    """
    if is_peer_report(ctx):
        return None

    raw_prompt = ctx.raw.get("prompt")
    if raw_prompt is None and hasattr(ctx, "prompt"):
        raw_prompt = ctx.prompt
    if isinstance(raw_prompt, dict):
        raw_prompt = raw_prompt.get("text") or raw_prompt.get("content") or ""
    prompt_str = str(raw_prompt or "").strip()

    query = extract_prompt_query(prompt_str)
    if query:
        output = _run_pkb_search(query, cwd=ctx.cwd)
        if output:
            msg = f"<academicOps PKB search results>\n{output}\n</academicOps PKB search results>"
            return warn(msg)

    if is_agent(ctx, "ida", "sara", "james"):
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


def be_quiet(ctx: HookContext) -> Result | None:
    """Remind Ida Prime to strip its reply down to what is load-bearing on stop."""
    if not _is_ida(ctx):
        return None
    if ctx.raw.get("background_tasks"):
        return None
    return block(*load_message_pair(ctx.hooks_dir, "quiet"))


def quiet_channel_reply(ctx: HookContext) -> Result | None:
    """Deny channel replies once for Ida Prime to enforce honesty and ADHD executive protection."""
    if not _is_ida(ctx):
        return None
    if not _is_channel_reply_tool(ctx.tool):
        return None

    state_path = _channel_gate_state_path(ctx.session_id)
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            if data.get("blocked_once"):
                return None
        except Exception:
            pass

    try:
        state_path.write_text(
            json.dumps({"blocked_once": True, "tool": ctx.tool}), encoding="utf-8"
        )
    except Exception:
        pass

    honesty_inject, honesty_user = load_message_pair(ctx.hooks_dir, "honesty")
    quiet_inject, quiet_user = load_message_pair(ctx.hooks_dir, "quiet")

    inject_parts = [p for p in (honesty_inject, quiet_inject) if p]
    combined_inject = "\n\n".join(inject_parts)

    user_parts = [u for u in (honesty_user, quiet_user) if u]
    combined_user = "\n\n".join(user_parts) if user_parts else None

    if ctx.client == "agy":
        return warn(combined_inject, combined_user)

    return refuse(combined_inject, combined_user)


channel_reply_gate = quiet_channel_reply


def _scrub(value: object) -> str:
    """Neutralise characters that let a client-supplied value forge a field."""
    return " ".join(str(value).split()).replace("|", "")


def _format_session_metadata(ctx: HookContext) -> str:
    now = datetime.now().astimezone()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S %z")

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = ""

    session_id = ctx.session_id or ctx.raw.get("session_id") or ctx.raw.get("conversationId") or ""
    cwd = ctx.cwd or ctx.raw.get("cwd") or ""

    pkb_version = os.environ.get("PKB_VERSION") or ctx.raw.get("pkb_version") or "unknown"

    parts = [
        f"session: {_scrub(session_id)}" if session_id else "session: unknown",
        f"time: {time_str}",
        f"host: {_scrub(hostname)}" if hostname else "host: unknown",
        f"cwd: {_scrub(cwd)}" if cwd else "cwd: unknown",
    ]
    parts.append(f"pkb: {_scrub(pkb_version)}")

    plugin_ver = (
        os.environ.get("AOPS_IMAGE_PLUGINS_VERSION")
        or ctx.raw.get("plugins")
        or ctx.raw.get("plugins_version")
    )
    if plugin_ver:
        parts.append(f"plugins: {_scrub(str(plugin_ver))}")

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

    The premise-check gate keys its state by the hook payload's session id,
    so the verdict script run from this session's Bash must default to the
    same id. CLAUDE_ENV_FILE is sourced before every Bash command, so each
    session's own file carries its own id.
    """
    env_file_str = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file_str or not ctx.session_id:
        return False
    env_file = Path(env_file_str)
    values = _read_env_file(env_file)
    values["AOPS_SESSION_ID"] = ctx.session_id
    _write_env_file(env_file, values)
    return True


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
    _export_session_id(ctx)

    injected = _get_injected_files(ctx)
    if injected:
        files_str = "Injected context files:\n" + "\n".join(injected)
        parts.append(files_str)
        user_parts.append(files_str)

    return warn("\n\n".join(parts), "\n\n".join(user_parts))


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind Ida and Sara that an incoming peer report is hearsay; the user's own messages are not."""
    clear_channel_gate_state(ctx.session_id)
    if not is_agent(ctx, "ida", "sara"):
        return None
    if not is_peer_report(ctx):
        return None
    return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


def _prepare_tracer_data(ctx: HookContext) -> dict[str, Any]:
    """Extract and normalize payload dictionary for claude_code_tracer."""
    data = dict(ctx.raw)
    if ctx.session_id:
        data.setdefault("session_id", ctx.session_id)
    if ctx.cwd:
        data.setdefault("cwd", ctx.cwd)
    if ctx.agent_type:
        data.setdefault("agent_type", ctx.agent_type)
    if ctx.agent_id:
        data.setdefault("agent_id", ctx.agent_id)
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
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.handle_user_prompt_submit(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer user_prompt_submit failed: %s", exc)
    return None


def pre_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer pre_tool failed: %s", exc)
    return None


def post_tool(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool failed: %s", exc)
    return None


def post_tool_failure(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.handle_post_tool_failure(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer post_tool_failure failed: %s", exc)
    return None


def stop(ctx: HookContext) -> Result | None:
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        data = _prepare_tracer_data(ctx)
        config = claude_code_tracer.discover_config(data)
        if config is not None:
            claude_code_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("claude_code_tracer stop failed: %s", exc)
    return None


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


def subagent_stop(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_subagent_stop")
    return None


def stop_failure(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_stop_failure")
    return None


def permission_request(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_permission_request")
    return None


def permission_denied(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_permission_denied")
    return None


def notification(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_notification")
    return None


def pre_compact(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_pre_compact")
    return None


def post_compact(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_post_compact")
    return None


def session_end(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_session_end")
    return None


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


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [
        user_prompt_submit,
        agy_user_prompt_submit,
        search_the_pkb,
        rule_against_hearsay,
        premise_check_arm,
    ],
    "PreToolUse": [h for h in (pre_tool, agy_pre_tool, premise_check_handler) if h is not None],
    "PostToolUse": [post_tool, agy_post_tool, premise_check_arm],
    "PostToolUseFailure": [post_tool_failure],
    "PostToolBatch": [premise_check_arm],
    "Stop": [stop, agy_stop, premise_check_handler],
    "SubagentStop": [subagent_stop],
    "StopFailure": [stop_failure],
    "PermissionRequest": [permission_request],
    "PermissionDenied": [permission_denied],
    "Notification": [notification],
    "PreCompact": [pre_compact],
    "PostCompact": [post_compact],
    "SessionEnd": [session_end],
}
