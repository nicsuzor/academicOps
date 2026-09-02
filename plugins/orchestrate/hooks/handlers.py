"""James's hook handlers."""

from __future__ import annotations

import json
import logging
import os
import shlex
import socket
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from dispatch import HookContext, Result, load_message_pair, warn

log = logging.getLogger("orchestrate.handlers")

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
    from task_body_gate import task_body_gate_handler
except ImportError:
    task_body_gate_handler = None

try:
    from premise_check_gate import premise_check_gate_handler, premise_check_open_gate
except ImportError:
    premise_check_gate_handler = None
    premise_check_open_gate = None

Handler = Callable[[HookContext], Result | None]

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


def _scrub(value: object) -> str:
    """Neutralise the two characters that let a client-supplied value forge a field.

    The metadata line is a single line of ``key: value`` pairs joined by ``" | "``,
    and both halves of it are read by an agent. Every value in it comes from the
    hook payload, so a ``cwd`` of ``/a | host: fake`` would render as a genuine
    ``host`` field, and a newline would end the line early. Whitespace collapses
    to single spaces and the delimiter is dropped outright, which is enough:
    without a ``|`` no value can produce the separator at all.
    """
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


def _isolate_credentials(ctx: HookContext) -> bool:
    # <!-- NS: better make this work for agy too. -->
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return False

    persist: dict[str, str] = {}
    if ctx.session_id:
        persist["AOPS_SESSION_ID"] = ctx.session_id

    # Clean ENV of potentially leaking credentials
    for var in _BASIC_VARS:
        val = os.environ.get(var)
        if val is not None:
            persist[var] = val

    bot_token = os.environ.get("AOPS_BOT_GH_TOKEN")
    if bot_token:
        persist.setdefault("GH_TOKEN", bot_token)
        persist.setdefault("GITHUB_TOKEN", bot_token)
        persist.setdefault(
            "GIT_SSH_COMMAND",
            "ssh -o IdentityAgent=none -o IdentitiesOnly=yes -o IdentityFile=/dev/null",
        )
        # simplified git config logic -- restrict access to SSH identity
        persist["GIT_CONFIG_COUNT"] = "4"
        persist["GIT_CONFIG_KEY_0"] = "url.https://github.com/.insteadOf"
        persist["GIT_CONFIG_VALUE_0"] = "git@github.com:"
        persist["GIT_CONFIG_KEY_1"] = "url.https://github.com/.insteadOf"
        persist["GIT_CONFIG_VALUE_1"] = "ssh://git@github.com/"
        persist["GIT_CONFIG_KEY_2"] = "credential.https://github.com.helper"
        persist["GIT_CONFIG_VALUE_2"] = ""
        persist["GIT_CONFIG_KEY_3"] = "credential.https://github.com.helper"
        persist["GIT_CONFIG_VALUE_3"] = (
            f'!f() {{ test "$1" = get && printf "username=x-access-token\\npassword=%s\\n" "{bot_token}"; }}; f'
        )

    try:
        with open(env_file, "a") as f:
            for key, value in persist.items():
                f.write(f"export {key}={shlex.quote(value)}\n")
        return True
    except OSError:
        return False


def _get_injected_files(ctx: HookContext) -> list[str]:
    injected = []
    cwd = Path(ctx.cwd) if ctx.cwd else Path.cwd()

    # Plugin scope
    plugin_dir = ctx.hooks_dir.parent.parent
    axioms_dir = plugin_dir / "rbg" / "axioms"
    if axioms_dir.exists():
        injected.append(f" - {axioms_dir.name}/*.md (plugin)")
    elif (plugin_dir.parent / "lib" / "axioms").exists():
        injected.append(" - lib/axioms/*.md (plugin)")

    # User scope
    home = Path.home()
    user_files = [
        home / ".claude.md",
        home / ".gemini.md",
        home / ".config" / "claude" / "CLAUDE.md",
    ]
    aca_data = os.environ.get("ACA_DATA")
    if aca_data:
        aca_path = Path(aca_data)
        user_files.extend(list((aca_path / ".agents" / "rules").glob("*.md")))

    for f in user_files:
        if f.exists():
            injected.append(f" - {f.name} (user)")

    # Project scope
    project_files = [
        cwd / "CLAUDE.md",
        cwd / "GEMINI.md",
        cwd / ".claude.md",
        cwd / ".agents" / "CORE.md",
    ]

    proj_rules = cwd / ".agents" / "rules"
    if proj_rules.exists() and proj_rules.is_dir():
        project_files.extend(list(proj_rules.glob("*.md")))

    for f in project_files:
        if f.exists():
            try:
                rel = f.relative_to(cwd)
            except ValueError:
                rel = f
            injected.append(f" - {rel} (project)")

    return injected


def session_start(ctx: HookContext) -> Result | None:
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
    if ctx.agent_type in ("aops:ida", "orchestrate:james"):
        if any(call.get("tool_name") == "Agent" for call in ctx.tool_calls):
            return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))

    return None


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims.

    When enabled, injects a reminder at the start of a subagent's turn
    to provide evidence sufficient to support its claims.

    """
    if ctx.agent_type in ("aops:ida"):
        return None

    if ctx.raw.get("background_tasks"):
        # No need to do anything until the background tasks complete.
        return None

    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


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
    """Tracer hook handler for canonical UserPromptSubmit, Claude Code side.

    Registered alongside ``agy_user_prompt_submit`` under the same canonical
    ``"UserPromptSubmit"`` key (see ``HANDLERS`` below) — each guards on
    ``ctx.client`` so exactly one tracer stack emits per client, the same
    split already used for ``pre_tool``/``agy_pre_tool``.
    """
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_user_prompt_submit(data, config)
    except Exception as exc:
        log.warning("user_prompt_submit tracer failed: %s", exc)
    return None


def agy_user_prompt_submit(ctx: HookContext) -> Result | None:
    """Tracer hook handler for canonical UserPromptSubmit, agy side.

    agy's wire event is ``PreInvocation``; ``lib/hooks/dispatch.py`` maps it
    onto canonical ``UserPromptSubmit`` before handler lookup, so this must be
    registered under that canonical key — not under a ``"PreInvocation"`` key,
    which dispatch never looks up and would never fire.
    """
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


def pre_tool(ctx: HookContext) -> Result | None:
    """Tracer hook handler for PreToolUse."""
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_pre_tool(data, config)
    except Exception as exc:
        log.warning("pre_tool tracer failed: %s", exc)
    return None


def post_tool(ctx: HookContext) -> Result | None:
    """Tracer hook handler for PostToolUse."""
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool(data, config)
    except Exception as exc:
        log.warning("post_tool tracer failed: %s", exc)
    return None


def post_tool_failure(ctx: HookContext) -> Result | None:
    """Tracer hook handler for PostToolUseFailure."""
    if claude_code_tracer is None or ctx.client != "claude":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_post_tool_failure(data, config)
    except Exception as exc:
        log.warning("post_tool_failure tracer failed: %s", exc)
    return None


def stop(ctx: HookContext) -> Result | None:
    """Tracer hook handler for Stop."""
    if claude_code_tracer is None or ctx.client == "agy":
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("stop tracer failed: %s", exc)
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
    """OTel turn-close for agy.

    Fires only from agy's genuine ``Stop`` wire event now: ``dispatch.py``'s
    ``TO_CANONICAL["agy"]["PostInvocation"]`` no longer aliases onto this
    canonical ``"Stop"`` key (see the comment there for why — it fired once
    per internal invocation/tool-call round-trip, not once per turn, and
    every extra fire made ``handle_stop`` below build and export a CHAIN
    span, then delete ``current_trace``, before the model had produced its
    final response, fragmenting one turn into several incomplete traces —
    aops_73e25af2). No payload-shape guard is needed here any more: a
    premature, per-invocation fire is no longer reachable.
    """
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
    # Both clients register here: agy's wire event is PreInvocation, which
    # dispatch.py's TO_CANONICAL maps onto this canonical key before handler
    # lookup runs — a "PreInvocation" registration here would never fire.
    "UserPromptSubmit": [user_prompt_submit, agy_user_prompt_submit, honest_output],
    "PreToolUse": [
        h
        for h in (pre_tool, agy_pre_tool, task_body_gate_handler, premise_check_gate_handler)
        if h is not None
    ],
    "PostToolUse": [post_tool, agy_post_tool],
    "PostToolUseFailure": [post_tool_failure],
    # Both clients register here: agy's wire event is its own "Stop" (not
    # PostInvocation — dispatch.py's TO_CANONICAL no longer aliases that
    # one onto anything; see the comment there).
    "Stop": [stop, agy_stop],
    "PostToolBatch": [h for h in (rule_against_hearsay, premise_check_open_gate) if h is not None],
    "SubagentStart": [honest_output],
}
