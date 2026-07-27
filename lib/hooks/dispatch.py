#!/usr/bin/env python3
"""Hook runtime entry point.

Invoked as ``dispatch.py <client> <event>``. Reads the hook payload as JSON
on stdin, normalizes client + event, runs the plugin's registered handlers
for that event, merges their results, and prints the client's wire-format
response on stdout. No output = no-op. See specs/ARCHITECTURE.md, Hooks.

This file is shared runtime, copied byte-identical into every plugin that
hooks (build stage 1, ``[shared]`` in the plugin's ``manifest/plugin.toml``).
A plugin supplies its own ``hooks/handlers.py`` next to this file; a plugin
with no handlers for an event is a no-op, not an error.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import clients  # noqa: E402
from context import HookContext, normalize  # noqa: E402
from result import Result, merge  # noqa: E402

Handler = Callable[[HookContext], "Result | None"]


def _load_handlers(event: str) -> list[Handler]:
    """Load this plugin's ``hooks/handlers.py``, if it ships one, and return
    the handlers it registers for ``event``.

    No ``handlers.py``, or no entry for this event, is a no-op — not an
    error.
    """
    handlers_path = _HOOKS_DIR / "handlers.py"
    if not handlers_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("handlers", handlers_path)
    if spec is None or spec.loader is None:
        print(f"dispatch: could not load {handlers_path}", file=sys.stderr)
        return []
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry: dict[str, list[Handler]] = getattr(module, "HANDLERS", {})
    return list(registry.get(event, []))


def _for_client(handlers: list[Handler], client: str) -> list[Handler]:
    """Keep only the handlers this client is meant to run.

    A handler may declare an ``only_on_clients`` attribute — the set of client
    names it is scoped to. One canonical event can reach a plugin from more
    than one client (agy's ``PreInvocation`` and Claude's ``UserPromptSubmit``
    are the same canonical event), and a plugin may have something to say on
    one of them and not the other. Declaring the scope on the handler keeps
    that decision visible where the handler is defined.

    No declaration means every client, so this is a no-op for handlers that
    don't use it.
    """
    kept = []
    for handler in handlers:
        scope = getattr(handler, "only_on_clients", None)
        if scope is None or client in scope:
            kept.append(handler)
    return kept


def _run_handler(handler: Handler, ctx: HookContext) -> Result | None:
    """Run one handler, isolated from every other handler's outcome.

    Fail policy: a handler that raises (a missing message file, a bug) is
    fail-safe — its own result is skipped and the exception is reported to
    stderr, but every other handler for this event still runs and still
    merges normally. A legitimate advisory from another handler must never
    be discarded just because an unrelated handler blew up, and this process
    must never crash on one handler's failure.
    """
    try:
        return handler(ctx)
    except Exception as exc:  # noqa: BLE001 - isolate this handler, not the process
        print(
            f"dispatch: handler {getattr(handler, '__name__', handler)!r} "
            f"raised {exc!r}; skipping its result (other handlers still run)",
            file=sys.stderr,
        )
        return None


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

    event = clients.to_canonical(client, wire_event)
    if event is None:
        # No hook wired for this (client, wire_event) pair. Clean no-op.
        return 0

    ctx = normalize(client, event, raw, _HOOKS_DIR)
    handlers = _for_client(_load_handlers(event), client)
    results = [_run_handler(h, ctx) for h in handlers]
    result = merge(results)

    output = clients.render(client, event, result)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # noqa: BLE001 - never emit a misleading success response
        print(f"dispatch: fatal error: {exc!r}", file=sys.stderr)
        sys.exit(1)
