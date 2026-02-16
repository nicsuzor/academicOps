import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.schemas import HookContext
from lib.gates.custom_conditions import check_custom_condition
from lib.gate_types import GateState


def test_validate_policy_condition_blocks_bare_python():
    ctx = MagicMock(spec=HookContext)
    ctx.tool_name = "Bash"
    ctx.tool_input = {"command": "python script.py"}

    state = MagicMock(spec=GateState)
    state.metrics = {}

    session_state = MagicMock()

    result = check_custom_condition("validate_policy", ctx, state, session_state)

    assert result is True
    assert "Bare 'python' command detected" in state.metrics["block_reason"]


def test_validate_policy_condition_allows_uv_run():
    ctx = MagicMock(spec=HookContext)
    ctx.tool_name = "Bash"
    ctx.tool_input = {"command": "uv run python script.py"}

    state = MagicMock(spec=GateState)
    state.metrics = {}

    session_state = MagicMock()

    result = check_custom_condition("validate_policy", ctx, state, session_state)

    assert result is False
    # Verify no block_reason is set for allowed commands
    assert "block_reason" not in state.metrics


def test_validate_policy_block_reason_format():
    """Verify the block reason includes required information."""
    ctx = MagicMock(spec=HookContext)
    ctx.tool_name = "Bash"
    ctx.tool_input = {"command": "python script.py"}

    state = MagicMock(spec=GateState)
    state.metrics = {}

    session_state = MagicMock()

    result = check_custom_condition("validate_policy", ctx, state, session_state)

    assert result is True
    assert "block_reason" in state.metrics
    block_reason = state.metrics["block_reason"]
    # Verify message includes command and policy reference
    assert "python script.py" in block_reason
    assert "P#93" in block_reason
