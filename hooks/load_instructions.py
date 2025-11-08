#!/usr/bin/env python3
"""
Load instruction files from ${AOPS}.

MINIMAL. No three-tier pattern. Simple file loading.

Usage:
    # SessionStart hook (default: loads _CORE.md if exists, outputs JSON)
    load_instructions.py

    # Load specific file
    load_instructions.py DEVELOPER.md

Exit codes:
    0: Success (even if no files found - fail gracefully)
    1: Error (missing required env var)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file


def get_file_path(filename: str) -> Path | None:
    """
    Get path to instruction file in ${AOPS}/core/.

    Returns Path or None if AO not set.
    """
    if ao_path := os.environ.get("AOPS"):
        return Path(ao_path) / "aOps" / "core" / filename
    return None


def load_file_content(path: Path | None) -> str | None:
    """Load content from a file path. Returns None if missing."""
    if path is None or not path.exists():
        return None

    try:
        return path.read_text()
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None


def get_git_remote_info() -> str | None:
    """Get git remote origin URL if in a git repository."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def output_json(content: str | None, filename: str) -> None:
    """Output in JSON format for SessionStart hook."""
    if not content:
        # No content found - output empty hook response
        output = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": "",
            }
        }
        print(json.dumps(output), file=sys.stdout)
        print(f"ℹ No {filename} found (skipped)", file=sys.stderr)
        return

    # Get git remote info
    git_remote = get_git_remote_info()
    git_section = ""
    if git_remote:
        git_section = f"## REPOSITORY\n\nGit remote origin: {git_remote}\n\n---\n\n"

    additional_context = (
        f"# Agent Instructions\n\n{git_section}## FRAMEWORK: Core Rules\n\n{content}"
    )

    # Output JSON for Claude Code hook
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }

    print(json.dumps(output), file=sys.stdout)
    print(f"✓ Loaded {filename}", file=sys.stderr)


def output_text(content: str | None, filename: str) -> None:
    """Output in plain text format for slash commands."""
    if not content:
        print(f"No {filename} found", file=sys.stdout)
        return

    print(f"# === {filename} ===\n", file=sys.stderr)
    print(content, file=sys.stderr)
    print(f"\n✓ Loaded {filename}", file=sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        description="Load instruction files from ${AOPS}/core"
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default="_CORE.md",
        help="Instruction file to load (default: _CORE.md)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        help="Output format (default: json if _CORE.md, text otherwise)",
    )

    args = parser.parse_args()

    # Read input from stdin (hook input data)
    input_data: dict[str, Any] = {}
    try:
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Determine output format
    if args.format:
        output_format = args.format
    else:
        # Default: JSON for _CORE.md (SessionStart), text for others
        output_format = "json" if args.filename == "_CORE.md" else "text"

    # Get file path
    file_path = get_file_path(args.filename)
    if file_path is None:
        print("WARNING: AO environment variable not set", file=sys.stderr)
        print("Expected: export AO=/home/nic/src/writing", file=sys.stderr)
        # Fail gracefully - output empty response for SessionStart
        if output_format == "json":
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": "",
                }
            }
            print(json.dumps(output), file=sys.stdout)
        sys.exit(0)

    # Load content
    content = load_file_content(file_path)

    # Prepare output data for logging
    output_data: dict[str, Any] = {
        "filename": args.filename,
        "format": output_format,
        "path": str(file_path) if file_path else None,
        "loaded": content is not None,
    }

    # Debug log hook execution
    safe_log_to_debug_file("SessionStart", input_data, output_data)

    # Output in requested format
    if output_format == "json":
        output_json(content, args.filename)
    else:
        output_text(content, args.filename)

    sys.exit(0)


if __name__ == "__main__":
    main()
