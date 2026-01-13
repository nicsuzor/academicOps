#!/usr/bin/env python3
"""Pre-commit hook: Check if all significant files are in INDEX.md."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Import from the main audit script
sys.path.insert(0, str(Path(__file__).parent))
from audit_framework_health import (
    HealthMetrics,
    check_file_accounting,
)


def main() -> int:
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    metrics = HealthMetrics()
    check_file_accounting(root, metrics)

    if metrics.files_not_in_index:
        print(f"ERROR: {len(metrics.files_not_in_index)} files not in INDEX.md:")
        for f in metrics.files_not_in_index[:10]:
            print(f"  - {f}")
        if len(metrics.files_not_in_index) > 10:
            print(f"  ... and {len(metrics.files_not_in_index) - 10} more")
        print("\nRun: uv run python scripts/audit_framework_health.py -m")
        return 1

    print("OK: All significant files accounted for in INDEX.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
