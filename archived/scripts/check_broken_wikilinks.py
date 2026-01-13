#!/usr/bin/env python3
"""Pre-commit hook: Check for broken wikilinks."""

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

    if metrics.broken_wikilinks:
        print(f"ERROR: {len(metrics.broken_wikilinks)} broken wikilinks:")
        for link in metrics.broken_wikilinks[:10]:
            print(f"  - {link['file']}: [[{link['target']}]]")
        if len(metrics.broken_wikilinks) > 10:
            print(f"  ... and {len(metrics.broken_wikilinks) - 10} more")
        print("\nFix wikilinks to point to valid files")
        return 1

    print("OK: All wikilinks resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
