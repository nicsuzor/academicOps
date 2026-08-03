"""James's hook handlers."""

from __future__ import annotations

import os
import shlex
from collections.abc import Callable

from dispatch import HookContext, Result, load_message_pair, warn

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
    if any(call.get("tool_name") == "Agent" for call in ctx.get("tool_calls", [])):
        return warn(*load_message_pair(ctx.hooks_dir, "hearsay"))


def honest_output(ctx: HookContext) -> Result | None:
    """Remind agents to present substantiating evidence with their claims."""
    return warn(*load_message_pair(ctx.hooks_dir, "honesty"))


HANDLERS: dict[str, list] = {
    "SessionStart": [session_start],
    "PostToolBatch": [rule_against_hearsay],
    "Stop": [honest_output],
    "SubagentStop": [honest_output],
}
