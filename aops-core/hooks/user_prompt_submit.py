#!/usr/bin/env -S uv run python
"""
UserPromptSubmit hook for Claude Code.

Thin wrapper that re-exports from lib/hydration/ for backwards compatibility.
The actual implementation lives in lib/ to avoid circular dependency issues
where lib/gates/ would otherwise import from hooks/.

Exit codes:
    0: Success
    1: Infrastructure failure (fail-fast)
"""

from pathlib import Path

from lib.hydration import build_hydration_instruction, should_skip_hydration
from lib.session_state import SessionState

HOOK_DIR = Path(__file__).parent
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"
INTENT_MAX_LENGTH = 500


def write_initial_hydrator_state(
    session_id: str, prompt: str, hydration_pending: bool = True
) -> None:
    """Write initial hydrator state with pending workflow.

    Called after processing prompt to set hydration pending flag.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: User's original prompt
        hydration_pending: Whether hydration gate should block until hydrator invoked
    """
    state = SessionState.load(session_id)

    state.global_turn_count += 1

    if hydration_pending:
        state.close_gate("hydration")
        state.get_gate("hydration").metrics["original_prompt"] = prompt
        if hasattr(state, "state") and "hydration_pending" in state.state:
            state.state["hydration_pending"] = True
    else:
        state.open_gate("hydration")
        if hasattr(state, "state") and "hydration_pending" in state.state:
            del state.state["hydration_pending"]

    state.save()


__all__ = [
    "build_hydration_instruction",
    "should_skip_hydration",
    "write_initial_hydrator_state",
    "HOOK_DIR",
    "INSTRUCTION_TEMPLATE_FILE",
    "INTENT_MAX_LENGTH",
]
