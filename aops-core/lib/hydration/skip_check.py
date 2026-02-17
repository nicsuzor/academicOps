"""Skip check for hydration - determines if prompt should skip hydration.

Moved from hooks/user_prompt_submit.py to fix dependency direction.
Gates (lib/gates/) can now import this without circular dependencies.
"""

from __future__ import annotations

from lib.hook_utils import is_subagent_session


def should_skip_hydration(
    prompt: str,
    session_id: str | None = None,
    *,
    is_subagent: bool | None = None,
) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Subagent sessions (they are themselves part of the hydration/task flow)
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - Expanded slash commands (containing <command-name>/ tag)
    - User ignore shortcut (prompts starting with '.')

    Args:
        prompt: The user's prompt text
        session_id: Optional session ID for subagent detection
        is_subagent: Pre-computed subagent flag from router context. When provided,
            skips is_subagent_session() call. This is important for Gemini CLI
            where is_sidechain flag detection requires full input_data context.

    Returns:
        True if hydration should be skipped
    """
    # 0. Skip if this is a subagent session
    # Subagents should never trigger their own hydration requirement
    # Use pre-computed flag if available (avoids Gemini is_sidechain detection gap)
    if is_subagent is True:
        return True
    if is_subagent is None and is_subagent_session({"session_id": session_id}):
        return True

    prompt_stripped = prompt.strip()

    # Agent/task completion notifications from background Task agents
    if prompt_stripped.startswith("<agent-notification>"):
        return True
    if prompt_stripped.startswith("<task-notification>"):
        return True

    # Expanded slash commands - the skill expansion IS the hydration
    # These contain <command-name>/xxx</command-name> tags from Claude Code
    if "<command-name>/" in prompt:
        return True

    # Skill invocations - generally skip hydration
    if prompt_stripped.startswith("/"):
        return True

    # Slash command expansions (e.g. "# /pull ...")
    if prompt_stripped.startswith("# /"):
        return True

    # User ignore shortcut - user explicitly wants no hydration
    if prompt_stripped.startswith("."):
        return True

    return False
