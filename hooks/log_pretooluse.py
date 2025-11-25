#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Minimal logging.

Logs PreToolUse events to data/sessions/<date>-<hash>-hooks.jsonl

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import re
import sys
from datetime import UTC, datetime
from typing import Any

from hooks.hook_logger import log_hook_event


# Destructive git operations that should be blocked
DESTRUCTIVE_GIT_PATTERNS = [
    r"git\s+reset\s+--hard",  # git reset --hard
    r"git\s+clean\s+-[fd]",  # git clean -f or -fd
    r"git\s+push\s+--force",  # git push --force (any branch)
    r"git\s+checkout\s+--\s+\.",  # git checkout -- . (discard all changes)
    r"git\s+stash\s+drop",  # git stash drop
]


def validate_minimal_documentation(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """
    Enforce MINIMAL principle for documentation files.

    Blocks creation of:
    - *-GUIDE.md files (e.g., INSTALLATION-GUIDE.md)
    - .md files exceeding 200 lines

    Returns:
        None if validation passes (continue)
        Dict with {"continue": False, "systemMessage": "..."} if blocked
    """
    if tool_name != "Write":
        return None

    file_path = args.get("file_path", "")
    content = args.get("content", "")

    # Block *-GUIDE.md files (e.g., INSTALLATION-GUIDE.md, USER-GUIDE.md)
    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path.upper():
        return {
            "continue": False,
            "systemMessage": (
                "❌ BLOCKED: *-GUIDE.md files violate MINIMAL principle.\n\n"
                "User explicitly: 'I hate installation guides. I hate long documents.'\n"
                "CLAUDE.md: 'the watchword is MINIMAL. We are ACTIVELY FIGHTING bloat.'\n\n"
                "Instead:\n"
                "- Add 2 sentences to README.md\n"
                "- Installation docs belong in package's auto-generated INSTALL.md\n"
                "- Never create separate guide files\n\n"
                "See: Issue #202"
            )
        }

    # Block .md files exceeding 200 lines
    if file_path.endswith(".md"):
        line_count = len(content.split("\n"))
        if line_count > 200:
            return {
                "continue": False,
                "systemMessage": (
                    f"❌ BLOCKED: {line_count} lines violates MINIMAL principle.\n\n"
                    "Documentation limits:\n"
                    "- Skills: 500 lines max\n"
                    "- Docs/chunks: 300 lines max\n"
                    "- General docs: 200 lines max\n\n"
                    "Consider:\n"
                    "- Is this documentation necessary?\n"
                    "- Can it be 2 sentences in README instead?\n"
                    "- Should it be split into focused chunks in docs/chunks/?\n\n"
                    "User values: 'efficiency over lengthy explanation'\n\n"
                    "See: Issue #202"
                )
            }

    return None


def validate_safe_git_usage(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """
    Enforce safe git practices (AXIOM 12: Git Safety Protocol).

    Blocks destructive git operations:
    - git reset --hard
    - git clean -f/-fd
    - git push --force to main/master
    - git checkout -- .
    - git stash drop

    Returns:
        None if validation passes (continue)
        Dict with {"continue": False, "systemMessage": "..."} if blocked
    """
    if tool_name != "Bash":
        return None

    command = args.get("command", "")

    # Check for destructive git patterns
    for pattern in DESTRUCTIVE_GIT_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "continue": False,
                "systemMessage": (
                    f"❌ BLOCKED: Destructive git command detected.\n\n"
                    f"Command: {command}\n\n"
                    f"AXIOM 12 (Git Safety Protocol):\n"
                    f"- NEVER run destructive/irreversible git commands\n"
                    f"- git reset --hard: Use git reset --soft or git reset --mixed instead\n"
                    f"- git clean -f: Review files first with git clean -n\n"
                    f"- git push --force: NEVER force push to main/master\n"
                    f"- git checkout -- .: Discard changes selectively, not all at once\n"
                    f"- git stash drop: Use git stash apply/pop instead\n\n"
                    f"Safe alternatives preserve work and enable recovery.\n"
                    f"Ask user for explicit confirmation if destruction is truly needed."
                ),
            }

    return None


def main():
    """Main hook entry point - logs and validates."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        # If no stdin or parsing fails, continue with empty input
        input_data = json.load(sys.stdin)

    session_id = input_data.get("session_id", "unknown")
    tool_name = input_data.get("tool", "")
    args = input_data.get("args", {})

    # Determine output based on validation
    output_data: dict[str, Any] = {}

    # Validate MINIMAL documentation principle
    validation_result = validate_minimal_documentation(tool_name, args)
    if validation_result is not None:
        output_data = validation_result
    else:
        # Validate safe git usage
        validation_result = validate_safe_git_usage(tool_name, args)
        if validation_result is not None:
            output_data = validation_result

    # Log to hooks session file (includes both input and output)
    log_hook_event(session_id, "PreToolUse", input_data, output_data)

    # Output result
    print(json.dumps(output_data))
    sys.exit(0)


if __name__ == "__main__":
    main()
