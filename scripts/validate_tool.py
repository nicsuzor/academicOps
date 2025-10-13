#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Validates tool usage against agent permissions.

This script enforces agent-specific tool restrictions using a modular rule system.

Exit codes:
- 0: Allow tool use
- 2: Block tool use (shows stderr message to agent)
"""

import json
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Callable, Optional


# ============================================================================
# Rule System - Define tool restrictions here
# ============================================================================


@dataclass
class ValidationRule:
    """A rule that validates tool usage against agent permissions."""

    name: str
    """Human-readable name for this rule"""

    tool_patterns: list[str] = field(default_factory=list)
    """List of tool name patterns (supports wildcards like 'mcp__github__*')"""

    file_patterns: list[str] = field(default_factory=list)
    """List of file path patterns (supports wildcards like 'bot/**', '**/.claude/**')"""

    command_patterns: list[str] = field(default_factory=list)
    """List of command patterns for Bash tools (e.g., '*git commit*')"""

    allowed_agents: set[str] = field(default_factory=set)
    """Set of agent names that are allowed to use this tool"""

    custom_matcher: Optional[Callable[[str, dict], bool]] = None
    """Optional custom matcher function for complex logic"""

    get_context: Callable[[dict], str] = lambda _: ""
    """Function that extracts context info for error messages"""

    def _matches_tool(self, tool_name: str) -> bool:
        """Check if tool name matches any tool patterns."""
        if not self.tool_patterns:
            return False
        return any(fnmatch(tool_name, pattern) for pattern in self.tool_patterns)

    def _matches_file(self, file_path: str) -> bool:
        """Check if file path matches any file patterns."""
        if not self.file_patterns:
            return False

        # Normalize path for consistent matching
        path = Path(file_path).as_posix()

        for pattern in self.file_patterns:
            # Handle different pattern styles
            if fnmatch(path, pattern):
                return True
            # Also check if any part of the path matches (for **/.claude/** style)
            if "**" in pattern:
                # Extract the key directory from pattern
                key_parts = [p for p in pattern.split("/") if p and p != "**"]
                path_parts = path.split("/")
                if any(key in path_parts for key in key_parts):
                    return True

        return False

    def _matches_command(self, command: str) -> bool:
        """Check if command matches any command patterns."""
        if not self.command_patterns:
            return False
        return any(fnmatch(command, pattern) for pattern in self.command_patterns)

    def matches(self, tool_name: str, tool_input: dict) -> bool:
        """Check if this rule applies to the tool call."""
        # Use custom matcher if provided
        if self.custom_matcher:
            return self.custom_matcher(tool_name, tool_input)

        # Tool pattern matching
        if self.tool_patterns and not self._matches_tool(tool_name):
            return False

        # File pattern matching (for Write/Edit/MultiEdit tools)
        if self.file_patterns:
            file_path = tool_input.get("file_path", "")
            if not file_path or not self._matches_file(file_path):
                return False

        # Command pattern matching (for Bash tool)
        if self.command_patterns:
            if tool_name != "Bash":
                return False
            command = tool_input.get("command", "")
            if not command or not self._matches_command(command):
                return False

        # If we have patterns and got here, we matched
        return bool(self.tool_patterns or self.file_patterns or self.command_patterns)

    def check(
        self, tool_name: str, tool_input: dict, active_agent: str
    ) -> tuple[bool, Optional[str]]:
        """Check if tool use is allowed and return (allowed, error_message)."""
        if not self.matches(tool_name, tool_input):
            return (True, None)

        if active_agent in self.allowed_agents:
            return (True, None)

        # Build error message
        context = self.get_context(tool_input)
        agents_list = "', '".join(sorted(self.allowed_agents))

        error = (
            f"❌ BLOCKED: {self.name}\n"
            f"   Active agent: {active_agent}\n"
            f"   Allowed agents: '{agents_list}'\n"
        )

        if context:
            error += f"   Context: {context}\n"

        error += f"\n   To perform this action:\n"

        if len(self.allowed_agents) == 1:
            agent = list(self.allowed_agents)[0]
            error += f"   1. Switch to agent: @agent-{agent}\n"
        else:
            error += (
                f"   1. Switch to one of: "
                + ", ".join(f"@agent-{a}" for a in sorted(self.allowed_agents))
                + "\n"
            )

        error += f"   2. Or request user to perform the action manually"

        return (False, error)


# Define all validation rules here using declarative patterns
VALIDATION_RULES = [
    ValidationRule(
        name="Protected file modifications restricted to trainer agent",
        tool_patterns=["Write", "Edit", "MultiEdit"],
        file_patterns=[
            "bot/*",
            "bot/**/*",
            "**/.claude/*",
            "**/.gemini/*",
            "**/agents/*",
        ],
        allowed_agents={"trainer"},
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
    ),
    ValidationRule(
        name="Git commits restricted to code-review agent",
        tool_patterns=[
            "Bash",
            "mcp__github__create_or_update_file",
            "mcp__github__push_files",
        ],
        command_patterns=["*git commit*"],
        allowed_agents={"code-review"},
        custom_matcher=lambda tool_name, tool_input: (
            # Bash: match git commit commands without --no-verify
            (
                tool_name == "Bash"
                and "git commit" in tool_input.get("command", "")
                and "--no-verify" not in tool_input.get("command", "")
            )
            # MCP GitHub tools that create commits
            or tool_name
            in {"mcp__github__create_or_update_file", "mcp__github__push_files"}
        ),
        get_context=lambda tool_input: (
            f"command: {tool_input.get('command', '')[:80]}"
            if "command" in tool_input
            else f"commit message: {tool_input.get('message', '')[:60]}"
            if "message" in tool_input
            else ""
        ),
    ),
]


def validate_tool_use(
    tool_name: str, tool_input: dict, active_agent: str
) -> tuple[bool, str | None]:
    """
    Validate if the active agent is allowed to use this tool.

    Args:
        tool_name: Name of the tool being called (e.g., 'Write', 'Edit')
        tool_input: Tool input parameters
        active_agent: Name of the active agent

    Returns:
        (allowed: bool, error_message: str | None)
    """
    # Check all validation rules
    for rule in VALIDATION_RULES:
        allowed, error = rule.check(tool_name, tool_input, active_agent)
        if not allowed:
            return (False, error)

    return (True, None)


def main():
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(2)

    # Extract tool information
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    active_agent = tool_input.get("subagent_type", "unknown")

    # Validate tool use
    allowed, error_message = validate_tool_use(tool_name, tool_input, active_agent)

    # Debug: Save input for inspection
    debug_file = Path("/tmp/claude-tool-input.json")
    debug_data = dict(input=input_data, allowed=allowed, error_message=error_message)
    with debug_file.open("a") as f:
        json.dump(debug_data, f, indent=None)
    if not allowed:
        print(error_message, file=sys.stderr)
        # sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
