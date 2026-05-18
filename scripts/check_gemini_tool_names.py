#!/usr/bin/env -S uv run python
"""Pre-commit hook: block Gemini-form tool names in aops-core source.

build.py transforms canonical mcp__server__tool names → mcp_server_tool
(and Read → read_file, etc.) when building the Gemini distribution.
Gemini polecat workers see only the Gemini catalog and silently write
these names back into source SKILL.md and agent files during edits.
This script catches the corruption before merge. See issue #1128.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure scripts/ package is on the path when run as a script
REPO_ROOT = Path(__file__).parent.parent.resolve()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.audit_agent_compliance import check_gemini_names


def main() -> int:
    violations = check_gemini_names(REPO_ROOT)
    if violations:
        print(
            f"FAIL: {len(violations)} Gemini-form tool name(s) found in source — "
            "these are build-output names that must not appear in aops-core/**/*.md:",
            file=sys.stderr,
        )
        for file_path, location, name in violations:
            print(f"  {file_path} [{location}]: {name!r}", file=sys.stderr)
        return 1
    print("OK: No Gemini-form tool names found in source.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
