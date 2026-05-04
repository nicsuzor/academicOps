#!/usr/bin/env python3
"""
Check that PKB MCP tool calls do not use data/brain path aliases.

This prevents regression of the alias-rewrite shim that was removed.
PKB tools should use id= with short-form identifiers, not path= with full paths.

Exit code: 0 if no violations found, 1 if violations exist.
"""

import re
import sys
from pathlib import Path


def check_for_path_aliases(filenames: list[str]) -> int:
    """Check files for PKB path aliases using full data paths."""
    violations = []

    # Construct regex to detect deprecated parameter alias (dynamically built to avoid self-match)
    invalid_path = r"\b" + "path" + r"\s*=\s*" + "[\"']?" + "/data/brain"
    pattern = re.compile(invalid_path)

    for filename in filenames:
        try:
            content = Path(filename).read_text()
            for line_no, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"{filename}:{line_no}: {line.strip()}")
        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read
            continue

    if violations:
        forbidden_param = "path" + "=" + "/data/brain"
        print(f"Error: Found PKB {forbidden_param} aliases (use id= instead):")
        for violation in violations:
            print(f"  {violation}")
        return 1

    return 0


if __name__ == "__main__":
    # Get files from git hook (passed as command-line args)
    filenames = sys.argv[1:] if len(sys.argv) > 1 else []

    if not filenames:
        # If no files provided, check common source directories
        filenames = []
        for pattern in [
            "aops-core/**/*.py",
            "aops-core/**/*.md",
            "scripts/**/*.py",
            "polecat/**/*.py",
        ]:
            filenames.extend(str(p) for p in Path(".").glob(pattern))

    sys.exit(check_for_path_aliases(filenames))
