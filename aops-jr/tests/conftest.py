"""Puts aops-jr, aops-jr/hooks, and aops/hooks on sys.path so tests can import hooks and gates directly."""

import sys
from pathlib import Path

_JR_DIR = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _JR_DIR / "hooks"
_AOPS_HOOKS_DIR = _JR_DIR.parent / "aops" / "hooks"

for p in (str(_JR_DIR), str(_HOOKS_DIR), str(_AOPS_HOOKS_DIR)):
    if Path(p).exists() and p not in sys.path:
        sys.path.insert(0, p)

