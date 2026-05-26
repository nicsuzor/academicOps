"""Silent/transparent events — task notifications and other no-op routing.

Events that should produce empty or minimal output from the router.
"""

import json
import uuid
from unittest.mock import patch

from hooks.router import HookRouter

from tests.hooks.gate_helpers import run_router_claude

TASK_NOTIFICATION_RAW_INPUT = {
    "permission_mode": "bypassPermissions",
    "prompt": (
        "<task-notification>\n"
        "<task-id>byszqmmj5</task-id>\n"
        "<tool-use-id>toolu_01KhbRm2oo5b8gzCqokMY68B</tool-use-id>\n"
        "<output-file>/tmp/claude-1000/-opt-nic--aops-crew-barbara-5-aops/tasks/byszqmmj5.output</output-file>\n"
        "<status>completed</status>\n"
        '<summary>Background command "Generate task graph data" completed (exit code 0)</summary>\n'
        "</task-notification>\n"
        "Read the output file to retrieve the result: "
        "/tmp/claude-1000/-opt-nic--aops-crew-barbara-5-aops/tasks/byszqmmj5.output"
    ),
}


class TestTaskNotificationSilent:
    """Task-notification prompts should produce empty router output."""

    def test_task_notification_ups_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        monkeypatch.setattr("hooks.router.persist_session_data", lambda data: None)
        monkeypatch.setattr("hooks.router.log_event_to_session", lambda *a, **kw: None)

        router = HookRouter()

        raw_input = {
            **TASK_NOTIFICATION_RAW_INPUT,
            "session_id": "test-task-notification-silent",
            "hook_event_name": "UserPromptSubmit",
        }

        ctx = router.normalize_input(raw_input)

        with patch("hooks.router.log_hook_event") as mock_log:
            canonical = router.execute_hooks(ctx)
            output = router.output_for_claude(canonical, ctx.hook_event)

            output_json = json.loads(output.model_dump_json(exclude_none=True))
            assert output_json == {}, (
                f"Expected empty output for task-notification UPS, got: {json.dumps(output_json, indent=2)}"
            )
            mock_log.assert_called_once_with(ctx, output=canonical)

    def test_task_notification_subprocess_returns_empty(self) -> None:
        """Task-notification via subprocess returns empty output."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": f"test-{uuid.uuid4()}",
            "prompt": "<task-notification>Task completed</task-notification>",
        }
        output, stderr = run_router_claude(input_data)
        assert output == {}, f"Expected empty output, got: {output}"
