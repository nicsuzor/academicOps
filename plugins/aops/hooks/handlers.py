"""aops hook handlers.

Registered against the canonical event names in ``clients.CANONICAL_EVENTS``
and loaded by the shared runtime in ``dispatch.py``, which puts this
directory on ``sys.path`` before importing this module.

Every agent-visible string comes from ``messages/<name>.md``.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import credentials
import result
import telemetry
from context import HookContext

Handler = Callable[[HookContext], "result.Result | None"]

# Tools whose entire purpose is to stop and wait for a person to answer.
_INTERACTIVE_TOOLS = frozenset(
    {
        "ask_question",
        "AskFollowupQuestion",
        "ask_followup_question",
        "Question",
    }
)

# A session that sets any of these to "1" has declared that no human is at the
# keyboard. This is the whole signal, deliberately: a hook runs as a subprocess
# with the payload piped to its stdin and its stdout captured, so no file
# descriptor it can see reports anything about whether a terminal is attached
# to the session that spawned it. The environment is the only thing that knows.
_HEADLESS_ENV = (
    "NONINTERACTIVE",
    "CI",
    "AOPS_POLECAT_CONTAINER",
    "CLAUDE_CODE_NON_INTERACTIVE",
)


def session_start(ctx: HookContext) -> result.Result | None:
    """Report telemetry configuration; scope credentials for container sessions.

    Reports only. Never sets a telemetry value and never supplies an endpoint.
    """
    parts = [ctx.message("session-start").format(telemetry=telemetry.report())]
    if credentials.isolate(ctx.raw) is not None:
        parts.append(ctx.message("session-start-isolated"))
    return result.warn("\n\n".join(parts))


def require_evidence_from_subagent(ctx: HookContext) -> result.Result | None:
    """Remind the parent agent to require evidence before accepting a result."""
    return result.warn(ctx.message("subagent-result"))


def present_checkable_evidence(ctx: HookContext) -> result.Result | None:
    """Remind an agent to present its answer with checkable evidence."""
    return result.warn(ctx.message("answer-evidence"))


def _is_headless() -> bool:
    return any(os.environ.get(name) == "1" for name in _HEADLESS_ENV)


def refuse_interactive_prompt_when_headless(ctx: HookContext) -> result.Result | None:
    """Refuse an interactive prompt that nobody is there to answer.

    The only refusing handler in the framework, and it refuses on a capability
    fact, never on a rule: a headless session has no human to answer, so the
    call cannot return and the session blocks until it times out. Everything
    else passes untouched — every other tool, and these tools in every session
    that has someone in it. See lib/hooks/result.py for what may and may not
    be a refusal.
    """
    if ctx.tool not in _INTERACTIVE_TOOLS:
        return None
    if not _is_headless():
        return None
    return result.refuse(ctx.message("headless-interactive-prompt").format(tool=ctx.tool))


HANDLERS: dict[str, list[Handler]] = {
    "SessionStart": [session_start],
    "PreToolUse": [refuse_interactive_prompt_when_headless],
    "SubagentStop": [require_evidence_from_subagent],
    "Stop": [present_checkable_evidence],
}
