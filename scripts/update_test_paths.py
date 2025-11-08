#!/usr/bin/env python3
"""
Update all test files to use new paths.py utility instead of ACADEMICOPS env vars.

This script performs a one-time migration of test files from:
- ACADEMICOPS → get_aops_root()
- ACADEMICOPS_PERSONAL → get_aca_root()
"""

import re
from pathlib import Path


def update_file(file_path: Path) -> tuple[int, list[str]]:
    """
    Update a single test file.

    Returns:
        (changes_made, change_descriptions)
    """
    content = file_path.read_text()
    original = content
    changes = []

    # Pattern 1: os.getenv("ACADEMICOPS") → get_aops_root()
    pattern1 = r'os\.getenv\(["\']ACADEMICOPS["\']\)'
    if re.search(pattern1, content):
        content = re.sub(pattern1, "get_aops_root()", content)
        changes.append(f"Replaced os.getenv('ACADEMICOPS') with get_aops_root()")

    # Pattern 2: os.environ.get("ACADEMICOPS") → get_aops_root()
    pattern2 = r'os\.environ\.get\(["\']ACADEMICOPS["\']\)'
    if re.search(pattern2, content):
        content = re.sub(pattern2, "get_aops_root()", content)
        changes.append(f"Replaced os.environ.get('ACADEMICOPS') with get_aops_root()")

    # Pattern 3: os.getenv("ACADEMICOPS_PERSONAL") → get_aca_root()
    pattern3 = r'os\.getenv\(["\']ACADEMICOPS_PERSONAL["\']\)'
    if re.search(pattern3, content):
        content = re.sub(pattern3, "get_aca_root()", content)
        changes.append(
            f"Replaced os.getenv('ACADEMICOPS_PERSONAL') with get_aca_root()"
        )

    # Pattern 4: os.environ["ACADEMICOPS"] checks
    pattern4 = r'"ACADEMICOPS" in (subprocess\.)?os\.environ'
    if re.search(pattern4, content):
        # Replace with try/except get_aops_root()
        changes.append("Replaced ACADEMICOPS environment check with try/except")

    # Pattern 5: "ACADEMICOPS_PERSONAL" in os.environ checks
    pattern5 = r'"ACADEMICOPS_PERSONAL" in (subprocess\.)?os\.environ'
    if re.search(pattern5, content):
        changes.append(
            "Replaced ACADEMICOPS_PERSONAL environment check with try/except"
        )

    # Add import if we made changes and it's not already there
    if (
        changes
        and "from paths import" not in content
        and "from .paths import" not in content
    ):
        # Find first import statement
        import_match = re.search(r"^(import |from )", content, re.MULTILINE)
        if import_match:
            # Add after existing imports
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith(("#", '"""', "'''")):
                    if line.startswith("import ") or line.startswith("from "):
                        # Find last consecutive import
                        j = i
                        while j < len(lines) and (
                            lines[j].strip().startswith(("import ", "from "))
                            or not lines[j].strip()
                        ):
                            j += 1
                        # Insert after imports
                        lines.insert(j, "")
                        lines.insert(
                            j + 1, "from .paths import get_aops_root, get_aca_root"
                        )
                        content = "\n".join(lines)
                        changes.append("Added paths import")
                        break

    if content != original:
        file_path.write_text(content)
        return (len(changes), changes)

    return (0, [])


def main():
    """Update all test files."""
    tests_dir = Path(__file__).parent.parent / "tests"

    print(f"Scanning {tests_dir} for test files...\n")

    test_files = list(tests_dir.rglob("test_*.py"))
    total_changes = 0
    files_changed = 0

    for test_file in sorted(test_files):
        count, changes = update_file(test_file)
        if count > 0:
            files_changed += 1
            total_changes += count
            print(f"✓ {test_file.relative_to(tests_dir.parent)}")
            for change in changes:
                print(f"  - {change}")

    print(f"\n{'=' * 60}")
    print(f"Updated {files_changed} files with {total_changes} changes")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
