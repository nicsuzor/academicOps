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
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HookContext:
    client: str
    event: str
    tool: str = ""
    command: str = ""
    session_id: str = ""
    agent_type: str = ""
    agent_id: str = ""
    prompt_id: str = ""
    transcript_path: str = ""
    cwd: str = ""
    hook_event_name: str = ""
    # PostToolBatch only: every tool call in the resolved batch, each a
    # ``{tool_name, tool_input, tool_use_id, tool_response}`` mapping. Empty on
    # every other event, so a handler can read it without guarding the event.
    tool_calls: tuple[dict[str, Any], ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)
    hooks_dir: Path = field(default_factory=Path)


class Kind(Enum):
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

    Members are compared with ``is``, which holds because the entry point at
    the bottom of this file guarantees one module object — and so one ``Kind``
    class — for the whole run. That guarantee is what makes this an ordinary
    enum rather than something defensive; see the ``__main__`` block.
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
    "PostToolUseFailure",
    # Fires once after every call in a resolved batch, carrying all of them in
    # ``tool_calls`` — the one event that sees a whole batch rather than a
    # single call. Claude Code only; agy has no wire equivalent.
    "PostToolBatch",
    "Stop",
    "SubagentStop",
)

STOP_EVENTS = ("Stop", "SubagentStop")
CONTINUATION_EVENTS = ("Stop", "SubagentStop", "PostToolBatch")

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
    return event in CONTINUATION_EVENTS and bool(raw.get("stop_hook_active"))


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
    record = asdict(ctx)
    record["ts"] = datetime.now(UTC).isoformat()
    try:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
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
        if r.kind is Kind.REFUSE:
            return r
    for r in present:
        if r.kind is Kind.BLOCK:
            return r
    return present[0] if present else None


def _render_claude(result: Result, event: str) -> dict:
    if result.kind is Kind.BLOCK:
        if event in BLOCKABLE_EVENTS:
            # The one shape Claude Code reads as "do not stop": a top-level
            # decision, not nested under hookSpecificOutput.
            blocked: dict[str, Any] = {"decision": "block", "reason": result.inject_text}
            if result.user_text:
                blocked["systemMessage"] = result.user_text
            return blocked

        else:
            # Block only means something on certain events; in case of misconfiguration
            # text is still worth delivering; the disposition is not, and a handler
            # must not read silence here as enforcement that happened.
            print(
                f"dispatch: block() is illegal on event {event!r}",
                file=sys.stderr,
            )

    if result.kind is Kind.REFUSE:
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
    if result.kind is Kind.REFUSE:
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
    raw_calls = raw.get("tool_calls")
    tool_calls = (
        tuple(c for c in raw_calls if isinstance(c, dict)) if isinstance(raw_calls, list) else ()
    )

    valid_keys = {f.name for f in fields(HookContext)}
    kwargs = {k: v for k, v in raw.items() if k in valid_keys and v is not None}

    kwargs.update(
        client=client,
        event=event,
        tool=raw.get("tool_name") or raw.get("toolName") or kwargs.get("tool", ""),
        command=command,
        session_id=raw.get("session_id")
        or raw.get("conversationId")
        or kwargs.get("session_id", ""),
        tool_calls=tool_calls,
        raw=raw,
        hooks_dir=hooks_dir,
    )
    return HookContext(**kwargs)


# The operator-visible switch for OTel emission. Read here only to decide
# whether a missing module is worth complaining about; `resolve()` in the
# module itself remains the authority on the destination.
_OTEL_TRACE_ENV = "COPE_EVALUATOR_OTEL_TRACE_PATH"


def _get_evaluator_otel_trace():
    """The OTel emitter, when the plugin this dispatch ships inside provides it.

    `evaluator_otel_trace` ships in rbg. This file is shared into every
    plugin's `hooks/` directory, and the entry point puts this module's own
    directory on `sys.path`, so the import below resolves against whichever
    plugin this copy is shipping inside — rbg's, in the builds checked. That
    is a file reading its own plugin's directory, not another plugin's. The
    traversal to `plugins/rbg/hooks` that used to sit here named another
    plugin by path, and in the `dist/<name>-<client>/` layout resolved to
    nothing, leaving the instrumentation a silent no-op.

    Tests may resolve this import by injecting a path instead; the sibling
    rule describes the shipped layout, not every possible one.

    Silence is right when nobody asked for OTel. It is wrong when someone did,
    so that case says so on stderr instead of disappearing.
    """
    try:
        import evaluator_otel_trace

        return evaluator_otel_trace
    except ImportError:
        if os.environ.get(_OTEL_TRACE_ENV):
            print(
                f"aops hooks: {_OTEL_TRACE_ENV} is set but evaluator_otel_trace is not "
                "importable here — OTel instrumentation ships with rbg, and this "
                "dispatch is running inside a plugin that does not carry it.",
                file=sys.stderr,
            )
        return None


def _instrument_otel_events(ctx: HookContext) -> None:
    otel_mod = _get_evaluator_otel_trace()
    if otel_mod is None:
        return

    config = otel_mod.resolve()
    if config is None:
        return

    # 1. Tool plumbing errors (unknown_tool, missing_mcp)
    plumbing_err = otel_mod.detect_tool_plumbing_error(ctx)
    if plumbing_err:
        err_type, err_msg = plumbing_err
        otel_mod.record_tool_plumbing_error(
            ctx, error_type=err_type, error_message=err_msg, config=config
        )

    # 2. SendMessage tool call linkage
    is_send_msg = ctx.tool == "SendMessage" or any(
        isinstance(call, dict)
        and (call.get("tool_name") == "SendMessage" or call.get("tool") == "SendMessage")
        for call in ctx.tool_calls
    )
    if is_send_msg:
        otel_mod.record_send_message(ctx, config=config)

    # 3. Agent idle/timeout on Stop or SubagentStop
    idle_timeout = otel_mod.detect_agent_idle_timeout(ctx)
    if idle_timeout:
        otel_mod.record_agent_idle_timeout(ctx, event_type=idle_timeout, config=config)

    # 4. SubagentStop unsent output inspection
    if ctx.event == "SubagentStop":
        otel_mod.record_subagent_stop(ctx, config=config)


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

    # Do not fire if we have already prevented a stop event this turn
    if is_continuation(event, raw):
        return 0

    hooks_dir = Path(__file__).resolve().parent
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))

    ctx = normalize(client, event, raw, hooks_dir)
    _log_fire(ctx)
    _instrument_otel_events(ctx)

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
    # Hand off to this same file imported under its own name, and do no work
    # here. Running it directly makes it the module ``__main__``; a plugin's
    # ``handlers.py`` then does ``from dispatch import ...``, which loads the
    # file a second time as ``dispatch``. Calling ``main`` on this side would
    # leave the handlers building results from one set of classes while the
    # renderers tested another — ``Result`` and ``Kind`` would be two unrelated
    # types with the same names, so every ``is`` comparison would be false and
    # every disposition would degrade to an advisory while reporting success.
    #
    # Re-entering here makes ``dispatch`` the only module that does anything:
    # handlers import it, ``main`` runs inside it, one set of classes. This
    # block is the whole reason those comparisons can be identity checks.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    import dispatch

    try:
        sys.exit(dispatch.main(sys.argv))
    except Exception as exc:
        print(f"dispatch: fatal error: {exc!r}", file=sys.stderr)
        sys.exit(1)
