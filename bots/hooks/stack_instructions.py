#!/usr/bin/env python3
"""
PostToolUse hook: Stack instructions from 3 tiers when reading bot/prompts/*.

When an agent reads a file in bot/prompts/, this hook augments the result with:
1. Framework tier (bot/prompts/FILE.md) - already read
2. User tier ($ACADEMICOPS_PERSONAL/prompts/FILE.md) - if exists
3. Project tier ($CLAUDE_PROJECT_DIR/prompts/FILE.md) - if exists

This enables 3-tier instruction inheritance without manual file management.
"""

import json
import os
import sys
from pathlib import Path


def load_tier(tier_path: Path) -> str | None:
    """Load a tier's content if it exists."""
    if not tier_path.exists():
        return None
    try:
        return tier_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {tier_path}: {e}", file=sys.stderr)
        return None


def stack_instructions(tool_use: dict, tool_result: dict) -> dict:
    """
    Stack instructions from 3 tiers if reading bot/prompts/*.

    Args:
        tool_use: The original tool use (contains tool name and parameters)
        tool_result: The result from the Read tool

    Returns:
        Hook output dict with systemMessage containing stacked instructions
    """
    # Only process Read tool
    if tool_use.get("tool") != "Read":
        return {}

    # Only process reads to bot/prompts/*
    file_path = tool_use.get("params", {}).get("file_path", "")
    if "bot/prompts/" not in file_path and "bots/prompts/" not in file_path:
        return {}

    # Extract filename from path
    filename = Path(file_path).name

    # Framework tier already in tool_result (that's what they just read)
    framework_content = tool_result.get("content", "")

    # User tier
    user_tier_path = None
    if academicops_personal := os.getenv("ACADEMICOPS_PERSONAL"):
        user_tier_path = Path(academicops_personal) / "prompts" / filename

    # Project tier
    project_tier_path = None
    if claude_project_dir := os.getenv("CLAUDE_PROJECT_DIR"):
        project_tier_path = Path(claude_project_dir) / "prompts" / filename

    # Load additional tiers
    user_content = load_tier(user_tier_path) if user_tier_path else None
    project_content = load_tier(project_tier_path) if project_tier_path else None

    # Build stacked message
    parts = []

    # Framework tier (always present since they just read it)
    parts.append("# Framework Tier (bot/prompts/)")
    parts.append(framework_content)

    # User tier (if exists)
    if user_content:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(f"# User Tier ({user_tier_path})")
        parts.append(user_content)

    # Project tier (if exists)
    if project_content:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(f"# Project Tier ({project_tier_path})")
        parts.append(project_content)

    # Only add system message if we have additional tiers
    if user_content or project_content:
        stacked_message = "\n".join(parts)
        return {
            "systemMessage": f"**3-Tier Stacked Instructions Loaded:**\n\n{stacked_message}"
        }

    return {}


def main():
    """PostToolUse hook entry point."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_use = hook_input.get("toolUse", {})
        tool_result = hook_input.get("toolResult", {})

        # Stack instructions if applicable
        result = stack_instructions(tool_use, tool_result)

        # Output hook result
        print(json.dumps(result))

    except Exception as e:
        # Fail gracefully - don't block workflow
        print(json.dumps({}), file=sys.stdout)
        print(f"Error in stack_instructions hook: {e}", file=sys.stderr)
        sys.exit(0)  # Exit 0 to not block


if __name__ == "__main__":
    main()
