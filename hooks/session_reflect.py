#!/usr/bin/env python3
"""
Stop hook: Trigger session reflection before session ends.

Injects instruction for main agent to invoke session-insights skill
with 'current' arg for real-time pattern analysis and heuristic updates.

Does NOT call LLM directly (H31 compliance). Just triggers the skill.

Exit codes:
    0: Success (no reflection needed - short session)
    1: Warning with reflection instruction (normal case)
"""

import json
import sys
from typing import Any


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Get session info
    session_id = input_data.get("session_id", "")
    transcript_path = input_data.get("transcript_path", "")

    # Skip reflection for very short sessions (less useful)
    # The agent can still manually invoke /reflect if desired
    if not transcript_path:
        print(json.dumps({}))
        sys.exit(0)

    # Inject reflection instruction
    message = """[AOPS: Session Reflection]

Before ending, run session reflection to capture learnings:

```
Skill(skill="session-insights", args="current")
```

This will:
1. Analyze this session for patterns (skill bypass, verification skip, etc.)
2. Map findings to heuristics (H2, H3, H4, etc.)
3. Present suggestions for you to approve/dismiss

You can skip by saying "skip reflection" or pressing Ctrl+C.
"""

    output: dict[str, Any] = {
        "reason": message,
        "continue": True,
    }

    print(json.dumps(output))
    sys.exit(1)  # 1 = warn but allow (shows message to agent)


if __name__ == "__main__":
    main()
