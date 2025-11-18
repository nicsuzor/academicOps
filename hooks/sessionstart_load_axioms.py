#!/usr/bin/env python3
"""
SessionStart hook: Load AXIOMS.md and inject as additional context.

Provides framework principles at the start of every session without
requiring @ syntax in CLAUDE.md or manual file reading.

Exit codes:
    0: Success (always continues)
    1: Fatal error (missing AXIOMS.md - fail-fast)
"""

import json
import sys
from pathlib import Path
from typing import Any

from lib.paths import get_aops_root


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


def main():
    """Main hook entry point - loads AXIOMS and continues."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Load AXIOMS.md (fail-fast if missing)
    try:
        axioms_content = load_axioms()
    except (FileNotFoundError, ValueError) as e:
        # Fail-fast: log error and exit with error code
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Build context
    additional_context = f"""# Framework Principles (AXIOMS.md)

{axioms_content}

---

**For more information**:
- Framework structure: See README.md
- Current state: See $ACA_DATA/projects/aops/STATE.md
- Vision and roadmap: See $ACA_DATA/projects/aops/VISION.md and ROADMAP.md
- Learning patterns: See $ACA_DATA/projects/aops/experiments/LOG.md
"""

    # Build output data
    output_data: dict[str, Any] = {"additionalContext": additional_context}

    # Output JSON (continue execution)
    print(json.dumps(output_data))

    # Status to stderr (get path for logging)
    from lib.paths import get_aops_root
    axioms_path = get_aops_root() / "AXIOMS.md"
    print(f"✓ Loaded AXIOMS.md from {axioms_path}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
