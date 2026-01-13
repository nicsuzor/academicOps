#!/usr/bin/env python3
"""
Pre-commit hook: Validate FRAMEWORK-PATHS.md exists and is current.

This hook ensures that FRAMEWORK-PATHS.md exists and has been generated
recently (within the last 7 days). Stale files may contain incorrect paths
if the environment has changed.

Exit codes:
    0: Validation passed
    1: Validation failed (file missing, stale, or malformed)
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

try:
    from paths import get_aops_root
except ImportError as e:
    print(f"Error: Failed to import from paths.py: {e}", file=sys.stderr)
    sys.exit(1)


def validate_framework_paths() -> tuple[bool, str]:
    """
    Validate FRAMEWORK-PATHS.md exists and is current.

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        aops_root = get_aops_root()
    except RuntimeError as e:
        return False, f"Environment not configured: {e}"

    framework_paths = aops_root / "FRAMEWORK-PATHS.md"

    # Check existence
    if not framework_paths.exists():
        return False, (
            f"FRAMEWORK-PATHS.md not found at {framework_paths}\n"
            f"Run: python3 aops-core/scripts/generate_framework_paths.py"
        )

    # Read and parse file
    try:
        content = framework_paths.read_text()
    except Exception as e:
        return False, f"Failed to read FRAMEWORK-PATHS.md: {e}"

    # Extract generated timestamp from frontmatter
    # Format: generated: 2026-01-13T08:47:01.548202+00:00
    timestamp_match = re.search(r"^generated:\s*([^\n]+)", content, re.MULTILINE)

    if not timestamp_match:
        return False, (
            "FRAMEWORK-PATHS.md is missing 'generated' field in frontmatter.\n"
            "This file should be auto-generated. "
            "Run: python3 aops-core/scripts/generate_framework_paths.py"
        )

    timestamp_str = timestamp_match.group(1).strip()

    # Parse ISO 8601 timestamp
    try:
        generated_time = datetime.fromisoformat(timestamp_str)
        # Ensure timezone-aware
        if generated_time.tzinfo is None:
            generated_time = generated_time.replace(tzinfo=timezone.utc)
    except ValueError as e:
        return False, f"Invalid timestamp format in FRAMEWORK-PATHS.md: {e}"

    # Check if stale (>7 days old)
    now = datetime.now(timezone.utc)
    age = now - generated_time
    max_age = timedelta(days=7)

    if age > max_age:
        return False, (
            f"FRAMEWORK-PATHS.md is stale (generated {age.days} days ago).\n"
            f"File may contain outdated paths.\n"
            f"Run: python3 aops-core/scripts/generate_framework_paths.py"
        )

    # Check that file contains "## Resolved Paths" section
    if "## Resolved Paths" not in content:
        return False, (
            "FRAMEWORK-PATHS.md is missing '## Resolved Paths' section.\n"
            "This file may be malformed. "
            "Run: python3 aops-core/scripts/generate_framework_paths.py"
        )

    # All checks passed
    return True, "FRAMEWORK-PATHS.md is valid and current"


def main() -> int:
    """
    Main entry point for pre-commit hook.

    Returns:
        int: Exit code (0=success, 1=failure)
    """
    success, message = validate_framework_paths()

    if success:
        # Validation passed - print nothing (pre-commit hook best practice)
        return 0
    else:
        # Validation failed - print error to stderr
        print("=" * 70, file=sys.stderr)
        print("PRE-COMMIT VALIDATION FAILED", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        print(file=sys.stderr)
        print(message, file=sys.stderr)
        print(file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
