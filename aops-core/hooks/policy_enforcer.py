#!/usr/bin/env python3
"""
PreToolUse policy enforcer for Claude Code.

Blocks operations that violate framework principles:
- MINIMAL: *-GUIDE.md files, .md files > 200 lines
- Git Safety: destructive git commands
- PKB Enforcement: direct filesystem reads of task markdown files

Exit codes:
    0: Always (JSON output determines allow/deny via permissionDecision field)
"""

import re
import sys
from pathlib import Path
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


def validate_minimal_documentation(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
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


def validate_safe_git_usage(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
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


def validate_protect_artifacts(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block modification of protected files (H#94)."""
    if tool_name not in ["Write", "Edit", "replace"]:
        return None

    # Handle both Claude Code (file_path) and Gemini CLI (file_path)
    file_path = args.get("file_path")
    if not file_path:
        return None

    # Load protected paths from project-local config
    protected_paths = []
    local_config = Path(".agent/rules/protected_paths.txt")
    if local_config.exists():
        try:
            protected_paths = [
                line.strip()
                for line in local_config.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            ]
        except Exception as e:
            print(f"WARNING: Failed to read {local_config}: {e}", file=sys.stderr)

    # Check if file_path matches any protected path
    for protected in protected_paths:
        if file_path.startswith(protected) or f"/{protected}" in file_path:
            return {
                "continue": False,
                "systemMessage": (
                    f"BLOCKED: Modification of protected path '{file_path}'.\n"
                    f"This path is protected by project-local rule (see .agent/rules/protected_paths.txt).\n"
                    "Modify source files instead and run build scripts if necessary."
                ),
            }

    return None


# Task file pattern: <project>-<uid>-<slug>.md files in data/tasks/ directories.
# These must be accessed via PKB MCP tools, not directly from the filesystem.
# Pattern matches any .md file anywhere inside a data/tasks/ subtree.
_TASK_MD_RE = re.compile(r"data/tasks/[^\s]*\.md")


def validate_no_direct_task_reads(tool_name: str, args: dict[str, Any]) -> dict[str, Any] | None:
    """Block direct filesystem access to task markdown files.

    Task files (data/tasks/**/<project>-<uid>-<slug>.md) must be accessed via
    PKB MCP tools (mcp__pkb__get_task, mcp__pkb__task_search, etc.), not by
    reading the filesystem directly. Direct reads cause token bloat and bypass
    the MCP server's consistency guarantees.
    """
    if tool_name not in ("Read", "Glob", "Grep"):
        return None

    # Normalise the relevant path argument for each tool
    if tool_name == "Read":
        path_str = str(args.get("file_path") or "")
    elif tool_name == "Glob":
        path_str = str(args.get("pattern") or args.get("path") or "")
    else:  # Grep
        path_str = str(args.get("path") or args.get("glob") or "")

    if not path_str:
        return None

    if _TASK_MD_RE.search(path_str):
        return {
            "continue": False,
            "systemMessage": (
                f"BLOCKED: Direct filesystem access to task file denied.\n"
                f"Path: {path_str}\n"
                "Use PKB MCP tools instead:\n"
                "  mcp__pkb__get_task(id='<task-id>')    — look up by ID\n"
                "  mcp__pkb__task_search(query='...')     — search by text\n"
                "  mcp__pkb__list_tasks(...)              — list tasks\n"
                "  mcp__pkb__pkb_context(...)             — task context\n"
                "See TOOLS.md § 'PKB Tool Usage' for the full reference."
            ),
        }

    return None
