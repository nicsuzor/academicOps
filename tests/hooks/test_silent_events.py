"""Silent/transparent events — task notifications and other no-op routing.

Events that should produce empty or minimal output from the router.
Task-notifications are not real user input, so no gates/hydrator/PKB-nudge
run for them — but they DO get one short guidance line (see
``task_notification.guidance`` template) reminding the agent to absorb
routine background completions silently rather than relay them.
"""

import json
import uuid
from unittest.mock import patch

from hooks.router import HookRouter

from tests.hooks.gate_helpers import run_router_claude

TASK_NOTIFICATION_GUIDANCE_MARKER = "background task notification"

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
    """Task-notification prompts get no gates/hydrator/PKB-nudge, only the
    short absorb-silently guidance line."""

    def test_task_notification_ups_returns_guidance_only(self, monkeypatch):
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        monkeypatch.setattr("hooks.router.persist_session_data", lambda data: None)

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
            additional_context = output_json.get("hookSpecificOutput", {}).get(
                "additionalContext", ""
            )
            assert TASK_NOTIFICATION_GUIDANCE_MARKER in additional_context, (
                f"Expected task-notification guidance, got: {json.dumps(output_json, indent=2)}"
            )
            # No verdict, system_message, or gate side-effects — only the
            # guidance context injection.
            assert output_json.get("hookSpecificOutput", {}).get("permissionDecision") is None
            # execute_hooks() no longer logs internally — logging happens once,
            # uniformly, in main() AFTER resolve_policy() runs (so the JSONL
            # entry reflects the resolved wire decision, not just the gate's
            # pre-translation verdict). See main()'s log_hook_event() call.
            mock_log.assert_not_called()

    def test_task_notification_subprocess_returns_guidance_only(self) -> None:
        """Task-notification via subprocess returns only the guidance injection."""
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": f"test-{uuid.uuid4()}",
            "prompt": "<task-notification>Task completed</task-notification>",
        }
        output, stderr = run_router_claude(input_data)
        additional_context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert TASK_NOTIFICATION_GUIDANCE_MARKER in additional_context, (
            f"Expected task-notification guidance, got: {output}"
        )
