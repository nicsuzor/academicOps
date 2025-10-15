#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Validates tool usage against agent permissions.

This script enforces agent-specific tool restrictions using a modular rule system.

Exit codes:
- 0: Allow tool use (includes user prompts)
- 1: Warn (allow with warning message)
- 2: Block tool use (shows stderr message to agent)
"""

import json
import re
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

    severity: str = "block"
    """Severity level: 'block' (hard deny), 'warn' (allow with warning), or 'force-ask' (prompt user)"""

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
    ) -> tuple[bool, Optional[str], str]:
        """Check if tool use is allowed and return (allowed, error_message, severity)."""
        if not self.matches(tool_name, tool_input):
            return (True, None, self.severity)

        # For force-ask, we always want to prompt regardless of allowed_agents
        if self.severity == "force-ask":
            # Continue to build the message below
            pass
        elif active_agent in self.allowed_agents:
            return (True, None, self.severity)

        # Build error message
        context = self.get_context(tool_input)

        # Use appropriate prefix based on severity
        if self.severity == "warn":
            prefix = "⚠️ WARNING:"
        elif self.severity == "force-ask":
            prefix = "❓ CONFIRMATION REQUIRED:"
        else:
            prefix = "❌ BLOCKED:"

        # For warnings, simplify the message (no need for agent switching instructions)
        if self.severity == "warn":
            error = f"{prefix} {self.name}\n"
            if context:
                error += f"   Context: {context}\n"
            return (False, error, self.severity)

        # For force-ask, provide context for user decision
        if self.severity == "force-ask":
            error = f"{prefix} {self.name}\n"
            if context:
                error += f"   Context: {context}\n"
            error += f"\n   This operation requires explicit user confirmation."
            return (False, error, self.severity)

        # For blocks, include full instructions
        if not self.allowed_agents:
            # Hard prohibition - no agents allowed
            error = (
                f"{prefix} {self.name}\n"
                f"   Active agent: {active_agent}\n"
                f"   This operation is prohibited for all agents.\n"
            )

            if context:
                error += f"   Context: {context}\n"

            error += (
                f"\n   This is a hard prohibition enforced by the validation system.\n"
                f"   If you believe this operation should be allowed, contact the user."
            )
        else:
            # Agent-restricted operation
            agents_list = "', '".join(sorted(self.allowed_agents))
            error = (
                f"{prefix} {self.name}\n"
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

        return (False, error, self.severity)


# Define all validation rules here using declarative patterns
# IMPORTANT: Rules are checked in order. More specific rules should come before general rules.
VALIDATION_RULES = [
    ValidationRule(
        name="Protected file modifications restricted to trainer agent",
        tool_patterns=["Write", "Edit", "MultiEdit"],
        file_patterns=[
            "**/.claude/*",
            "**/.gemini/*",
        ],
        allowed_agents={"trainer"},
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
        severity="block",
    ),
    ValidationRule(
        name="All code should be self-documenting; no new documentation allowed",
        tool_patterns=["Write"],
        allowed_agents={"trainer"},  # Trainer can create any .md file if truly needed
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Write"
            and tool_input.get("file_path", "").lower().endswith(".md")
            and not _is_allowed_md_path(tool_input.get("file_path", ""))
        ),
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
        severity="block",
    ),
    ValidationRule(
        name="Git commits restricted to code-review agent",
        severity="block",
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
    ValidationRule(
        name="Inline Python execution (python -c) is prohibited. Create a proper test file instead.",
        severity="block",
        tool_patterns=["Bash"],
        allowed_agents=set(),  # No exceptions - hard block for all agents
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash"
            and bool(re.search(r"\bpython[3]?\s+-c\b", tool_input.get("command", "")))
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', '')[:80]}",
    ),
    ValidationRule(
        name="You must use 'uv run ...' to activate python environments for python-based tools.",
        severity="warn",
        tool_patterns=["Bash"],
        allowed_agents=set(),  # Empty set means no agents are "allowed" (always triggers)
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash" and _requires_uv_run(tool_input.get("command", ""))
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', '')[:80]}",
    ),
]


def _is_allowed_md_path(file_path: str) -> bool:
    """
    Check if .md file is in an allowed path (mirrors pre-commit hook logic).

    Allowed paths:
    - bot/agents/*.md: Agent instructions (executable behavior definitions)
    - papers/**/*.md: Research papers
    - manuscripts/**/*.md: Manuscript drafts
    - projects/*/papers/**/*.md: Project-specific research papers
    - projects/*/manuscripts/**/*.md: Project-specific manuscript drafts

    Everything else is considered documentation and is prohibited per Axiom #5.

    NOTE: Claude Code passes absolute paths to this function, so we need to
    convert them to relative paths for pattern matching.
    """
    if not file_path:
        return False

    # Convert to Path object
    path_obj = Path(file_path)

    # If absolute path, convert to relative path from cwd
    # This handles the case where Claude Code passes absolute paths
    if path_obj.is_absolute():
        try:
            # Get current working directory
            cwd = Path.cwd()
            # Convert to relative path
            path_obj = path_obj.relative_to(cwd)
        except ValueError:
            # Path is not relative to cwd, return False (block it)
            # Files outside the working directory should not be created
            return False

    # Convert to POSIX string for pattern matching
    path = path_obj.as_posix()

    # Allow agent instructions (these ARE executable code)
    if re.match(r"^bot/agents/.*\.md$", path):
        return True

    # Allow research papers in top-level papers/ directory
    if re.match(r"^papers/.*\.md$", path):
        return True

    # Allow manuscripts in top-level manuscripts/ directory
    if re.match(r"^manuscripts/.*\.md$", path):
        return True

    # Allow project manuscripts and papers
    if re.match(r"^projects/[^/]+/(papers|manuscripts)/.*\.md$", path):
        return True

    return False


def _requires_uv_run(command: str) -> bool:
    """
    Check if a command should be run with 'uv run' prefix.

    Returns True if:
    - Command contains python-related tools (python, pytest, fastapi, streamlit, fastmcp)
    - The python tool is NOT prefixed with 'uv run'

    Examples:
    - "python script.py" -> True (warn)
    - "uv run python script.py" -> False (no warn)
    - "timeout 60 python script.py" -> True (warn)
    - "timeout 60 uv run python script.py" -> False (no warn)
    """
    if not command:
        return False

    command_lower = command.lower()

    # Python-related commands that should use uv run
    python_tools = ["python", "pytest", "fastapi", "streamlit", "fastmcp"]

    for tool in python_tools:
        # Look for the tool with word boundaries, capturing the position
        # Word boundary patterns: start of string, after whitespace, or after shell operators
        pattern = r"(^|[\s;&|])({tool}(?:\d+)?)(?:$|[\s;&|])".format(
            tool=re.escape(tool)
        )

        for match in re.finditer(pattern, command_lower):
            # Get the position where the tool starts
            tool_start = match.start(2)

            # Look backwards from the tool to check if 'uv run' appears immediately before
            before_tool = command_lower[:tool_start]

            # Check if 'uv run' appears at the end of before_tool (with optional whitespace)
            if not re.search(r'uv\s+run\s*$', before_tool):
                # This tool invocation is not prefixed with 'uv run'
                return True

    return False


def validate_tool_use(
    tool_name: str, tool_input: dict, active_agent: str
) -> tuple[bool, str | None, str]:
    """
    Validate if the active agent is allowed to use this tool.

    Args:
        tool_name: Name of the tool being called (e.g., 'Write', 'Edit')
        tool_input: Tool input parameters
        active_agent: Name of the active agent

    Returns:
        (allowed: bool, error_message: str | None, severity: str)
    """
    # Check all validation rules
    for rule in VALIDATION_RULES:
        allowed, error, severity = rule.check(tool_name, tool_input, active_agent)
        if not allowed:
            return (False, error, severity)

    return (True, None, "block")


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
    allowed, error_message, severity = validate_tool_use(
        tool_name, tool_input, active_agent
    )
    should_continue = True
    systemMessage = None
    exit_code = 0

    # Map severity to permissionDecision
    if allowed:
        allow_message = "allow"
        should_continue = True
        exit_code = 0

    elif severity == "force-ask":
        allow_message = "ask"
        systemMessage = error_message
        should_continue = False  # Pause execution until user confirms
        exit_code = 0
    elif severity == "warn":
        # Warnings don't block execution, but show a message
        allow_message = "allow"
        should_continue = True
        systemMessage = error_message
        exit_code = 1
    else:
        allow_message = "deny"
        should_continue = False
        exit_code = 2  # Block execution

    # Format for claude code
    output = {
        # Whether Claude should continue after hook execution (default: true)
        # it seems like we shouldn't have 'continue' be true if we are denying permission
        "continue": should_continue,
        # Message shown when continue is false
        "stopReason": None,
        "suppressOutput": False,  # Hide stdout from transcript mode (default: false)
        "systemMessage": systemMessage,  # Optional warning message shown to the user
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            # permissionDecision": "allow" | "deny" | "ask",
            #    "allow" bypasses the permission system. permissionDecisionReason is shown to the user but not to Claude.
            #    "deny" prevents the tool call from executing. permissionDecisionReason is shown to Claude.
            #    "ask" asks the user to confirm the tool call in the UI. permissionDecisionReason is shown to the user but not to Claude.
            "permissionDecision": allow_message,
            "permissionDecisionReason": error_message,
        },
    }


    # Debug: Save input for inspection
    debug_file = Path("/tmp/claude-tool-input.json")
    debug_data = dict(input=input_data, output=output)
    with debug_file.open("a") as f:
        json.dump(debug_data, f, indent=None)
        f.write("\n")

    print(json.dumps(output), file=sys.stderr)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
