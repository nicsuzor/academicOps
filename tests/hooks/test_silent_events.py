"""Silent/transparent events — task notifications and other no-op routing.

Events that should produce empty or minimal output from the router.
Task-notifications are not real user input, so no gates/hydrator/PKB-nudge
run for them — but they DO get one short guidance line (see
``task_notification.guidance`` template) reminding the agent to absorb
routine background completions silently rather than relay them.
"""

import json
import uuid
from pathlib import Path
from unittest.mock import patch

from hooks.router import HookRouter

from tests.hooks.gate_helpers import run_router_claude, run_router_claude_raw

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


class TestLogAllHooksUnhandledEvents:
    """aops_2597b5ff scope D, item 1/4a: every CC hook event the installed
    client emits — including the 20 newly-subscribed-but-gate-less ones and
    anything genuinely unrecognized — must be a log-only no-op: exit 0, no
    crash, no block, and (critically) still LOGGED rather than silently
    dropped. router._call_gate_method's if/elif chain has no branch for these
    events and falls through to `return None`, so this is really proving the
    fallthrough is safe end-to-end through main(), not just unit-testable."""

    def _read_log_entries(self, log_path: Path) -> list[dict]:
        assert log_path.exists(), f"expected a log line at {log_path}, found none"
        return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]

    def test_newly_subscribed_gateless_event_logs_and_noops(self, monkeypatch, tmp_path) -> None:
        """TaskCreated: one of the 20 events added to hooks.json in this PR.
        No gate branch exists for it in router._call_gate_method."""
        log_path = tmp_path / "gateless-event-hooks.jsonl"
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(log_path))

        input_data = {
            "hook_event_name": "TaskCreated",
            "session_id": f"test-{uuid.uuid4()}",
        }
        stdout, returncode, stderr = run_router_claude_raw(input_data)

        assert returncode == 0, f"router must exit 0 on an unhandled event; stderr={stderr}"
        assert "Traceback" not in stderr, f"router must not crash; stderr={stderr}"
        output = json.loads(stdout)
        # No enforcement channel fired — this event carries no gate verdict.
        assert output.get("decision") != "block"

        entries = self._read_log_entries(log_path)
        assert len(entries) == 1
        assert entries[0]["hook_event"] == "TaskCreated"

    def test_truly_unknown_event_logs_and_noops(self, monkeypatch, tmp_path) -> None:
        """An event name the router has never heard of (not even in the
        confirmed 30-event set) must still degrade to a safe no-op — the
        router must never assume it knows the full event universe."""
        log_path = tmp_path / "unknown-event-hooks.jsonl"
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(log_path))

        input_data = {
            "hook_event_name": "SomeFutureEventNoOneHasHeardOfYet",
            "session_id": f"test-{uuid.uuid4()}",
        }
        stdout, returncode, stderr = run_router_claude_raw(input_data)

        assert returncode == 0, f"router must exit 0 on an unknown event; stderr={stderr}"
        assert "Traceback" not in stderr, f"router must not crash; stderr={stderr}"
        output = json.loads(stdout)
        assert output.get("decision") != "block"

        entries = self._read_log_entries(log_path)
        assert len(entries) == 1
        assert entries[0]["hook_event"] == "SomeFutureEventNoOneHasHeardOfYet"


class TestUpsDiagnosticEnrichment:
    """aops_2597b5ff scope D, item 3/4b: the UPS diagnostic instrument.

    Every UserPromptSubmit log line must carry prompt_id, a prompt preview +
    length, whether _is_task_notification matched, and every gate transition
    the event caused — regardless of which execute_hooks() branch (the
    task-notification short-circuit, or the normal gate-dispatch path) the
    prompt took. This is the actual diagnostic for Nic's re-arm question.
    """

    def _read_log_entries(self, log_path: Path) -> list[dict]:
        assert log_path.exists(), f"expected a log line at {log_path}, found none"
        return [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]

    def test_normal_prompt_ups_diagnostic_fields_and_gate_transition(
        self, monkeypatch, tmp_path
    ) -> None:
        """A real (non-task-notification) UPS: is_task_notification=False, and
        exit_reflection's unconditional UPS trigger (definitions.py — fires on
        EVERY UserPromptSubmit regardless of EXIT_REFLECTION_GATE_MODE) must
        show up in gate_transitions, proving the plumbing actually captures a
        real gate re-arm end-to-end."""
        log_path = tmp_path / "ups-diagnostic-hooks.jsonl"
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(log_path))

        prompt = "please help me refactor the widget module " + ("x" * 200)
        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": f"test-{uuid.uuid4()}",
            "prompt": prompt,
            "prompt_id": "test-prompt-id-12345",
        }
        output, stderr = run_router_claude(input_data)

        entries = self._read_log_entries(log_path)
        assert len(entries) == 1
        entry = entries[0]
        diagnostic = entry["output"]["metadata"]["ups_diagnostic"]

        assert diagnostic["prompt_id"] == "test-prompt-id-12345"
        assert diagnostic["prompt_preview"] == prompt[:80]
        assert diagnostic["prompt_length"] == len(prompt)
        assert diagnostic["is_task_notification"] is False

        transitions = diagnostic["gate_transitions"]
        assert any(t["gate"] == "exit_reflection" for t in transitions), (
            f"Expected exit_reflection's unconditional UPS re-arm trigger in "
            f"gate_transitions, got: {transitions}"
        )
        exit_reflection_transition = next(t for t in transitions if t["gate"] == "exit_reflection")
        assert exit_reflection_transition["hook_event"] == "UserPromptSubmit"
        assert exit_reflection_transition["to_status"] == "closed"

    def test_task_notification_ups_diagnostic_marks_short_circuit(
        self, monkeypatch, tmp_path
    ) -> None:
        """The short-circuit branch (is_task_notification=True) must ALSO be
        diagnostically logged — this is the branch Nic's leading hypothesis
        says background completions sometimes DON'T take (the
        '[SYSTEM NOTIFICATION - NOT USER INPUT]' preamble case), so proving
        this branch's own logging is correct is what lets a real log line
        distinguish the two."""
        log_path = tmp_path / "ups-diagnostic-notification-hooks.jsonl"
        monkeypatch.setenv("AOPS_HOOK_LOG_PATH", str(log_path))

        input_data = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": f"test-{uuid.uuid4()}",
            "prompt": "<task-notification>Task completed</task-notification>",
        }
        run_router_claude(input_data)

        entries = self._read_log_entries(log_path)
        assert len(entries) == 1
        diagnostic = entries[0]["output"]["metadata"]["ups_diagnostic"]

        assert diagnostic["is_task_notification"] is True
        # No gates ran on the short-circuit branch — nothing could have
        # transitioned.
        assert diagnostic["gate_transitions"] == []
