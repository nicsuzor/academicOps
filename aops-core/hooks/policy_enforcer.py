#!/usr/bin/env python3
"""
PreToolUse policy enforcer for Claude Code.

Blocks operations that violate framework principles:
- MINIMAL: *-GUIDE.md files, .md files > 200 lines
- Git Safety: destructive git commands

Exit codes:
    0: Always (JSON output determines allow/deny via permissionDecision field)
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



def count_prose_lines(content: str) -> int:
    """Count lines excluding mermaid/code blocks."""
    lines = content.split("\n")
    count = 0
    in_code_block = False

    for line in lines:
        # Toggle on code fence (``` or ```mermaid, etc.)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if not in_code_block:
            count += 1

    return count


def validate_minimal_documentation(
    tool_name: str, args: dict[str, Any]
) -> dict[str, Any] | None:
    """Block *-GUIDE.md files and .md files > 200 prose lines."""
    if tool_name != "Write":
        return None

    if "file_path" not in args:
        raise ValueError("Write tool args requires 'file_path' parameter (P#8: fail-fast)")
    if "content" not in args:
        raise ValueError("Write tool args requires 'content' parameter (P#8: fail-fast)")
    file_path = args["file_path"]
    content = args["content"]

    if file_path.endswith("-GUIDE.md") or "GUIDE.md" in file_path.upper():
        return {
            "continue": False,
            "systemMessage": (
                "BLOCKED: *-GUIDE.md files violate MINIMAL principle.\n"
                "Add 2 sentences to README.md instead."
            ),
        }

    if file_path.endswith(".md"):
        prose_lines = count_prose_lines(content)
        if prose_lines > 200:
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: {prose_lines} prose lines exceeds 200 line limit.\n"
                    "(Code/mermaid blocks excluded from count.)\n"
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

    if "command" not in args:
        raise ValueError("Bash tool args requires 'command' parameter (P#8: fail-fast)")
    command = args["command"]

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

    if "tool_name" not in input_data:
        raise ValueError("input_data requires 'tool_name' parameter (P#8: fail-fast)")
    if "tool_input" not in input_data:
        raise ValueError("input_data requires 'tool_input' parameter (P#8: fail-fast)")
    tool_name = input_data["tool_name"]
    args = input_data["tool_input"]

    # Check policies in order
    result = validate_minimal_documentation(tool_name, args)
    if result is None:
        result = validate_safe_git_usage(tool_name, args)

    # If blocking, use JSON permissionDecision:deny with exit 0
    # Exit 0 ensures Claude Code processes the JSON output (exit 2 ignores stdout)
    if result and result.get("continue") is False:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "additionalContext": result.get("systemMessage", "BLOCKED by policy")
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Allow: output JSON to stdout, exit 0
    if result is None:
        result = {}
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
