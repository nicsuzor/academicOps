"""Tests for span attribute resolution and task_id validation in claude_code_tracer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

import claude_code_tracer


def test_is_valid_task_id_rejects_placeholders_and_empty():
    assert not claude_code_tracer.is_valid_task_id("")
    assert not claude_code_tracer.is_valid_task_id("   ")
    assert not claude_code_tracer.is_valid_task_id("ns")
    assert not claude_code_tracer.is_valid_task_id("NS")
    assert not claude_code_tracer.is_valid_task_id("default")
    assert not claude_code_tracer.is_valid_task_id("academicops")
    assert not claude_code_tracer.is_valid_task_id("aops")


def test_is_valid_task_id_accepts_valid_formats():
    assert claude_code_tracer.is_valid_task_id("c4f828a2")
    assert claude_code_tracer.is_valid_task_id("ida-b3ff18ba")
    assert claude_code_tracer.is_valid_task_id("sara-37d4f9bf")
    assert claude_code_tracer.is_valid_task_id("task-123")
    assert claude_code_tracer.is_valid_task_id("epic-001")
    assert claude_code_tracer.is_valid_task_id("wf-bootstrap-test")
    assert claude_code_tracer.is_valid_task_id("d9d71b69-0354-48c5-be7d-ed55fc6112b8")


def test_resolve_cwd_priority(tmp_path):
    # 1. Payload cwd takes top priority
    data = {"cwd": str(tmp_path / "from_data")}
    state = {"cwd": str(tmp_path / "from_state")}
    assert claude_code_tracer.resolve_cwd(data, state) == str((tmp_path / "from_data").resolve())

    # 2. State cwd takes second priority
    assert claude_code_tracer.resolve_cwd({}, state) == str((tmp_path / "from_state").resolve())

    # 3. CLAUDE_PROJECT_DIR env var
    with patch.dict("os.environ", {"CLAUDE_PROJECT_DIR": str(tmp_path / "from_env")}):
        assert claude_code_tracer.resolve_cwd({}, {}) == str((tmp_path / "from_env").resolve())


def test_resolve_agent_name_sources(tmp_path):
    # 1. Payload agent
    assert claude_code_tracer.resolve_agent_name(data={"agent": "sara"}) == "sara"
    assert claude_code_tracer.resolve_agent_name(data={"agent_name": "marsha"}) == "marsha"
    assert claude_code_tracer.resolve_agent_name(data={"agent_type": "plugin:rbg"}) == "rbg"

    # 2. State agent_name
    assert claude_code_tracer.resolve_agent_name(state={"agent_name": "sara"}) == "sara"

    # 3. Environment variable
    with patch.dict("os.environ", {"CLAUDE_AGENT_NAME": "james"}):
        assert claude_code_tracer.resolve_agent_name() == "james"

    # 4. .claude/settings.json in cwd
    local_dir = tmp_path / "project"
    claude_dir = local_dir / ".claude"
    claude_dir.mkdir(parents=True)
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps({"agent": "pauli"}), encoding="utf-8")

    assert claude_code_tracer.resolve_agent_name(cwd=str(local_dir)) == "pauli"


def test_resolve_agent_name_does_not_climb_when_local_claude_exists(tmp_path):
    parent_dir = tmp_path / "workspace"
    parent_claude = parent_dir / ".claude"
    parent_claude.mkdir(parents=True)
    (parent_claude / "settings.json").write_text(json.dumps({"agent": "ida"}), encoding="utf-8")

    child_dir = parent_dir / "dispatch"
    child_claude = child_dir / ".claude"
    child_claude.mkdir(parents=True)
    # child has .claude but no agent in settings
    (child_claude / "settings.json").write_text(json.dumps({}), encoding="utf-8")

    # Because child_dir has a local .claude, it must NOT climb to parent_dir and inherit "ida"
    # Instead, the directory heuristic matches "dispatch" -> "sara"
    resolved = claude_code_tracer.resolve_agent_name(cwd=str(child_dir))
    assert resolved == "sara"


def test_resolve_agent_name_directory_heuristics(tmp_path):
    dispatch_dir = tmp_path / "dispatch"
    dispatch_dir.mkdir()
    assert claude_code_tracer.resolve_agent_name(cwd=str(dispatch_dir)) == "sara"

    ida_dir = tmp_path / "ida"
    ida_dir.mkdir()
    assert claude_code_tracer.resolve_agent_name(cwd=str(ida_dir)) == "ida"

    james_dir = tmp_path / "james"
    james_dir.mkdir()
    assert claude_code_tracer.resolve_agent_name(cwd=str(james_dir)) == "james"


def test_discover_config_sanitizes_task_id():
    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "GENAI_ENGINE_TASK_ID": "ns",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "", "Namespace 'ns' should be stripped from task_id"
        assert "cwd" in cfg
        assert "agent_name" in cfg

    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "AOPS_TASK_ID": "task-456",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "task-456"


def test_build_and_export_spans_sets_attributes():
    mock_span = MagicMock()
    mock_span.get_span_context.return_value = MagicMock(trace_id=1, span_id=2)
    mock_tracer = MagicMock()
    mock_tracer.start_span.return_value = mock_span
    mock_provider = MagicMock()
    mock_provider.get_tracer.return_value = mock_tracer

    otel_mock = (
        MagicMock(),  # trace
        MagicMock(),  # Resource
        MagicMock(return_value=mock_provider),  # TracerProvider
        MagicMock(),  # SpanContext
        MagicMock(),  # SimpleSpanProcessor
        MagicMock(),  # OTLPSpanExporter
        MagicMock(),  # SpanKind
        MagicMock(),  # TraceFlags
        MagicMock(),  # NonRecordingSpan
        MagicMock(),  # StatusCode
    )

    config = {
        "endpoint": "localhost:4317",
        "project_name": "academicOps",
        "service_name": "academicOps",
        "task_id": "ns",  # invalid task_id, should be omitted
    }
    records = [
        {
            "name": "test-span",
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
            config=config,
            session_id="test-session-123",
            username="test-user",
            span_records=records,
            agent_name="sara",
            cwd="/workspace/junior/dispatch",
        )

    # Inspect set_attribute calls on the span
    called_attrs = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}

    assert called_attrs.get("service.name") == "academicOps"
    assert called_attrs.get("agent.name") == "sara"
    assert called_attrs.get("cwd") == "/workspace/junior/dispatch"
    assert called_attrs.get("project.dir") == "/workspace/junior/dispatch"
    assert "task.id" not in called_attrs
    assert "tag.task_id" not in called_attrs
