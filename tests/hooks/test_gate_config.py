"""
Unit tests for gate_config.py

Tests all tool categories, gate requirements, execution order,
initial states, opening conditions, and closure triggers.
"""

import pytest
import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(AOPS_CORE))
sys.path.insert(0, str(AOPS_CORE / "hooks"))

from hooks.gate_config import (
    TOOL_CATEGORIES,
    TOOL_GATE_REQUIREMENTS,
    GATE_EXECUTION_ORDER,
    MAIN_AGENT_ONLY_GATES,
    GATE_MODE_DEFAULTS,
    GATE_MODE_ENV_VARS,
    GATE_INITIAL_STATE,
    GATE_OPENING_CONDITIONS,
    GATE_CLOSURE_TRIGGERS,
    get_tool_category,
    get_required_gates,
    get_gates_for_event,
    is_main_agent_only,
    get_gate_initial_state,
    get_gate_opening_condition,
    get_gate_closure_triggers,
    should_gate_close_on_tool,
)


class TestToolCategories:
    """Tests for TOOL_CATEGORIES classification."""

    def test_read_only_tools_include_claude_read_tools(self):
        """Claude read-only tools are correctly categorized."""
        read_only = TOOL_CATEGORIES["read_only"]
        assert "Read" in read_only
        assert "Glob" in read_only
        assert "Grep" in read_only
        assert "WebFetch" in read_only
        assert "WebSearch" in read_only

    def test_read_only_tools_include_gemini_read_tools(self):
        """Gemini read-only tools are correctly categorized."""
        read_only = TOOL_CATEGORIES["read_only"]
        assert "read_file" in read_only
        assert "view_file" in read_only
        assert "list_dir" in read_only
        assert "find_by_name" in read_only
        assert "grep_search" in read_only

    def test_read_only_tools_include_mcp_read_tools(self):
        """MCP read-only tools are correctly categorized."""
        read_only = TOOL_CATEGORIES["read_only"]
        assert "mcp__plugin_aops-core_memory__retrieve_memory" in read_only
        assert "mcp__plugin_aops-core_task_manager__get_task" in read_only
        assert "mcp__plugin_aops-core_task_manager__list_tasks" in read_only

    def test_write_tools_include_claude_write_tools(self):
        """Claude write tools are correctly categorized."""
        write = TOOL_CATEGORIES["write"]
        assert "Edit" in write
        assert "Write" in write
        assert "Bash" in write
        assert "NotebookEdit" in write

    def test_write_tools_include_gemini_write_tools(self):
        """Gemini write tools are correctly categorized."""
        write = TOOL_CATEGORIES["write"]
        assert "write_file" in write
        assert "replace" in write
        assert "run_shell_command" in write

    def test_write_tools_include_mcp_mutating_tools(self):
        """MCP mutating tools are correctly categorized."""
        write = TOOL_CATEGORIES["write"]
        assert "mcp__plugin_aops-core_memory__store_memory" in write
        assert "mcp__plugin_aops-core_task_manager__create_task" in write
        assert "mcp__plugin_aops-core_task_manager__update_task" in write
        assert "mcp__plugin_aops-core_task_manager__complete_task" in write

    def test_meta_tools_include_agent_tools(self):
        """Meta tools are correctly categorized."""
        meta = TOOL_CATEGORIES["meta"]
        assert "Task" in meta
        assert "Skill" in meta
        assert "TodoWrite" in meta
        assert "AskUserQuestion" in meta
        assert "EnterPlanMode" in meta
        assert "ExitPlanMode" in meta

    def test_categories_are_mutually_exclusive(self):
        """No tool should appear in multiple categories."""
        read_only = TOOL_CATEGORIES["read_only"]
        write = TOOL_CATEGORIES["write"]
        meta = TOOL_CATEGORIES["meta"]

        assert read_only.isdisjoint(write), "read_only and write overlap"
        assert read_only.isdisjoint(meta), "read_only and meta overlap"
        assert write.isdisjoint(meta), "write and meta overlap"


class TestToolGateRequirements:
    """Tests for TOOL_GATE_REQUIREMENTS mapping."""

    def test_read_only_requires_only_hydration(self):
        """Read-only tools only require hydration gate."""
        assert TOOL_GATE_REQUIREMENTS["read_only"] == ["hydration"]

    def test_meta_requires_only_hydration(self):
        """Meta tools only require hydration gate."""
        assert TOOL_GATE_REQUIREMENTS["meta"] == ["hydration"]

    def test_write_requires_all_primary_gates(self):
        """Write tools require hydration, task, critic, custodiet gates."""
        expected = ["hydration", "task", "critic", "custodiet"]
        assert TOOL_GATE_REQUIREMENTS["write"] == expected

    def test_stop_requires_all_gates(self):
        """Stop event requires all gates including QA and handover."""
        expected = ["hydration", "task", "critic", "custodiet", "qa", "handover"]
        assert TOOL_GATE_REQUIREMENTS["stop"] == expected


class TestGateExecutionOrder:
    """Tests for GATE_EXECUTION_ORDER sequences."""

    def test_session_start_gates(self):
        """SessionStart has correct gate sequence."""
        gates = GATE_EXECUTION_ORDER["SessionStart"]
        assert "session_env_setup" in gates
        assert "unified_logger" in gates
        assert "session_start" in gates
        # Order matters: env setup first
        assert gates.index("session_env_setup") < gates.index("session_start")

    def test_user_prompt_submit_gates(self):
        """UserPromptSubmit has correct gate sequence."""
        gates = GATE_EXECUTION_ORDER["UserPromptSubmit"]
        assert "user_prompt_submit" in gates
        assert "unified_logger" in gates

    def test_pre_tool_use_gates(self):
        """PreToolUse has correct gate sequence."""
        gates = GATE_EXECUTION_ORDER["PreToolUse"]
        assert "unified_logger" in gates
        assert "subagent_restrictions" in gates
        assert "tool_gate" in gates

    def test_post_tool_use_gates(self):
        """PostToolUse has correct gate sequence."""
        gates = GATE_EXECUTION_ORDER["PostToolUse"]
        assert "unified_logger" in gates
        assert "task_binding" in gates
        assert "accountant" in gates
        assert "post_hydration" in gates
        assert "post_critic" in gates
        assert "post_qa" in gates
        assert "skill_activation" in gates

    def test_stop_gates(self):
        """Stop event has correct gate sequence."""
        gates = GATE_EXECUTION_ORDER["Stop"]
        assert "unified_logger" in gates
        assert "stop_gate" in gates
        assert "generate_transcript" in gates
        assert "session_end_commit" in gates

    def test_all_events_have_unified_logger(self):
        """Every event type includes unified_logger."""
        for event, gates in GATE_EXECUTION_ORDER.items():
            assert "unified_logger" in gates, f"{event} missing unified_logger"


class TestMainAgentOnlyGates:
    """Tests for MAIN_AGENT_ONLY_GATES subagent bypass rules."""

    def test_tool_gate_is_main_agent_only(self):
        """tool_gate should only run for main agent."""
        assert "tool_gate" in MAIN_AGENT_ONLY_GATES

    def test_hydration_is_main_agent_only(self):
        """hydration should only run for main agent."""
        assert "hydration" in MAIN_AGENT_ONLY_GATES

    def test_custodiet_is_main_agent_only(self):
        """custodiet should only run for main agent."""
        assert "custodiet" in MAIN_AGENT_ONLY_GATES

    def test_stop_gate_is_main_agent_only(self):
        """stop_gate should only run for main agent."""
        assert "stop_gate" in MAIN_AGENT_ONLY_GATES

    def test_post_triggers_are_main_agent_only(self):
        """Post-tool triggers should only run for main agent."""
        assert "post_hydration" in MAIN_AGENT_ONLY_GATES
        assert "post_critic" in MAIN_AGENT_ONLY_GATES
        assert "post_qa" in MAIN_AGENT_ONLY_GATES


class TestGateModeDefaults:
    """Tests for GATE_MODE_DEFAULTS and GATE_MODE_ENV_VARS."""

    def test_hydration_default_is_block(self):
        """Hydration gate defaults to block mode."""
        assert GATE_MODE_DEFAULTS["hydration"] == "block"

    def test_task_default_is_warn(self):
        """Task gate defaults to warn mode."""
        assert GATE_MODE_DEFAULTS["task"] == "warn"

    def test_custodiet_default_is_warn(self):
        """Custodiet gate defaults to warn mode."""
        assert GATE_MODE_DEFAULTS["custodiet"] == "warn"

    def test_critic_default_is_warn(self):
        """Critic gate defaults to warn mode."""
        assert GATE_MODE_DEFAULTS["critic"] == "warn"

    def test_qa_default_is_warn(self):
        """QA gate defaults to warn mode."""
        assert GATE_MODE_DEFAULTS["qa"] == "warn"

    def test_env_vars_match_defaults(self):
        """Each default has a corresponding env var."""
        for gate_name in GATE_MODE_DEFAULTS:
            assert gate_name in GATE_MODE_ENV_VARS


class TestGateInitialState:
    """Tests for GATE_INITIAL_STATE values."""

    def test_hydration_starts_closed(self):
        """Hydration gate starts closed (must hydrate first)."""
        assert GATE_INITIAL_STATE["hydration"] == "closed"

    def test_task_starts_open(self):
        """Task gate starts open (allow planning first)."""
        assert GATE_INITIAL_STATE["task"] == "open"

    def test_critic_starts_open(self):
        """Critic gate starts open (allow planning first)."""
        assert GATE_INITIAL_STATE["critic"] == "open"

    def test_custodiet_starts_open(self):
        """Custodiet gate starts open (allow planning first)."""
        assert GATE_INITIAL_STATE["custodiet"] == "open"

    def test_qa_starts_closed(self):
        """QA gate starts closed (must verify before stop)."""
        assert GATE_INITIAL_STATE["qa"] == "closed"

    def test_handover_starts_open(self):
        """Handover gate starts open (closes on uncommitted changes)."""
        assert GATE_INITIAL_STATE["handover"] == "open"


class TestGateOpeningConditions:
    """Tests for GATE_OPENING_CONDITIONS logic."""

    def test_hydration_opens_on_hydrator_task(self):
        """Hydration gate opens when hydrator agent completes."""
        condition = GATE_OPENING_CONDITIONS["hydration"]
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:prompt-hydrator"
        assert condition["output_contains"] == "HYDRATION RESULT"

    def test_task_opens_on_task_manager_tools(self):
        """Task gate opens on create/claim/update task."""
        condition = GATE_OPENING_CONDITIONS["task"]
        assert condition["event"] == "PostToolUse"
        assert "create" in condition["tool_pattern"]
        assert "claim" in condition["tool_pattern"]
        assert "update" in condition["tool_pattern"]

    def test_critic_opens_on_critic_approval(self):
        """Critic gate opens when critic agent approves."""
        condition = GATE_OPENING_CONDITIONS["critic"]
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:critic"
        assert condition["output_contains"] == "APPROVED"

    def test_custodiet_opens_on_ok(self):
        """Custodiet gate opens when custodiet confirms OK."""
        condition = GATE_OPENING_CONDITIONS["custodiet"]
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:custodiet"
        assert condition["output_contains"] == "OK"

    def test_qa_opens_on_qa_completion(self):
        """QA gate opens when QA verification completes."""
        condition = GATE_OPENING_CONDITIONS["qa"]
        assert condition["event"] == "PostToolUse"
        assert "qa" in condition["subagent_or_skill"]

    def test_handover_opens_on_handover_skill(self):
        """Handover gate opens when handover skill is invoked."""
        condition = GATE_OPENING_CONDITIONS["handover"]
        assert condition["event"] == "PostToolUse"
        assert condition["skill_name"] == "aops-core:handover"


class TestGateClosureTriggers:
    """Tests for GATE_CLOSURE_TRIGGERS logic."""

    def test_hydration_closes_on_new_prompt(self):
        """Hydration gate re-closes on new user prompt."""
        triggers = GATE_CLOSURE_TRIGGERS["hydration"]
        assert len(triggers) == 1
        assert triggers[0]["event"] == "UserPromptSubmit"

    def test_task_closes_on_complete(self):
        """Task gate re-closes when task is completed."""
        triggers = GATE_CLOSURE_TRIGGERS["task"]
        assert any(
            "complete_task" in t.get("tool_pattern", "")
            for t in triggers
        )

    def test_critic_closes_on_new_prompt(self):
        """Critic gate re-closes on new user prompt."""
        triggers = GATE_CLOSURE_TRIGGERS["critic"]
        prompt_trigger = next(
            (t for t in triggers if t["event"] == "UserPromptSubmit"),
            None
        )
        assert prompt_trigger is not None

    def test_critic_closes_on_task_complete(self):
        """Critic gate re-closes when task is completed."""
        triggers = GATE_CLOSURE_TRIGGERS["critic"]
        complete_trigger = next(
            (t for t in triggers if "complete_task" in t.get("tool_pattern", "")),
            None
        )
        assert complete_trigger is not None

    def test_custodiet_closes_on_new_prompt(self):
        """Custodiet gate re-closes on new user prompt."""
        triggers = GATE_CLOSURE_TRIGGERS["custodiet"]
        prompt_trigger = next(
            (t for t in triggers if t["event"] == "UserPromptSubmit"),
            None
        )
        assert prompt_trigger is not None

    def test_custodiet_closes_after_threshold_writes(self):
        """Custodiet gate re-closes after N write operations."""
        triggers = GATE_CLOSURE_TRIGGERS["custodiet"]
        threshold_trigger = next(
            (t for t in triggers if "threshold_counter" in t),
            None
        )
        assert threshold_trigger is not None
        assert threshold_trigger["threshold_value"] == 7

    def test_handover_closes_on_git_dirty(self):
        """Handover gate re-closes when repo has uncommitted changes."""
        triggers = GATE_CLOSURE_TRIGGERS["handover"]
        dirty_trigger = next(
            (t for t in triggers if t.get("condition") == "git_dirty"),
            None
        )
        assert dirty_trigger is not None

    def test_qa_does_not_reclose(self):
        """QA gate does not have closure triggers (stays open once verified)."""
        assert "qa" not in GATE_CLOSURE_TRIGGERS


class TestGetToolCategory:
    """Tests for get_tool_category helper function."""

    def test_read_returns_read_only(self):
        """Read tool returns 'read_only' category."""
        assert get_tool_category("Read") == "read_only"

    def test_edit_returns_write(self):
        """Edit tool returns 'write' category."""
        assert get_tool_category("Edit") == "write"

    def test_task_returns_meta(self):
        """Task tool returns 'meta' category."""
        assert get_tool_category("Task") == "meta"

    def test_unknown_tool_returns_write(self):
        """Unknown tools default to 'write' (conservative)."""
        assert get_tool_category("UnknownTool") == "write"

    def test_mcp_read_tool_returns_read_only(self):
        """MCP read tools return 'read_only' category."""
        assert get_tool_category("mcp__plugin_aops-core_task_manager__get_task") == "read_only"

    def test_mcp_write_tool_returns_write(self):
        """MCP write tools return 'write' category."""
        assert get_tool_category("mcp__plugin_aops-core_task_manager__create_task") == "write"


class TestGetRequiredGates:
    """Tests for get_required_gates helper function."""

    def test_read_tool_requires_hydration(self):
        """Read tool requires only hydration."""
        assert get_required_gates("Read") == ["hydration"]

    def test_edit_tool_requires_all_primary_gates(self):
        """Edit tool requires all primary gates."""
        gates = get_required_gates("Edit")
        assert "hydration" in gates
        assert "task" in gates
        assert "critic" in gates
        assert "custodiet" in gates

    def test_unknown_tool_requires_write_gates(self):
        """Unknown tools require write gates (conservative)."""
        gates = get_required_gates("UnknownTool")
        assert "hydration" in gates
        assert "task" in gates


class TestGetGatesForEvent:
    """Tests for get_gates_for_event helper function."""

    def test_session_start_returns_gates(self):
        """SessionStart returns its gate list."""
        gates = get_gates_for_event("SessionStart")
        assert len(gates) > 0
        assert "session_start" in gates

    def test_unknown_event_returns_empty(self):
        """Unknown event returns empty list."""
        assert get_gates_for_event("UnknownEvent") == []


class TestIsMainAgentOnly:
    """Tests for is_main_agent_only helper function."""

    def test_tool_gate_is_main_only(self):
        """tool_gate returns True."""
        assert is_main_agent_only("tool_gate") is True

    def test_unified_logger_is_not_main_only(self):
        """unified_logger returns False (runs for all agents)."""
        assert is_main_agent_only("unified_logger") is False


class TestGetGateInitialState:
    """Tests for get_gate_initial_state helper function."""

    def test_hydration_returns_closed(self):
        """hydration returns 'closed'."""
        assert get_gate_initial_state("hydration") == "closed"

    def test_task_returns_open(self):
        """task returns 'open'."""
        assert get_gate_initial_state("task") == "open"

    def test_unknown_gate_returns_closed(self):
        """Unknown gates default to 'closed'."""
        assert get_gate_initial_state("unknown_gate") == "closed"


class TestGetGateOpeningCondition:
    """Tests for get_gate_opening_condition helper function."""

    def test_hydration_returns_condition(self):
        """hydration returns its opening condition."""
        condition = get_gate_opening_condition("hydration")
        assert "event" in condition
        assert condition["event"] == "PostToolUse"

    def test_unknown_gate_returns_empty(self):
        """Unknown gates return empty dict."""
        assert get_gate_opening_condition("unknown_gate") == {}


class TestGetGateClosureTriggers:
    """Tests for get_gate_closure_triggers helper function."""

    def test_hydration_returns_triggers(self):
        """hydration returns its closure triggers."""
        triggers = get_gate_closure_triggers("hydration")
        assert len(triggers) == 1

    def test_qa_returns_empty(self):
        """QA returns empty list (no re-closure)."""
        assert get_gate_closure_triggers("qa") == []


class TestShouldGateCloseOnTool:
    """Tests for should_gate_close_on_tool helper function."""

    def test_handover_closes_on_write_tool(self):
        """Handover gate should close on write tool."""
        # Note: This requires the git_dirty condition which is checked elsewhere
        # The function checks tool_category match
        result = should_gate_close_on_tool("handover", "Edit", "PostToolUse")
        assert result is True

    def test_hydration_does_not_close_on_tool(self):
        """Hydration gate doesn't close on tool use (only on UserPromptSubmit)."""
        result = should_gate_close_on_tool("hydration", "Edit", "PostToolUse")
        assert result is False

    def test_wrong_event_does_not_trigger_close(self):
        """Wrong event type doesn't trigger closure."""
        result = should_gate_close_on_tool("handover", "Edit", "PreToolUse")
        assert result is False
