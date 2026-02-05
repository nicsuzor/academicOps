"""Tests for ntfy push notification integration."""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(AOPS_CORE_DIR / "aops-core"))

from hooks import gate_registry  # noqa: E402
from hooks import ntfy_notifier  # noqa: E402


class TestNtfyConfig(unittest.TestCase):
    """Test ntfy configuration loading from environment."""

    @patch.dict("os.environ", {}, clear=True)
    def test_config_disabled_when_no_topic(self):
        """Returns None when NTFY_TOPIC not set."""
        from lib.paths import get_ntfy_config

        config = get_ntfy_config()
        self.assertIsNone(config)

    @patch.dict(
        "os.environ",
        {
            "NTFY_TOPIC": "test-topic",
            "NTFY_SERVER": "https://ntfy.sh",
            "NTFY_PRIORITY": "3",
            "NTFY_TAGS": "robot,test",
        },
        clear=True,
    )
    def test_config_returns_dict_when_configured(self):
        """Returns config dict when all vars set."""
        from lib.paths import get_ntfy_config

        config = get_ntfy_config()
        self.assertIsNotNone(config)
        self.assertEqual(config["topic"], "test-topic")
        self.assertEqual(config["server"], "https://ntfy.sh")
        self.assertEqual(config["priority"], 3)
        self.assertEqual(config["tags"], "robot,test")

    @patch.dict("os.environ", {"NTFY_TOPIC": "test-topic"}, clear=True)
    def test_config_fails_without_server(self):
        """Raises RuntimeError when NTFY_TOPIC set but NTFY_SERVER missing."""
        from lib.paths import get_ntfy_config

        with self.assertRaises(RuntimeError) as ctx:
            get_ntfy_config()
        self.assertIn("NTFY_SERVER", str(ctx.exception))

    @patch.dict(
        "os.environ",
        {"NTFY_TOPIC": "test-topic", "NTFY_SERVER": "https://ntfy.sh"},
        clear=True,
    )
    def test_config_fails_without_priority(self):
        """Raises RuntimeError when NTFY_PRIORITY missing."""
        from lib.paths import get_ntfy_config

        with self.assertRaises(RuntimeError) as ctx:
            get_ntfy_config()
        self.assertIn("NTFY_PRIORITY", str(ctx.exception))

    @patch.dict(
        "os.environ",
        {
            "NTFY_TOPIC": "test-topic",
            "NTFY_SERVER": "https://ntfy.sh",
            "NTFY_PRIORITY": "3",
        },
        clear=True,
    )
    def test_config_fails_without_tags(self):
        """Raises RuntimeError when NTFY_TAGS missing."""
        from lib.paths import get_ntfy_config

        with self.assertRaises(RuntimeError) as ctx:
            get_ntfy_config()
        self.assertIn("NTFY_TAGS", str(ctx.exception))


class TestNtfyNotifierFunctions(unittest.TestCase):
    """Test ntfy_notifier module functions."""

    def setUp(self):
        self.config = {
            "enabled": True,
            "topic": "test-topic",
            "server": "https://ntfy.sh",
            "priority": 3,
            "tags": "robot,test",
        }

    @patch("hooks.ntfy_notifier.urllib.request.urlopen")
    def test_send_notification_success(self, mock_urlopen):
        """send_notification returns True on success."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ntfy_notifier.send_notification(
            self.config, title="Test", message="Hello"
        )
        self.assertTrue(result)
        mock_urlopen.assert_called_once()

    @patch("hooks.ntfy_notifier.urllib.request.urlopen")
    def test_send_notification_failure_returns_false(self, mock_urlopen):
        """send_notification returns False on network error."""
        import urllib.error

        mock_urlopen.side_effect = urllib.error.URLError("Network error")

        result = ntfy_notifier.send_notification(
            self.config, title="Test", message="Hello"
        )
        self.assertFalse(result)

    @patch("hooks.ntfy_notifier.urllib.request.urlopen")
    def test_send_notification_non_200_returns_false(self, mock_urlopen):
        """send_notification returns False on non-200 status."""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = ntfy_notifier.send_notification(
            self.config, title="Test", message="Hello"
        )
        self.assertFalse(result)

    @patch("hooks.ntfy_notifier.send_notification")
    def test_notify_session_start(self, mock_send):
        """notify_session_start sends correct notification."""
        mock_send.return_value = True
        ntfy_notifier.notify_session_start(self.config, "abc123def456")

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        self.assertEqual(call_args[1]["title"], "Session Started")
        self.assertIn("abc123de", call_args[1]["message"])

    @patch("hooks.ntfy_notifier.send_notification")
    def test_notify_session_stop_with_task(self, mock_send):
        """notify_session_stop includes task ID in message."""
        mock_send.return_value = True
        ntfy_notifier.notify_session_stop(self.config, "session123", "task-456")

        call_args = mock_send.call_args
        self.assertIn("task-456", call_args[1]["message"])

    @patch("hooks.ntfy_notifier.send_notification")
    def test_notify_subagent_stop_with_verdict(self, mock_send):
        """notify_subagent_stop includes verdict in message."""
        mock_send.return_value = True
        ntfy_notifier.notify_subagent_stop(self.config, "session123", "critic", "PASS")

        call_args = mock_send.call_args
        self.assertIn("PASS", call_args[1]["message"])
        self.assertIn("white_check_mark", call_args[1]["tags"])

    @patch("hooks.ntfy_notifier.send_notification")
    def test_notify_subagent_stop_warn_verdict(self, mock_send):
        """notify_subagent_stop uses warning tag for non-PASS verdict."""
        mock_send.return_value = True
        ntfy_notifier.notify_subagent_stop(
            self.config, "session123", "critic", "REVISE"
        )

        call_args = mock_send.call_args
        self.assertIn("warning", call_args[1]["tags"])


class TestNtfyGateIntegration(unittest.TestCase):
    """Test ntfy gate integration in gate_registry."""

    def setUp(self):
        self.config = {
            "enabled": True,
            "topic": "test-topic",
            "server": "https://ntfy.sh",
            "priority": 3,
            "tags": "robot,test",
        }

    @patch("hooks.gate_registry.get_ntfy_config")
    def test_gate_skips_when_not_configured(self, mock_config):
        """Gate returns None when ntfy not configured."""
        mock_config.return_value = None

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="SessionStart",
            input_data={},
        )

        result = gate_registry.run_ntfy_notifier(ctx)
        self.assertIsNone(result)

    @patch("hooks.gate_registry.get_ntfy_config")
    @patch("hooks.ntfy_notifier.notify_session_start")
    def test_gate_notifies_on_session_start(self, mock_notify, mock_config):
        """Gate sends notification on SessionStart."""
        mock_config.return_value = self.config
        mock_notify.return_value = True

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="SessionStart",
            input_data={},
        )

        result = gate_registry.run_ntfy_notifier(ctx)

        mock_notify.assert_called_once_with(self.config, "test-session")
        self.assertIsNone(result)  # Gate never blocks

    @patch("hooks.gate_registry.get_ntfy_config")
    @patch("hooks.gate_registry.session_state")
    @patch("hooks.ntfy_notifier.notify_session_stop")
    def test_gate_notifies_on_stop(self, mock_notify, mock_session, mock_config):
        """Gate sends notification on Stop."""
        mock_config.return_value = self.config
        mock_session.get_current_task.return_value = "task-123"
        mock_notify.return_value = True

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="Stop",
            input_data={},
        )

        result = gate_registry.run_ntfy_notifier(ctx)

        mock_notify.assert_called_once_with(self.config, "test-session", "task-123")
        self.assertIsNone(result)

    @patch("hooks.gate_registry.get_ntfy_config")
    @patch("hooks.ntfy_notifier.notify_task_bound")
    def test_gate_notifies_on_task_binding(self, mock_notify, mock_config):
        """Gate sends notification when task is bound."""
        mock_config.return_value = self.config
        mock_notify.return_value = True

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                "tool_name": "mcp__plugin_aops-core_task_manager__update_task",
                "tool_input": {"id": "task-abc", "status": "in_progress"},
            },
        )

        result = gate_registry.run_ntfy_notifier(ctx)

        mock_notify.assert_called_once_with(self.config, "test-session", "task-abc")
        self.assertIsNone(result)

    @patch("hooks.gate_registry.get_ntfy_config")
    @patch("hooks.ntfy_notifier.notify_subagent_stop")
    def test_gate_notifies_on_subagent_stop(self, mock_notify, mock_config):
        """Gate sends notification when subagent completes."""
        mock_config.return_value = self.config
        mock_notify.return_value = True

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="PostToolUse",
            input_data={
                "tool_name": "Task",
                "tool_input": {"subagent_type": "critic"},
                "tool_result": {"verdict": "PASS"},
            },
        )

        result = gate_registry.run_ntfy_notifier(ctx)

        mock_notify.assert_called_once_with(
            self.config, "test-session", "critic", "PASS"
        )
        self.assertIsNone(result)

    @patch("hooks.gate_registry.get_ntfy_config")
    def test_gate_handles_config_error_gracefully(self, mock_config):
        """Gate logs and continues on config error."""
        mock_config.side_effect = RuntimeError("Config error")

        ctx = gate_registry.GateContext(
            session_id="test-session",
            event_name="SessionStart",
            input_data={},
        )

        # Should not raise
        result = gate_registry.run_ntfy_notifier(ctx)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
