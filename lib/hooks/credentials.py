"""Session credential configuration.

SessionStart appends to the env file the client names in ``CLAUDE_ENV_FILE``
(Claude Code creates one per session and sets the variable itself), adding a
git-credential shim that resolves push auth from ``AOPS_BOT_GH_TOKEN``.

This does not isolate anything. Every value written here is read from the
process environment and stays there: the file adds a second copy for tools the
client launches from it, it does not confine the first. Any agent-facing text
about this must say so — see
``plugins/aops/hooks/messages/session-start-isolated.md``.
"""

from __future__ import annotations

import os
import shlex
import sys
from typing import Any

_BASIC_VARS = (
    "AOPS_SESSIONS",
    "AOPS_BOT_GH_TOKEN",
    "PKB_MCP_URL",
    "PKB_MCP_TOOL_PREFIX",
)


def isolate(raw: dict[str, Any]) -> dict[str, str] | None:
    """Write the scoped env file for this session.

    Returns the persisted key/value dict, or ``None`` if there was nothing to
    do (no ``CLAUDE_ENV_FILE`` in the environment).
    """
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return None

    persist: dict[str, str] = {}
    session_id = raw.get("session_id") or raw.get("conversationId")
    if session_id:
        persist["AOPS_SESSION_ID"] = session_id

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
        git_config = [
            ("url.https://github.com/.insteadOf", "git@github.com:"),
            ("url.https://github.com/.insteadOf", "ssh://git@github.com/"),
            ("credential.https://github.com.helper", ""),
            (
                "credential.https://github.com.helper",
                '!f() { test "$1" = get && printf '
                '"username=x-access-token\npassword=%s\n" '
                '"${AOPS_BOT_GH_TOKEN}"; }; f',
            ),
        ]
        persist["GIT_CONFIG_COUNT"] = str(len(git_config))
        for i, (cfg_key, cfg_val) in enumerate(git_config):
            persist[f"GIT_CONFIG_KEY_{i}"] = cfg_key
            persist[f"GIT_CONFIG_VALUE_{i}"] = cfg_val

    try:
        with open(env_file, "a") as f:
            for key, value in persist.items():
                f.write(f"export {key}={shlex.quote(value)}\n")
    except OSError as exc:
        print(f"credentials.isolate: failed to write {env_file}: {exc!r}", file=sys.stderr)

    return persist
