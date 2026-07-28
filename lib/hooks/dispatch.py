#!/usr/bin/env python3
"""Hook runtime entry point.

Invoked as ``dispatch.py <client> <event>``. Reads the hook payload as JSON
on stdin, normalizes client + event, runs the plugin's registered handlers
for that event, merges their results, and prints the client's wire-format
response on stdout. No output = no-op. See specs/ARCHITECTURE.md, Hooks.

A handler that fails is isolated rather than fatal, and its failure joins the
response on the way out (lib/hooks/degraded.py) so the person in the session
learns that a check they rely on has stopped running.

This file is shared runtime, copied byte-identical into every plugin that
hooks (build stage 1, ``[shared]`` in the plugin's ``manifest/plugin.toml``).
A plugin supplies its own ``hooks/handlers.py`` next to this file; a plugin
with no handlers for an event is a no-op, not an error.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import clients  # noqa: E402
import degraded  # noqa: E402
from context import HookContext, normalize  # noqa: E402
from result import Result, merge  # noqa: E402

Handler = Callable[[HookContext], "Result | None"]


def _log_fire(client: str, event: str, ctx: HookContext) -> None:
    """Append one record to ``$AOPS_HOOK_LOG_PATH``, if set.

    This is the primary evidence "did the framework actually fire" that
    specs/polecat/tmux-interactive-driving.md names — distinct from "did the
    client's UI render something." No env var, no record: nothing here sets
    a default path or invents one, and nothing here may raise into the hook
    it is trying to record — a logging failure must never break the call.
    """
    log_path = os.environ.get("AOPS_HOOK_LOG_PATH")
    if not log_path:
        return
    record = {
        "ts": datetime.now(UTC).isoformat(),
        "client": client,
        "event": event,
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
        degraded.report(
            degraded.HANDLER,
            "aops hooks: this plugin's handlers could not be loaded, so none of its checks ran",
            f"no import spec for {handlers_path}",
        )
        return []
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - a broken module must not end the session
        degraded.report(
            degraded.HANDLER,
            "aops hooks: this plugin's handlers could not be loaded, so none of its checks ran",
            f"{handlers_path} raised {exc!r} on import",
        )
        return []
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
    fail-safe — its own result is skipped and the failure is reported, but
    every other handler for this event still runs and still merges normally. A
    legitimate advisory from another handler must never be discarded just
    because an unrelated handler blew up, and this process must never crash on
    one handler's failure.

    Reported through ``degraded`` rather than straight to stderr: the check
    silently not running is precisely what the person in the session needs to
    know, and stderr reaches nobody (lib/hooks/degraded.py).
    """
    try:
        return handler(ctx)
    except Exception as exc:  # noqa: BLE001 - isolate this handler, not the process
        name = getattr(handler, "__name__", handler)
        degraded.report(
            degraded.HANDLER,
            f"aops hooks: the {name!r} check failed and did not run",
            f"raised {exc!r}; every other handler for this event still ran",
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
    _log_fire(client, event, ctx)
    handlers = _for_client(_load_handlers(event), client)
    results = [_run_handler(h, ctx) for h in handlers]
    # Whatever the handlers had to say, plus anything the framework broke on
    # its way to saying it — the second is invisible to the user otherwise.
    result = degraded.attach(merge(results), ctx.hooks_dir, ctx.session_id)

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
