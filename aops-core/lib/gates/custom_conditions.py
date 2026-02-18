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

    if name == "creates_brain_folder":
        # Check if a Write/Bash tool attempts to create new folders in /home/nic/brain
        # This is a policy enforcement to prevent folder proliferation
        # Returns True if the operation would create a new folder
        import os
        import re
        from pathlib import Path

        BRAIN_ROOT = Path(os.path.expanduser("~/brain"))

        tool_name = ctx.tool_name
        tool_input = ctx.tool_input or {}

        if tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            if file_path:
                target = Path(file_path)
                # Check if any NEW directory would be created under brain root
                if str(target).startswith(str(BRAIN_ROOT)):
                    # Walk up from target's parent to brain root
                    parent = target.parent
                    while str(parent).startswith(str(BRAIN_ROOT)) and parent != BRAIN_ROOT:
                        if not parent.exists():
                            # This would create a new folder
                            state.metrics["blocked_path"] = str(parent)
                            return True
                        parent = parent.parent
            return False

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            # Check for mkdir commands targeting brain directory
            # Extract paths from mkdir/install -d commands and check against BRAIN_ROOT
            mkdir_patterns = [
                # mkdir with optional -p flag
                r"mkdir\s+(?:-p\s+)?['\"]?([^'\";\s]+)['\"]?",
                # install -d
                r"install\s+-d\s+['\"]?([^'\";\s]+)['\"]?",
            ]
            for pattern in mkdir_patterns:
                match = re.search(pattern, command)
                if match:
                    target_path = match.group(1)
                    # Expand ~ if present
                    expanded = Path(os.path.expanduser(target_path))
                    # Check if this path is under BRAIN_ROOT
                    if str(expanded).startswith(str(BRAIN_ROOT)):
                        if not expanded.exists():
                            state.metrics["blocked_path"] = str(expanded)
                            return True
            return False

        return False

    return False
