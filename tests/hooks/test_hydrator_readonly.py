"""Regression test for hydrator read-only enforcement.

Regression: The prompt-hydrator agent executed actual work (Edit/Write)
instead of returning a plan. This test ensures the gate blocks mutating
tools for hydrator sessions.

Task: aops-dbe06e8c
"""

import os
import pytest
from unittest.mock import patch

from hooks.gate_registry import (
    GateContext,
    check_subagent_tool_restrictions,
    MUTATING_TOOLS,
)
from lib.gate_model import GateVerdict


class TestHydratorReadOnly:
    """Test that prompt-hydrator cannot use mutating tools."""

    def test_hydrator_cannot_use_edit_tool(self):
        """Regression: hydrator tried to Edit files instead of returning plan."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test.py"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is not None, "Should block Edit tool for hydrator"
            assert result.verdict == GateVerdict.DENY
            assert "cannot use mutating tools" in result.context_injection

    def test_hydrator_cannot_use_write_tool(self):
        """Hydrator should not be able to Write files."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Write", "tool_input": {"file_path": "/tmp/test.py"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is not None, "Should block Write tool for hydrator"
            assert result.verdict == GateVerdict.DENY

    def test_hydrator_cannot_use_bash_tool(self):
        """Hydrator should not be able to run Bash commands."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Bash", "tool_input": {"command": "echo test"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is not None, "Should block Bash tool for hydrator"
            assert result.verdict == GateVerdict.DENY

    def test_hydrator_can_use_read_tool(self):
        """Hydrator should be able to Read files (read-only operation)."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Read", "tool_input": {"file_path": "/tmp/test.py"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is None, "Should allow Read tool for hydrator"

    def test_non_hydrator_subagent_allowed_mutating_tools(self):
        """Other subagents (like planner) should be allowed to use mutating tools."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:planner"}):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test.py"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is None, "Should allow Edit for non-hydrator subagent"

    def test_main_agent_allowed_mutating_tools(self):
        """Main agent (no subagent type) should be allowed mutating tools."""
        # Ensure env var is not set
        env_without_subagent = {k: v for k, v in os.environ.items() if k != "CLAUDE_SUBAGENT_TYPE"}
        with patch.dict(os.environ, env_without_subagent, clear=True):
            ctx = GateContext(
                session_id="test-session",
                event_name="PreToolUse",
                input_data={"tool_name": "Edit", "tool_input": {"file_path": "/tmp/test.py"}},
            )
            result = check_subagent_tool_restrictions(ctx)

            assert result is None, "Should allow Edit for main agent"

    def test_hydrator_variant_names_blocked(self):
        """Hydrator with variant naming should also be blocked."""
        variants = [
            "aops-core:prompt-hydrator",
            "prompt-hydrator",
            "aops-core:my-custom-hydrator",  # Contains "hydrator"
        ]
        for variant in variants:
            with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": variant}):
                ctx = GateContext(
                    session_id="test-session",
                    event_name="PreToolUse",
                    input_data={"tool_name": "Edit", "tool_input": {}},
                )
                result = check_subagent_tool_restrictions(ctx)

                assert result is not None, f"Should block Edit for hydrator variant: {variant}"
                assert result.verdict == GateVerdict.DENY

    def test_only_pretooluse_event_checked(self):
        """Gate should only apply to PreToolUse events."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            for event in ["PostToolUse", "SessionStart", "Stop", "SubagentStop"]:
                ctx = GateContext(
                    session_id="test-session",
                    event_name=event,
                    input_data={"tool_name": "Edit", "tool_input": {}},
                )
                result = check_subagent_tool_restrictions(ctx)

                assert result is None, f"Should not check {event} events"

    def test_all_mutating_tools_blocked_for_hydrator(self):
        """All tools in MUTATING_TOOLS set should be blocked for hydrator."""
        with patch.dict(os.environ, {"CLAUDE_SUBAGENT_TYPE": "aops-core:prompt-hydrator"}):
            for tool_name in MUTATING_TOOLS:
                ctx = GateContext(
                    session_id="test-session",
                    event_name="PreToolUse",
                    input_data={"tool_name": tool_name, "tool_input": {}},
                )
                result = check_subagent_tool_restrictions(ctx)

                assert result is not None, f"Should block {tool_name} for hydrator"
                assert result.verdict == GateVerdict.DENY
