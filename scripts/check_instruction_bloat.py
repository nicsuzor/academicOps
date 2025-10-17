#!/usr/bin/env python3
"""
Pre-commit hook to prevent instruction bloat in agent files.

Enforces anti-bloat protocol by blocking commits that grow instruction files
beyond acceptable thresholds (25 lines OR 20% growth).

Related issues: #116, #87
"""

import subprocess
import sys
from pathlib import Path


def get_file_line_count(file_path: str, commit: str = "HEAD") -> int:
    """Get line count of a file at a specific commit."""
    try:
        result = subprocess.run(
            ["git", "show", f"{commit}:{file_path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.splitlines())
    except subprocess.CalledProcessError:
        # File doesn't exist in previous commit (new file)
        return 0


def get_staged_line_count(file_path: str) -> int:
    """Get line count of currently staged version."""
    try:
        result = subprocess.run(
            ["git", "show", f":{file_path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.splitlines())
    except subprocess.CalledProcessError:
        # File not staged or deleted
        return 0


def check_instruction_file(file_path: str) -> tuple[bool, str]:
    """
    Check if instruction file growth exceeds thresholds.

    Returns: (is_valid, error_message)
    """
    old_lines = get_file_line_count(file_path)
    new_lines = get_staged_line_count(file_path)

    # File deleted or not staged
    if new_lines == 0:
        return True, ""

    # New file - allow without restriction
    if old_lines == 0:
        return True, ""

    # Calculate growth
    lines_added = new_lines - old_lines
    percent_growth = (lines_added / old_lines * 100) if old_lines > 0 else 0

    # Threshold: 25 lines OR 20% growth (either triggers block)
    lines_threshold = 25
    percent_threshold = 20

    if lines_added > lines_threshold or percent_growth > percent_threshold:
        return (
            False,
            f"""
INSTRUCTION BLOAT DETECTED: {file_path}

  Old size: {old_lines} lines
  New size: {new_lines} lines
  Growth:   +{lines_added} lines ({percent_growth:.1f}%)

  THRESHOLD EXCEEDED: {lines_added} lines > {lines_threshold} OR {percent_growth:.1f}% > {percent_threshold}%

⛔ COMMIT BLOCKED - Anti-Bloat Protocol (issue #116, #87)

Before adding instructions, you MUST check the Enforcement Hierarchy:

  Q1: Can SCRIPTS prevent this problem? → Write validation/automation code
  Q2: Can HOOKS enforce this? → Add pre-commit or SessionStart hook
  Q3: Can CONFIG block this? → Update .claude/settings.json permissions
  Q4: Can TEMPLATES provide this? → Create reusable template file

Instructions are the LAST RESORT (agents forget in long conversations).

If you've verified Q1-Q4 and instructions are truly necessary:

  1. Document in GitHub issue why architectural solutions won't work
  2. Get user approval for large instruction additions
  3. Bypass this check: git commit --no-verify

See bot/agents/TRAINER.md (Phase 2, Steps 6-7) for full protocol.
""",
        )

    return True, ""


def main() -> int:
    """Main entry point for pre-commit hook."""
    # Get list of staged instruction files
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        capture_output=True,
        text=True,
        check=True,
    )

    staged_files = result.stdout.strip().split("\n")

    # Filter to instruction files only
    instruction_patterns = [
        "bot/agents/*.md",
        "docs/agents/*.md",
        "projects/*/agents/*.md",
    ]

    instruction_files = []
    for file_path in staged_files:
        path = Path(file_path)
        if path.suffix == ".md" and any(
            path.match(pattern) for pattern in instruction_patterns
        ):
            instruction_files.append(file_path)

    if not instruction_files:
        # No instruction files staged, nothing to check
        return 0

    # Check each instruction file
    failed = False
    for file_path in instruction_files:
        is_valid, error_msg = check_instruction_file(file_path)
        if not is_valid:
            print(error_msg, file=sys.stderr)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
