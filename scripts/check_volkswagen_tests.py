#!/usr/bin/env python3
"""Detect Volkswagen test patterns in test files.

A Volkswagen test defines expected outcomes but doesn't actually verify them,
or uses superficial checks (keyword matching) that pass on wrong behavior.

Per H37: Use LLM semantic evaluation, never keyword/substring matching.

Exit codes:
    0 - No violations found
    1 - Violations found (blocks commit)
"""

import re
import sys
from pathlib import Path


def find_violations(file_path: Path) -> list[tuple[int, str, str]]:
    """Find Volkswagen test patterns in a file.

    Returns:
        List of (line_number, violation_type, line_content) tuples
    """
    violations = []
    content = file_path.read_text()
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip lines with explicit verification comment
        if "# verified:" in line.lower():
            continue

        # Pattern 1: any(x in text for x in list) - keyword matching
        # Matches: any(ind in output for ind in indicators)
        if re.search(r"any\s*\([^)]*\s+in\s+[^)]+\s+for\s+[^)]+\s+in\s+", line):
            violations.append((i, "keyword_matching", line.strip()))

        # Pattern 2: all(x in text for x in list) - keyword matching
        if re.search(r"all\s*\([^)]*\s+in\s+[^)]+\s+for\s+[^)]+\s+in\s+", line):
            violations.append((i, "keyword_matching", line.strip()))

        # Pattern 3: assert len(x) > 0 for LLM output verification
        # Only flag when checking response/output that should have semantic verification
        # Skip: file existence checks, collection length checks
        if re.search(r"assert\s+len\s*\([^)]*\)\s*>\s*0", line):
            var_match = re.search(r"assert\s+len\s*\(([^)]+)\)", line)
            if var_match:
                var_name = var_match.group(1).strip()
                # Only flag if it looks like LLM output verification
                if any(
                    weak in var_name.lower()
                    for weak in ["output", "response"]
                ) and "file" not in line.lower() and "path" not in line.lower():
                    violations.append((i, "weak_length_check", line.strip()))

        # Pattern 4: Truncation in demo/test output
        if "print(" in line and ("[:3000]" in line or "[:5000]" in line):
            if "# verified:" not in line.lower():
                violations.append((i, "truncated_output", line.strip()))

    return violations


def main() -> int:
    """Check all test files for Volkswagen patterns."""
    test_dir = Path("tests")

    if not test_dir.exists():
        print("No tests/ directory found")
        return 0

    all_violations: dict[Path, list[tuple[int, str, str]]] = {}

    for test_file in test_dir.rglob("test_*.py"):
        violations = find_violations(test_file)
        if violations:
            all_violations[test_file] = violations

    if not all_violations:
        return 0

    print("=" * 70)
    print("VOLKSWAGEN TEST PATTERNS DETECTED (H37)")
    print("=" * 70)
    print()
    print("These patterns create false confidence by appearing to verify")
    print("without actually checking behavior. Fix or add '# verified:' comment.")
    print()

    for file_path, violations in all_violations.items():
        print(f"\n{file_path}:")
        for line_num, violation_type, line_content in violations:
            print(f"  Line {line_num} [{violation_type}]:")
            print(f"    {line_content[:80]}...")

    print()
    print("=" * 70)
    print(f"Found {sum(len(v) for v in all_violations.values())} violations")
    print("See HEURISTICS.md H37 for requirements")
    print("=" * 70)

    return 1


if __name__ == "__main__":
    sys.exit(main())
