#!/usr/bin/env python3
"""
Unit tests for hooks/router.py - Generic hook router.

Tests cover:
- Output merging (additionalContext concatenation)
- Permission decision precedence (deny > ask > allow)
- Exit code aggregation (worst wins)
- Async dispatch and collection
- Registry lookup for each hook event
"""

import json
from unittest.mock import patch, MagicMock


# We'll import the router module once it exists
# For now, define the expected interface via tests


class TestOutputMerging:
    """Test output consolidation rules."""

    def test_merge_additional_context_concatenates_with_separator(self):
        """additionalContext from multiple hooks should be joined with ---."""
        from router import merge_outputs

        outputs = [
            {"hookSpecificOutput": {"additionalContext": "Context from hook 1"}},
            {"hookSpecificOutput": {"additionalContext": "Context from hook 2"}},
            {"hookSpecificOutput": {"additionalContext": "Context from hook 3"}},
        ]

        # Use PostToolUse which supports hookSpecificOutput (SessionStart doesn't)
        result = merge_outputs(outputs, "PostToolUse")

        expected_context = "Context from hook 1\n\n---\n\nContext from hook 2\n\n---\n\nContext from hook 3"
        assert result["hookSpecificOutput"]["additionalContext"] == expected_context
        assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"

    def test_merge_skips_empty_additional_context(self):
        """Empty additionalContext should not add separators."""
        from router import merge_outputs

        outputs = [
            {"hookSpecificOutput": {"additionalContext": "Context 1"}},
            {"hookSpecificOutput": {}},  # No additionalContext
            {"hookSpecificOutput": {"additionalContext": "Context 2"}},
        ]

        result = merge_outputs(outputs, "PostToolUse")

        expected_context = "Context 1\n\n---\n\nContext 2"
        assert result["hookSpecificOutput"]["additionalContext"] == expected_context
        assert result["hookSpecificOutput"]["hookEventName"] == "PostToolUse"

    def test_merge_system_message_concatenates_with_newlines(self):
        """systemMessage from multiple hooks should be joined with newlines."""
        from router import merge_outputs

        outputs = [
            {"systemMessage": "Message 1"},
            {"systemMessage": "Message 2"},
        ]

        result = merge_outputs(outputs, "PreToolUse")

        assert result["systemMessage"] == "Message 1\nMessage 2"

    def test_merge_empty_outputs_returns_empty(self):
        """Empty output list should return minimal valid output."""
        from router import merge_outputs

        result = merge_outputs([], "SessionStart")

        assert result == {}

    def test_merge_noop_outputs(self):
        """Empty dict outputs ({}) should merge cleanly."""
        from router import merge_outputs

        outputs = [{}, {}, {}]

        result = merge_outputs(outputs, "Stop")

        assert result == {}

    def test_merge_stop_hook_decision_and_reason(self):
        """Stop hook decision/reason fields should be preserved."""
        from router import merge_outputs

        outputs = [
            {"decision": "block", "reason": "Please add reflection"},
            {},  # Second hook has no output
        ]

        result = merge_outputs(outputs, "Stop")

        assert result["decision"] == "block"
        assert result["reason"] == "Please add reflection"

    def test_merge_stop_hook_multiple_reasons(self):
        """Multiple Stop hooks with reasons should concatenate."""
        from router import merge_outputs

        outputs = [
            {"decision": "block", "reason": "Missing reflection"},
            {"decision": "block", "reason": "Uncommitted changes"},
        ]

        result = merge_outputs(outputs, "Stop")

        assert result["decision"] == "block"
        assert "Missing reflection" in result["reason"]
        assert "Uncommitted changes" in result["reason"]

    def test_merge_stop_hook_stopReason(self):
        """Stop hook stopReason should be preserved for user display."""
        from router import merge_outputs

        outputs = [
            {
                "decision": "block",
                "reason": "Add reflection before ending",
                "stopReason": "Session blocked: missing reflection",
            },
        ]

        result = merge_outputs(outputs, "Stop")

        assert result["decision"] == "block"
        assert result["reason"] == "Add reflection before ending"
        assert result["stopReason"] == "Session blocked: missing reflection"

    def test_merge_subagent_stop_hook_fields(self):
        """SubagentStop hooks should also preserve decision/reason fields."""
        from router import merge_outputs

        outputs = [
            {"decision": "block", "reason": "Subagent needs reflection"},
        ]

        result = merge_outputs(outputs, "SubagentStop")

        assert result["decision"] == "block"
        assert result["reason"] == "Subagent needs reflection"


class TestPermissionDecisionPrecedence:
    """Test permission decision merging (deny > ask > allow)."""

    def test_deny_wins_over_allow(self):
        """deny should take precedence over allow."""
        from router import merge_permission_decisions

        decisions = ["allow", "deny", "allow"]

        result = merge_permission_decisions(decisions)

        assert result == "deny"

    def test_deny_wins_over_ask(self):
        """deny should take precedence over ask."""
        from router import merge_permission_decisions

        decisions = ["ask", "deny", "ask"]

        result = merge_permission_decisions(decisions)

        assert result == "deny"

    def test_ask_wins_over_allow(self):
        """ask should take precedence over allow."""
        from router import merge_permission_decisions

        decisions = ["allow", "ask", "allow"]

        result = merge_permission_decisions(decisions)

        assert result == "ask"

    def test_all_allow_returns_allow(self):
        """All allow decisions should return allow."""
        from router import merge_permission_decisions

        decisions = ["allow", "allow", "allow"]

        result = merge_permission_decisions(decisions)

        assert result == "allow"

    def test_empty_decisions_returns_none(self):
        """No decisions should return None."""
        from router import merge_permission_decisions

        result = merge_permission_decisions([])

        assert result is None

    def test_single_deny_in_many_allows(self):
        """Single deny among many allows should return deny."""
        from router import merge_permission_decisions

        decisions = ["allow"] * 10 + ["deny"] + ["allow"] * 10

        result = merge_permission_decisions(decisions)

        assert result == "deny"


class TestExitCodeAggregation:
    """Test exit code merging (worst wins: 2 > 1 > 0)."""

    def test_all_zero_returns_zero(self):
        """All successful hooks should return 0."""
        from router import aggregate_exit_codes

        codes = [0, 0, 0, 0]

        result = aggregate_exit_codes(codes)

        assert result == 0

    def test_one_failure_returns_worst(self):
        """Single failure should propagate."""
        from router import aggregate_exit_codes

        codes = [0, 0, 1, 0]

        result = aggregate_exit_codes(codes)

        assert result == 1

    def test_block_code_wins(self):
        """Exit code 2 (block) should win over 1 (warn)."""
        from router import aggregate_exit_codes

        codes = [0, 1, 2, 1, 0]

        result = aggregate_exit_codes(codes)

        assert result == 2

    def test_empty_codes_returns_zero(self):
        """No exit codes should return 0 (success)."""
        from router import aggregate_exit_codes

        result = aggregate_exit_codes([])

        assert result == 0


class TestContinueLogic:
    """Test continue field merging (AND logic)."""

    def test_all_true_returns_true(self):
        """All continue=True should return True."""
        from router import merge_continue_flags

        flags = [True, True, True]

        result = merge_continue_flags(flags)

        assert result is True

    def test_one_false_returns_false(self):
        """Single continue=False should return False."""
        from router import merge_continue_flags

        flags = [True, True, False, True]

        result = merge_continue_flags(flags)

        assert result is False

    def test_empty_flags_returns_true(self):
        """No flags should default to True (continue)."""
        from router import merge_continue_flags

        result = merge_continue_flags([])

        assert result is True


class TestSuppressOutputLogic:
    """Test suppressOutput field merging (OR logic)."""

    def test_all_false_returns_false(self):
        """All suppressOutput=False should return False."""
        from router import merge_suppress_flags

        flags = [False, False, False]

        result = merge_suppress_flags(flags)

        assert result is False

    def test_one_true_returns_true(self):
        """Single suppressOutput=True should return True."""
        from router import merge_suppress_flags

        flags = [False, False, True, False]

        result = merge_suppress_flags(flags)

        assert result is True

    def test_empty_flags_returns_false(self):
        """No flags should default to False (don't suppress)."""
        from router import merge_suppress_flags

        result = merge_suppress_flags([])

        assert result is False


class TestHookRegistry:
    """Test hook registry lookup."""

    def test_session_start_has_hooks(self):
        """SessionStart should have registered hooks."""
        from router import HOOK_REGISTRY

        assert "SessionStart" in HOOK_REGISTRY
        assert len(HOOK_REGISTRY["SessionStart"]) > 0

    def test_pre_tool_use_has_hooks(self):
        """PreToolUse should have registered hooks."""
        from router import HOOK_REGISTRY

        assert "PreToolUse" in HOOK_REGISTRY
        assert len(HOOK_REGISTRY["PreToolUse"]) > 0

    def test_post_tool_use_has_hooks(self):
        """PostToolUse should have registered hooks."""
        from router import HOOK_REGISTRY

        assert "PostToolUse" in HOOK_REGISTRY
        assert len(HOOK_REGISTRY["PostToolUse"]) > 0

    def test_user_prompt_submit_has_hooks(self):
        """UserPromptSubmit should have registered hooks."""
        from router import HOOK_REGISTRY

        assert "UserPromptSubmit" in HOOK_REGISTRY
        assert len(HOOK_REGISTRY["UserPromptSubmit"]) > 0

    def test_unknown_event_returns_empty(self):
        """Unknown hook event should return empty list."""
        from router import get_hooks_for_event

        hooks = get_hooks_for_event("UnknownEvent")

        assert hooks == []

    def test_matcher_variant_lookup(self):
        """PostToolUse:TodoWrite should return specific hooks."""
        from router import get_hooks_for_event

        hooks = get_hooks_for_event("PostToolUse", matcher="TodoWrite")

        # Should get the TodoWrite-specific hooks
        assert len(hooks) > 0


class TestAsyncDispatch:
    """Test async hook dispatch and collection."""

    def test_async_hooks_dispatched_first(self):
        """Async hooks should be started before sync hooks run."""
        from router import dispatch_hooks

        # This test verifies the dispatch order
        # Async hooks should be started, then sync hooks run, then async collected
        call_order = []

        def mock_start_async(script_path, input_data):
            call_order.append(f"start_async:{script_path.name}")
            return MagicMock()

        def mock_run_sync(script, input_data):
            call_order.append(f"run_sync:{script}")
            return ({}, 0)

        def mock_collect_async(proc):
            call_order.append("collect_async")
            return ({}, 0)

        hooks = [
            {"script": "async_hook.py", "async": True},
            {"script": "sync_hook1.py"},
            {"script": "sync_hook2.py"},
        ]

        with patch("router.start_async_hook", mock_start_async):
            with patch("router.run_sync_hook", mock_run_sync):
                with patch("router.collect_async_result", mock_collect_async):
                    dispatch_hooks(hooks, {})

        # Verify order: async started first, then sync hooks, then async collected
        assert call_order[0] == "start_async:async_hook.py"
        assert "run_sync:sync_hook1.py" in call_order
        assert "run_sync:sync_hook2.py" in call_order
        assert call_order[-1] == "collect_async"


class TestFullRouter:
    """Integration tests for the full router."""

    def test_router_returns_valid_json(self):
        """Router should always return valid JSON."""
        from router import route_hooks

        input_data = {"hook_event_name": "SessionStart"}

        with patch("router.run_hook_script") as mock_run:
            mock_run.return_value = ({}, 0)
            result, exit_code = route_hooks(input_data)

        # Result should be JSON-serializable
        json.dumps(result)  # Should not raise

    def test_router_handles_missing_event_name(self):
        """Router should handle missing hook_event_name gracefully."""
        from router import route_hooks

        input_data = {}  # No hook_event_name

        result, exit_code = route_hooks(input_data)

        # Should return empty result, exit 0 (no hooks to run)
        assert exit_code == 0
