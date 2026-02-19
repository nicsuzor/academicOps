from hooks.schemas import HookContext

from lib.gate_types import GateState
from lib.session_state import SessionState


def check_custom_condition(
    name: str, ctx: HookContext, state: GateState, session_state: SessionState
) -> bool:
    """
    Evaluate a named custom condition.
    """
    if name == "has_uncommitted_work":
        try:
            from lib.commit_check import check_uncommitted_work

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
            from lib.commit_check import check_uncommitted_work

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
            from lib.hydration import should_skip_hydration

            # Extract prompt
            # For Claude, prompt is not directly in input usually?
            # It might be in 'user_message' or similar if router normalizes it.
            # Or we look at raw input.
            prompt = ctx.raw_input.get("prompt")  # Gemini
            if not prompt:
                # Try to extract from raw input for Claude if structured differently
                # But for now assume it's available or skip
                return False

            # Pass ctx.is_subagent so should_skip_hydration() uses the router's
            # pre-computed value rather than falling back to is_subagent_session()
            # heuristics. This centralises subagent detection and prevents the
            # is_subagent_session() fallback from running when ctx.is_subagent=False.
            return not should_skip_hydration(prompt, ctx.session_id, is_subagent=ctx.is_subagent)
        except ImportError:
            return False

    if name == "has_framework_reflection":
        try:
            from lib.transcript_parser import parse_framework_reflection

            # Load transcript and check for reflection
            transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
            if not transcript_path:
                return False

            # Read recent transcript content
            from pathlib import Path

            path = Path(transcript_path)
            if not path.exists():
                return False

            # Read last portion of transcript to check for reflection
            # Framework reflections are typically at the end
            content = path.read_text()
            # Parse the reflection
            reflection = parse_framework_reflection(content)
            return reflection is not None
        except (ImportError, Exception):
            return False

    if name == "missing_framework_reflection":
        # Inverse check - returns True when reflection is MISSING
        try:
            from lib.transcript_parser import parse_framework_reflection

            transcript_path = ctx.transcript_path or ctx.raw_input.get("transcript_path")
            if not transcript_path:
                return True  # Missing if no transcript

            from pathlib import Path

            path = Path(transcript_path)
            if not path.exists():
                return True  # Missing if file doesn't exist

            content = path.read_text()
            reflection = parse_framework_reflection(content)
            return reflection is None  # True when reflection is missing
        except (ImportError, Exception):
            return True  # Assume missing on error

    if name == "uac_verified":
        # Check if all UAC are marked done in current task body
        task_id = session_state.main_agent.current_task
        if not task_id:
            # No task bound = no UAC to verify (or already satisfied by other means)
            return True

        try:
            from lib.task_storage import TaskStorage

            storage = TaskStorage()
            task = storage.get_task(task_id)
            if not task:
                return True

            # Use the existing check from tasks_server logic (re-implemented or imported)
            # For simplicity, we check if ANY [ ] exists in task body
            import re

            if re.search(r"^\s*-\s*\[ \]\s+.*$", task.body, re.MULTILINE):
                # Update list of incomplete items for gate metrics
                incomplete = re.findall(r"^\s*-\s*\[ \]\s+(.*)$", task.body, re.MULTILINE)
                uac_gate = session_state.get_gate("uac")
                uac_gate.metrics["incomplete_uac_list"] = "\n".join(
                    f"- [ ] {i}" for i in incomplete
                )
                return False

            return True
        except Exception:
            return True

    if name == "has_incomplete_uac":
        # Inverse of uac_verified for policy matching
        return not check_custom_condition("uac_verified", ctx, state, session_state)

    return False
