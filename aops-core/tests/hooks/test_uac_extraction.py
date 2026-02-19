import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add aops-core to path
AOPS_CORE = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(AOPS_CORE))

from hooks.schemas import HookContext
from lib.gates.custom_actions import execute_custom_action
from lib.session_state import SessionState


def test_extract_uac_logic():
    # Setup mock session state
    session_id = "test-session"
    state = SessionState.create(session_id)

    # Mock hydrator output
    hydrator_output = """
<hydration_result>
## HYDRATION RESULT
**Intent**: Fix the bug

### Acceptance Criteria

1. Verification test passes
2. No regressions found
- Bonus: code is cleaner

### Execution Plan
1. Fix it
2. Test it
</hydration_result>
"""

    ctx = MagicMock(spec=HookContext)
    ctx.session_id = session_id
    ctx.tool_output = hydrator_output
    ctx.subagent_type = "prompt-hydrator"

    # Execute action
    result = execute_custom_action("extract_uac", ctx, state.get_gate("uac"), state)

    assert result is not None
    assert "Extracted 3" in result.system_message

    # Verify state updates
    assert len(state.main_agent.user_acceptance_criteria) == 3
    assert state.main_agent.user_acceptance_criteria[0] == "Verification test passes"
    assert state.main_agent.user_acceptance_criteria[1] == "No regressions found"
    assert state.main_agent.user_acceptance_criteria[2] == "Bonus: code is cleaner"
    assert state.main_agent.uac_checked == [False, False, False]

    # Verify gate metrics
    assert "incomplete_uac_list" in state.get_gate("uac").metrics
    assert "Verification test passes" in state.get_gate("uac").metrics["incomplete_uac_list"]
