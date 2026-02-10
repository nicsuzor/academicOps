import unittest
from unittest.mock import MagicMock
from lib.gates.engine import GenericGate
from lib.gate_types import GateConfig, GateTrigger, GateCondition, GateTransition, GateStatus, GateState
from hooks.schemas import HookContext
from lib.session_state import SessionState

class TestEngineUnblocking(unittest.TestCase):
    def test_pretooluse_unblock_trigger(self):
        """Verify that a trigger in PreToolUse updates the state before policies are checked."""
        config = GateConfig(
            name="test",
            description="Test gate",
            initial_status=GateStatus.CLOSED,
            triggers=[
                GateTrigger(
                    condition=GateCondition(hook_event="PreToolUse", tool_name_pattern="unblock"),
                    transition=GateTransition(target_status=GateStatus.OPEN)
                )
            ],
            policies=[]
        )
        gate = GenericGate(config)
        
        state = SessionState.create("session-123")
        state.gates["test"] = GateState(status=GateStatus.CLOSED)
        
        ctx = HookContext(
            session_id="session-123",
            hook_event="PreToolUse",
            tool_name="unblock",
            raw_input={}
        )
        
        result = gate.check(ctx, state)
        
        # Verify state is now OPEN
        self.assertEqual(state.gates["test"].status, GateStatus.OPEN)
        self.assertEqual(result.verdict.value, "allow")

    def test_pretooluse_unblock_prevents_policy_deny(self):
        """Verify that unblocking in PreToolUse prevents a policy from denying the same turn."""
        config = GateConfig(
            name="test",
            description="Test gate with policy",
            initial_status=GateStatus.CLOSED,
            triggers=[
                GateTrigger(
                    condition=GateCondition(hook_event="PreToolUse", tool_name_pattern="unblock"),
                    transition=GateTransition(target_status=GateStatus.OPEN)
                )
            ],
            policies=[
                # Policy that denies if CLOSED
                # Note: excluded_tool_categories is NOT used here to force policy check
                {
                    "condition": GateCondition(hook_event="PreToolUse", current_status=GateStatus.CLOSED),
                    "verdict": "deny",
                    "message_template": "Blocked!"
                }
            ]
        )
        # Manually fix policies because Pydantic might complain about dict in GatePolicy
        from lib.gate_types import GatePolicy
        config.policies = [GatePolicy(**p) if isinstance(p, dict) else p for p in config.policies]
        
        gate = GenericGate(config)
        
        state = SessionState.create("session-123")
        state.gates["test"] = GateState(status=GateStatus.CLOSED)
        
        ctx = HookContext(
            session_id="session-123",
            hook_event="PreToolUse",
            tool_name="unblock",
            raw_input={}
        )
        
        result = gate.check(ctx, state)
        
        # Should be ALLOW because the trigger ran first and opened the gate
        self.assertEqual(state.gates["test"].status, GateStatus.OPEN)
        self.assertEqual(result.verdict.value, "allow")

if __name__ == "__main__":
    unittest.main()
