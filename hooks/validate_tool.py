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
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from hook_debug import safe_log_to_debug_file
from hook_models import PreToolUseHookOutput, PreToolUseOutput

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

    custom_matcher: Callable[[str, dict], bool] | None = None
    """Optional custom matcher function for complex logic"""

    get_context: Callable[[dict], str] = lambda _: ""
    """Function that extracts context info for error messages"""

    get_fix_guidance: Callable[[dict], str] | None = None
    """Optional function that provides specific guidance on how to fix the error"""

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
    ) -> tuple[bool, str | None, str]:
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
            error += "\n   This operation requires explicit user confirmation."
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

            # Add specific fix guidance if available
            if self.get_fix_guidance:
                fix_guidance = self.get_fix_guidance(tool_input)
                if fix_guidance:
                    error += f"\n   How to fix:\n{fix_guidance}\n"
            else:
                # Generic guidance if no specific fix available
                error += (
                    "\n   This is a hard prohibition enforced by the validation system.\n"
                    "   If you believe this operation should be allowed, contact the user."
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

            error += "\n   To perform this action:\n"

            if len(self.allowed_agents) == 1:
                agent = next(iter(self.allowed_agents))
                error += f"   1. Switch to agent: @agent-{agent}\n"
            else:
                error += (
                    "   1. Switch to one of: "
                    + ", ".join(f"@agent-{a}" for a in sorted(self.allowed_agents))
                    + "\n"
                )

            error += "   2. Or request user to perform the action manually"

        return (False, error, self.severity)


# Define all validation rules here using declarative patterns
# IMPORTANT: Rules are checked in order. More specific rules should come before general rules.
VALIDATION_RULES = [
    ValidationRule(
        name="killall command is prohibited - too dangerous on shared machine",
        severity="block",
        tool_patterns=["Bash"],
        allowed_agents=set(),  # No agents allowed - hard prohibition
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash"
            and any(
                # Match killall as a command (with word boundaries)
                part.strip().startswith("killall ")
                or part.strip() == "killall"
                or " killall " in part
                for part in tool_input.get("command", "").split(";")
            )
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', 'unknown')}",
        get_fix_guidance=lambda tool_input: (
            "   CRITICAL: This machine runs multiple projects simultaneously.\n"
            "   You must target THIS PROJECT'S processes specifically.\n"
            "   \n"
            "   Instead of 'killall' or generic patterns:\n"
            "   ❌ WRONG: kill $(pgrep -f python)      # Kills ALL Python processes\n"
            "   ❌ WRONG: pkill streamlit               # Kills ALL Streamlit instances\n"
            "   ❌ WRONG: killall node                  # Kills ALL Node processes\n"
            "   \n"
            "   ✅ CORRECT approaches:\n"
            "   1. Use project-specific pattern with full path:\n"
            "      kill $(pgrep -f '/full/path/to/this/project')\n"
            "   \n"
            "   2. List processes first, verify they're yours, then kill specific PID:\n"
            "      ps aux | grep '/path/to/project'\n"
            "      kill <specific-pid>\n"
            "   \n"
            "   3. Use port-based targeting if applicable:\n"
            "      lsof -ti:8501 | xargs kill  # Only if you know the port is yours\n"
        ),
    ),
    ValidationRule(
        name="Generic process termination patterns are too broad - must be project-specific",
        severity="warn",  # Warn instead of block - allows override with caution
        tool_patterns=["Bash"],
        allowed_agents=set(),
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash"
            and (
                # Match dangerous generic patterns
                "pgrep -f python" in tool_input.get("command", "")
                or "pgrep -f node" in tool_input.get("command", "")
                or "pgrep -f streamlit" in tool_input.get("command", "")
                or "pkill python" in tool_input.get("command", "")
                or "pkill node" in tool_input.get("command", "")
                or "pkill streamlit" in tool_input.get("command", "")
                or "pkill -f python" in tool_input.get("command", "")
                or "pkill -f node" in tool_input.get("command", "")
                or "pkill -f streamlit" in tool_input.get("command", "")
            )
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', 'unknown')}",
        get_fix_guidance=lambda tool_input: (
            "   This pattern will affect ALL projects on this machine.\n"
            "   \n"
            "   Use project-specific targeting:\n"
            "   - Include full path: pgrep -f '/full/path/to/this/project/'\n"
            '   - Use working directory: pgrep -f "$PWD"\n'
            "   - Verify PIDs before acting: ps aux | grep <pattern> | grep $PWD\n"
        ),
    ),
    ValidationRule(
        name="Protected file modifications restricted to trainer agent",
        severity="warn",
        tool_patterns=["Write", "Edit", "MultiEdit"],
        file_patterns=[
            "**/.claude/*",
            "**/.gemini/*",
        ],
        allowed_agents={"trainer"},
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
    ),
    ValidationRule(
        name="All code should be self-documenting; no new documentation allowed",
        severity="warn",  # Changed from block to warn - allows override with warning
        tool_patterns=["Write"],
        allowed_agents={"trainer"},  # Trainer can create any .md file if truly needed
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Write"
            and tool_input.get("file_path", "").lower().endswith(".md")
            and not _is_allowed_md_path(tool_input.get("file_path", ""))
        ),
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
    ),
    ValidationRule(
        name="Git commits restricted to code-review agent",
        severity="warn",
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
        name="Files in /tmp prohibited - violates academicOps axiom #5 (build for replication)",
        severity="block",
        tool_patterns=["Write"],
        allowed_agents=set(),  # No exceptions - hard block for all agents
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Write"
            and tool_input.get("file_path", "").startswith("/tmp/")
            and (
                "test" in tool_input.get("file_path", "").lower()
                or tool_input.get("file_path", "").endswith(".py")
            )
        ),
        get_context=lambda tool_input: f"file: {tool_input.get('file_path', 'unknown')}",
        get_fix_guidance=lambda tool_input: (
            "   - WHY: /tmp files violate academicOps axiom #5 - we build infrastructure for\n"
            "     long-term replication, not single-use throwaway scripts.\n"
            "   - FIX: Create test in proper project location:\n"
            "     1. Identify the project (e.g., 'buttermilk' in projects/buttermilk/)\n"
            "     2. Create test: Write(projects/<project>/tests/test_<feature>.py, your_code)\n"
            "     3. Add to git: git add projects/<project>/tests/test_<feature>.py\n"
            "     4. Run: uv run pytest projects/<project>/tests/test_<feature>.py\n"
            "   - POLICY: All tests must be permanent, versioned, and replicable.\n"
            "   - ONLY exception: /tmp is allowed ONLY for trainer agent doing diagnostics."
        ),
    ),
    ValidationRule(
        name="Inline Python execution (python -c) is prohibited. Create a proper test file instead.",
        severity="warn",  # Changed from block to warn - allows ad-hoc analysis with warning
        tool_patterns=["Bash"],
        allowed_agents=set(),  # Warning for all agents, but not blocked
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash"
            and bool(re.search(r"\bpython[3]?\s+-c\b", tool_input.get("command", "")))
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', '')[:80]}",
        get_fix_guidance=lambda tool_input: (
            "   - WHY: Inline Python code creates unreproducible, untestable one-off scripts.\n"
            "   - FIX: Write your code to a proper test file instead:\n"
            "     1. Identify the project (e.g., 'buttermilk' in projects/buttermilk/)\n"
            "     2. Create test: Write(projects/<project>/tests/test_<feature>.py, your_code)\n"
            "     3. Run it: uv run pytest projects/<project>/tests/test_<feature>.py\n"
            "   - POLICY: All code must be in files for reproducibility and testing."
        ),
    ),
    ValidationRule(
        name="You must use 'uv run ...' to activate python environments for python-based tools.",
        severity="block",
        tool_patterns=["Bash"],
        allowed_agents=set(),  # Empty set means no agents are "allowed" (always triggers)
        custom_matcher=lambda tool_name, tool_input: (
            tool_name == "Bash" and _requires_uv_run(tool_input.get("command", ""))
        ),
        get_context=lambda tool_input: f"command: {tool_input.get('command', '')[:80]}",
        get_fix_guidance=lambda tool_input: (
            f"   - WHY: Python tools must run in the project's virtual environment.\n"
            f"   - FIX: Prefix your command with 'uv run':\n"
            f"     ❌ {tool_input.get('command', '')[:60]}\n"
            f"     ✅ uv run {tool_input.get('command', '')[:60]}\n"
            f"   - EXAMPLES:\n"
            f"     • uv run python script.py\n"
            f"     • uv run pytest tests/\n"
            f"     • uv run python -m module_name"
        ),
    ),
]


def _is_allowed_md_path(file_path: str) -> bool:
    """
    Check if .md file is in an allowed path.

    BLOCKED locations:
    - Project root (top-level .md files like README.md, HOWTO.md)
    - docs/ directory (documentation files)

    ALLOWED locations (content directories in $AO):
    - talks/ - Presentation content
    - slides/ - Slide decks
    - data/ - Data files

    Everything else is allowed (pre-commit hook provides comprehensive validation).

    This hook prevents the MOST COMMON mistake: creating docs in project root.
    The pre-commit hook provides full validation with user override option.

    Separation of concerns:
    - This hook: Prevent common real-time mistakes
    - Pre-commit: Comprehensive validation (bot/*, papers/*, etc.)
    """
    if not file_path:
        return False

    # Convert to Path object
    path_obj = Path(file_path)

    # If absolute path, convert to relative path from cwd
    if path_obj.is_absolute():
        try:
            cwd = Path.cwd()
            path_obj = path_obj.relative_to(cwd)
        except ValueError:
            # Path outside cwd - allow (pre-commit will catch if problematic)
            return True

    # Convert to POSIX string for pattern matching
    path = path_obj.as_posix()

    # ALLOW: Content directories in $AO (writing repo)
    # These are legitimate content artifacts, not documentation
    personal_path = os.getenv("AOPS")
    if personal_path:
        cwd = Path.cwd()
        personal_dir = Path(personal_path).resolve()
        if cwd.resolve() == personal_dir:
            # We're in the personal repo - allow content directories
            content_dirs = ["talks/", "slides/", "data/"]
            if any(path.startswith(d) for d in content_dirs):
                return True

    # BLOCK: Top-level .md files in project root
    # Example: README.md, HOWTO.md, GUIDE.md
    if "/" not in path:
        return False

    # BLOCK: Files in docs/ directory
    # Example: docs/README.md, docs/API.md
    if path.startswith("docs/"):
        return False

    # Allow everything else
    # Pre-commit hook will provide comprehensive validation
    return True


def _requires_uv_run(command: str) -> bool:
    """
    Check if a command should be run with 'uv run' prefix.

    Returns True if:
    - Command starts with python-related tools (python, pytest, fastapi, streamlit, fastmcp)
    - The python tool is NOT prefixed with 'uv run'
    - Skips tools invoked as Python modules (e.g., 'python -m pytest')

    Examples:
    - "python script.py" -> True (warn)
    - "uv run python script.py" -> False (no warn)
    - "timeout 60 python script.py" -> True (warn)
    - "timeout 60 uv run python script.py" -> False (no warn)
    - "uv run python -m pytest" -> False (no warn, pytest invoked via python -m)
    - "gh issue comment ... python ..." -> False (python in args, not command)
    """
    if not command:
        return False

    command_lower = command.lower()

    # Python-related commands that should use uv run
    python_tools = ["python", "pytest", "fastapi", "streamlit", "fastmcp"]

    # Split command into tokens, handling common shell patterns
    # We only check if the COMMAND itself (not arguments) is a Python tool
    # Split on whitespace and shell operators, but only check early tokens
    tokens = re.split(r"[\s;&|]+", command_lower.strip())

    # Check first few tokens (to handle cases like "timeout 60 python script.py")
    # We check up to 6 tokens to handle wrappers with arguments
    for i, token in enumerate(tokens[:6]):
        # Skip empty tokens
        if not token:
            continue

        # Skip numeric tokens (arguments to wrappers like "timeout 60")
        if re.match(r"^\d+$", token):
            continue

        # Skip common command wrappers that don't need uv run
        if token in ["timeout", "nice", "env", "time", "sudo", "sh", "bash"]:
            continue

        # Check if this token is a Python tool
        for tool in python_tools:
            # Match exact tool name (with optional version number like python3)
            if re.match(rf"^{re.escape(tool)}(?:\d+)?$", token):
                # Found a Python tool as the actual command
                # Now check if it's properly prefixed with 'uv run'

                # Look at tokens before this one
                before_tokens = tokens[:i]

                # Skip if invoked via 'python -m' (check NEXT token)
                # Example: "python -m pytest" should be allowed without uv run
                # because it's invoking a module via python, not a standalone tool
                if i + 1 < len(tokens) and tokens[i + 1] == "-m":
                    # This is 'python -m <module>' pattern
                    # The python itself still needs 'uv run' prefix
                    # So we DON'T skip - we continue checking for 'uv run'
                    pass
                # Also check if this is a module name after 'python -m'
                # Example: in "python -m pytest", when we find "pytest" token,
                # we check if it came after "-m"
                elif i > 0 and tokens[i - 1] == "-m":
                    # This tool is a module name (e.g., 'pytest' in 'python -m pytest')
                    # Skip validation - it's covered by the python validation
                    continue

                # Check if 'uv run' appears in the tokens before this tool
                # We need both 'uv' and 'run' to appear consecutively
                has_uv_run = False
                for j in range(len(before_tokens) - 1):
                    if before_tokens[j] == "uv" and before_tokens[j + 1] == "run":
                        has_uv_run = True
                        break

                if not has_uv_run:
                    # Python tool found without 'uv run' prefix
                    return True

        # If we found a non-wrapper, non-Python command, stop checking
        # (the actual command is something else, like 'gh', 'git', 'echo', etc.)
        if token not in [
            "timeout",
            "nice",
            "env",
            "time",
            "sudo",
            "sh",
            "bash",
            "uv",
            "run",
        ] and not re.match(r"^\d+$", token):
            break

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
        input_data["argv"] = sys.argv
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        sys.exit(2)

    # Extract tool information
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    # Note: Claude Code enforces agent tool restrictions via frontmatter `tools` field
    # This hook only validates patterns (paths, commands, operations)
    active_agent = "unknown"  # Not used for validation

    # Validate tool use
    allowed, error_message, severity = validate_tool_use(
        tool_name, tool_input, active_agent
    )
    exit_code = 0

    # Map severity to permissionDecision and exit code
    if allowed:
        permission_decision = "allow"
        exit_code = 0
    elif severity == "force-ask":
        permission_decision = "ask"
        exit_code = 0
    elif severity == "warn":
        # Warnings don't block execution, but show a message
        permission_decision = "allow"
        exit_code = 1
    else:
        permission_decision = "deny"
        exit_code = 2  # Block execution

    # Build output using Pydantic models
    hook_output = PreToolUseOutput(
        hookSpecificOutput=PreToolUseHookOutput(
            permissionDecision=permission_decision,
            permissionDecisionReason=error_message,
        )
    )

    # Convert to dict for JSON serialization
    output_dict = hook_output.model_dump(by_alias=True, exclude_none=True)

    # Debug log hook execution
    safe_log_to_debug_file("PreToolUse", input_data, output_dict)

    # Output JSON to stdout (Claude Code hook specification)
    print(json.dumps(output_dict))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
