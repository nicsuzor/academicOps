#!/usr/bin/env python3
"""CLI runner for premise-check verdict, invoked by supervisor agents."""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve hooks directory from either source tree or packaged distribution
_HERE = Path(__file__).resolve()
_CANDIDATES = [
    _HERE.parents[3] / "hooks",  # plugins/orchestrate/hooks/
    _HERE.parents[2] / "hooks",  # distribution layout dist/orchestrate-*/hooks/
]

_HOOKS_DIR = None
for candidate in _CANDIDATES:
    if (candidate / "premise_check_verdict.py").is_file():
        _HOOKS_DIR = candidate
        break

if _HOOKS_DIR and str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

for parent in _HERE.parents:
    lib_candidate = parent / "lib" / "hooks"
    if (lib_candidate / "dispatch.py").is_file():
        if str(lib_candidate) not in sys.path:
            sys.path.insert(0, str(lib_candidate))
        break

try:
    import premise_check_verdict as pcv
except ImportError as exc:
    print(f"verdict.py: failed to import premise_check_verdict ({exc})", file=sys.stderr)
    sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    return pcv.main(argv)


if __name__ == "__main__":
    sys.exit(main())
