"""Spans from a GitHub Actions run carry the run's identity, and no other spans do."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer

_GITHUB_ENV = {
    "GITHUB_ACTIONS": "true",
    "GITHUB_REPOSITORY": "nicsuzor/academicOps",
    "GITHUB_RUN_ID": "1234567890",
    "GITHUB_RUN_ATTEMPT": "2",
    "GITHUB_WORKFLOW": "Claude Code",
    "GITHUB_JOB": "claude",
    "GITHUB_EVENT_NAME": "issue_comment",
    "GITHUB_REF": "refs/heads/dev",
    "GITHUB_SHA": "0123456789abcdef0123456789abcdef01234567",
    "GITHUB_SERVER_URL": "https://github.com",
}


def test_github_resource_attrs_empty_outside_actions():
    with patch.dict("os.environ", {"GITHUB_RUN_ID": "1"}, clear=True):
        assert claude_code_tracer._github_resource_attrs() == {}


def test_github_resource_attrs_identify_the_run():
    with patch.dict("os.environ", _GITHUB_ENV, clear=True):
        attrs = claude_code_tracer._github_resource_attrs()

    assert attrs == {
        "github.repository": "nicsuzor/academicOps",
        "github.run_id": "1234567890",
        "github.run_attempt": "2",
        "github.workflow": "Claude Code",
        "github.job": "claude",
        "github.event_name": "issue_comment",
        "github.ref": "refs/heads/dev",
        "github.sha": "0123456789abcdef0123456789abcdef01234567",
        "github.run_url": "https://github.com/nicsuzor/academicOps/actions/runs/1234567890/attempts/2",
    }


def test_github_resource_attrs_skip_unset_values():
    env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": "o/r"}
    with patch.dict("os.environ", env, clear=True):
        assert claude_code_tracer._github_resource_attrs() == {"github.repository": "o/r"}


def _export_one_span() -> dict:
    mock_span = MagicMock()
    mock_span.get_span_context.return_value = MagicMock(trace_id=1, span_id=2)
    mock_tracer = MagicMock()
    mock_tracer.start_span.return_value = mock_span
    mock_provider = MagicMock()
    mock_provider.get_tracer.return_value = mock_tracer
    otel_mock = (
        MagicMock(),
        MagicMock(),
        MagicMock(return_value=mock_provider),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
    )
    records = [
        {
            "name": "Bash",
            "start_ns": 1000,
            "end_ns": 2000,
            "trace_id_hex": "0123456789abcdef0123456789abcdef",
            "span_id_hex": "0123456789abcdef",
            "attributes": {},
        }
    ]
    with (
        patch.object(claude_code_tracer, "_otel_imports", return_value=otel_mock),
        patch.object(claude_code_tracer, "_create_exporter", return_value=MagicMock()),
    ):
        claude_code_tracer._build_and_export_spans(
            config={"endpoint": "localhost:4318", "project_name": "github-actions"},
            session_id="s-1",
            username="runner",
            span_records=records,
            agent_name="qa",
            cwd="/home/runner/work/academicOps/academicOps",
        )
    return {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}


def test_exported_spans_carry_github_run_attrs():
    with patch.dict("os.environ", _GITHUB_ENV, clear=True):
        attrs = _export_one_span()

    assert attrs["github.run_id"] == "1234567890"
    assert attrs["github.repository"] == "nicsuzor/academicOps"
    assert attrs["github.run_url"].endswith("/actions/runs/1234567890/attempts/2")
    assert attrs["session.id"] == "s-1"


def test_exported_spans_outside_actions_have_no_github_attrs():
    with patch.dict("os.environ", {}, clear=True):
        attrs = _export_one_span()

    assert not [k for k in attrs if k.startswith("github.")]
