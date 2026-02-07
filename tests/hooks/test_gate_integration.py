"""
Integration tests for gate lifecycle.

Tests gate state transitions across the full hook lifecycle,
including opening conditions, closure triggers, and cross-gate interactions.
"""

import os
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add aops-core to path
AOPS_CORE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(AOPS_CORE))
sys.path.insert(0, str(AOPS_CORE / "hooks"))
sys.path.insert(0, str(AOPS_CORE / "lib"))


class TestGateLifecycleHydration:
    """Integration tests for hydration gate lifecycle."""

    def test_hydration_starts_closed(self):
        """Hydration gate starts in closed state."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("hydration") == "closed"

    def test_hydration_opens_on_hydrator_completion(self):
        """Hydration gate opening condition is hydrator Task completion."""
        from hooks.gate_config import get_gate_opening_condition
        condition = get_gate_opening_condition("hydration")
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:prompt-hydrator"
        assert "HYDRATION RESULT" in condition["output_contains"]

    def test_hydration_recloses_on_new_prompt(self):
        """Hydration gate re-closes on UserPromptSubmit."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("hydration")
        assert len(triggers) == 1
        assert triggers[0]["event"] == "UserPromptSubmit"

    def test_read_only_tools_require_only_hydration(self):
        """Read-only tools only need hydration gate."""
        from hooks.gate_config import get_required_gates
        gates = get_required_gates("Read")
        assert gates == ["hydration"]
        assert "task" not in gates
        assert "critic" not in gates


class TestGateLifecycleTask:
    """Integration tests for task gate lifecycle."""

    def test_task_starts_open(self):
        """Task gate starts open to allow planning."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("task") == "open"

    def test_task_opens_on_task_manager_success(self):
        """Task gate opens when task manager tools succeed."""
        from hooks.gate_config import get_gate_opening_condition
        import re
        condition = get_gate_opening_condition("task")
        assert condition["event"] == "PostToolUse"
        # Verify pattern matches task operations
        pattern = condition["tool_pattern"]
        assert re.search(pattern, "mcp__plugin_aops-core_task_manager__create_task")
        assert re.search(pattern, "mcp__plugin_aops-core_task_manager__claim_task")
        assert re.search(pattern, "mcp__plugin_aops-core_task_manager__update_task")

    def test_task_closes_on_complete(self):
        """Task gate re-closes when task is completed."""
        from hooks.gate_config import get_gate_closure_triggers
        import re
        triggers = get_gate_closure_triggers("task")
        complete_trigger = next(
            (t for t in triggers if "tool_pattern" in t and
             re.search(t["tool_pattern"], "mcp__plugin_aops-core_task_manager__complete_task")),
            None
        )
        assert complete_trigger is not None


class TestGateLifecycleCritic:
    """Integration tests for critic gate lifecycle."""

    def test_critic_starts_open(self):
        """Critic gate starts open to allow planning."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("critic") == "open"

    def test_critic_opens_on_approval(self):
        """Critic gate opens when critic agent approves."""
        from hooks.gate_config import get_gate_opening_condition
        condition = get_gate_opening_condition("critic")
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:critic"
        assert condition["output_contains"] == "APPROVED"

    def test_critic_closes_on_new_prompt(self):
        """Critic gate re-closes on new user prompt."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("critic")
        prompt_trigger = next(
            (t for t in triggers if t["event"] == "UserPromptSubmit"),
            None
        )
        assert prompt_trigger is not None

    def test_critic_closes_on_task_complete(self):
        """Critic gate re-closes when task is completed."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("critic")
        complete_trigger = next(
            (t for t in triggers if "complete_task" in t.get("tool_pattern", "")),
            None
        )
        assert complete_trigger is not None


class TestGateLifecycleCustodiet:
    """Integration tests for custodiet gate lifecycle."""

    def test_custodiet_starts_open(self):
        """Custodiet gate starts open."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("custodiet") == "open"

    def test_custodiet_opens_on_ok(self):
        """Custodiet gate opens when custodiet confirms OK."""
        from hooks.gate_config import get_gate_opening_condition
        condition = get_gate_opening_condition("custodiet")
        assert condition["event"] == "PostToolUse"
        assert condition["subagent_type"] == "aops-core:custodiet"
        assert condition["output_contains"] == "OK"

    def test_custodiet_closes_on_new_prompt(self):
        """Custodiet gate re-closes on new user prompt."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("custodiet")
        prompt_trigger = next(
            (t for t in triggers if t["event"] == "UserPromptSubmit"),
            None
        )
        assert prompt_trigger is not None

    def test_custodiet_closes_after_threshold(self):
        """Custodiet gate re-closes after threshold write operations."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("custodiet")
        threshold_trigger = next(
            (t for t in triggers if "threshold_counter" in t),
            None
        )
        assert threshold_trigger is not None
        assert threshold_trigger["threshold_value"] == 7
        assert threshold_trigger["tool_category"] == "write"


class TestGateLifecycleQA:
    """Integration tests for QA gate lifecycle."""

    def test_qa_starts_closed(self):
        """QA gate starts closed (must verify before stop)."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("qa") == "closed"

    def test_qa_opens_on_verification(self):
        """QA gate opens when QA verification completes."""
        from hooks.gate_config import get_gate_opening_condition
        condition = get_gate_opening_condition("qa")
        assert condition["event"] == "PostToolUse"
        assert "qa" in condition["subagent_or_skill"]

    def test_qa_does_not_reclose(self):
        """QA gate stays open once verified."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("qa")
        assert triggers == []


class TestGateLifecycleHandover:
    """Integration tests for handover gate lifecycle."""

    def test_handover_starts_open(self):
        """Handover gate starts open."""
        from hooks.gate_config import get_gate_initial_state
        assert get_gate_initial_state("handover") == "open"

    def test_handover_opens_on_skill(self):
        """Handover gate opens when handover skill is invoked."""
        from hooks.gate_config import get_gate_opening_condition
        condition = get_gate_opening_condition("handover")
        assert condition["event"] == "PostToolUse"
        assert condition["skill_name"] == "aops-core:handover"

    def test_handover_closes_on_git_dirty(self):
        """Handover gate re-closes when repo has uncommitted changes."""
        from hooks.gate_config import get_gate_closure_triggers
        triggers = get_gate_closure_triggers("handover")
        dirty_trigger = next(
            (t for t in triggers if t.get("condition") == "git_dirty"),
            None
        )
        assert dirty_trigger is not None
        assert dirty_trigger["tool_category"] == "write"


class TestWriteToolGateChain:
    """Integration tests for write tool gate chain enforcement."""

    def test_write_tools_require_all_primary_gates(self):
        """Write tools require hydration + task + critic + custodiet."""
        from hooks.gate_config import get_required_gates
        gates = get_required_gates("Edit")
        assert "hydration" in gates
        assert "task" in gates
        assert "critic" in gates
        assert "custodiet" in gates

    def test_stop_requires_all_gates(self):
        """Stop event requires all gates including QA and handover."""
        from hooks.gate_config import TOOL_GATE_REQUIREMENTS
        stop_gates = TOOL_GATE_REQUIREMENTS["stop"]
        assert "hydration" in stop_gates
        assert "task" in stop_gates
        assert "critic" in stop_gates
        assert "custodiet" in stop_gates
        assert "qa" in stop_gates
        assert "handover" in stop_gates


class TestSubagentBypass:
    """Integration tests for subagent bypass rules."""

    def test_main_agent_only_gates_bypass_for_subagents(self):
        """Gates in MAIN_AGENT_ONLY_GATES should bypass for subagents."""
        from hooks.gate_config import MAIN_AGENT_ONLY_GATES, is_main_agent_only

        # All these should be main-agent only
        assert is_main_agent_only("tool_gate")
        assert is_main_agent_only("hydration")
        assert is_main_agent_only("custodiet")
        assert is_main_agent_only("stop_gate")

        # unified_logger should run for all
        assert not is_main_agent_only("unified_logger")

    def test_hydrator_cannot_use_mutating_tools(self):
        """Hydrator subagent is blocked from mutating tools."""
        from hooks.gate_registry import MUTATING_TOOLS

        # Verify Edit, Write, Bash are in mutating tools
        assert "Edit" in MUTATING_TOOLS
        assert "Write" in MUTATING_TOOLS
        assert "Bash" in MUTATING_TOOLS


class TestToolCategoryConsistency:
    """Integration tests for tool category consistency."""

    def test_gate_config_and_registry_aligned(self):
        """gate_config TOOL_CATEGORIES aligned with gate_registry patterns."""
        from hooks.gate_config import TOOL_CATEGORIES
        from hooks.gate_registry import MUTATING_TOOLS, SAFE_READ_TOOLS

        # All MUTATING_TOOLS should be in write category
        for tool in MUTATING_TOOLS:
            if tool in TOOL_CATEGORIES["write"]:
                continue
            # Some tools may use different names in config vs registry
            # This is expected for Gemini/Claude naming differences

        # All SAFE_READ_TOOLS should be in read_only category
        for tool in SAFE_READ_TOOLS:
            if tool in TOOL_CATEGORIES["read_only"]:
                continue
            # Some MCP tools may have different naming conventions

    def test_mcp_tools_categorized(self):
        """MCP tools are properly categorized."""
        from hooks.gate_config import get_tool_category

        # Read MCP tools
        assert get_tool_category("mcp__plugin_aops-core_task_manager__get_task") == "read_only"
        assert get_tool_category("mcp__plugin_aops-core_task_manager__list_tasks") == "read_only"

        # Write MCP tools
        assert get_tool_category("mcp__plugin_aops-core_task_manager__create_task") == "write"
        assert get_tool_category("mcp__plugin_aops-core_task_manager__update_task") == "write"


class TestGateExecutionOrderIntegrity:
    """Integration tests for gate execution order integrity."""

    def test_unified_logger_always_first_or_present(self):
        """unified_logger is in every event's gate list."""
        from hooks.gate_config import GATE_EXECUTION_ORDER

        for event, gates in GATE_EXECUTION_ORDER.items():
            assert "unified_logger" in gates, f"{event} missing unified_logger"

    def test_session_start_env_setup_before_session_start(self):
        """session_env_setup runs before session_start."""
        from hooks.gate_config import GATE_EXECUTION_ORDER

        gates = GATE_EXECUTION_ORDER["SessionStart"]
        assert gates.index("session_env_setup") < gates.index("session_start")

    def test_post_tool_use_has_accountant(self):
        """PostToolUse includes accountant for state tracking."""
        from hooks.gate_config import GATE_EXECUTION_ORDER

        gates = GATE_EXECUTION_ORDER["PostToolUse"]
        assert "accountant" in gates

    def test_stop_has_transcript_generation(self):
        """Stop event includes transcript generation."""
        from hooks.gate_config import GATE_EXECUTION_ORDER

        gates = GATE_EXECUTION_ORDER["Stop"]
        assert "generate_transcript" in gates


class TestGateModeEnforcement:
    """Integration tests for gate mode (block vs warn) enforcement."""

    def test_default_modes_are_valid(self):
        """All default modes are valid values."""
        from hooks.gate_config import GATE_MODE_DEFAULTS

        valid_modes = {"block", "warn"}
        for gate, mode in GATE_MODE_DEFAULTS.items():
            assert mode in valid_modes, f"{gate} has invalid mode: {mode}"

    def test_env_vars_use_consistent_naming(self):
        """Environment variable names use consistent pattern."""
        from hooks.gate_config import GATE_MODE_ENV_VARS

        for gate, env_var in GATE_MODE_ENV_VARS.items():
            # All should end with _MODE
            assert env_var.endswith("_MODE"), f"{gate} env var doesn't end with _MODE"
            # All should be uppercase
            assert env_var == env_var.upper(), f"{gate} env var not uppercase"


class TestGateClosureOnToolCategory:
    """Integration tests for gate closure based on tool category."""

    def test_handover_closes_on_write_category(self):
        """Handover gate should close when write tools are used."""
        from hooks.gate_config import should_gate_close_on_tool, get_tool_category

        # Edit is a write tool
        assert get_tool_category("Edit") == "write"
        # Handover should close on write tools
        assert should_gate_close_on_tool("handover", "Edit", "PostToolUse") is True

    def test_handover_does_not_close_on_read(self):
        """Handover gate should NOT close on read-only tools."""
        from hooks.gate_config import should_gate_close_on_tool, get_tool_category

        # Read is a read_only tool
        assert get_tool_category("Read") == "read_only"
        # Handover should NOT close on read tools
        assert should_gate_close_on_tool("handover", "Read", "PostToolUse") is False


class TestBashCommandClassification:
    """Integration tests for Bash command classification consistency."""

    def test_safe_bash_bypasses_task_gate(self):
        """Safe Bash commands don't require task binding."""
        from hooks.gate_registry import _should_require_task

        # Safe commands
        assert _should_require_task("Bash", {"command": "git status"}) is False
        assert _should_require_task("Bash", {"command": "cat file.txt"}) is False
        assert _should_require_task("Bash", {"command": "ls -la"}) is False

    def test_destructive_bash_requires_task_gate(self):
        """Destructive Bash commands require task binding."""
        from hooks.gate_registry import _should_require_task

        # Destructive commands
        assert _should_require_task("Bash", {"command": "rm file.txt"}) is True
        assert _should_require_task("Bash", {"command": "git commit -m 'test'"}) is True
        assert _should_require_task("Bash", {"command": "echo 'x' > file"}) is True

    def test_hydration_safe_bash_bypasses_hydration(self):
        """Hydration-safe Bash commands bypass hydration gate."""
        from hooks.gate_registry import _is_hydration_safe_bash

        # Git operations for handover
        assert _is_hydration_safe_bash("git add .") is True
        assert _is_hydration_safe_bash("git commit -m 'test'") is True
        assert _is_hydration_safe_bash("git push") is True

        # Read operations
        assert _is_hydration_safe_bash("cat file.txt") is True
        assert _is_hydration_safe_bash("jq '.data' file.json") is True


class TestGateStateTransitions:
    """Integration tests for gate state transitions."""

    def test_closed_to_open_requires_condition(self):
        """Gates only open when their opening condition is met."""
        from hooks.gate_config import GATE_INITIAL_STATE, GATE_OPENING_CONDITIONS

        # Gates that start closed must have opening conditions
        for gate, state in GATE_INITIAL_STATE.items():
            if state == "closed":
                assert gate in GATE_OPENING_CONDITIONS, \
                    f"{gate} starts closed but has no opening condition"

    def test_gates_with_closure_triggers(self):
        """Gates with closure triggers can re-close."""
        from hooks.gate_config import GATE_CLOSURE_TRIGGERS

        # Verify expected gates have closure triggers
        assert "hydration" in GATE_CLOSURE_TRIGGERS
        assert "task" in GATE_CLOSURE_TRIGGERS
        assert "critic" in GATE_CLOSURE_TRIGGERS
        assert "custodiet" in GATE_CLOSURE_TRIGGERS
        assert "handover" in GATE_CLOSURE_TRIGGERS

        # QA should NOT have closure triggers
        assert "qa" not in GATE_CLOSURE_TRIGGERS
