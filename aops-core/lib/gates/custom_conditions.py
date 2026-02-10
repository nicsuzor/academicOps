from hooks.schemas import HookContext

from lib.gate_types import GateState
from lib.session_state import SessionState


def check_custom_condition(name: str, ctx: HookContext, state: GateState, session_state: SessionState) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "has_uncommitted_work":
        try:
            from hooks.session_end_commit_check import check_uncommitted_work
            # Use transcript path from input if context is missing it
            path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
            result = check_uncommitted_work(ctx.session_id, path)
            if result.should_block:
                state.metrics["block_reason"] = result.message
                return True
            return False
        except ImportError:
            return False

    if name == "has_unpushed_commits":
        try:
            from hooks.session_end_commit_check import check_uncommitted_work
            path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
            result = check_uncommitted_work(ctx.session_id, path)
            if result.reminder_needed:
                 state.metrics["warning_message"] = result.message
                 return True
            return False
        except ImportError:
             return False

    if name == "is_hydratable":
        try:
            from hooks.user_prompt_submit import should_skip_hydration
            # Extract prompt
            # For Claude, prompt is not directly in input usually?
            # It might be in 'user_message' or similar if router normalizes it.
            # Or we look at raw input.
            prompt = ctx.raw_input.get("prompt") # Gemini
            if not prompt:
                # Try to extract from raw input for Claude if structured differently
                # But for now assume it's available or skip
                return False

            return not should_skip_hydration(prompt, ctx.session_id)
        except ImportError:
            return False

    return False
