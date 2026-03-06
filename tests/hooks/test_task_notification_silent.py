"""Test that task-notification UserPromptSubmit produces empty output.

When Claude Code sends a task-notification prompt (background task completed),
the hook router should return an empty JSON object {} — no system message,
no verdict, no null values. The notification is internal plumbing and the
router should be transparent.

Source payload: /tmp/stop.jsonl line 1 (session 86b2bb57).
"""

import json

from hooks.router import HookRouter

# Raw input exactly as captured from the UserPromptSubmit call in /tmp/stop.jsonl
TASK_NOTIFICATION_RAW_INPUT = {
    "permission_mode": "bypassPermissions",
    "prompt": (
        "<task-notification>\n"
        "<task-id>byszqmmj5</task-id>\n"
        "<tool-use-id>toolu_01KhbRm2oo5b8gzCqokMY68B</tool-use-id>\n"
        "<output-file>/tmp/claude-1000/-opt-nic--aops-crew-barbara-5-aops/tasks/byszqmmj5.output</output-file>\n"
        "<status>completed</status>\n"
        '<summary>Background command "Start Streamlit from worktree on port 8501" completed (exit code 0)</summary>\n'
        "</task-notification>\n"
        "Read the output file to retrieve the result: "
        "/tmp/claude-1000/-opt-nic--aops-crew-barbara-5-aops/tasks/byszqmmj5.output"
    ),
}


class TestTaskNotificationSilent:
    """Task-notification prompts should produce empty router output."""

    def test_task_notification_ups_returns_empty_dict(self, monkeypatch):
        """UserPromptSubmit for a task-notification should output {}.

        The router currently emits system_message (gate status icons) and
        hookSpecificOutput with permissionDecision for every UPS event.
        For task-notifications this is noise — the output should be empty.
        """
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        monkeypatch.setattr("hooks.router.persist_session_data", lambda data: None)
        monkeypatch.setattr("hooks.router.log_event_to_session", lambda *a, **kw: None)
        monkeypatch.setattr("hooks.router.log_hook_event", lambda *a, **kw: None)

        router = HookRouter()

        raw_input = {
            **TASK_NOTIFICATION_RAW_INPUT,
            "session_id": "test-task-notification-silent",
            "hook_event_name": "UserPromptSubmit",
        }

        ctx = router.normalize_input(raw_input)
        canonical = router.execute_hooks(ctx)
        output = router.output_for_claude(canonical, ctx.hook_event)

        output_json = json.loads(output.model_dump_json(exclude_none=True))
        assert output_json == {}, (
            f"Expected empty output for task-notification UPS, got: {json.dumps(output_json, indent=2)}"
        )
