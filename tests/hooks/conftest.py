"""Puts aops/hooks on sys.path so tests can `import gates` directly.

The gate system deliberately has no package installed on the path — it runs
as a plugin hook script (aops/hooks/gate_dispatch.py), which gets its own
directory on sys.path automatically when invoked directly. Tests replicate
that by inserting the same directory.
"""

import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[2] / "aops" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
