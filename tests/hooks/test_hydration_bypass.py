#!/usr/bin/env python3
"""Unit tests for hydration bypass functionality.

Tests that prompts starting with '.' or '/' correctly bypass the hydration gate
by ensuring UserPromptSubmit sets hydration_pending=False.

Related:
- Task ns-feyk: Hydration gate: don't block if user input starts with '.' or '/'
- Feature ns-1h65: Block progress until prompt hydrator has run
"""

import os
import sys
from pathlib import Path

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.user_prompt_submit import should_skip_hydration  # noqa: E402


@pytest.fixture(autouse=True)
def clear_polecat_env(monkeypatch):
    """Ensure POLECAT_SESSION_TYPE is not set during tests.

    Polecat sessions skip hydration by design, but tests need to verify
    prompt-based skip logic without session-type interference.
    """
    monkeypatch.delenv("POLECAT_SESSION_TYPE", raising=False)


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

    def test_polecat_session_bypasses_hydration(self, monkeypatch):
        """Polecat sessions should bypass hydration.

        Polecat workers run the hydrator themselves as their first step,
        so injecting hydration instructions into their prompt is redundant.
        """
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "polecat")
        # Any prompt should bypass when in polecat session
        assert should_skip_hydration("Create a new function")
        assert should_skip_hydration("Fix the bug")
        assert should_skip_hydration("")

    def test_crew_session_does_not_bypass_hydration(self, monkeypatch):
        """Crew sessions should NOT bypass hydration (only polecat sessions do).

        Crew workers are interactive and need hydration like regular sessions.
        """
        monkeypatch.setenv("POLECAT_SESSION_TYPE", "crew")
        # Normal prompts should NOT bypass for crew sessions
        assert not should_skip_hydration("Create a new function")
