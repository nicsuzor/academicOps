#!/usr/bin/env python3
"""Pre-commit hook: Check if SKILL.md files exceed 500 lines."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Import from the main audit script
sys.path.insert(0, str(Path(__file__).parent))
from audit_framework_health import (
    HealthMetrics,
    check_skill_sizes,
)


def main() -> int:
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    metrics = HealthMetrics()
    check_skill_sizes(root, metrics)

    if metrics.oversized_skills:
        print(f"ERROR: {len(metrics.oversized_skills)} skills exceed 500 lines:")
        for s in metrics.oversized_skills:
            print(f"  - {s['skill']}: {s['lines']} lines")
        print("\nMove rationale/reference content to specs/ or references/")
        return 1

    print("OK: All SKILL.md files are under 500 lines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
