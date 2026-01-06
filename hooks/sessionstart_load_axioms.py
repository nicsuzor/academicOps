#!/usr/bin/env python3
"""
SessionStart hook: Load AXIOMS.md, HEURISTICS.md, and CORE.md as additional context.

Provides framework principles, empirical heuristics, and user context at the
start of every session without requiring @ syntax in CLAUDE.md or manual file reading.

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


def load_framework() -> str:
    """
    Load FRAMEWORK.md content (paths - DO NOT GUESS).

    Returns:
        FRAMEWORK content as string

    Raises:
        FileNotFoundError: If FRAMEWORK.md doesn't exist (fail-fast)
    """
    aops_root = get_aops_root()
    framework_path = aops_root / "FRAMEWORK.md"

    if not framework_path.exists():
        msg = (
            f"FATAL: FRAMEWORK.md missing at {framework_path}. "
            "SessionStart hook requires this file for framework paths."
        )
        raise FileNotFoundError(msg)

    content = framework_path.read_text().strip()

    if not content:
        msg = f"FATAL: FRAMEWORK.md at {framework_path} is empty."
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


def load_heuristics() -> str:
    """
    Load HEURISTICS.md content.

    Returns:
        HEURISTICS content as string

    Raises:
        FileNotFoundError: If HEURISTICS.md doesn't exist (fail-fast)
    """
    aops_root = get_aops_root()
    heuristics_path = aops_root / "HEURISTICS.md"

    # Fail-fast: HEURISTICS.md is required
    if not heuristics_path.exists():
        msg = (
            f"FATAL: HEURISTICS.md missing at {heuristics_path}. "
            "SessionStart hook requires this file to exist. "
            "Framework cannot operate without empirical heuristics."
        )
        raise FileNotFoundError(msg)

    content = heuristics_path.read_text().strip()

    if not content:
        msg = f"FATAL: HEURISTICS.md at {heuristics_path} is empty."
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


def expand_path_variables(content: str, aops_root: Path, data_root: Path) -> str:
    """
    Replace $AOPS and $ACA_DATA variables with resolved absolute paths.

    Args:
        content: Text content containing path variables
        aops_root: Resolved AOPS path
        data_root: Resolved ACA_DATA path

    Returns:
        Content with variables replaced by absolute paths
    """
    result = content.replace("$AOPS", str(aops_root))
    result = result.replace("$ACA_DATA", str(data_root))
    return result


def main():
    """Main hook entry point - loads AXIOMS, HEURISTICS, and CORE, then continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Clean up this session's criteria gate file (fresh start for each session)
    session_id = input_data.get("session_id", "")
    if session_id:
        gate_file = Path(f"/tmp/claude-criteria-gate-{session_id}")
        gate_file.unlink(missing_ok=True)

    # Get resolved paths early for variable expansion
    aops_root = get_aops_root()
    data_root = get_data_root()

    # Load FRAMEWORK.md (fail-fast if missing)
    try:
        framework_content = load_framework()
        framework_content = expand_path_variables(
            framework_content, aops_root, data_root
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load AXIOMS.md (fail-fast if missing)
    try:
        axioms_content = load_axioms()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load HEURISTICS.md (fail-fast if missing)
    try:
        heuristics_content = load_heuristics()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load CORE.md (fail-fast if missing)
    try:
        core_content = load_core()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Build context - FRAMEWORK (paths), AXIOMS (principles), HEURISTICS (empirical), CORE (user)
    additional_context = f"""# Framework Paths (FRAMEWORK.md)

{framework_content}

---

# Framework Principles (AXIOMS.md)

{axioms_content}

---

# Framework Heuristics (HEURISTICS.md)

{heuristics_content}

---

# User Context (CORE.md)

{core_content}
"""

    # Use already-resolved paths for logging
    framework_path = aops_root / "FRAMEWORK.md"
    axioms_path = aops_root / "AXIOMS.md"
    heuristics_path = aops_root / "HEURISTICS.md"
    core_path = data_root / "CORE.md"

    # Build output data (sent to Claude)
    hook_specific_output: dict[str, Any] = {
        "hookEventName": "SessionStart",
        "additionalContext": additional_context,
        "filesLoaded": [
            str(framework_path),
            str(axioms_path),
            str(heuristics_path),
            str(core_path),
        ],
    }
    output_data: dict[str, Any] = {"hookSpecificOutput": hook_specific_output}

    # Log event with output data (so transcript can show it)
    session_id = input_data.get("session_id", "unknown")
    log_hook_event(
        session_id=session_id,
        hook_event="SessionStart",
        input_data=input_data,
        output_data={"hookSpecificOutput": hook_specific_output},
        exit_code=0,
    )

    # Output JSON (continue execution)
    print(json.dumps(output_data))

    # Status to stderr
    print(f"✓ Loaded FRAMEWORK.md from {framework_path}", file=sys.stderr)
    print(f"✓ Loaded AXIOMS.md from {axioms_path}", file=sys.stderr)
    print(f"✓ Loaded HEURISTICS.md from {heuristics_path}", file=sys.stderr)
    print(f"✓ Loaded CORE.md from {core_path}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
