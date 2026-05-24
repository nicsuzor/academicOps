from unittest.mock import patch

import pytest
from hooks.schemas import HookContext
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


@pytest.fixture
def mock_subagent_file(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    pauli_md = agents_dir / "pauli.md"
    pauli_md.write_text(
        "---\n"
        "name: pauli\n"
        "tools:\n"
        "- read_file\n"
        "- activate_skill\n"
        "- run_shell_command\n"
        "- write_file\n"
        "---\n"
        "# Pauli\n"
    )
    return tmp_path


def test_dispatch_fidelity_gate_blocks_dropped_tools(mock_subagent_file):
    """Test that dispatch_fidelity gate blocks when tools requested are not in allowed list."""
    with (
        patch("lib.paths.get_aops_root", return_value=mock_subagent_file),
        patch("lib.paths.get_skills_dir", return_value=mock_subagent_file),
    ):
        GateRegistry.initialize()
        gate = GateRegistry.get_gate("dispatch_fidelity")

        ctx = HookContext(
            session_id="test-session",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={
                "subagent_type": "pauli",
                "prompt": "do something",
                "tools": ["Bash", "Read", "Grep", "Glob", "Edit", "Write", "Skill"],
            },
            raw_input={},
        )
        state = SessionState.create("test-session")

        result = gate.check(ctx, state)

        assert result is not None
        assert result.verdict.value == "deny"
        # Grep (grep_search), Glob (glob), Edit (replace) are not in pauli.md
        assert "Grep" in result.system_message
        assert "Glob" in result.system_message
        assert "Edit" in result.system_message
        # Bash (run_shell_command), Read (read_file), Write (write_file), Skill (activate_skill) are in pauli.md, should not be in message
        assert "- `Bash`" not in result.system_message


def test_dispatch_fidelity_gate_allows_valid_tools(mock_subagent_file):
    """Test that dispatch_fidelity gate allows when all requested tools are allowed."""
    with (
        patch("lib.paths.get_aops_root", return_value=mock_subagent_file),
        patch("lib.paths.get_skills_dir", return_value=mock_subagent_file),
    ):
        GateRegistry.initialize()
        gate = GateRegistry.get_gate("dispatch_fidelity")

        ctx = HookContext(
            session_id="test-session",
            hook_event="PreToolUse",
            tool_name="Agent",
            tool_input={
                "subagent_type": "pauli",
                "prompt": "do something",
                "tools": ["Bash", "Read", "Write", "Skill"],
            },
            raw_input={},
        )
        state = SessionState.create("test-session")

        result = gate.check(ctx, state)

        # None means no block (passed through gate)
        assert result is None
