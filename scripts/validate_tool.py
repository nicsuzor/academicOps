#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code: Validates tool usage against agent permissions.

This script enforces agent-specific tool restrictions. Currently implements:
- Write/Edit restrictions: Only 'trainer' agent can use Write/Edit tools

Exit codes:
- 0: Allow tool use
- 2: Block tool use (shows stderr message to agent)
"""
import json
import os
import sys
from pathlib import Path


def get_active_agent(transcript_path: str | None) -> str:
    """
    Detect the active agent from conversation transcript.

    Args:
        transcript_path: Path to the conversation JSONL file

    Returns:
        Agent name (e.g., 'trainer', 'developer') or 'unknown' if not detected
    """
    # Try environment variable first (for manual testing)
    agent = os.environ.get("CLAUDE_ACTIVE_AGENT")
    if agent:
        return agent

    # Read the transcript to find the most recent agent activation
    if not transcript_path or not Path(transcript_path).exists():
        return "unknown"

    try:
        # Read JSONL file line by line
        with open(transcript_path, "r") as f:
            lines = f.readlines()

        # Search backwards through conversation for @agent- mentions
        for line in reversed(lines):
            try:
                entry = json.loads(line)

                # Check if this is a user message with @agent- mention
                if entry.get("type") == "user_message":
                    content = entry.get("content", "")
                    if isinstance(content, str):
                        # Look for @agent-trainer, @agent-developer, etc.
                        import re

                        match = re.search(r"@agent-(\w+)", content)
                        if match:
                            return match.group(1)

            except (json.JSONDecodeError, KeyError):
                continue

    except Exception as e:
        # If we can't read transcript, log error but don't block
        print(f"Warning: Could not read transcript: {e}", file=sys.stderr)

    return "unknown"


def validate_tool_use(tool_name: str, tool_input: dict, active_agent: str) -> tuple[bool, str | None]:
    """
    Validate if the active agent is allowed to use this tool.

    Args:
        tool_name: Name of the tool being called (e.g., 'Write', 'Edit')
        tool_input: Tool input parameters
        active_agent: Name of the active agent

    Returns:
        (allowed: bool, error_message: str | None)
    """

    # Rule 1: Only trainer agent can use Write/Edit
    WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}

    if tool_name in WRITE_TOOLS:
        if active_agent != "trainer":
            file_path = tool_input.get("file_path", "unknown")
            return (
                False,
                f"❌ BLOCKED: Only 'trainer' agent can use {tool_name} tool.\n"
                f"   Active agent: {active_agent}\n"
                f"   Target file: {file_path}\n"
                f"   \n"
                f"   To make changes:\n"
                f"   1. Switch to trainer agent: @agent-trainer\n"
                f"   2. Or request user to make the change manually"
            )

    # Command validation rules (existing functionality)
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        issues = validate_command(command)
        if issues:
            return (False, "\n".join(f"• {msg}" for msg in issues))

    return (True, None)


def validate_command(command: str) -> list[str]:
    """Validate bash commands against best practices."""
    issues = []

    # Existing validation rules
    if "grep" in command and "|" not in command:
        issues.append("Use 'rg' (ripgrep) instead of 'grep' for better performance")

    if "find" in command and "-name" in command:
        issues.append("Use 'rg --files' instead of 'find -name' for better performance")

    return issues


def main():
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(2)

    # Debug: Save input for inspection
    debug_file = Path("/tmp/claude-tool-input.json")
    with debug_file.open("w") as f:
        json.dump(input_data, f, indent=2)

    # Extract tool information
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    transcript_path = input_data.get("transcript_path")

    # Detect active agent
    active_agent = get_active_agent(transcript_path)

    # Validate tool use
    allowed, error_message = validate_tool_use(tool_name, tool_input, active_agent)

    if not allowed:
        print(error_message, file=sys.stderr)
        sys.exit(2)  # Block the tool call

    # Allow the tool call
    sys.exit(0)


if __name__ == "__main__":
    main()
