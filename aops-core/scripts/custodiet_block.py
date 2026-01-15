#!/usr/bin/env python3
"""CLI wrapper to set custodiet block flag.

Usage:
    custodiet_block.py <session_id> <reason>

Example:
    custodiet_block.py abc123 "Agent modified setup.sh without approval - violates P#5"
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add aops-core to path so lib is a proper package
aops_core_path = Path(__file__).parent.parent
sys.path.insert(0, str(aops_core_path))

from lib.session_state import is_custodiet_enabled, set_custodiet_block


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: custodiet_block.py <session_id> <reason>", file=sys.stderr)
        return 1

    session_id = sys.argv[1]
    reason = sys.argv[2]

    set_custodiet_block(session_id, reason)

    if is_custodiet_enabled():
        print(f"Block set for session {session_id}")
    else:
        print(f"Block recorded for session {session_id} (CUSTODIET_DISABLED - not enforced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
