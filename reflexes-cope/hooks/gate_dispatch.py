#!/usr/bin/env python3
"""Gate dispatcher for reflexes-cope plugin.

Reads raw hook JSON from stdin, normalizes to Event, runs reflexes_evaluator,
and prints emitted wire format if an advisory verdict is returned.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_COPE_DIR = _HOOKS_DIR.parent
for d in [str(_HOOKS_DIR), str(_COPE_DIR)]:
    if d in sys.path:
        sys.path.remove(d)
    sys.path.insert(0, d)

from gates.emit import emit
from gates.event import normalize
from gates.reflexes_evaluator import reflexes_evaluator


def main() -> int:
    client = sys.argv[1] if len(sys.argv) > 1 else "claude"

    raw = {}
    if not sys.stdin.isatty():
        try:
            raw = json.load(sys.stdin)
        except json.JSONDecodeError:
            raw = {}

    event = normalize(raw)

    verdict = reflexes_evaluator(event, {})
    output = emit(verdict, event, client)
    if output:
        print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
