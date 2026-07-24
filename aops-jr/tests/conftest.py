"""Puts aops-jr and aops-jr/hooks on sys.path so tests can import hooks and gates directly."""

import sys
from pathlib import Path

_JR_DIR = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _JR_DIR / "hooks"

for p in (str(_JR_DIR), str(_HOOKS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)
