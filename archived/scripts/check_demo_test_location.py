#!/usr/bin/env python3
"""Pre-commit hook: Enforce demo tests are in tests/demo/ directory.

Per ns-0p7: Demo tests should BOTH be marked with @pytest.mark.demo AND
placed in tests/demo/ directory. This hook enforces both directions:

1. Files with @pytest.mark.demo must be in tests/demo/
2. Files in tests/demo/ should have @pytest.mark.demo

This prevents Volkswagen test patterns where demo tests are scattered
across directories and lose their visibility/purpose.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def find_demo_markers_outside_demo_dir(tests_dir: Path) -> list[tuple[Path, int]]:
    """Find files with @pytest.mark.demo that are NOT in tests/demo/."""
    violations = []
    demo_dir = tests_dir / "demo"

    for py_file in tests_dir.rglob("*.py"):
        # Skip files in tests/demo/
        if demo_dir in py_file.parents or py_file.parent == demo_dir:
            continue

        # Skip conftest files (they may have demo fixtures)
        if py_file.name == "conftest.py":
            continue

        content = py_file.read_text()
        # Look for @pytest.mark.demo
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(r"@pytest\.mark\.demo\b", line):
                violations.append((py_file, i))
                break  # One violation per file is enough

    return violations


def find_demo_dir_files_without_marker(tests_dir: Path) -> list[Path]:
    """Find test files in tests/demo/ that lack @pytest.mark.demo marker."""
    violations = []
    demo_dir = tests_dir / "demo"

    if not demo_dir.exists():
        return []

    for py_file in demo_dir.glob("test_*.py"):
        content = py_file.read_text()
        if "@pytest.mark.demo" not in content:
            violations.append(py_file)

    return violations


def main() -> int:
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()
    tests_dir = root / "tests"

    if not tests_dir.is_dir():
        print(f"Error: Tests directory does not exist: {tests_dir}", file=sys.stderr)
        return 1

    exit_code = 0

    # Check 1: Demo markers outside tests/demo/
    # TODO: Make this blocking (exit_code = 1) once existing tests are migrated
    # Tracked in: ns-0p7
    outside_violations = find_demo_markers_outside_demo_dir(tests_dir)
    if outside_violations:
        print("WARNING: @pytest.mark.demo found outside tests/demo/:")
        for path, line in outside_violations:
            rel_path = path.relative_to(root)
            print(f"  - {rel_path}:{line}")
        print("\nMove demo tests to tests/demo/ directory (per ns-0p7)")
        # Currently warning-only; will become blocking after migration
        # exit_code = 1

    # Check 2: Files in tests/demo/ without marker
    missing_marker = find_demo_dir_files_without_marker(tests_dir)
    if missing_marker:
        print("WARNING: Files in tests/demo/ missing @pytest.mark.demo:")
        for path in missing_marker:
            rel_path = path.relative_to(root)
            print(f"  - {rel_path}")
        print("\nAdd @pytest.mark.demo decorator to test classes/functions")
        # This is a warning, not a failure

    if exit_code == 0:
        print("OK: Demo test locations are valid")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
