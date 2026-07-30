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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class HookContext:
    client: str
    event: str
    tool: str = ""
    command: str = ""
    session_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    hooks_dir: Path = field(default_factory=Path)


@dataclass(frozen=True)
class Result:
    inject_text: str
    user_text: str | None = None
    is_refusal: bool = False


def warn(message: str, user_text: str | None = None) -> Result:
    return Result(message, user_text)


def refuse(reason: str, user_text: str | None = None) -> Result:
    return Result(reason, user_text, is_refusal=True)


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
    present = [r for r in results if r is not None]
    for r in present:
        if r.is_refusal:
            return r
    return present[0] if present else None


def _render_claude(result: Result, event: str) -> dict:
    if result.is_refusal:
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
    if result.is_refusal:
        return {"decision": "deny", "reason": result.inject_text}
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
