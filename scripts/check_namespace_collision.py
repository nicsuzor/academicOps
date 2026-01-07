#!/usr/bin/env python3
"""Pre-commit hook: Check for namespace collisions across framework objects.

Per H8: Framework objects (skills, commands, hooks, agents) must have unique
names across all namespaces. Claude Code treats same-named commands as
model-only, causing "can only be invoked by Claude" errors for users.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Import from the main audit script
sys.path.insert(0, str(Path(__file__).parent))
from audit_framework_health import check_namespace_collisions  # noqa: E402


def main() -> int:
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    collisions = check_namespace_collisions(root)

    if collisions:
        print(f"ERROR: {len(collisions)} namespace collision(s) detected:")
        print()
        for name, ns1, ns2 in collisions:
            print(f"  - '{name}' exists in both {ns1}/ and {ns2}/")
        print()
        print("Why this matters: Claude Code treats same-named commands as model-only,")
        print("causing 'can only be invoked by Claude' errors for users.")
        print()
        print("Fix: Rename the conflicting file to avoid the collision.")
        print("See HEURISTICS.md H8 for details.")
        return 1

    print("OK: No namespace collisions detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
