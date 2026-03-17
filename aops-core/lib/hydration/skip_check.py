"""Skip check for hydration - determines if prompt should skip hydration.

Moved from hooks/user_prompt_submit.py to fix dependency direction.
Gates (lib/gates/) can now import this without circular dependencies.
"""

from __future__ import annotations

import re

from lib.hook_utils import is_subagent_session


def _command_args_need_hydration(prompt: str) -> bool:
    """Check if slash command arguments contain natural language needing intent parsing.

    Returns True when <command-args> contains multi-word content suggesting
    the user mixed a task reference with natural language instructions
    (e.g., "/pull task-id and deconstruct").

    Single-token args (just a task ID) don't need hydration.
    """
    match = re.search(r"<command-args>(.*?)</command-args>", prompt, re.DOTALL)
    if not match:
        return False

    args = match.group(1).strip()
    if not args:
        return False

    # Single token (task ID, skill name, etc.) — no hydration needed
    tokens = args.split()
    if len(tokens) <= 1:
        return False

    # Multi-token args: likely contains natural language that needs intent parsing
    return True


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
    - Expanded slash commands WITHOUT multi-word arguments
    - Skill invocations (prompts starting with '/')
    - User ignore shortcut (prompts starting with '.')

    Slash commands WITH multi-word arguments are NOT skipped — the hydrator
    parses user intent from the arguments before execution begins.

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

    # Expanded slash commands: skip UNLESS args contain natural language
    # The skill expansion provides the workflow, but multi-word args may carry
    # user intent that needs parsing (e.g., "/pull task-id and deconstruct")
    if "<command-name>/" in prompt:
        if _command_args_need_hydration(prompt):
            return False  # Hydrate: args need intent parsing
        return True  # Skip: bare command or single-token arg

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
