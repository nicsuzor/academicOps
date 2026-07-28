"""aops hook handlers.

Registered against the canonical event names in ``clients.CANONICAL_EVENTS``
and loaded by the shared runtime in ``dispatch.py``, which puts this
directory on ``sys.path`` before importing this module.

Every agent-visible string comes from ``messages/<name>.md``, and every
user-visible one from ``messages/<name>.user.md`` beside it (lib/hooks/
messages.py). No handler here builds either from a Python literal.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import credentials
import messages
import result
import telemetry
from context import HookContext

Handler = Callable[[HookContext], "result.Result | None"]


def _warn(ctx: HookContext, name: str) -> result.Result:
    """Advisory carrying both readers' versions of one message.

    ``ctx.message`` is the agent's copy; the user's one-liner is optional and
    loaded beside it, so a message that has not grown one yet still works.
    """
    return result.warn(*messages.load_pair(ctx.hooks_dir, name))


# Tools whose entire purpose is to stop and wait for a person to answer.
# ``AskUserQuestion`` is Claude Code's own name for that tool, so it is the one
# name on this list that a shipped session actually uses; the rest are the
# spellings other harnesses give the same capability.
_INTERACTIVE_TOOLS = frozenset(
    {
        "AskUserQuestion",
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
    # <!-- NS: Make sure this reports plugin version and loaded plugins and whatever else we're going to need -- tracing urls etc. but have a separate hook for functionality that exists only in other packages, don't introduce cross-package messages -->
    
    agent, user = messages.load_pair(ctx.hooks_dir, "session-start")
    parts = [agent.format(telemetry=telemetry.report())]
    lines = [user] if user else []
    if credentials.isolate(ctx.raw) is not None:
        isolated, isolated_user = messages.load_pair(ctx.hooks_dir, "session-start-isolated")
        parts.append(isolated)
        if isolated_user:
            lines.append(isolated_user)
    return result.warn("\n\n".join(parts), " ".join(lines) or None)


def present_checkable_evidence(ctx: HookContext) -> result.Result | None:
    """Remind an agent that is stopping to present its answer with evidence.

    Serves both stop events, because both deliver to the same reader. A hook's
    output goes to the session the hook fired in, so ``SubagentStop`` reaches
    the subagent that is stopping — not its parent, which is not in that
    session and never sees a line of it. A message addressed to the parent
    ("interrogate what you were just handed") lands in front of the agent that
    produced the work, which can only confuse it about whose claim is under
    review. So there is one message here, addressed to whoever is stopping.

    Skipped when ``stop_hook_active`` is set: the client sets it once a stop
    hook has already continued this stop cycle, and injecting again on the
    resulting stop re-continues it — an unbounded loop with no user input.

    Skipped while background tasks are still outstanding: the agent is
    holding, not stopping, and has nothing new to present yet. Firing here
    would nag it into re-outputting a deliverable that does not exist yet.
    """
    if ctx.raw.get("stop_hook_active") or ctx.raw.get("background_tasks"):
        return None
    return _warn(ctx, "answer-evidence")


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
    agent, user = messages.load_pair(ctx.hooks_dir, "headless-interactive-prompt")
    return result.refuse(
        agent.format(tool=ctx.tool),
        user.format(tool=ctx.tool) if user else None,
    )


HANDLERS: dict[str, list[Handler]] = {
    "SessionStart": [session_start],
    "PreToolUse": [refuse_interactive_prompt_when_headless],
    "SubagentStop": [present_checkable_evidence],
    "Stop": [present_checkable_evidence],
}
