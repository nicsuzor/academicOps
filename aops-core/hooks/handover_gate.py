#!/usr/bin/env python3
"""
PostToolUse hook: Detect /handover skill invocation and clear stop gate.

When the Skill tool is invoked with skill="handover" or "aops-core:handover",
this hook sets the handover_skill_invoked flag in session state, allowing
the stop hook to pass.

Exit codes:
    0: Success (always - this hook doesn't block, only tracks state)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))


def is_handover_skill_invocation(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check if this is a handover skill invocation.

    Args:
        tool_name: Name of the tool being invoked
        tool_input: Tool input parameters

    Returns:
        True if this is a handover skill invocation
    """
    if tool_name != "Skill":
        return False

    skill_name = tool_input.get("skill", "")
    # Match both short and fully-qualified names
    if skill_name in ("handover", "aops-core:handover"):
        return True

    return False


def is_handover_delegation(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """Check if this is a handover delegation (Gemini)."""
    if tool_name != "delegate_to_agent":
        return False

    agent_name = tool_input.get("agent_name", "")
    # If delegating to something named "handover" or "aops-core:handover"
    # Or generically, if the *agent* is handover.
    # But usually handover is a SKILL, not an AGENT.
    # If Gemini uses a skill via delegation? Unlikely.
    # But if there's an agent named 'handover-agent'?
    # Assuming for now mostly Skill tool usage, but supporting direct tool call 'handover' if exposed.
    return agent_name in ("handover", "aops-core:handover")


def is_handover_tool(tool_name: str) -> bool:
    """Check if tool name itself is handover."""
    return tool_name == "handover"


def main() -> None:
    """Main hook entry point."""
    try:
        input_data: dict[str, Any] = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        sys.exit(0)

    # Extract tool info (support both naming conventions)
    tool_name = input_data.get("tool_name") or input_data.get("toolName", "")
    tool_input = input_data.get("tool_input") or input_data.get("toolInput", {})

    # Support Skill tool, direct tool, or delegation
    is_handover = (
        is_handover_skill_invocation(tool_name, tool_input)
        or is_handover_delegation(tool_name, tool_input)
        or is_handover_tool(tool_name)
    )

    if not is_handover:
        print(json.dumps({}))
        sys.exit(0)

    # Get session ID from environment
    session_id = os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        print(json.dumps({}))
        sys.exit(0)

    # Set handover skill invoked flag
    try:
        from lib.session_state import set_handover_skill_invoked

        set_handover_skill_invoked(session_id)
        output = {"systemMessage": "[Gate] Handover skill invoked. Stop gate cleared."}
        print(json.dumps(output))
    except Exception as e:
        print(f"handover_gate hook error: {e}", file=sys.stderr)
        print(json.dumps({}))

    sys.exit(0)


if __name__ == "__main__":
    main()
