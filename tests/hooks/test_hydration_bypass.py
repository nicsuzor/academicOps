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

import pytest

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

from hooks.user_prompt_submit import should_skip_hydration


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
