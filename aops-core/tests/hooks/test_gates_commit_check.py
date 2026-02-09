import unittest
from unittest.mock import MagicMock, patch

from hooks.schemas import HookContext
from lib.gate_model import GateResult, GateVerdict
from lib.gates.custodiet import CustodietGate
from lib.session_state import SessionState


class TestCustodietGateCommitCheck(unittest.TestCase):
    def setUp(self):
        self.gate = CustodietGate()
        self.state = SessionState.create("test-session")
        self.ctx = HookContext(
            session_id="test-session",
            hook_event="Stop",
            raw_input={"transcript_path": "/tmp/transcript.jsonl"}
        )

    @patch("lib.gates.custodiet.check_uncommitted_work")
    def test_on_stop_blocking(self, mock_check):
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.should_block = True
        mock_result.reminder_needed = False
        mock_result.message = "Uncommitted changes detected."
        mock_check.return_value = mock_result

        # Call on_stop
        result = self.gate.on_stop(self.ctx, self.state)

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.verdict, GateVerdict.DENY)
        self.assertIn("Uncommitted changes detected", result.system_message)
        self.assertIn("Uncommitted changes detected", result.context_injection)

    @patch("lib.gates.custodiet.check_uncommitted_work")
    def test_on_stop_reminder(self, mock_check):
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.should_block = False
        mock_result.reminder_needed = True
        mock_result.message = "Reminder: Unpushed commits."
        mock_check.return_value = mock_result

        # Call on_stop
        result = self.gate.on_stop(self.ctx, self.state)

        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.verdict, GateVerdict.ALLOW)
        self.assertIn("Reminder: Unpushed commits", result.system_message)

    @patch("lib.gates.custodiet.check_uncommitted_work")
    def test_on_stop_clean(self, mock_check):
        # Setup mock return value
        mock_result = MagicMock()
        mock_result.should_block = False
        mock_result.reminder_needed = False
        mock_result.message = ""
        mock_check.return_value = mock_result

        # Call on_stop
        result = self.gate.on_stop(self.ctx, self.state)

        # Verify result
        self.assertIsNone(result)
