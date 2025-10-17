#!/usr/bin/env python3
"""
Read instruction files from 3-tier hierarchy: bot → personal → project.

Usage: read_instructions.py <filename>

Reads <filename> from all three levels and outputs:
- User feedback to stdout (colored, brief)
- Full instruction text to stderr (for agent consumption)

Exit codes:
    0: At least one file found and read
    1: All three files missing (blocking error)
"""

import os
import sys
from pathlib import Path


# ANSI color codes
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
RESET = "\033[0m"


def get_paths(filename: str) -> dict[str, Path | None]:
    """
    Get paths to instruction files at all three levels.
    
    Returns dict with keys: bot, personal, project (values are Path or None)
    """
    paths = {}
    
    # Bot level (required environment variable)
    if bot_path := os.environ.get("ACADEMICOPS_BOT"):
        paths["bot"] = Path(bot_path) / "agents" / filename
    else:
        paths["bot"] = None
    
    # Personal level (optional)
    if personal_path := os.environ.get("ACADEMICOPS_PERSONAL"):
        paths["personal"] = Path(personal_path) / "agents" / filename
    else:
        paths["personal"] = None
    
    # Project level (current working directory)
    paths["project"] = Path.cwd() / "agents" / filename
    
    return paths


def read_file(path: Path) -> str | None:
    """Read file and return contents, or None if missing/error."""
    try:
        return path.read_text()
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"{RED}✗{RESET} Error reading {path}: {e}", file=sys.stdout)
        return None


def main():
    if len(sys.argv) != 2:
        print(f"{RED}✗{RESET} Usage: read_instructions.py <filename>", file=sys.stdout)
        sys.exit(1)
    
    filename = sys.argv[1]
    paths = get_paths(filename)
    
    # Read all files
    contents = {}
    for level, path in paths.items():
        if path and path.exists():
            if content := read_file(path):
                contents[level] = {"path": path, "content": content}
    
    # Check if we found at least one file
    if not contents:
        print(f"{RED}✗{RESET} No {filename} found at any level", file=sys.stdout)
        print(f"  Searched:", file=sys.stdout)
        for level, path in paths.items():
            if path:
                print(f"    - {level}: {path}", file=sys.stdout)
        sys.exit(1)
    
    # Print user-friendly status to stdout
    status_parts = []
    for level in ["bot", "personal", "project"]:
        if level in contents:
            status_parts.append(f"{GREEN}✓{RESET} {level}")
        elif paths[level]:
            status_parts.append(f"{YELLOW}○{RESET} {level}")
    
    print(f"Loaded {filename}: {' '.join(status_parts)}", file=sys.stdout)
    
    # Print full instruction text to stderr (for agent consumption)
    # Print in priority order: project → personal → bot (highest to lowest)
    for level in ["project", "personal", "bot"]:
        if level in contents:
            print(f"# === {level.upper()}: {filename} ===\n", file=sys.stderr)
            print(contents[level]["content"], file=sys.stderr)
            print("\n", file=sys.stderr)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
