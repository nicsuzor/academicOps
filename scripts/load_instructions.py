#!/usr/bin/env python3
"""
SessionStart hook to enforce reading core instruction files.

This script is called by Claude Code at the start of every session.
It forces agents to read the hierarchical instruction files by injecting
them as additional context.

Loading Hierarchy:
1. Framework Core (REQUIRED): $ACADEMICOPS_BOT/agents/_CORE.md
2. Personal Context (OPTIONAL): $ACADEMICOPS_PERSONAL/docs/agents/INSTRUCTIONS.md
3. Project Context (OPTIONAL): $PWD/bots/docs/INSTRUCTIONS.md
   - Falls back to: $PWD/docs/bots/INSTRUCTIONS.md (legacy support)

Input: JSON with session start source.

Exit codes:
    0: Success (stdout shown to Claude)
    2: Blocking errors are ignored
    other exit codes: show stderr to user only

Output:
    Prints instructions on STDOUT that will be injected into agent context
"""

import datetime
import json
import os
import sys
from pathlib import Path


def get_academicops_root() -> Path:
    """
    Find the academicOps framework root using environment variable.

    Returns the academicOps root directory.
    Raises ValueError if ACADEMICOPS_BOT is not set.
    """
    if env_path := os.environ.get("ACADEMICOPS_BOT"):
        return Path(env_path).resolve()

    # ACADEMICOPS_BOT is required - no fallback
    raise ValueError(
        "ACADEMICOPS_BOT environment variable is not set. "
        "Add to your shell profile: export ACADEMICOPS_BOT=/path/to/academicOps"
    )


def get_personal_context_root() -> Path | None:
    """
    Find personal context directory using environment variable.

    Returns None if not found (personal context is optional).
    """
    # Check environment variable
    if env_path := os.environ.get("ACADEMICOPS_PERSONAL"):
        path = Path(env_path).resolve()
        if path.exists():
            return path
        # ACADEMICOPS_PERSONAL is set but path doesn't exist - warn but continue
        print(f"Warning: ACADEMICOPS_PERSONAL is set but path does not exist: {env_path}", file=sys.stderr)

    # No personal context found (this is OK - it's optional)
    return None


def get_project_root() -> Path:
    """Find the current project root (where Claude Code was launched from)."""
    return Path.cwd()


def read_instruction_file(path: Path) -> str:
    """Read an instruction file and return its contents."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return f"ERROR: Required instruction file not found: {path}"
    except Exception as e:
        return f"ERROR: Failed to read {path}: {e}"


def get_project_instructions_path(project_root: Path) -> Path | None:
    """
    Find project-specific instructions following the new /bots/ structure.
    
    Search order:
    1. bots/docs/INSTRUCTIONS.md (NEW standard)
    2. docs/bots/INSTRUCTIONS.md (LEGACY support)
    3. docs/agents/INSTRUCTIONS.md (LEGACY support)
    
    Returns the first found path, or None if none exist.
    """
    # Preferred: new /bots/ structure
    new_path = project_root / "bots" / "docs" / "INSTRUCTIONS.md"
    if new_path.exists():
        return new_path
    
    # Legacy: docs/bots/ (previous standard)
    legacy_bots = project_root / "docs" / "bots" / "INSTRUCTIONS.md"
    if legacy_bots.exists():
        return legacy_bots
    
    # Legacy: docs/agents/ (oldest standard)
    legacy_agents = project_root / "docs" / "agents" / "INSTRUCTIONS.md"
    if legacy_agents.exists():
        return legacy_agents
    
    # No project instructions found
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}
    input_data["argv"] = sys.argv

    # Get paths using environment variables or fallbacks
    academicops_root = get_academicops_root()
    personal_root = get_personal_context_root()
    project_root = get_project_root()

    # Required: Core framework instructions
    generic_instructions = academicops_root / "agents" / "_CORE.md"
    generic_content = read_instruction_file(generic_instructions)

    if generic_content.startswith("ERROR:"):
        print("CRITICAL: Failed to load core framework instructions", file=sys.stderr)
        print(generic_content, file=sys.stderr)
        print(f"Searched at: {generic_instructions}", file=sys.stderr)
        print(f"ACADEMICOPS_BOT={os.environ.get('ACADEMICOPS_BOT', 'not set')}", file=sys.stderr)
        sys.exit(1)

    # Optional: Personal context
    user_content = ""
    if personal_root:
        user_instructions = personal_root / "docs" / "agents" / "INSTRUCTIONS.md"
        user_content = read_instruction_file(user_instructions)
        if user_content.startswith("ERROR:"):
            # Personal context is optional - just note it
            print(f"Note: Personal context not found at {user_instructions}", file=sys.stderr)
            user_content = ""

    # Optional: Project-specific instructions (with legacy fallback)
    project_content = ""
    project_instructions = get_project_instructions_path(project_root)
    
    if project_instructions:
        # Don't load if it's the same as personal context
        if personal_root and project_instructions == (personal_root / "docs" / "agents" / "INSTRUCTIONS.md"):
            print(f"Note: Project instructions same as personal context, skipping duplicate", file=sys.stderr)
        else:
            project_content = read_instruction_file(project_instructions)
            if project_content.startswith("ERROR:"):
                project_content = ""
            else:
                # Inform user which path was used
                if "bots/docs" in str(project_instructions):
                    print(f"✓ Loaded project instructions from bots/docs/INSTRUCTIONS.md", file=sys.stderr)
                else:
                    print(f"✓ Loaded project instructions from {project_instructions.relative_to(project_root)} (legacy location)", file=sys.stderr)

    # Build context based on what's available
    sections = []

    if user_content:
        sections.append(f"""## PRIMARY: Your Work Context

{user_content}""")

    if project_content:
        sections.append(f"""## PROJECT: Current Project Context

{project_content}""")

    sections.append(f"""## BACKGROUND: Framework Operating Rules

{generic_content}""")

    additional_context = "# Required Agent Instructions\n\n" + "\n\n---\n\n".join(sections)
    additional_context += "\n\n---\n\n**Priority**: Your strategic goals and active projects take precedence. Framework development happens when needed, not by default.\n"

    # Construct the additional context message in the correct format for SessionStart hooks
    # See: https://docs.claude.com/en/docs/claude-code/hooks
    context = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }

    # Output as JSON for Claude Code to parse
    print(json.dumps(context), file=sys.stdout)

    # Status message to stderr
    loaded = ["core"]
    if user_content:
        loaded.append("personal")
    if project_content:
        loaded.append("project")
    print(f"✓ Loaded {', '.join(loaded)} instruction files", file=sys.stderr)

    # Debug: Save input for inspection
    debug_file = Path("/tmp/validate_env.json")
    debug_data = {
        "input": input_data,
        "output": context,
        "timestamp": datetime.datetime.now().isoformat(),
        "paths": {
            "academicops_root": str(academicops_root),
            "personal_root": str(personal_root) if personal_root else None,
            "project_root": str(project_root),
            "project_instructions": str(project_instructions) if project_instructions else None,
        },
    }
    with debug_file.open("a") as f:
        json.dump(debug_data, f, indent=None)
        f.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
