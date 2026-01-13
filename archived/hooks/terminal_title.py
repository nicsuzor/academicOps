#!/usr/bin/env python3
"""
SessionStart hook: Set terminal title to project name.

Provides instant visual identification of which project a terminal is running.
Uses ANSI escape sequences supported by most terminal emulators.
"""

import json
import os
import subprocess
import sys


def get_project_name() -> str:
    """Get project name from git remote or directory."""
    try:
        # Try git remote first
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            # Extract repo name from URL (e.g., "nicsuzor/writing.git" -> "writing")
            url = result.stdout.strip()
            name = url.split("/")[-1].replace(".git", "")
            return name
    except Exception:
        pass

    # Fallback to directory name
    return os.path.basename(os.getcwd())


def set_terminal_title(title: str) -> None:
    """Set terminal title via ANSI escape sequence."""
    # OSC 0 sets both title and icon name
    # Works in: iTerm2, Terminal.app, Windows Terminal, most xterm-compatible terminals
    sys.stderr.write(f"\033]0;CC: {title}\007")
    sys.stderr.flush()


def main() -> None:
    """Main hook entry point."""
    # Read input (required by hook protocol)
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    # Get and set project name
    project = get_project_name()
    set_terminal_title(project)

    # Return empty response (hook completed successfully)
    print(json.dumps({}))
    sys.exit(0)


if __name__ == "__main__":
    main()
