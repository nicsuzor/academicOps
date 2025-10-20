#!/usr/bin/env python3
"""
Load instruction files from 3-tier hierarchy: framework → personal → project.

ONE script, ONE pattern, TWO output modes.

Usage:
    # SessionStart hook (default: loads _CORE.md, outputs JSON)
    load_instructions.py

    # Slash commands (custom file, outputs plain text)
    load_instructions.py DEVELOPER.md
    load_instructions.py _CHUNKS/FAIL-FAST.md

    # Force plain text output
    load_instructions.py _CORE.md --format=text

Loading Hierarchy (ALWAYS the same, NO legacy fallbacks):
1. Framework: $ACADEMICOPS_BOT/bots/agents/<filename>
2. Personal:  $ACADEMICOPS_PERSONAL/bots/agents/<filename> (if exists)
3. Project:   $PWD/bots/agents/<filename> (if exists)

Output Modes:
- JSON (default when no filename): For SessionStart hook
- Text (when filename given): For slash commands

Exit codes:
    0: Success
    1: Error (missing required env var or file)
"""

import argparse
import json
import os
import sys
from pathlib import Path


def get_tier_paths(filename: str) -> dict[str, Path | None]:
    """
    Get paths to instruction file at all three tiers.

    Returns dict with keys: framework, personal, project
    Each value is a Path or None.
    """
    paths = {}

    # Framework tier (REQUIRED)
    if bot_path := os.environ.get("ACADEMICOPS_BOT"):
        paths["framework"] = Path(bot_path) / "bots" / "agents" / filename
    else:
        # Fail fast - ACADEMICOPS_BOT is required
        raise ValueError(
            "ACADEMICOPS_BOT environment variable not set. "
            "Add to shell: export ACADEMICOPS_BOT=/path/to/bot"
        )

    # Personal tier (OPTIONAL)
    if personal_path := os.environ.get("ACADEMICOPS_PERSONAL"):
        paths["personal"] = Path(personal_path) / "bots" / "agents" / filename
    else:
        paths["personal"] = None

    # Project tier (OPTIONAL)
    paths["project"] = Path.cwd() / "bots" / "agents" / filename

    return paths


def load_tier_content(path: Path | None) -> str | None:
    """Load content from a tier path. Returns None if missing."""
    if path is None:
        return None

    if not path.exists():
        return None

    try:
        return path.read_text()
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None


def output_json(contents: dict[str, str], filename: str) -> None:
    """Output in JSON format for SessionStart hook."""
    # Build context sections in priority order: project → personal → framework
    sections = []

    if "project" in contents:
        sections.append(f"## PROJECT: Current Project Context\n\n{contents['project']}")

    if "personal" in contents:
        sections.append(f"## PERSONAL: Your Work Context\n\n{contents['personal']}")

    if "framework" in contents:
        sections.append(f"## FRAMEWORK: Core Rules\n\n{contents['framework']}")

    additional_context = "# Agent Instructions\n\n" + "\n\n---\n\n".join(sections)

    # Output JSON for Claude Code hook
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }

    print(json.dumps(output), file=sys.stdout)

    # Status to stderr
    loaded = [tier for tier in ["framework", "personal", "project"] if tier in contents]
    print(f"✓ Loaded {filename} from: {', '.join(loaded)}", file=sys.stderr)


def output_text(contents: dict[str, str], filename: str) -> None:
    """Output in plain text format for slash commands."""
    # Output in priority order: project → personal → framework
    for tier in ["project", "personal", "framework"]:
        if tier in contents:
            print(f"# === {tier.upper()}: {filename} ===\n", file=sys.stderr)
            print(contents[tier], file=sys.stderr)
            print("\n", file=sys.stderr)

    # Status summary to stdout (visible to user)
    loaded = [tier for tier in ["framework", "personal", "project"] if tier in contents]
    missing = [tier for tier in ["framework", "personal", "project"] if tier not in contents]

    status_parts = []
    if "framework" in contents:
        status_parts.append("✓ framework")
    if "personal" in contents:
        status_parts.append("✓ personal")
    if "project" in contents:
        status_parts.append("✓ project")

    print(f"Loaded {filename}: {' '.join(status_parts)}", file=sys.stdout)


def main():
    parser = argparse.ArgumentParser(
        description="Load instruction files from 3-tier hierarchy"
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

    # Determine output format
    if args.format:
        output_format = args.format
    else:
        # Default: JSON for _CORE.md (SessionStart), text for others (commands)
        output_format = "json" if args.filename == "_CORE.md" else "text"

    # Get paths for all three tiers
    try:
        paths = get_tier_paths(args.filename)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load content from each tier
    contents = {}
    for tier, path in paths.items():
        if content := load_tier_content(path):
            contents[tier] = content

    # Framework tier is REQUIRED
    if "framework" not in contents:
        print(f"ERROR: Framework file not found: {paths['framework']}", file=sys.stderr)
        print(f"Searched at: {paths['framework']}", file=sys.stderr)
        print(f"ACADEMICOPS_BOT={os.environ.get('ACADEMICOPS_BOT', 'NOT SET')}", file=sys.stderr)
        sys.exit(1)

    # Output in requested format
    if output_format == "json":
        output_json(contents, args.filename)
    else:
        output_text(contents, args.filename)

    sys.exit(0)


if __name__ == "__main__":
    main()
