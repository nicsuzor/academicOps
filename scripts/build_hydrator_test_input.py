#!/usr/bin/env python3
"""Build hydrator test input file for acceptance testing.

Constructs the same context file that the UserPromptSubmit hook builds in live
sessions, so acceptance tests can invoke the prompt-hydrator with full context
(SKILLS.md, WORKFLOWS.md, AXIOMS, HEURISTICS, project workflows).

Usage:
    uv run scripts/build_hydrator_test_input.py "check my email"

Prints the path to the generated context file. Pass this path directly to the
prompt-hydrator subagent:

    Agent(subagent_type='aops-core:prompt-hydrator', prompt=<path>)

Why this is needed
------------------
In live sessions the hook calls build_hydration_instruction() which writes a
rich context bundle to a temp file, then the main agent passes that file path
to the hydrator subagent.  When tests invoke the hydrator directly with a raw
user prompt (not a file path), the hydrator receives zero framework context and
all routing tests fail with "out of scope" or "no tools found".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Add aops-core to sys.path so lib imports work
_AOPS_CORE = Path(__file__).parent.parent / "aops-core"
sys.path.insert(0, str(_AOPS_CORE))

from lib.hydration.builder import build_hydration_instruction  # noqa: E402

TEST_SESSION_ID = "test-hydrator-session"


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: build_hydrator_test_input.py <prompt>", file=sys.stderr)
        print(
            'Example: uv run scripts/build_hydrator_test_input.py "check my email"', file=sys.stderr
        )
        sys.exit(1)

    prompt = sys.argv[1]

    instruction = build_hydration_instruction(
        session_id=TEST_SESSION_ID,
        prompt=prompt,
        transcript_path=None,
    )

    # Extract the file path from the returned instruction string.
    # Instruction format: `Agent(subagent_type='aops-core:prompt-hydrator', prompt='<path>')`
    match = re.search(r"prompt='([^']+)'", instruction)
    if not match:
        print(f"ERROR: Could not extract path from instruction:\n{instruction}", file=sys.stderr)
        sys.exit(1)

    context_path = match.group(1)
    print(context_path)


if __name__ == "__main__":
    main()
