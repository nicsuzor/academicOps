from hooks.schemas import HookContext
from lib.gate_model import GateResult
from lib.gate_types import GateState, GateStatus
from lib.session_state import SessionState

def execute_custom_action(name: str, ctx: HookContext, state: GateState, session_state: SessionState) -> GateResult | None:
    """
    Execute a named custom action.
    """
    # Reserved for future complex logic (e.g. file generation)
    # Currently handled by hook scripts directly.
    return None
