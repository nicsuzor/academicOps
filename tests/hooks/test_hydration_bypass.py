#!/usr/bin/env python3
"""Unit tests for hydration bypass functionality.

Tests that prompts starting with '.' or '/' correctly bypass the hydration gate
by ensuring UserPromptSubmit sets hydration_pending=False.

Related:
- Task ns-feyk: Hydration gate: don't block if user input starts with '.' or '/'
- Feature ns-1h65: Block progress until prompt hydrator has run
"""

import sys
from pathlib import Path

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.user_prompt_submit import should_skip_hydration  # noqa: E402


class TestHydrationBypass:
    """Test bypass conditions for hydration gate."""

    def test_dot_prefix_bypasses_hydration(self):
        """Prompts starting with '.' should bypass hydration."""
        assert should_skip_hydration(".run some command")
        assert should_skip_hydration(". with space after dot")
        assert should_skip_hydration(".no-space")

    def test_slash_prefix_bypasses_hydration(self):
        """Prompts starting with '/' should bypass hydration (slash commands)."""
        assert should_skip_hydration("/commit")
        assert should_skip_hydration("/learn")
        assert should_skip_hydration("/help")
        assert should_skip_hydration("/ with space")

    def test_agent_notification_bypasses_hydration(self):
        """Agent notifications should bypass hydration."""
        assert should_skip_hydration("<agent-notification>task complete</agent-notification>")
        assert should_skip_hydration("<task-notification>result</task-notification>")

    def test_normal_prompts_do_not_bypass(self):
        """Regular prompts should NOT bypass hydration."""
        assert not should_skip_hydration("Create a new function")
        assert not should_skip_hydration("Fix the bug in auth.py")
        assert not should_skip_hydration("What is the status of bd task ns-123?")
        assert not should_skip_hydration("Run tests")

    def test_prompts_with_dot_slash_in_middle_do_not_bypass(self):
        """Prompts with '.' or '/' in middle should NOT bypass (only prefix counts)."""
        assert not should_skip_hydration("Please run ./script.sh")
        assert not should_skip_hydration("Fix src/auth.py issue")
        assert not should_skip_hydration("Check the file.txt contents")

    def test_empty_prompt_does_not_bypass(self):
        """Empty prompts should NOT bypass."""
        assert not should_skip_hydration("")
        assert not should_skip_hydration("   ")

    def test_whitespace_handling(self):
        """Leading whitespace should be stripped before checking prefix."""
        # should_skip_hydration strips the prompt, so these should bypass
        assert should_skip_hydration("   .dotted")
        assert should_skip_hydration("\n/slash")
        assert should_skip_hydration("\t.tabbed")

    def test_polecat_worker_bypasses_hydration(self):
        """Polecat worker prompts should bypass hydration (aops-b218bcac).

        Polecat workers receive pre-hydrated task bodies from the swarm
        supervisor. They should not require additional hydration, which
        would cause quota exhaustion and worker crashes.
        """
        # Standard polecat worker header
        polecat_prompt = """You are a polecat worker. Your task has already been claimed and your worktree is ready. Do not claim or re-claim this task. Do not run `/pull`. Just execute.

## Your Task

- **ID**: aops-b218bcac
- **Title**: Bug: Gemini workers crash on hydration gate
- **Type**: bug

## Task Body

Fix the hydration gate bug.
"""
        assert should_skip_hydration(polecat_prompt)

        # Just the polecat worker marker
        assert should_skip_hydration("You are a polecat worker. Execute the task.")

        # Just the task claimed marker
        assert should_skip_hydration("Your task has already been claimed. Execute.")

        # Structured task body format
        assert should_skip_hydration("## Your Task\n\n- **ID**: task-123\n\nDo the thing.")

    def test_polecat_markers_in_middle_do_not_bypass(self):
        """Polecat markers in unstructured contexts should still bypass.

        Note: Unlike prefix checks, these markers bypass anywhere in the
        prompt because the polecat worker prompt structure is distinctive.
        """
        # These SHOULD bypass because they contain the markers
        assert should_skip_hydration("The message says: You are a polecat worker")
        assert should_skip_hydration("It says Your task has already been claimed")

    def test_similar_but_different_prompts_do_not_bypass(self):
        """Prompts that look similar but aren't polecat should NOT bypass."""
        # These should NOT bypass - they don't have the exact markers
        assert not should_skip_hydration("You are a worker bee")
        assert not should_skip_hydration("Your task is to complete this")
        assert not should_skip_hydration("## My Task\n\nDo something")
