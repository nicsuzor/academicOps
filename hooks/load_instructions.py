#!/usr/bin/env python3
"""
Load instruction files from 3-tier hierarchy: framework → personal → project.

ONE script, ONE pattern, TWO output modes, OPTIONAL discovery.

Usage:
    # SessionStart hook (default: loads _CORE.md, outputs JSON)
    load_instructions.py

    # SessionStart hook with discovery manifest
    load_instructions.py --discovery

    # Slash commands (custom file, outputs plain text)
    load_instructions.py DEVELOPER.md
    load_instructions.py _CHUNKS/FAIL-FAST.md

    # Force plain text output
    load_instructions.py _CORE.md --format=text

Loading Hierarchy (ALWAYS the same, NO legacy fallbacks):
1. Framework: $ACADEMICOPS_BOT/core/<filename>
2. Personal:  $ACADEMICOPS_PERSONAL/core/<filename> (if exists)
3. Project:   $PWD/docs/bots/<filename> (if exists)

Output Modes:
- JSON (default when no filename): For SessionStart hook
- Text (when filename given): For slash commands

Discovery Mode (--discovery):
- Scans framework tier for available bot instruction files
- Includes lightweight manifest in SessionStart output
- Enables agents to discover what files they can read

Exit codes:
    0: Success
    1: Error (missing required env var or file)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file


def get_tier_paths(filename: str) -> dict[str, Path | None]:
    """
    Get paths to instruction file at all three tiers.

    Returns dict with keys: framework, personal, project
    Each value is a Path or None.
    """
    paths = {}

    # Framework tier (REQUIRED)
    if bot_path := os.environ.get("ACADEMICOPS_BOT"):
        paths["framework"] = Path(bot_path) / "core" / filename
    else:
        # Fail fast - ACADEMICOPS_BOT is required
        raise ValueError(
            "ACADEMICOPS_BOT environment variable not set. "
            "Add to shell: export ACADEMICOPS_BOT=/path/to/bot"
        )

    # Personal tier (OPTIONAL)
    if personal_path := os.environ.get("ACADEMICOPS_PERSONAL"):
        paths["personal"] = Path(personal_path) / "core" / filename
    else:
        paths["personal"] = None

    # Project tier (OPTIONAL)
    paths["project"] = Path.cwd() / "docs" / "bots" / filename

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


def output_json(contents: dict[str, str], filename: str, include_discovery: bool = False) -> None:
    """Output in JSON format for SessionStart hook."""
    # Get git remote info
    git_remote = get_git_remote_info()
    git_section = ""
    if git_remote:
        git_section = f"## REPOSITORY\n\nGit remote origin: {git_remote}\n\n---\n\n"

    # Build context sections in priority order: project → personal → framework
    sections = []

    if "project" in contents:
        sections.append(f"## PROJECT: Current Project Context\n\n{contents['project']}")

    if "personal" in contents:
        sections.append(f"## PERSONAL: Your Work Context\n\n{contents['personal']}")

    if "framework" in contents:
        sections.append(f"## FRAMEWORK: Core Rules\n\n{contents['framework']}")

    # Add discovery manifest if requested
    if include_discovery:
        discovery = generate_discovery_manifest()
        if discovery:
            sections.append(f"---\n\n{discovery}")

    additional_context = "# Agent Instructions\n\n" + git_section + "\n\n---\n\n".join(sections)

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
    discovery_note = " (with discovery)" if include_discovery else ""
    print(f"✓ Loaded {filename} from: {', '.join(loaded)}{discovery_note}", file=sys.stderr)


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


def generate_discovery_manifest() -> str:
    """
    Generate a manifest of available bot instruction files.

    Scans framework tier to discover what files are available,
    then creates a lightweight manifest for agents.
    """
    bot_path = os.environ.get("ACADEMICOPS_BOT")
    if not bot_path:
        return ""

    agents_dir = Path(bot_path) / "core"
    if not agents_dir.exists():
        return ""

    # Find all .md files in core/
    available_files = []
    try:
        for md_file in sorted(agents_dir.glob("*.md")):
            if md_file.name.startswith("_"):
                # Skip _CORE.md and other internal files
                continue
            available_files.append(md_file.name)
    except Exception as e:
        print(f"Warning: Could not scan {agents_dir}: {e}", file=sys.stderr)
        return ""

    if not available_files:
        return ""

    # Build manifest
    manifest = ["## Available Bot Instructions", ""]
    manifest.append("The following bot instruction files are available via the 3-tier system:")
    manifest.append("(framework → personal → project)")
    manifest.append("")

    for filename in available_files:
        # Extract a simple description from the filename
        name = filename.replace(".md", "").replace("_", " ").title()
        manifest.append(f"- `/core/{filename}` - {name} mode")

    manifest.append("")
    manifest.append("Read these files when relevant to your task. They will be automatically")
    manifest.append("stacked from all available tiers (framework/personal/project).")

    return "\n".join(manifest)


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
    parser.add_argument(
        "--discovery",
        action="store_true",
        help="Include discovery manifest of available bot files",
    )

    args = parser.parse_args()

    # Read input from stdin (hook input data)
    input_data: dict[str, Any] = {}
    try:
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

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

    # Prepare output data for logging
    output_data: dict[str, Any] = {
        "filename": args.filename,
        "format": output_format,
        "tiers_loaded": list(contents.keys()),
        "paths": {k: str(v) for k, v in paths.items() if v is not None},
    }

    # Debug log hook execution
    safe_log_to_debug_file("SessionStart", input_data, output_data)

    # Output in requested format
    if output_format == "json":
        output_json(contents, args.filename, include_discovery=args.discovery)
    else:
        output_text(contents, args.filename)

    sys.exit(0)


if __name__ == "__main__":
    main()
