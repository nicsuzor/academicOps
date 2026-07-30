"""aops hook handlers.

Registered against the canonical event names and loaded by the shared runtime in
``dispatch.py``.
"""

from __future__ import annotations

import os
import shlex
from collections.abc import Callable

from dispatch import HookContext, Result, refuse, warn

Handler = Callable[[HookContext], Result | None]

_INTERACTIVE_TOOLS = frozenset(
    {
        "AskUserQuestion",
        "ask_question",
        "AskFollowupQuestion",
        "ask_followup_question",
        "Question",
    }
)

_HEADLESS_ENV = (
    "NONINTERACTIVE",
    "CI",
    "AOPS_POLECAT_CONTAINER",
    "CLAUDE_CODE_NON_INTERACTIVE",
)

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


def _isolate_credentials(ctx: HookContext) -> bool:
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return False

    persist: dict[str, str] = {}
    if ctx.session_id:
        persist["AOPS_SESSION_ID"] = ctx.session_id

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
        # simplified git config logic
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


def present_checkable_evidence(ctx: HookContext) -> Result | None:
    if ctx.raw.get("stop_hook_active") or ctx.raw.get("background_tasks"):
        return None
    return warn(
        "You are stopping. Please ensure you have presented checkable evidence.",
        "Ensure evidence is presented.",
    )


def _is_headless() -> bool:
    return any(os.environ.get(name) == "1" for name in _HEADLESS_ENV)


def refuse_interactive_prompt_when_headless(ctx: HookContext) -> Result | None:
    if ctx.tool not in _INTERACTIVE_TOOLS:
        return None
    if not _is_headless():
        return None
    return refuse(
        f"Interactive tool {ctx.tool} cannot be used in a headless session. Please proceed automatically.",
        f"Refused {ctx.tool} (headless)",
    )


HANDLERS: dict[str, list[Handler]] = {
    "SessionStart": [session_start],
    "PreToolUse": [refuse_interactive_prompt_when_headless],
    "SubagentStop": [present_checkable_evidence],
    "Stop": [present_checkable_evidence],
}
