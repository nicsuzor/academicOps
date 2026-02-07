import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

# Now we can import from hooks and lib
from hooks.gate_registry import GATE_CHECKS, GateContext
from lib.gate_model import GateVerdict

# --- Fixtures ---


@pytest.fixture(params=["gemini", "claude"])
def cli_agent(request) -> str:
    """Fixture that parameterizes across both supported agent types."""
    return request.param


# --- Mocking Helpers ---


def mock_session_state(
    is_hydration_pending: bool = False,
    task_bound: bool = False,
    plan_mode_invoked: bool = False,
    critic_invoked: bool = False,
    hydrator_active: bool = False,
    hydration_temp_path: str = "/tmp/hydrator/test",
    gates_bypassed: bool = False,
):
    """
    Returns a context manager that patches all relevant session_state functions.
    """
    gates = {
        "task_bound": task_bound,
        "plan_mode_invoked": plan_mode_invoked,
        "critic_invoked": critic_invoked,
    }

    state = {"state": {"gates_bypassed": gates_bypassed}}

    return patch.multiple(
        "lib.session_state",
        is_hydration_pending=MagicMock(return_value=is_hydration_pending),
        check_all_gates=MagicMock(return_value=gates),
        is_hydrator_active=MagicMock(return_value=hydrator_active),
        get_hydration_temp_path=MagicMock(return_value=hydration_temp_path),
        load_session_state=MagicMock(return_value=state),
    )


# --- Tool Call Simulation ---


def _simulate_tool_call(agent: str, instruction: str) -> Dict[str, Any]:
    """
    Helper to generate tool input JSON based on instruction.
    Mimics what the provider (Gemini/Claude) would send in their raw hook input.
    """
    if "read file" in instruction:
        path = instruction.split(" ")[-1]
        if agent == "gemini":
            return {"toolName": "read_file", "toolInput": {"file_path": path}}
        else:
            return {"tool_name": "Read", "tool_input": {"file_path": path}}

    if "list_prompts" in instruction:
        if agent == "gemini":
            return {"toolName": "list_prompts", "toolInput": {}}
        else:
            return {"tool_name": "list_prompts", "tool_input": {}}

    if "activate_skill" in instruction:
        skill = instruction.split(" ")[-1]
        if agent == "gemini":
            return {"toolName": "activate_skill", "toolInput": {"name": skill}}
        else:
            return {"tool_name": "Skill", "tool_input": {"skill": skill}}

    if "write_file" in instruction:
        path = "test.txt"
        content = "hello"
        if "with_content" in instruction:
            content = instruction.split("with_content ")[-1]

        if agent == "gemini":
            return {
                "toolName": "write_to_file",
                "toolInput": {"file_path": path, "content": content},
            }
        else:
            return {
                "tool_name": "Write",
                "tool_input": {"file_path": path, "content": content},
            }

    if "create_task" in instruction:
        if agent == "gemini":
            return {"toolName": "create_task", "toolInput": {"title": "test"}}
        else:
            return {
                "tool_name": "mcp__plugin_aops-core_task_manager__create_task",
                "tool_input": {"title": "test"},
            }

    if "bash" in instruction:
        cmd = instruction.split("bash ")[-1]
        if agent == "gemini":
            return {"toolName": "run_shell_command", "toolInput": {"command": cmd}}
        else:
            return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    return {}


# --- Tests ---


@pytest.mark.parametrize(
    "gate, instruction, session_state_args, expected_result",
    [
        # Hydration Gate Tests
        (
            "hydration",
            "read file /etc/hosts",
            {"is_hydration_pending": True},
            "blocked",
        ),
        (
            "hydration",
            "read file /etc/hosts",
            {"is_hydration_pending": False},
            "allowed",
        ),
        (
            "hydration",
            "list_prompts",
            {"is_hydration_pending": True},
            "allowed",
        ),  # Hydration-safe tool
        (
            "hydration",
            "activate_skill prompt-hydrator",
            {"is_hydration_pending": True},
            "allowed",
        ),  # Hydration bypass
        # Task Required Gate Tests (Destructive tools)
        ("task_required", "write_file test.txt", {"task_bound": False}, "blocked"),
        ("task_required", "write_file test.txt", {"task_bound": True}, "allowed"),
        (
            "task_required",
            "create_task title='Test'",
            {"task_bound": False},
            "allowed",
        ),  # Task binding tools allowed
        ("task_required", "bash ls", {"task_bound": False}, "block"),  # bash disallowed
        (
            "task_required",
            "bash -c 'rm -rf /fakepath'",
            {"critic_invoked": False},
            "blocked",
        ),  # Destructive bash also disallowed
        # Task Required with Full Enforcement (Hydrator/Critic check)
        (
            "task_required",
            "write_file test.txt",
            {"task_bound": True, "plan_mode_invoked": False, "critic_invoked": False},
            "allowed",
        ),  # Default is task-only
        # Axiom Enforcer Gate Tests (P#8: Fail-fast / No workarounds)
        (
            "axiom_enforcer",
            "write_file_with_content try: pass except: pass",
            {},
            "blocked",
        ),
    ],
)
def test_gate_enforcement_logic(
    cli_agent, gate, instruction, session_state_args, expected_result
):
    """
    Test that specific gates enforce rules correctly across both agents by
    mocking the session state and simulating raw provider input.
    """
    # 1. Prepare Input
    raw_input = _simulate_tool_call(cli_agent, instruction)

    # 2. Map gate key to check function
    check_func = GATE_CHECKS.get(gate)
    if not check_func:
        raise ValueError(f"Unknown gate: {gate}")

    # 3. Execute with mocked environment
    with (
        mock_session_state(**session_state_args),
        patch("pathlib.Path.exists", return_value=True),
        patch.dict(
            os.environ, {"HYDRATION_GATE_MODE": "block", "TASK_GATE_MODE": "block"}
        ),
    ):
        ctx = GateContext(
            session_id="test-session-123", event_name="PreToolUse", input_data=raw_input
        )

        result = check_func(ctx)

    # 4. Verify Verdict
    if expected_result == "blocked":
        assert result is not None
        assert result.verdict in (GateVerdict.DENY, GateVerdict.WARN)
    elif expected_result == "allowed":
        assert result is None or result.verdict == GateVerdict.ALLOW


def test_full_gate_enforcement(cli_agent):
    """Verify that full three-gate enforcement works when enabled via environment."""
    instruction = "write_file test.txt"
    raw_input = _simulate_tool_call(cli_agent, instruction)
    check_func = GATE_CHECKS.get("task_required")

    # Scenario: Task bound, but hydrator and critic NOT invoked
    state_args = {
        "task_bound": True,
        "plan_mode_invoked": False,
        "critic_invoked": False,
    }

    with (
        mock_session_state(**state_args),
        patch.dict(
            os.environ,
            {
                "TASK_GATE_MODE": "block",
                "TASK_GATE_ENFORCE_ALL": "true",  # Enable full enforcement
            },
        ),
    ):
        ctx = GateContext(
            session_id="test-session-123", event_name="PreToolUse", input_data=raw_input
        )

        result = check_func(ctx)

        # Should be blocked because TASK_GATE_ENFORCE_ALL is true
        assert result is not None
        assert result.verdict == GateVerdict.DENY
        assert (
            "Critic" in result.context_injection
            or "Hydrate" in result.context_injection
        )
