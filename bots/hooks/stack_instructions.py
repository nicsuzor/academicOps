#!/usr/bin/env python3
"""
PostToolUse hook: Stack instructions from 3 tiers when reading /bots/**/*.md.

When an agent reads a file matching /bots/**/*.md, this hook provides stacked content:
1. Framework tier ($ACADEMICOPS_BOT/bots/...) - REQUIRED
2. Personal tier ($ACADEMICOPS_PERSONAL/bots/...) - if exists
3. Project tier ($PWD/bots/...) - if exists

This enables 3-tier instruction inheritance without manual file management.

CRITICAL: This hook fires even when the Read fails (file doesn't exist in working dir).
This is by design - it allows us to provide stacked content for files that only exist
in framework/personal tiers, not in the current project.
"""

import json
import os
import sys
from pathlib import Path

from hook_debug import safe_log_to_debug_file


def load_tier(tier_path: Path) -> str | None:
    """Load a tier's content if it exists."""
    if not tier_path.exists():
        return None
    try:
        return tier_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {tier_path}: {e}", file=sys.stderr)
        return None


def extract_bots_relative_path(file_path: str) -> str | None:
    """
    Extract the relative path within /bots/ directory.

    Examples:
        /bots/agents/DEVELOPER.md -> agents/DEVELOPER.md
        /home/user/project/bots/agents/trainer.md -> agents/trainer.md
        /something/else.md -> None
    """
    # Normalize path
    path_str = str(Path(file_path).as_posix())

    # Check if "bots" is a component of the path
    if "bots" not in Path(file_path).parts:
        return None

    # Extract everything after /bots/
    try:
        bots_index = path_str.index("/bots/")
        relative_path = path_str[bots_index + 6:]  # +6 to skip "/bots/"
        return relative_path
    except ValueError:
        return None


def stack_instructions(tool_name: str, tool_input: dict, tool_response: dict) -> dict:
    """
    Stack instructions from 3 tiers if reading /bots/**/*.md.

    Args:
        tool_name: The name of the tool that was used
        tool_input: The input parameters to the tool
        tool_response: The result from the tool (may contain error if file not found)

    Returns:
        Hook output dict with additionalContext containing stacked instructions
    """
    # Only process Read tool
    if tool_name != "Read":
        return {}

    # Only process reads to /bots/**/*.md
    file_path = tool_input.get("file_path", "")
    relative_path = extract_bots_relative_path(file_path)

    if not relative_path:
        return {}

    # Only process .md files
    if not relative_path.endswith(".md"):
        return {}

    # Get tier paths
    bot_path = os.getenv("ACADEMICOPS_BOT")
    personal_path = os.getenv("ACADEMICOPS_PERSONAL")
    project_path = Path.cwd()

    # Framework tier (REQUIRED)
    framework_tier_path = None
    if bot_path:
        framework_tier_path = Path(bot_path) / "bots" / relative_path

    # Personal tier (OPTIONAL)
    personal_tier_path = None
    if personal_path:
        personal_tier_path = Path(personal_path) / "bots" / relative_path

    # Project tier (OPTIONAL)
    project_tier_path = project_path / "bots" / relative_path

    # Load content from each tier
    framework_content = load_tier(framework_tier_path) if framework_tier_path else None
    personal_content = load_tier(personal_tier_path) if personal_tier_path else None
    project_content = load_tier(project_tier_path) if project_tier_path else None

    # Framework tier is REQUIRED
    if not framework_content:
        # No stacking possible without framework tier
        return {}

    # Build stacked content
    parts = []

    # Framework tier (base)
    parts.append(f"# Framework Tier: {relative_path}")
    parts.append(f"_Source: {framework_tier_path}_")
    parts.append("")
    parts.append(framework_content)

    # Personal tier (if exists)
    if personal_content:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(f"# Personal Tier: {relative_path}")
        parts.append(f"_Source: {personal_tier_path}_")
        parts.append("")
        parts.append(personal_content)

    # Project tier (if exists)
    if project_content:
        parts.append("")
        parts.append("---")
        parts.append("")
        parts.append(f"# Project Tier: {relative_path}")
        parts.append(f"_Source: {project_tier_path}_")
        parts.append("")
        parts.append(project_content)

    # Build final stacked message
    stacked_message = "\n".join(parts)

    # Determine if original Read succeeded or failed
    read_failed = "error" in tool_response or not tool_response.get("success", True)

    # Build context message
    if read_failed:
        # Read failed (file doesn't exist in project) - provide full stacked content
        tiers_loaded = ["framework"]
        if personal_content:
            tiers_loaded.append("personal")
        if project_content:
            tiers_loaded.append("project")

        context_header = (
            f"**3-Tier Stacked Instructions**: `{relative_path}`\n\n"
            f"_Loaded from: {' → '.join(tiers_loaded)}_\n\n"
            "---\n\n"
        )
        additional_context = context_header + stacked_message
    else:
        # Read succeeded (file exists in project) - supplement with other tiers
        if personal_content or project_content:
            tiers_loaded = []
            if personal_content:
                tiers_loaded.append("personal")
            if project_content:
                tiers_loaded.append("project")

            context_header = (
                f"**Additional tier(s) found for** `{relative_path}`:\n\n"
                f"_Supplementing with: {', '.join(tiers_loaded)}_\n\n"
                "---\n\n"
            )
            additional_context = context_header + stacked_message
        else:
            # Only framework tier exists, which was already read
            return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": additional_context,
        }
    }


def main():
    """PostToolUse hook entry point."""
    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        tool_name = hook_input.get("tool_name", "")
        tool_input = hook_input.get("tool_input", {})
        tool_response = hook_input.get("tool_response", {})

        # Stack instructions if applicable
        result = stack_instructions(tool_name, tool_input, tool_response)

        # Debug log hook execution
        safe_log_to_debug_file("PostToolUse", hook_input, result)

        # Output hook result (always output valid JSON)
        if result:
            print(json.dumps(result))
        else:
            # Empty result means no stacking needed
            print(json.dumps({}))

    except Exception as e:
        # Fail gracefully - don't block workflow
        print(json.dumps({}), file=sys.stdout)
        print(f"Error in stack_instructions hook: {e}", file=sys.stderr)
        sys.exit(0)  # Exit 0 to not block


if __name__ == "__main__":
    main()
