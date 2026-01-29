#!/usr/bin/env python3
"""
PreToolUse command interceptor for Claude Code.

Intercepts and transforms tool calls before execution. Modular design with
configurable transformers per tool. No-op by default when unconfigured.

Uses Claude Code's `updatedInput` capability to modify tool parameters
without blocking execution.

Architecture:
    1. Load config from $ACA_DATA/command_intercept.yaml
    2. Check if tool_name has registered transformer
    3. If yes: apply transformation, return updatedInput
    4. If no: pass through (no-op)

Exit codes:
    0: Success (transformation applied or pass-through)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

# Config location
ACA_DATA = os.environ.get("ACA_DATA", str(Path.home() / ".aca"))
CONFIG_PATH = Path(ACA_DATA) / "command_intercept.yaml"

# Default exclusion patterns for Glob
DEFAULT_GLOB_EXCLUDES = [
    ".venv",
    "node_modules",
    "__pycache__",
    ".git",
    "*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]


def load_config() -> dict[str, Any]:
    """
    Load configuration from YAML file.

    Returns:
        Config dict, or empty dict if file doesn't exist.
    """
    if not CONFIG_PATH.exists():
        return {}

    try:
        with open(CONFIG_PATH) as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception:
        return {}


def glob_pattern_to_fd_args(pattern: str) -> str:
    """
    Convert a glob pattern to fd arguments.

    Examples:
        **/*.py -> -e .py
        **/*.{ts,tsx} -> -e .ts -e .tsx
        src/**/*.js -> -e .js (in src/)
        *.md -> -e .md -d 1
    """
    # Extract extension from pattern
    if pattern.startswith("**/"):
        # Recursive pattern like **/*.py
        remainder = pattern[3:]  # Remove **/
        if remainder.startswith("*."):
            ext = remainder[1:]  # .py
            return f"-e '{ext}'"
    elif pattern.startswith("*."):
        # Non-recursive like *.md
        ext = pattern[1:]
        return f"-e '{ext}' -d 1"

    # For complex patterns, just search by glob
    return f"-g '{pattern}'"


def transform_glob(
    tool_input: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None, bool]:
    """
    Transform Glob to fd command.

    Since Glob doesn't support exclusions, we block and suggest fd instead.
    fd respects .gitignore by default, solving the .venv problem.

    Args:
        tool_input: Original Glob parameters (pattern, path)
        config: Transformer config with exclusion patterns

    Returns:
        Tuple of (updated_input or None, context_message or None, should_block)
    """
    # Get exclusion patterns from config, or use defaults
    transformers = config.get("transformers", [])
    exclude_patterns = DEFAULT_GLOB_EXCLUDES

    for t in transformers:
        if t.get("name") == "exclude_directories":
            patterns = t.get("config", {}).get("patterns")
            if patterns:
                exclude_patterns = patterns
            break

    pattern = tool_input.get("pattern", "")
    search_path = tool_input.get("path", ".")

    # Build fd command
    fd_args = glob_pattern_to_fd_args(pattern)

    # Add explicit excludes for patterns not in .gitignore
    exclude_flags = " ".join(f"-E '{p}'" for p in exclude_patterns)

    # fd syntax: fd [OPTIONS] [pattern] [path]
    fd_command = f"fd {fd_args} {exclude_flags} . '{search_path}'"

    context = f"Glob blocked: use fd instead (respects .gitignore).\nRun: {fd_command}"

    # Return should_block=True to deny the Glob call
    return None, context, True


def transform_grep(
    tool_input: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None, bool]:
    """
    Transform Grep to rg command.

    Block Grep and suggest rg instead for consistency with fd substitution.
    rg respects .gitignore by default.

    Args:
        tool_input: Original Grep parameters
        config: Transformer config

    Returns:
        Tuple of (updated_input or None, context_message or None, should_block)
    """
    pattern = tool_input.get("pattern", "")
    search_path = tool_input.get("path", ".")
    file_type = tool_input.get("type", "")
    glob_filter = tool_input.get("glob", "")
    case_insensitive = tool_input.get("-i", False)
    context_lines = tool_input.get("-C", 0)
    before_lines = tool_input.get("-B", 0)
    after_lines = tool_input.get("-A", 0)

    # Build rg command
    rg_args = []

    # Case insensitive
    if case_insensitive:
        rg_args.append("-i")

    # Context lines
    if context_lines:
        rg_args.append(f"-C {context_lines}")
    else:
        if before_lines:
            rg_args.append(f"-B {before_lines}")
        if after_lines:
            rg_args.append(f"-A {after_lines}")

    # File type filter
    if file_type:
        rg_args.append(f"-t {file_type}")

    # Glob filter
    if glob_filter:
        rg_args.append(f"-g '{glob_filter}'")

    # Line numbers by default
    rg_args.append("-n")

    args_str = " ".join(rg_args)
    rg_command = f"rg {args_str} '{pattern}' '{search_path}'"

    context = f"Grep blocked: use rg instead (respects .gitignore).\nRun: {rg_command}"

    return None, context, True


def transform_tool(
    tool_name: str, tool_input: dict[str, Any], config: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None, bool]:
    """
    Apply transformation for a specific tool.

    Args:
        tool_name: Name of the tool (Glob, Grep, etc.)
        tool_input: Original tool parameters
        config: Full config dict

    Returns:
        Tuple of (updated_input or None, context_message or None, should_block)
    """
    tools_config = config.get("tools", {})
    tool_config = tools_config.get(tool_name, {})

    # Check if tool is enabled
    if not tool_config.get("enabled", False):
        return None, None, False

    # Dispatch to tool-specific transformer
    if tool_name == "Glob":
        return transform_glob(tool_input, tool_config)
    elif tool_name == "Grep":
        return None, None, False
        # <!-- NS: I think this is broken for gemini at the moment. -->
        return transform_grep(tool_input, tool_config)

    return None, None, False


def main() -> None:
    """Main hook entry point."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # No input or invalid JSON - pass through
        print(json.dumps({}))
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if not tool_name:
        # No tool name - pass through
        print(json.dumps({}))
        sys.exit(0)

    # Load config
    config = load_config()

    # Check master switch
    if not config.get("enabled", True):
        # Disabled globally - pass through
        print(json.dumps({}))
        sys.exit(0)

    # Apply transformation
    updated_input, context, should_block = transform_tool(tool_name, tool_input, config)

    # Build output
    if updated_input is None and context is None and not should_block:
        # No transformation - pass through
        print(json.dumps({}))
        sys.exit(0)

    output: dict[str, Any] = {}

    if should_block:
        # Block the tool call and provide alternative
        output = {"verdict": "deny", "context_injection": context if context else None}
    elif updated_input is not None:
        # Allow with modified input
        output = {"verdict": "allow", "metadata": {"updated_input": updated_input}}
        if context:
            output["context_injection"] = context
    elif context is not None:
        # Advisory only (Warn/Allow with context)
        # Using 'warn' to signify attention needed, which maps to allowed with context in Claude
        output = {"verdict": "warn", "context_injection": context}
    else:
        # Pass through empty
        output = {}

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
