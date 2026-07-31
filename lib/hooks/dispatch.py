#!/usr/bin/env python3
"""Hook runtime entry point.

Invoked as ``dispatch.py <client> <event>``.
Reads the hook payload as JSON on stdin, normalizes client + event, runs
the plugin's registered handlers, merges their results, and prints the response.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HookContext:
    client: str
    event: str
    tool: str = ""
    command: str = ""
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    hooks_dir: Path = field(default_factory=Path)


class Kind(StrEnum):
    """One of three dispositions, in descending order of force.

    ``REFUSE`` denies a tool call outright and is reserved for structural
    impossibility — the session as configured cannot carry the call out, so
    letting it through produces a hang rather than an outcome. It is never a
    rule verdict.

    ``BLOCK`` refuses to let a *stop* land: the turn continues so the agent
    can do the thing the hook asked for. It is legal only on the events in
    ``BLOCKABLE_EVENTS``, because no other event has a stop to withhold.

    ``ADVISE`` is neither: text the agent reads and weighs, which is what
    every rule-driven handler is limited to.

    One field with three values rather than a flag per disposition, so a result
    cannot hold two at once. The renderers resolve the dispositions in their own
    order, and a result that was both a refusal and a block would render as
    whichever each renderer happened to test first.

    **Compare members with ``==``, never with ``is``.** This module is loaded
    twice in a live hook: once as ``__main__`` (the entry point) and again as
    ``dispatch`` when a plugin's ``handlers.py`` does ``from dispatch import
    block``. Those are two module objects with two distinct ``Kind`` classes, so
    a member built handler-side is never *identical* to the one the renderer
    tests against. ``StrEnum`` is what makes ``==`` still hold across them — a
    plain ``Enum`` compares unequal, by identity, and would break this. An
    ``is`` comparison here fails silently too: the disposition degrades to an
    advisory and a gate that reports success never fires.
    """

    ADVISE = "advise"
    REFUSE = "refuse"
    BLOCK = "block"


@dataclass(frozen=True)
class Result:
    inject_text: str
    user_text: str | None = None
    kind: Kind = Kind.ADVISE


def warn(message: str, user_text: str | None = None) -> Result:
    return Result(message, user_text)


def refuse(reason: str, user_text: str | None = None) -> Result:
    return Result(reason, user_text, Kind.REFUSE)


def block(reason: str, user_text: str | None = None) -> Result:
    return Result(reason, user_text, Kind.BLOCK)


def load_message_pair(hooks_dir: Path, name: str) -> tuple[str, str | None]:
    agent_path = hooks_dir / "messages" / f"{name}.md"
    user_path = hooks_dir / "messages" / f"{name}.user.md"
    agent = agent_path.read_text(encoding="utf-8").strip() if agent_path.exists() else ""
    user = user_path.read_text(encoding="utf-8").strip() if user_path.exists() else None
    return agent, user


Handler = Callable[[HookContext], Result | None]

CANONICAL_EVENTS = (
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
    "SubagentStop",
)

STOP_EVENTS = ("Stop", "SubagentStop")

# The events a block disposition is honoured on. Claude Code reads
# ``decision: "block"`` on a stop and gives the session another turn; on every
# other event the field is not part of the response contract, so emitting it
# there is a no-op the handler would mistake for enforcement.
BLOCKABLE_EVENTS = STOP_EVENTS


def is_continuation(event: str, raw: dict[str, Any]) -> bool:
    """Is this stop the one our own injection caused, rather than a real one?

    A hook that injects on a stop gives the session another turn, which stops
    again and re-fires the hook; the client marks that re-entry with
    ``stop_hook_active``. Answering yes here is what gives a stop hook
    once-per-chain semantics with no state of its own.

    Claude Code (and Antigravity) can re-fire Stop/SubagentStop for the same
    stop after a hook already ran once for it — the client re-invokes the same
    hook to let it reconsider, and the re-invocation payload carries
    ``stop_hook_active=true``. Treating that re-entry as a fresh stop is the
    loop that hit ``router.py`` on 2026-07-13. Callers must check this before
    ``normalize()``, before logging the fire, and before loading or running any
    handler — structurally, in the dispatcher itself rather than in each
    handler, so every current and future Stop/SubagentStop handler is covered
    without having to remember it.
    """
    return event in STOP_EVENTS and bool(raw.get("stop_hook_active"))


TO_CANONICAL = {
    "claude": {name: name for name in CANONICAL_EVENTS},
    "agy": {
        "PreInvocation": "UserPromptSubmit",
        "PostInvocation": "Stop",
    },
}


def to_canonical(client: str, wire_event: str) -> str | None:
    mapping = TO_CANONICAL.get(client, {})
    if wire_event in mapping:
        return mapping[wire_event]
    return wire_event


def _log_fire(ctx: HookContext) -> None:
    log_path = os.environ.get("AOPS_HOOK_LOG_PATH")
    if not log_path:
        return
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "client": ctx.client,
        "event": ctx.event,
        "session_id": ctx.session_id,
        "tool": ctx.tool,
    }
    try:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def _load_handlers(event: str, hooks_dir: Path) -> list[Handler]:
    handlers_path = hooks_dir / "handlers.py"
    if not handlers_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("handlers", handlers_path)
    if spec is None or spec.loader is None:
        print(f"aops hooks: failed to load {handlers_path} (no spec)", file=sys.stderr)
        return []
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"aops hooks: failed to load {handlers_path}: {exc!r}", file=sys.stderr)
        return []

    registry = getattr(module, "HANDLERS", {})
    handlers = list(registry.get(event, []))
    for h in registry.get("*", []):
        if h not in handlers:
            handlers.append(h)
    return handlers


def _run_handler(handler: Handler, ctx: HookContext) -> Result | None:
    try:
        return handler(ctx)
    except Exception as exc:
        name = getattr(handler, "__name__", str(handler))
        msg = f"aops hooks: handler {name!r} failed with {exc!r}"
        print(msg, file=sys.stderr)
        return warn(msg)


def _merge(results: list[Result | None]) -> Result | None:
    """Strongest disposition wins, then first-registered.

    Within one plugin's handlers only. Two plugins registered on the same event
    are two processes and never meet here, so this settles registration order,
    not precedence between plugins — the client decides that.
    """
    present = [r for r in results if r is not None]
    for r in present:
        if r.kind == Kind.REFUSE:
            return r
    for r in present:
        if r.kind == Kind.BLOCK:
            return r
    return present[0] if present else None


def _render_claude(result: Result, event: str) -> dict:
    if result.kind == Kind.BLOCK and event in BLOCKABLE_EVENTS:
        # The one shape Claude Code reads as "do not stop": a top-level
        # decision, not nested under hookSpecificOutput.
        blocked: dict[str, Any] = {"decision": "block", "reason": result.inject_text}
        if result.user_text:
            blocked["systemMessage"] = result.user_text
        return blocked

    if result.kind == Kind.BLOCK:
        # A block only means something on Stop/SubagentStop — Claude Code has no
        # "block" shape for any other event. A handler that returns one here is
        # a wiring bug: report it loudly and degrade to an advisory rather than
        # emit a shape that corrupts the response or silently does nothing. The
        # text is still worth delivering; the disposition is not, and a handler
        # must not read silence here as enforcement that happened.
        print(
            f"dispatch: block() is illegal on event {event!r} (Claude Code only "
            "reads a block decision on Stop/SubagentStop) — degrading to an "
            "advisory instead of corrupting the hook response",
            file=sys.stderr,
        )

    if result.kind == Kind.REFUSE:
        specific = {
            "hookEventName": event,
            "permissionDecision": "deny",
            "permissionDecisionReason": result.inject_text,
        }
    else:
        specific = {"hookEventName": event, "additionalContext": result.inject_text}

    output: dict[str, Any] = {"hookSpecificOutput": specific}
    if result.user_text:
        output["systemMessage"] = result.user_text
    return output


def _render_agy(result: Result) -> dict:
    """agy has no blockable event, so a block reaches it as advice or not at all.

    Its ``PostInvocation`` response contract is a bare object with no disposition
    field to carry one, and the invocation has already ended by the time the
    event fires. The text still has somewhere to go, so it goes there.
    """
    if result.kind == Kind.REFUSE:
        return {"decision": "deny", "reason": result.inject_text}
    # agy has no blocking shape at all, on any event — a block() downgrades
    # to the same advisory shape a warn() would render as.
    return {"injectSteps": [{"ephemeralMessage": result.inject_text}]}


def render(client: str, event: str, result: Result | None) -> dict:
    if result is None:
        return {}
    if client == "claude":
        return _render_claude(result, event)
    if client == "agy":
        return _render_agy(result)
    return {}


def normalize(client: str, event: str, raw: dict[str, Any], hooks_dir: Path) -> HookContext:
    tool_input = raw.get("tool_input")
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    return HookContext(
        client=client,
        event=event,
        tool=raw.get("tool_name") or raw.get("toolName") or "",
        command=command,
        session_id=raw.get("session_id") or raw.get("conversationId") or "",
        raw=raw,
        hooks_dir=hooks_dir,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: dispatch.py <client> <event>", file=sys.stderr)
        return 1
    client, wire_event = argv[1], argv[2]

    raw: dict[str, Any] = {}
    if not sys.stdin.isatty():
        try:
            raw = json.load(sys.stdin)
        except json.JSONDecodeError:
            raw = {}

    event = to_canonical(client, wire_event)
    if event is None:
        return 0

    # Structural self-loop guard: no-op before any handler is loaded or run,
    # and before normalize() / _log_fire() — no state is touched, nothing is
    # printed. See is_continuation()'s docstring for what this guards against.
    if is_continuation(event, raw):
        return 0

    hooks_dir = Path(__file__).resolve().parent
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))

    ctx = normalize(client, event, raw, hooks_dir)
    _log_fire(ctx)

    handlers = _load_handlers(event, hooks_dir)

    kept_handlers = []
    for h in handlers:
        scope = getattr(h, "only_on_clients", None)
        if scope is None or client in scope:
            kept_handlers.append(h)

    results = [_run_handler(h, ctx) for h in kept_handlers]
    result = _merge(results)

    output = render(client, event, result)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:
        print(f"dispatch: fatal error: {exc!r}", file=sys.stderr)
        sys.exit(1)
