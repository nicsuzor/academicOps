"""Test that every turn root, typed or injected, carries non-empty output.value

From what its Stop hook holds, across all prompt shapes:
- Typed user prompt
- Task notification (<task-notification ...>)
- Cross-session message (<cross-session-message ...>)
- Channel message (telegram: ... or <channel-message ...>)
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer as cct

CONFIG = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
SESSION = "sess-turn-output"


class _CollectingExporter(SpanExporter):
    def __init__(self) -> None:
        self.spans = []

    def export(self, spans):
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def named(self, name: str) -> list:
        return [s for s in self.spans if s.name == name]


@pytest.fixture
def tracer_env(tmp_path, monkeypatch):
    monkeypatch.setattr(cct, "STATE_DIR", tmp_path / "tracer")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("AOPS_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("")
    return transcript


@pytest.fixture
def exporter():
    exp = _CollectingExporter()
    with patch.object(cct, "_create_exporter", return_value=exp):
        yield exp


def _hook(handler, transcript: Path, **payload) -> None:
    handler({"session_id": SESSION, "transcript_path": str(transcript), **payload}, CONFIG)


@pytest.mark.parametrize(
    ("prompt_shape", "prompt_text", "assistant_message"),
    [
        (
            "typed",
            "What is the status of the repository?",
            "The repository is currently on branch dev with all checks green.",
        ),
        (
            "task_notification",
            '<task-notification id="task_123"><status>done</status><summary>Worker completed PR review</summary></task-notification>',
            "Acknowledged task completion for task_123. Verification passed.",
        ),
        (
            "cross_session_message",
            '<cross-session-message from="ida:sara"><report>Claim verified against criteria</report></cross-session-message>',
            "Received report from sara. The claim is accepted.",
        ),
        (
            "channel_message",
            "telegram: Please review the latest benchmark results.",
            "I have reviewed the benchmark results and posted the summary to Telegram.",
        ),
    ],
)
def test_turn_root_carries_output_value_from_stop_hook_payload(
    tracer_env,
    exporter,
    prompt_shape,
    prompt_text,
    assistant_message,
):
    """Every turn root carries non-empty output.value from the Stop hook's last_assistant_message."""
    _hook(cct.handle_user_prompt_submit, tracer_env, prompt=prompt_text)
    _hook(cct.handle_stop, tracer_env, last_assistant_message=assistant_message)

    (turn_span,) = exporter.named("claude-code-turn")
    assert turn_span.attributes.get("input.value") == prompt_text
    assert turn_span.attributes.get("output.value") == assistant_message
    assert turn_span.attributes.get("output.value") is not None
    assert len(turn_span.attributes["output.value"]) > 0
