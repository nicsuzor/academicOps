#!/usr/bin/env python3
"""
SessionStart hook: Load AXIOMS.md and CORE.md and inject as additional context.

Provides framework principles and user context at the start of every session
without requiring @ syntax in CLAUDE.md or manual file reading.

Exit codes:
    0: Success (always continues)
    1: Fatal error (missing required files - fail-fast)
"""

import json
import sys
from pathlib import Path
from typing import Any

from lib.paths import get_aops_root, get_data_root
from hooks.hook_logger import log_hook_event


def load_readme() -> str:
    """
    Load README.md content (framework paths and structure).

    Returns:
        README content as string

    Raises:
        FileNotFoundError: If README.md doesn't exist (fail-fast)
    """
    aops_root = get_aops_root()
    readme_path = aops_root / "README.md"

    if not readme_path.exists():
        msg = (
            f"FATAL: README.md missing at {readme_path}. "
            "SessionStart hook requires this file for framework paths."
        )
        raise FileNotFoundError(msg)

    content = readme_path.read_text().strip()

    if not content:
        msg = f"FATAL: README.md at {readme_path} is empty."
        raise ValueError(msg)

    return content


def load_axioms() -> str:
    """
    Load AXIOMS.md content.

    Returns:
        AXIOMS content as string

    Raises:
        FileNotFoundError: If AXIOMS.md doesn't exist (fail-fast)
    """
    # Get paths at runtime (after environment variables are set)
    aops_root = get_aops_root()
    axioms_path = aops_root / "AXIOMS.md"

    # Fail-fast: AXIOMS.md is required
    if not axioms_path.exists():
        msg = (
            f"FATAL: AXIOMS.md missing at {axioms_path}. "
            "SessionStart hook requires this file to exist. "
            "Framework cannot operate without core principles."
        )
        raise FileNotFoundError(msg)

    # Read file
    content = axioms_path.read_text().strip()

    # Basic validation
    if not content:
        msg = f"FATAL: AXIOMS.md at {axioms_path} is empty."
        raise ValueError(msg)

    return content


def load_core() -> str:
    """
    Load CORE.md content from $ACA_DATA.

    Returns:
        CORE.md content as string

    Raises:
        FileNotFoundError: If CORE.md doesn't exist (fail-fast)
    """
    # Get data root at runtime
    data_root = get_data_root()
    core_path = data_root / "CORE.md"

    # Fail-fast: CORE.md is required
    if not core_path.exists():
        msg = (
            f"FATAL: CORE.md missing at {core_path}. "
            "SessionStart hook requires this file to exist. "
            "User context cannot be loaded without CORE.md."
        )
        raise FileNotFoundError(msg)

    # Read file
    content = core_path.read_text().strip()

    # Basic validation
    if not content:
        msg = f"FATAL: CORE.md at {core_path} is empty."
        raise ValueError(msg)

    return content


def main():
    """Main hook entry point - loads AXIOMS and CORE, then continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Load README.md (fail-fast if missing)
    try:
        readme_content = load_readme()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load AXIOMS.md (fail-fast if missing)
    try:
        axioms_content = load_axioms()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load CORE.md (fail-fast if missing)
    try:
        core_content = load_core()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Build context - README first (paths), then AXIOMS (principles), then CORE (user)
    additional_context = f"""# Framework Structure (README.md)

{readme_content}

---

# Framework Principles (AXIOMS.md)

{axioms_content}

---

# User Context (CORE.md)

{core_content}
"""

    # Get paths for logging
    readme_path = get_aops_root() / "README.md"
    axioms_path = get_aops_root() / "AXIOMS.md"
    core_path = get_data_root() / "CORE.md"

    # Build output data (sent to Claude)
    output_data: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context
        }
    }

    # Build log data with file metadata (for hook logs only)
    log_output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context,
            "filesLoaded": [str(readme_path), str(axioms_path), str(core_path)]
        }
    }

    # Log to hook logger
    session_id = input_data.get("session_id", "unknown")
    log_hook_event(session_id, "SessionStart", input_data, log_output, exit_code=0)

    # Output JSON (continue execution) - without filesLoaded metadata
    print(json.dumps(output_data))

    # Status to stderr
    print(f"✓ Loaded README.md from {readme_path}", file=sys.stderr)
    print(f"✓ Loaded AXIOMS.md from {axioms_path}", file=sys.stderr)
    print(f"✓ Loaded CORE.md from {core_path}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
