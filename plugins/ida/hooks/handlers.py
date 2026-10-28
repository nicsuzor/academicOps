from __future__ import annotations

"""ida hook handlers."""


import json
import logging
import os
import re
import secrets
import shlex
import socket
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import (
    HookContext,
    Result,
    _merge,
    _run_handler,
    load_message_pair,
    warn,
)
from hearsay_gate import (
    hearsay_arm,
    hearsay_handler,
    prompt_text,
    should_arm_hearsay,
)
from hearsay_gate import (
    is_peer_report as is_peer_report,
)

premise_check_arm = hearsay_arm
premise_check_handler = hearsay_handler

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
# injection point in the framework -- and has no ceiling of its own beyond
# the backend's default result count and format. Set well above the measured p95 so normal output is never touched; it only
# bites if the backend's output grows unexpectedly large.
_MAX_INJECT_CHARS = 8000
_TRUNCATION_MARKER = "\n[...truncated, output exceeded injection budget...]"
_MAX_QUERY_CHARS = 8192
_DEFAULT_SEARCH_LIMIT = 5
_DEFAULT_SEARCH_DETAIL = "snippet"

_PEER_PREAMBLE = re.compile(
    r"^(?:Another Claude session sent a message:\s*)+",
    re.IGNORECASE,
)

_ENVELOPE_RE = re.compile(
    r"^\s*<(?:channel|cross-session-message|teammate-message|task-notification|subagent-handback|agent-message|handback)\b[^>]*>(.*?)(?:</[^>]+>|\s*$)",
    re.DOTALL,
)


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


def honest_output(ctx: HookContext) -> Result | None:
    """Remind subagents on SubagentStart to write reports in premise-check shape."""
    if ctx.event != "SubagentStart" or ctx.raw.get("background_tasks"):
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


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
    """Extract searchable text from a prompt, unwrapping channel and message envelopes.

    Unwraps <channel ...> envelopes, peer envelopes (<cross-session-message>,
    <teammate-message>, <subagent-handback>, <task-notification>, etc.), and
    peer preambles. Prompts without envelopes are used as typed. ANSI escape
    codes are removed and surrounding whitespace stripped.

    Skips argument-less slash commands (/cmd) by returning an empty string so
    no PKB search runs. Slash commands with arguments (/cmd <arg>) send <arg>
    whole up to 8 KB.
    """
    if not prompt:
        return ""
    text = prompt
    while True:
        pm = _PEER_PREAMBLE.match(text)
        if pm:
            text = text[pm.end() :].lstrip()
        m = _ENVELOPE_RE.match(text)
        if m:
            text = m.group(1).strip()
            continue
        break

    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text).strip()
    if not text:
        return ""

    if text.startswith("/"):
        parts = text.split(None, 1)
        if len(parts) == 1:
            return ""
        arg = parts[1].strip()
        if not arg:
            return ""
        return arg[:_MAX_QUERY_CHARS]

    return text[:_MAX_QUERY_CHARS]


# Cloudflare Access service-token pairs, in order of preference. The worker
# pair comes first because it has no polecat dispatch access (Nic, tg 2369).
_ACCESS_TOKEN_PAIRS = (
    ("WORKER_MCP_TOKEN_ID", "WORKER_MCP_TOKEN_SECRET"),
    ("DISPATCHER_MCP_TOKEN_ID", "DISPATCHER_MCP_TOKEN_SECRET"),
)


def _resolve_mcp_headers() -> dict[str, str]:
    """HTTP headers for the PKB endpoint, from the environment only.

    `PKB_MCP_HEADERS` is a JSON object of header name to value.
    A Cloudflare Access service-token pair supplies the Access headers: the
    worker pair `WORKER_MCP_TOKEN_ID` / `WORKER_MCP_TOKEN_SECRET` by default,
    because it has no polecat dispatch access, else the dispatcher pair
    `DISPATCHER_MCP_TOKEN_ID` / `DISPATCHER_MCP_TOKEN_SECRET`. A malformed
    `PKB_MCP_HEADERS` is logged and ignored, never silently swallowed.
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

    for id_var, secret_var in _ACCESS_TOKEN_PAIRS:
        cf_id = os.environ.get(id_var)
        cf_secret = os.environ.get(secret_var)
        if cf_id and cf_secret:
            headers.setdefault("CF-Access-Client-Id", cf_id)
            headers.setdefault("CF-Access-Client-Secret", cf_secret)
            break

    return headers


def _tracer_state_dir() -> Path:
    env_dir = os.environ.get("TRACER_STATE_DIR") or os.environ.get("AOPS_TRACER_DIR")
    if env_dir:
        return Path(env_dir)
    if claude_code_tracer is not None and hasattr(claude_code_tracer, "STATE_DIR"):
        state_dir = Path(claude_code_tracer.STATE_DIR)
        if state_dir.is_absolute():
            try:
                return Path.home().joinpath(*state_dir.parts[-2:])
            except Exception:
                pass
        return state_dir
    return Path.home() / ".aops" / "tracer"


def _resolve_tracer_traceparent(session_id: str | None = None) -> str:
    """Resolve or generate a W3C traceparent header for the outgoing search request."""
    if session_id:
        tracer_file = _tracer_state_dir() / f"{session_id}.json"
        if tracer_file.is_file():
            try:
                data = json.loads(tracer_file.read_text(encoding="utf-8"))
                cur = data.get("current_trace") or {}
                trace_id = cur.get("trace_id")
                span_id = cur.get("root_span_id") or cur.get("span_id")
                if trace_id and span_id:
                    return f"00-{trace_id}-{span_id}-01"
            except Exception as exc:
                log.debug("Could not read tracer file for session %s: %s", session_id, exc)

    env_tp = os.environ.get("TRACEPARENT")
    if env_tp and re.match(r"^00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$", env_tp):
        return env_tp

    trace_id = secrets.token_hex(16)
    span_id = secrets.token_hex(8)
    return f"00-{trace_id}-{span_id}-01"


def _session_cache_path() -> Path:
    return _tracer_state_dir() / "pkb_session_cache.json"


def _get_cached_mcp_session(cache_path: Path | None = None) -> str | None:
    path = cache_path or _session_cache_path()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ts = data.get("timestamp", 0)
                if time.time() - float(ts) < 86400:
                    return data.get("session_id")
        except Exception as exc:
            log.debug("Could not read PKB session cache: %s", exc)
    return None


def _save_cached_mcp_session(session_id: str, cache_path: Path | None = None) -> None:
    path = cache_path or _session_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"session_id": session_id, "timestamp": time.time()}),
            encoding="utf-8",
        )
    except Exception as exc:
        log.warning("Could not write PKB session cache: %s", exc)


def _parse_mcp_response(raw_body: str) -> str | None:
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        data = None
        for line in raw_body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    payload = json.loads(line[5:].strip())
                    if isinstance(payload, dict):
                        if "error" in payload:
                            raise RuntimeError(f"PKB MCP error: {payload['error']}")
                        if "result" in payload:
                            data = payload
                            break
                except json.JSONDecodeError:
                    continue
        if data is None:
            return None

    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"PKB MCP error: {data['error']}")

    result = data.get("result", {})
    content = result.get("content", [])
    texts = []
    for item in content:
        if isinstance(item, dict):
            text = item.get("text", "")
            if text:
                texts.append(text)
        else:
            texts.append(str(item))

    out = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", "\n".join(texts)).strip()
    return _cap_output(out) if out else None


def _initialize_mcp_session(mcp_url: str, base_headers: dict[str, str]) -> str | None:
    init_headers = dict(base_headers)
    init_headers.pop("mcp-session-id", None)
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "academicOps", "version": "0.10"},
        },
    }
    data_bytes = json.dumps(init_payload).encode("utf-8")
    req = urllib.request.Request(mcp_url, data=data_bytes, headers=init_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_SEARCH_TIMEOUT_SECONDS) as resp:
            sess_id = resp.headers.get("mcp-session-id")
            if sess_id:
                _save_cached_mcp_session(sess_id)
                return sess_id
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError(
                f"the PKB endpoint refused authorisation (HTTP {exc.code}); check PKB_MCP_HEADERS, WORKER_MCP_TOKEN_ID / WORKER_MCP_TOKEN_SECRET, or DISPATCHER_MCP_TOKEN_ID / DISPATCHER_MCP_TOKEN_SECRET"
            ) from exc
        raise RuntimeError(
            f"the PKB endpoint failed with HTTP {exc.code} during initialize: {exc.reason}"
        ) from exc
    except TimeoutError as exc:
        raise TimeoutError(
            f"the PKB endpoint did not answer within {_SEARCH_TIMEOUT_SECONDS} seconds"
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise TimeoutError(
                f"the PKB endpoint did not answer within {_SEARCH_TIMEOUT_SECONDS} seconds"
            ) from exc
        raise RuntimeError(f"the PKB endpoint is unreachable ({mcp_url}): {exc.reason}") from exc
    return None


def _resolve_surface(ctx: HookContext | None = None) -> str:
    """Resolve the execution surface class."""
    if env_surface := os.environ.get("AOPS_SURFACE"):
        return env_surface
    if os.environ.get("GITHUB_ACTIONS"):
        return "github-actions"
    if ctx and getattr(ctx, "client", "") == "agy":
        return "agy"
    if os.environ.get("ANTIGRAVITY_CLI") or os.environ.get("GEMINI_CLI"):
        return "agy"
    return "claude-code"


def _post_mcp_search(
    mcp_url: str,
    query: str,
    headers: dict[str, str] | None = None,
    session_id: str | None = None,
    traceparent: str | None = None,
    prompt_id: str | None = None,
    agent_id: str | None = None,
    surface: str | None = None,
    limit: int = _DEFAULT_SEARCH_LIMIT,
    detail: str = _DEFAULT_SEARCH_DETAIL,
) -> str | None:
    """Search the PKB over a single streamable-HTTP POST to PKB_MCP_URL."""
    sess_id = session_id if session_id is not None else (os.environ.get("AOPS_SESSION_ID") or "")
    tp = traceparent or _resolve_tracer_traceparent(sess_id)

    pid = prompt_id or ""
    if not pid and sess_id:
        tracer_file = _tracer_state_dir() / f"{sess_id}.json"
        if tracer_file.is_file():
            try:
                tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
                pid = (tdata.get("current_trace") or {}).get("prompt_id") or ""
            except Exception:
                pass
    if not pid:
        pid = secrets.token_hex(8)

    if sess_id:
        tracer_file = _tracer_state_dir() / f"{sess_id}.json"
        if tracer_file.is_file():
            try:
                tdata = json.loads(tracer_file.read_text(encoding="utf-8"))
                cur = tdata.get("current_trace")
                if isinstance(cur, dict) and cur.get("prompt_id") != pid:
                    cur["prompt_id"] = pid
                    tracer_file.write_text(json.dumps(tdata), encoding="utf-8")
            except Exception as exc:
                log.debug(
                    "Could not update prompt_id in tracer file for session %s: %s", sess_id, exc
                )

    req_headers: dict[str, str] = {
        "User-Agent": "academicOps/0.10 (prompt-hydration)",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "x-session-id": sess_id,
        "traceparent": tp,
    }
    if headers:
        for k, v in headers.items():
            req_headers[k] = v

    cached_session = _get_cached_mcp_session()
    if cached_session:
        req_headers["mcp-session-id"] = cached_session

    prefix = os.environ.get("PKB_MCP_TOOL_PREFIX", "pkb_")
    tool_name = f"{prefix}search"
    session_payload = {
        "session_id": sess_id,
        "prompt_id": pid,
        "agent_id": agent_id or "",
        "caller": "hook",
        "surface": surface or _resolve_surface(),
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "query": query,
                "limit": limit,
                "detail": detail,
                "_session": session_payload,
            },
        },
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    def _execute_post(hdrs: dict[str, str]) -> tuple[int, str]:
        req = urllib.request.Request(mcp_url, data=data_bytes, headers=hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=_SEARCH_TIMEOUT_SECONDS) as resp:
                status = resp.status if hasattr(resp, "status") else resp.getcode()
                body = resp.read().decode("utf-8", errors="replace")
                return status, body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return exc.code, body
        except TimeoutError as exc:
            raise TimeoutError(
                f"the PKB endpoint did not answer within {_SEARCH_TIMEOUT_SECONDS} seconds"
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError(
                    f"the PKB endpoint did not answer within {_SEARCH_TIMEOUT_SECONDS} seconds"
                ) from exc
            raise RuntimeError(
                f"the PKB endpoint is unreachable ({mcp_url}): {exc.reason}"
            ) from exc

    status, body = _execute_post(req_headers)

    if status in (401, 403):
        raise RuntimeError(
            f"the PKB endpoint refused authorisation (HTTP {status}); check PKB_MCP_HEADERS, WORKER_MCP_TOKEN_ID / WORKER_MCP_TOKEN_SECRET, or DISPATCHER_MCP_TOKEN_ID / DISPATCHER_MCP_TOKEN_SECRET"
        )

    session_needed = False
    err_obj = None

    try:
        parsed = json.loads(body)
        if isinstance(parsed, dict) and "error" in parsed:
            err_obj = parsed["error"]
    except json.JSONDecodeError:
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    payload = json.loads(line[5:].strip())
                    if isinstance(payload, dict) and "error" in payload:
                        err_obj = payload["error"]
                        break
                except json.JSONDecodeError:
                    continue

    if err_obj is not None:
        err_msg = str(err_obj).lower()
        if "session" in err_msg:
            session_needed = True
        elif status == 200:
            raise RuntimeError(f"PKB MCP error: {err_obj}")

    if session_needed:
        new_session = _initialize_mcp_session(mcp_url, req_headers)
        if new_session:
            req_headers["mcp-session-id"] = new_session
            status, body = _execute_post(req_headers)
            if status in (401, 403):
                raise RuntimeError(
                    f"the PKB endpoint refused authorisation (HTTP {status}); check PKB_MCP_HEADERS, WORKER_MCP_TOKEN_ID / WORKER_MCP_TOKEN_SECRET, or DISPATCHER_MCP_TOKEN_ID / DISPATCHER_MCP_TOKEN_SECRET"
                )
            if status != 200:
                clean_body = " ".join(body.split())
                raise RuntimeError(f"the PKB endpoint failed with HTTP {status}: {clean_body}")
        else:
            clean_body = " ".join(body.split())
            raise RuntimeError(
                f"the PKB endpoint requires session initialization but initialize failed: HTTP {status} {clean_body}"
            )
    elif status != 200:
        clean_body = " ".join(body.split())
        raise RuntimeError(f"the PKB endpoint failed with HTTP {status}: {clean_body}")

    return _parse_mcp_response(body)


def _run_pkb_search(
    prompt: str,
    cwd: str | Path | None = None,
    session_id: str | None = None,
    traceparent: str | None = None,
    prompt_id: str | None = None,
    agent_id: str | None = None,
    surface: str | None = None,
    limit: int | None = None,
    detail: str | None = None,
) -> str | None:
    query = extract_prompt_query(prompt)[:_MAX_QUERY_CHARS]
    if not query:
        return None

    mcp_url = os.environ.get("PKB_MCP_URL")
    if not mcp_url:
        log.warning("PKB_MCP_URL not found for UserPromptSubmit hook")
        return None

    headers = _resolve_mcp_headers()
    kwargs: dict[str, Any] = {}
    if session_id is not None:
        kwargs["session_id"] = session_id
    if traceparent is not None:
        kwargs["traceparent"] = traceparent
    if prompt_id is not None:
        kwargs["prompt_id"] = prompt_id
    if agent_id is not None:
        kwargs["agent_id"] = agent_id
    if surface is not None:
        kwargs["surface"] = surface
    if limit is not None:
        kwargs["limit"] = limit
    if detail is not None:
        kwargs["detail"] = detail

    if kwargs:
        return _post_mcp_search(mcp_url, query, headers, **kwargs)
    return _post_mcp_search(mcp_url, query, headers)


def search_the_pkb(ctx: HookContext) -> Result | None:
    """Ground every prompt in the PKB before the agent acts on it.

    Returns the output of `pkb search {prompt}` wrapped in
    `<academicOps PKB search results>` tags when matches are found;
    otherwise returns None. Empty results inject nothing.
    Argument-less slash commands are skipped so they make no PKB call.
    Peer reports, subagent handbacks, task notifications, and incoming channel
    messages are searched to ground the turn in existing PKB context.
    """
    prompt_str = prompt_text(ctx)
    query = extract_prompt_query(prompt_str)
    if not query:
        return None

    session_id = (
        getattr(ctx, "session_id", None)
        or ctx.raw.get("session_id")
        or ctx.raw.get("conversationId")
        or os.environ.get("AOPS_SESSION_ID")
        or None
    )
    prompt_id = (
        getattr(ctx, "prompt_id", None)
        or ctx.raw.get("prompt_id")
        or ctx.raw.get("promptId")
        or None
    )
    agent_id = getattr(ctx, "agent_id", None) or ctx.raw.get("agent_id") or None

    search_kwargs: dict[str, Any] = {"cwd": ctx.cwd}
    if session_id:
        search_kwargs["session_id"] = session_id
    if prompt_id:
        search_kwargs["prompt_id"] = prompt_id
    if agent_id:
        search_kwargs["agent_id"] = agent_id

    output = _run_pkb_search(query, **search_kwargs)
    if output and output.strip():
        msg = f"<academicOps PKB search results>\n{output}\n</academicOps PKB search results>"
        return warn(msg)

    return None


def _scrub(value: object) -> str:
    """Neutralise characters that let a client-supplied value forge a field."""
    return " ".join(str(value).split()).replace("|", "")


def _resolve_plugin_version(ctx: HookContext) -> str | None:
    """Resolve the installed plugin version from env or manifest."""
    if ver := os.environ.get("AOPS_IMAGE_PLUGINS_VERSION"):
        return ver.strip()
    if ctx.hooks_dir:
        manifest_file = ctx.hooks_dir.parent / ".claude-plugin" / "plugin.json"
        if manifest_file.is_file():
            data = json.loads(manifest_file.read_text(encoding="utf-8"))
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


PREMISE_CHECK_POINTER = (
    "Reports follow `premise-check`: written in its shape and checked on receipt."
)


def session_start(ctx: HookContext) -> Result | None:
    """Handle SessionStart for Claude Code and SessionStart for agy."""
    metadata = _format_session_metadata(ctx)
    parts = [
        metadata,
        PREMISE_CHECK_POINTER,
    ]
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


def _session_pointer_dir() -> Path:
    override = os.environ.get("AOPS_SESSION_POINTER_DIR")
    path = Path(override) if override else Path(tempfile.gettempdir()) / "aops_session_pointer"
    path.mkdir(parents=True, exist_ok=True)
    return path


def agy_session_pointer(ctx: HookContext) -> Result | None:
    """Deliver the session-start pointer on agy, once per conversation.

    The agy hooks are wired without SessionStart, so the pointer rides on the
    first PreInvocation that reaches this conversation. ``invocationNum``
    restarts at 0 on every turn and ``initialNumSteps`` starts above 1 in IDE
    conversations, so neither marks the first one; a marker file keyed by the
    conversation id does.
    """
    if ctx.client != "agy" or not ctx.session_id:
        return None
    safe_session = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", ctx.session_id)
    marker = _session_pointer_dir() / f"{safe_session}.delivered"
    try:
        with marker.open("x", encoding="utf-8") as f:
            f.write(datetime.now().astimezone().isoformat())
    except FileExistsError:
        return None
    return warn(PREMISE_CHECK_POINTER)


honesty_on_peer_message = honest_output


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind agents that an incoming peer report or foreground subagent return is hearsay."""
    if not should_arm_hearsay(ctx):
        return None
    return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


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


def post_tool_degraded_check(ctx: HookContext) -> Result | None:
    """Detect degraded capability flags in tool results and warn."""
    tool_resp = ctx.raw.get("tool_response") or ctx.raw.get("toolResponse")
    if not tool_resp:
        return None

    if isinstance(tool_resp, str):
        try:
            tool_resp = json.loads(tool_resp)
        except Exception:
            return None

    if not isinstance(tool_resp, dict):
        return None

    has_degraded = False
    details = []
    if tool_resp.get("voiceSent") is False or tool_resp.get("voiceError"):
        has_degraded = True
        err = tool_resp.get("voiceError") or "voiceSent is false"
        details.append(f"voiceError: {err}")

    for k, v in tool_resp.items():
        if k.endswith("_error") and v:
            has_degraded = True
            details.append(f"{k}: {v}")

    if has_degraded:
        msg_template, user_template = load_message_pair(ctx.hooks_dir, "degraded_capability")
        if not msg_template:
            msg_template = (
                "Degraded capability failure detected in tool response. Under `halt-on-failure` and `fail-fast`:\n"
                "- Do not silently swallow this degradation or treat the action as fully successful.\n"
                "- Required: Report the capability failure verbatim to the user and invoke /learn to diagnose the root cause (do not create tasks)."
            )
        inject_text = f"{msg_template}\n\nDegraded output details:\n" + "\n".join(
            f"- {d}" for d in details
        )
        return warn(inject_text, user_template)

    return None


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

    from dataclasses import replace

    ctx = replace(ctx, prompt_id=prompt_id)

    _run_claude_tracer(ctx, "handle_user_prompt_submit")
    agy_user_prompt_submit(ctx)
    steps = (
        agy_session_pointer,
        search_the_pkb,
        rule_against_hearsay,
        hearsay_arm,
    )
    return _merge([_run_handler(step, ctx) for step in steps])


def pre_tool(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PreToolUse."""
    _run_claude_tracer(ctx, "handle_pre_tool")
    agy_pre_tool(ctx)
    return _run_handler(hearsay_handler, ctx)


def post_tool(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PostToolUse."""
    _run_claude_tracer(ctx, "handle_post_tool")
    agy_post_tool(ctx)
    steps = (
        post_tool_degraded_check,
        hearsay_arm,
    )
    return _merge([_run_handler(step, ctx) for step in steps])


def post_tool_batch(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical PostToolBatch."""
    return _run_handler(rule_against_hearsay, ctx)


def post_tool_failure(ctx: HookContext) -> Result | None:
    _run_claude_tracer(ctx, "handle_post_tool_failure")
    return None


def subagent_start(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical SubagentStart."""
    return _run_handler(honest_output, ctx)


def stop(ctx: HookContext) -> Result | None:
    """Single entry-point handler for canonical Stop."""
    _run_claude_tracer(ctx, "handle_stop")
    agy_stop(ctx)
    return _run_handler(hearsay_handler, ctx)


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
