"""Gate enforcing AOPS_BOT_GH_TOKEN for all git/gh push operations.

Fail-closed policy: git push and gh push operations require AOPS_BOT_GH_TOKEN
to be explicitly set in the environment. If unset or empty, the gate denies the action.
"""

from __future__ import annotations

import os

from gates.event import Event
from gates.verdict import Verdict, deny

_PUSH_COMMAND_MARKERS = (
    "git push",
    "gh pr create",
    "gh pr merge",
    "gh release create",
    "gh repo create",
)


def require_aops_bot_gh_token(e: Event, state: dict) -> Verdict | None:
    """Enforce AOPS_BOT_GH_TOKEN presence for git and gh push commands."""
    if e.event != "PreToolUse":
        return None

    if e.tool != "Bash":
        return None

    cmd = (e.command or "").strip()
    if not cmd:
        return None

    is_push_op = any(marker in cmd for marker in _PUSH_COMMAND_MARKERS)
    if not is_push_op:
        return None

    bot_token = os.environ.get("AOPS_BOT_GH_TOKEN")
    if not bot_token:
        return deny(
            "FATAL: AOPS_BOT_GH_TOKEN is unset. All git/gh push operations "
            "fail closed unless AOPS_BOT_GH_TOKEN is set in the environment."
        )

    return None
