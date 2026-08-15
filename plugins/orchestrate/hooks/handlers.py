"""James's hook handlers."""

from __future__ import annotations

import logging
import os
import shlex
from collections.abc import Callable
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

Handler = Callable[[HookContext], Result | None]

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


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


def session_start(ctx: HookContext) -> Result | None:
    parts = ["aops hook: Session started."]
    user_parts = []

    if _isolate_credentials(ctx):
        parts.append("Credentials have been isolated in CLAUDE_ENV_FILE.")
        user_parts.append("Credentials isolated.")

    return warn("\n\n".join(parts), " ".join(user_parts) or None)


def rule_against_hearsay(ctx: HookContext) -> Result | None:
    """Remind the dispatcher that a subagent's report is not evidence."""
    if any(call.get("tool_name") == "Agent" for call in ctx.tool_calls):
        return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims.

    When enabled, injects a reminder at the start of a subagent's turn
    to provide evidence sufficient to support its claims.

    """
    if ctx.agent_type == "ida:ida":
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
    """Tracer hook handler for UserPromptSubmit."""
    if claude_code_tracer is None:
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_user_prompt_submit(data, config)
    except Exception as exc:
        log.warning("user_prompt_submit tracer failed: %s", exc)
    return None


def pre_tool(ctx: HookContext) -> Result | None:
    """Tracer hook handler for PreToolUse."""
    if claude_code_tracer is None:
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
    if claude_code_tracer is None:
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
    if claude_code_tracer is None:
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
    if claude_code_tracer is None:
        return None
    try:
        config = claude_code_tracer.discover_config()
        if config is not None:
            data = _prepare_tracer_data(ctx)
            claude_code_tracer.handle_stop(data, config)
    except Exception as exc:
        log.warning("stop tracer failed: %s", exc)
    return None


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "UserPromptSubmit": [user_prompt_submit],
    "PreToolUse": [pre_tool],
    "PostToolUse": [post_tool],
    "PostToolUseFailure": [post_tool_failure],
    "Stop": [stop],
    "PostToolBatch": [rule_against_hearsay],
    "SubagentStart": [honest_output],
}
