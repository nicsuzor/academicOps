#!/usr/bin/env python3
"""Pre-commit hook: Check for orphan files (no incoming wikilinks).

This is a WARNING-only check - exits 0 but reports orphans.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Import from the main audit script
sys.path.insert(0, str(Path(__file__).parent))
from audit_framework_health import (
    HealthMetrics,
    check_wikilinks,
)


def main() -> int:
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    metrics = HealthMetrics()
    check_wikilinks(root, metrics)

    if metrics.orphan_files:
        print(f"WARNING: {len(metrics.orphan_files)} orphan files (no incoming links):")
        for f in metrics.orphan_files[:20]:
            print(f"  - {f}")
        if len(metrics.orphan_files) > 20:
            print(f"  ... and {len(metrics.orphan_files) - 20} more")
        print("\nConsider adding wikilinks to connect these files")
        # Return 0 - this is a warning, not a failure
        return 0

    print("OK: No orphan files detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
