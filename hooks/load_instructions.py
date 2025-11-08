#!/usr/bin/env python3
"""
Load core instruction files on SessionStart.

MINIMAL. Just loads the 4 core files and presents them.

Exit codes:
    0: Success (always - fail gracefully if files missing)
"""

import json
import subprocess
import sys
from pathlib import Path


def get_docs_path() -> Path:
    """Get path to docs directory relative to this hook."""
    hook_dir = Path(__file__).parent
    repo_root = hook_dir.parent
    return repo_root / "docs"


def load_file(docs_path: Path, filename: str) -> str | None:
    """Load a file. Returns None if missing."""
    file_path = docs_path / filename
    if not file_path.exists():
        print(f"⚠ {filename} not found", file=sys.stderr)
        return None

    try:
        return file_path.read_text()
    except Exception as e:
        print(f"⚠ Error reading {filename}: {e}", file=sys.stderr)
        return None


def get_git_remote() -> str | None:
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


def main():
    # Files to load
    files_to_load = [
        "CORE.md",
        "AXIOMS.md",
        "ACCOMMODATIONS.md",
        "STYLE-QUICK.md",
    ]

    # Get docs path
    docs_path = get_docs_path()

    # Load all files
    sections = []
    loaded_count = 0

    for filename in files_to_load:
        content = load_file(docs_path, filename)
        if content:
            sections.append(f"# {filename}\n\n{content}")
            loaded_count += 1
            print(f"✓ Loaded {filename}", file=sys.stderr)

    # Build additional context
    if not sections:
        # No files loaded - output warning in context
        additional_context = "# WARNING: load_instructions.py not found"
        print("⚠ No instruction files loaded", file=sys.stderr)
    else:
        # Combine all sections
        git_remote = get_git_remote()
        git_section = ""
        if git_remote:
            git_section = f"## Repository\n\nGit remote: {git_remote}\n\n---\n\n"

        combined = "\n\n---\n\n".join(sections)
        additional_context = f"# READ AND OBEY\n\n{git_section}{combined}"
        print(f"✓ Loaded {loaded_count}/{len(files_to_load)} files", file=sys.stderr)

    # Output JSON for SessionStart hook
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
        }
    }

    print(json.dumps(output), file=sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
