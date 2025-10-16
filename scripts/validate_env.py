#!/usr/bin/env python3
"""
SessionStart hook to enforce reading core instruction files.

This script is called by Claude Code at the start of every session.
It forces agents to read the hierarchical instruction files by injecting
them as additional context.

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
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Find the repository root (parent of bot/ submodule)."""
    # This script is at bot/scripts/validate_env.py
    # Repo root is two levels up
    script_path = Path(__file__).resolve()
    return script_path.parent.parent.parent


def read_instruction_file(path: Path) -> str:
    """Read an instruction file and return its contents."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return f"ERROR: Required instruction file not found: {path}"
    except Exception as e:
        return f"ERROR: Failed to read {path}: {e}"


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        input_data = {}
    input_data["argv"] = sys.argv

    repo_root = get_repo_root()

    # Required instruction files (in load order)
    generic_instructions = repo_root / "bot" / "agents" / "_CORE.md"
    user_instructions = repo_root / "docs" / "agents" / "INSTRUCTIONS.md"

    # Read both files
    generic_content = read_instruction_file(generic_instructions)
    user_content = read_instruction_file(user_instructions)

    # Check for errors
    if generic_content.startswith("ERROR:") or user_content.startswith("ERROR:"):
        print("CRITICAL: Failed to load required instruction files", file=sys.stderr)
        print(generic_content, file=sys.stderr)
        print(user_content, file=sys.stderr)
        sys.exit(1)

    # Construct the additional context message in the correct format for SessionStart hooks
    # See: https://docs.claude.com/en/docs/claude-code/hooks
    context = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"""# Required Agent Instructions

## PRIMARY: Your Work Context

{user_content}

---

## BACKGROUND: Framework Operating Rules

{generic_content}

---

**Priority**: Your strategic goals and active projects take precedence. Framework development happens when needed, not by default.
""",
        }
    }

    # Output as JSON for Claude Code to parse
    print(json.dumps(context), file=sys.stdout)

    # Also print a simple reminder to stderr (visible to user maybe?)
    print("✓ Loaded core instruction files", file=sys.stderr)

    # Debug: Save input for inspection
    debug_file = Path("/tmp/validate_env.json")
    debug_data = {
        "input": input_data,
        "output": context,
        "tiemstamp": datetime.datetime.now().isoformat(),
    }
    with debug_file.open("a") as f:
        json.dump(debug_data, f, indent=None)
        f.write("\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
