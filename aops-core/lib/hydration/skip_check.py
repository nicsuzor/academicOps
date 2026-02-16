"""Skip check for hydration - determines if prompt should skip hydration.

Moved from hooks/user_prompt_submit.py to fix dependency direction.
Gates (lib/gates/) can now import this without circular dependencies.
"""

from __future__ import annotations

from lib.hook_utils import is_subagent_session


def should_skip_hydration(prompt: str, session_id: str | None = None) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Subagent sessions (they are themselves part of the hydration/task flow)
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - Expanded slash commands (containing <command-name>/ tag)
    - User ignore shortcut (prompts starting with '.')
    - Polecat workers (task body IS the hydrated context - aops-b218bcac)

    Args:
        prompt: The user's prompt text
        session_id: Optional session ID for subagent detection

    Returns:
        True if hydration should be skipped
    """
    # 0. Skip if this is a subagent session
    # Subagents should never trigger their own hydration requirement
    if is_subagent_session({"session_id": session_id}):
        return True

    prompt_stripped = prompt.strip()

    # Polecat workers: task body IS the hydrated context
    # These workers receive pre-hydrated task prompts from the swarm supervisor.
    # They should not require additional hydration, which would cause:
    # 1. Unnecessary API calls (quota exhaustion risk)
    # 2. Worker crashes if hydration subagent fails (aops-b218bcac)
    if _is_polecat_worker_prompt(prompt_stripped):
        return True

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


def _is_polecat_worker_prompt(prompt: str) -> bool:
    """Detect if this is a polecat worker prompt.

    Polecat workers receive their task body as the initial prompt, which is
    already fully hydrated by the swarm supervisor. They should skip hydration
    to avoid:
    1. Redundant subagent calls (quota exhaustion risk)
    2. Worker crashes if hydration subagent fails (aops-b218bcac)

    Detection is based on the standard polecat worker prompt header injected
    by the swarm supervisor.

    Args:
        prompt: The stripped prompt text

    Returns:
        True if this is a polecat worker prompt
    """
    # Standard polecat worker header (injected by swarm-supervisor skill)
    if "You are a polecat worker" in prompt:
        return True

    # Task already claimed marker (indicates pre-hydrated task execution)
    if "Your task has already been claimed" in prompt:
        return True

    # ## Your Task with task ID marker (structured task body)
    if "## Your Task" in prompt and "**ID**:" in prompt:
        return True

    return False
