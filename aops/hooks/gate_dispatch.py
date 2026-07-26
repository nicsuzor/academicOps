#!/usr/bin/env python3
"""Gate dispatcher: stdin JSON -> Event -> gates -> merge -> emit.

One script, registered once per event in each plugin's hooks/hooks.json.
Reads the raw hook JSON from stdin, normalizes it to a small Event, runs
every gate in the registry, merges their verdicts (deny > warn > allow),
and prints the client's wire format for the result. No output = no-op.

Canonical source for every plugin that ships gate/router infrastructure
(aops-jr, reflexes-cope): scripts/build.py fans this file out, byte-identical,
alongside gates/, into each plugin's built hooks/ directory.

See specs/enforcement/hook-gate-system.md for the design.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

if "gates" in sys.modules and not hasattr(sys.modules["gates"], "emit"):
    del sys.modules["gates"]
    for mod in list(sys.modules.keys()):
        if mod.startswith("gates."):
            del sys.modules[mod]

from gates.emit import emit
from gates.event import Event, normalize
from gates.registry import GATES
from gates.state import load, save
from gates.verdict import Verdict, merge

# Events where Claude Code (or Antigravity) re-fires the same hook after it
# already ran once for this stop; re-running gates against a self-triggered
# re-entry is the exact loop that hit router.py on 2026-07-13. Guarded here,
# structurally, so every current and future Stop/SubagentStop gate is
# protected without each gate having to remember to check it itself.
_SELF_LOOP_GUARDED_EVENTS = {"Stop", "SubagentStop"}


def _run_gate(gate, event: Event, state: dict) -> Verdict | None:
    """Run one gate, isolated from every other gate's outcome.

    Fail policy: a gate that raises is treated as fail-SAFE for a safety
    system — its own verdict is skipped (and the exception is reported to
    stderr for visibility), but every other gate still runs and still
    merges normally. In particular a legitimate `deny` from another gate
    must never be discarded just because an unrelated gate blew up. The
    process must not crash and must still emit the correct merged verdict.
    """
    try:
        return gate(event, state)
    except Exception as exc:  # noqa: BLE001 - isolate this gate, not the process
        print(
            f"gate_dispatch: gate {getattr(gate, '__name__', gate)!r} raised "
            f"{exc!r}; skipping its verdict (other gates still run)",
            file=sys.stderr,
        )
        return None


def main() -> int:
    client = sys.argv[1] if len(sys.argv) > 1 else "claude"

    raw = {}
    if not sys.stdin.isatty():
        try:
            raw = json.load(sys.stdin)
        except json.JSONDecodeError:
            raw = {}

    event = normalize(raw)

    # Structural self-loop guard (see _SELF_LOOP_GUARDED_EVENTS above): a
    # truthy stop_hook_active on a Stop/SubagentStop payload means this is a
    # self-triggered re-entry, not a fresh stop. No-op: no gates run, no
    # state is touched, nothing is printed.
    if event.event in _SELF_LOOP_GUARDED_EVENTS and raw.get("stop_hook_active"):
        return 0

    state = load(event.session_id)

    verdicts = [_run_gate(gate, event, state) for gate in GATES]
    verdict = merge(verdicts)

    save(event.session_id, state)

    output = emit(verdict, event, client)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
