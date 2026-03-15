"""Hydration instruction builder.

Moved from hooks/user_prompt_submit.py to fix dependency direction.
Gates (lib/gates/) can now import this without circular dependencies.
"""

from __future__ import annotations

from pathlib import Path

from lib.session_state import SessionState
from lib.template_loader import load_template

# Path to instruction template
HOOK_DIR = Path(__file__).parent.parent.parent / "hooks"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"


def build_hydration_instruction(
    session_id: str,
    prompt: str,
    transcript_path: str | None = None,
    state: SessionState | None = None,
) -> str:
    """Build instruction for main agent to invoke hydrator.

    Manages gate state and returns the short instruction string.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: The user's original prompt
        transcript_path: Unused, kept for API compatibility
        state: Optional existing SessionState object

    Returns:
        Short instruction string telling the agent to invoke the hydrator skill
    """
    if state is None:
        state = SessionState.load(session_id)
        should_save = True
    else:
        should_save = False

    state.global_turn_count += 1

    gate = state.get_gate("hydration")
    gate.metrics["original_prompt"] = prompt
    state.close_gate("hydration")

    if hasattr(state, "state") and "hydration_pending" in state.state:
        state.state["hydration_pending"] = True

    if should_save:
        state.save()

    return load_template(INSTRUCTION_TEMPLATE_FILE)
