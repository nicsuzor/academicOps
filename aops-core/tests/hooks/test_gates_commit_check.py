import unittest
from unittest.mock import MagicMock, patch

from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gates.definitions import GATE_CONFIGS
from lib.gates.engine import GenericGate
from lib.session_state import SessionState

# Find custodiet config
CUSTODIET_CONFIG = next(c for c in GATE_CONFIGS if c.name == "custodiet")


class TestCustodietGateCommitCheck(unittest.TestCase):
    def setUp(self):
        self.gate = GenericGate(CUSTODIET_CONFIG)
        self.state = SessionState.create("test-session")
        self.ctx = HookContext(
            session_id="test-session",
            hook_event="Stop",
            raw_input={"transcript_path": "/tmp/transcript.jsonl"},
        )

    @patch("hooks.session_end_commit_check.check_uncommitted_work")
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
        if result:
            self.assertEqual(result.verdict, GateVerdict.DENY)
            # Check system message (resolved from {block_reason} metric)
            # Note: check_custom_condition sets the metric.
            self.assertIsNotNone(result.system_message)
            if result.system_message:
                self.assertIn("Uncommitted changes detected", result.system_message)

    @patch("hooks.session_end_commit_check.check_uncommitted_work")
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
        if result:
            self.assertEqual(result.verdict, GateVerdict.WARN)
            self.assertIsNotNone(result.system_message)
            if result.system_message:
                self.assertIn("Reminder: Unpushed commits", result.system_message)

    @patch("hooks.session_end_commit_check.check_uncommitted_work")
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
