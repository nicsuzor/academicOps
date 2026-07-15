#!/usr/bin/env python3
"""Gate dispatcher: stdin JSON -> Event -> gates -> merge -> emit.

One script, registered once per event in hooks/hooks.json. Reads the raw
hook JSON from stdin, normalizes it to a small Event, runs every gate in
the registry, merges their verdicts (deny > warn > allow), and prints the
client's wire format for the result. No output = no-op.

See specs/enforcement/hook-gate-system.md for the design.
"""

from __future__ import annotations

import json
import sys

from gates.emit import emit
from gates.event import normalize
from gates.registry import GATES
from gates.state import load, save
from gates.verdict import merge


def main() -> int:
    client = sys.argv[1] if len(sys.argv) > 1 else "claude"

    raw = {}
    if not sys.stdin.isatty():
        try:
            raw = json.load(sys.stdin)
        except json.JSONDecodeError:
            raw = {}

    event = normalize(raw)
    state = load(event.session_id)

    verdicts = [gate(event, state) for gate in GATES]
    verdict = merge(verdicts)

    save(event.session_id, state)

    output = emit(verdict, event, client)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
