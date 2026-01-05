#!/usr/bin/env python3
"""
PreToolUse policy enforcer for Claude Code.

Blocks operations that violate framework principles:
- MINIMAL: *-GUIDE.md files, .md files > 200 lines
- Git Safety: destructive git commands

Exit codes (per Claude Code docs):
    0: Allow - JSON output on stdout is processed
    2: Block - only stderr is read (message shown to Claude)
"""

import contextlib
import json
import re
import sys
from typing import Any


# Destructive git operations that should be blocked
DESTRUCTIVE_GIT_PATTERNS = [
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[fd]",
    r"git\s+push\s+--force",
    r"git\s+checkout\s+--\s+\.",
    r"git\s+stash\s+drop",
]


def validate_minimal_documentation(
    tool_name: str, args: dict[str, Any]
) -> dict[str, Any] | None:
    """Block *-GUIDE.md files and .md files > 200 lines."""
    if tool_name != "Write":
        return None

    file_path = args.get("file_path", "")
    content = args.get("content", "")

    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path.upper():
        return {
            "continue": False,
            "systemMessage": (
                "BLOCKED: *-GUIDE.md files violate MINIMAL principle.\n"
                "Add 2 sentences to README.md instead."
            ),
        }

    if file_path.endswith(".md"):
        line_count = len(content.split("\n"))
        if line_count > 200:
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: {line_count} lines exceeds 200 line limit for docs.\n"
                    "Split into focused chunks or reduce content."
                ),
            }

    return None


def validate_safe_git_usage(
    tool_name: str, args: dict[str, Any]
) -> dict[str, Any] | None:
    """Block destructive git operations."""
    if tool_name != "Bash":
        return None

    command = args.get("command", "")

    for pattern in DESTRUCTIVE_GIT_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: Destructive git command.\n"
                    f"Command: {command}\n"
                    f"Use safe alternatives or ask user for explicit confirmation."
                ),
            }

    return None


def main():
    """Main hook entry point - validates and returns result."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    args = input_data.get("tool_input", {})

    # Check policies in order
    result = validate_minimal_documentation(tool_name, args)
    if result is None:
        result = validate_safe_git_usage(tool_name, args)

    # If blocking, write message to stderr and exit 2
    # Per Claude Code docs: exit code 2 = block, only stderr is read
    if result and result.get("continue") is False:
        print(result.get("systemMessage", "BLOCKED by policy"), file=sys.stderr)
        sys.exit(2)

    # Allow: output JSON to stdout, exit 0
    print(json.dumps(result or {}))
    sys.exit(0)


if __name__ == "__main__":
    main()
