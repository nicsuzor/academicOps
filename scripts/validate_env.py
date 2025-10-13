#!/usr/bin/env python3
"""
SessionStart hook to enforce reading core instruction files.

This script is called by Claude Code at the start of every session.
It forces agents to read the hierarchical instruction files by injecting
them as additional context.

Exit codes:
    0: Success (continue with session)
    1: Error (halt session)

Output:
    Prints instructions that will be injected into agent context
"""

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
    repo_root = get_repo_root()

    # Required instruction files (in load order)
    generic_instructions = repo_root / "bot" / "agents" / "INSTRUCTIONS.md"
    user_instructions = repo_root / "docs" / "agents" / "INSTRUCTIONS.md"

    # Read both files
    generic_content = read_instruction_file(generic_instructions)
    user_content = read_instruction_file(user_instructions)

    # Check for errors
    if generic_content.startswith("ERROR:") or user_content.startswith("ERROR:"):
        print(f"CRITICAL: Failed to load required instruction files", file=sys.stderr)
        print(generic_content, file=sys.stderr)
        print(user_content, file=sys.stderr)
        sys.exit(1)

    # Construct the additional context message in the correct format for SessionStart hooks
    # See: https://docs.claude.com/en/docs/claude-code/hooks
    context = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": f"""# Required Agent Instructions

The following instruction files have been loaded and MUST be followed:

## 1. Generic Agent Rules (bot/agents/INSTRUCTIONS.md)

{generic_content}

---

## 2. User-Specific Context (docs/agents/INSTRUCTIONS.md)

{user_content}

---

**These instructions are MANDATORY. They override any default behaviors.**
"""
        }
    }

    # Output as JSON for Claude Code to parse
    print(json.dumps(context, indent=2))

    # Also print a simple reminder to stderr (visible to user)
    print("✓ Loaded core instruction files", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
