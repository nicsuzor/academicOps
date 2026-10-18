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


import agy_tracer


def test_resolve_agent_name_sources(tmp_path):
    # 1. Payload fields
    assert claude_code_tracer.resolve_agent_name(data={"agent": "sara"}) == "sara"
    assert claude_code_tracer.resolve_agent_name(data={"agent_name": "marsha"}) == "marsha"
    assert claude_code_tracer.resolve_agent_name(data={"agent_type": "plugin:rbg"}) == "rbg"
    assert claude_code_tracer.resolve_agent_name(data={"subagent_type": "pauli"}) == "pauli"
    assert claude_code_tracer.resolve_agent_name(data={"role": "planner"}) == "planner"

    # 2. Environment variable AOPS_AGENT_NAME (one env var only)
    with patch.dict("os.environ", {"AOPS_AGENT_NAME": "james"}, clear=True):
        assert claude_code_tracer.resolve_agent_name() == "james"

    # 3. Payload takes precedence over AOPS_AGENT_NAME
    with patch.dict("os.environ", {"AOPS_AGENT_NAME": "james"}):
        assert claude_code_tracer.resolve_agent_name(data={"agent": "sara"}) == "sara"

    # 4. Old env vars ignored
    with patch.dict(
        "os.environ",
        {"CLAUDE_AGENT_NAME": "james", "AGENT_NAME": "james", "AGY_AGENT_NAME": "james"},
        clear=True,
    ):
        assert claude_code_tracer.resolve_agent_name() == ""


def test_resolve_agent_name_no_settings_scan_or_heuristics(tmp_path):
    # Settings file must NOT be scanned
    local_dir = tmp_path / "project"
    claude_dir = local_dir / ".claude"
    claude_dir.mkdir(parents=True)
    (claude_dir / "settings.json").write_text(json.dumps({"agent": "pauli"}), encoding="utf-8")
    with patch.dict("os.environ", {}, clear=True):
        assert claude_code_tracer.resolve_agent_name(cwd=str(local_dir)) == ""

    # Directory heuristics must NOT apply
    dispatch_dir = tmp_path / "dispatch"
    dispatch_dir.mkdir()
    ida_dir = tmp_path / "ida"
    ida_dir.mkdir()
    james_dir = tmp_path / "james"
    james_dir.mkdir()
    with patch.dict("os.environ", {}, clear=True):
        assert claude_code_tracer.resolve_agent_name(cwd=str(dispatch_dir)) == ""
        assert claude_code_tracer.resolve_agent_name(cwd=str(ida_dir)) == ""
        assert claude_code_tracer.resolve_agent_name(cwd=str(james_dir)) == ""

    # Unnamed returns empty string, never defaults to "ida"
    with patch.dict("os.environ", {}, clear=True):
        assert claude_code_tracer.resolve_agent_name() == ""
        assert claude_code_tracer.resolve_agent_name(data={}) == ""


def test_claude_tracer_named_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "human", "text": "hello"}) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-claude-named"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("claude_code_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch(
            "claude_code_tracer._save_state",
            side_effect=lambda sid, st: state_store.update({sid: st}),
        ),
        patch(
            "claude_code_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)
        ),
        patch(
            "claude_code_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("claude_code_tracer._session_lock"),
        patch.dict("os.environ", {}, clear=True),
    ):
        claude_code_tracer.handle_user_prompt_submit(
            {
                "session_id": session_id,
                "prompt": "hello",
                "agent_name": "sara",
                "transcript_path": str(transcript),
            },
            config,
        )
        assert state_store[session_id].get("agent_name") == "sara"

        claude_code_tracer.handle_stop(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "last_assistant_message": "done",
            },
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    assert chain_span["attributes"].get("agent.name") == "sara"
    assert exported_kwargs[0].get("agent_name") == "sara"


def test_claude_tracer_env_only_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "human", "text": "hello"}) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-claude-env"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("claude_code_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch(
            "claude_code_tracer._save_state",
            side_effect=lambda sid, st: state_store.update({sid: st}),
        ),
        patch(
            "claude_code_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)
        ),
        patch(
            "claude_code_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("claude_code_tracer._session_lock"),
        patch.dict("os.environ", {"AOPS_AGENT_NAME": "james"}, clear=True),
    ):
        claude_code_tracer.handle_user_prompt_submit(
            {"session_id": session_id, "prompt": "hello", "transcript_path": str(transcript)},
            config,
        )
        # Session state must NOT store the env var
        assert "agent_name" not in state_store[session_id]

        claude_code_tracer.handle_stop(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "last_assistant_message": "done",
            },
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    assert chain_span["attributes"].get("agent.name") == "james"
    assert exported_kwargs[0].get("agent_name") == "james"


def test_claude_tracer_unnamed_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "human", "text": "hello"}) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-claude-unnamed"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("claude_code_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch(
            "claude_code_tracer._save_state",
            side_effect=lambda sid, st: state_store.update({sid: st}),
        ),
        patch(
            "claude_code_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)
        ),
        patch(
            "claude_code_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("claude_code_tracer._session_lock"),
        patch.dict("os.environ", {}, clear=True),
    ):
        claude_code_tracer.handle_user_prompt_submit(
            {"session_id": session_id, "prompt": "hello", "transcript_path": str(transcript)},
            config,
        )
        assert "agent_name" not in state_store[session_id]

        claude_code_tracer.handle_stop(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "last_assistant_message": "done",
            },
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    # No span or resource carries agent.name
    assert "agent.name" not in chain_span["attributes"]
    assert not exported_kwargs[0].get("agent_name")


def test_agy_tracer_named_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Explain OTel"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "Done",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-agy-named"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch("agy_tracer._save_state", side_effect=lambda sid, st: state_store.update({sid: st})),
        patch("agy_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)),
        patch(
            "agy_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("agy_tracer._session_lock"),
        patch.dict("os.environ", {}, clear=True),
    ):
        agy_tracer.handle_pre_invocation(
            {
                "conversationId": session_id,
                "invocationNum": 0,
                "agent_name": "sara",
                "transcriptPath": str(transcript),
            },
            config,
        )
        assert state_store[session_id].get("agent_name") == "sara"

        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    assert chain_span["attributes"].get("agent.name") == "sara"
    assert exported_kwargs[0].get("agent_name") == "sara"


def test_agy_tracer_env_only_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Explain OTel"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "Done",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-agy-env"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch("agy_tracer._save_state", side_effect=lambda sid, st: state_store.update({sid: st})),
        patch("agy_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)),
        patch(
            "agy_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("agy_tracer._session_lock"),
        patch.dict("os.environ", {"AOPS_AGENT_NAME": "james"}, clear=True),
    ):
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
            config,
        )
        assert "agent_name" not in state_store[session_id]

        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    assert chain_span["attributes"].get("agent.name") == "james"
    assert exported_kwargs[0].get("agent_name") == "james"


def test_agy_tracer_unnamed_session(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Explain OTel"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "Done",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_kwargs: list[dict] = []

    session_id = "session-agy-unnamed"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch("agy_tracer._save_state", side_effect=lambda sid, st: state_store.update({sid: st})),
        patch("agy_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)),
        patch(
            "agy_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_kwargs.append(kwargs),
            ),
        ),
        patch("agy_tracer._session_lock"),
        patch.dict("os.environ", {}, clear=True),
    ):
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
            config,
        )
        assert "agent_name" not in state_store[session_id]

        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert len(exported_records) > 0
    chain_span = exported_records[0]
    assert "agent.name" not in chain_span["attributes"]
    assert not exported_kwargs[0].get("agent_name")


def test_unnamed_session_subagent_spans_retain_naming():
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

    config = {
        "endpoint": "localhost:4317",
    }
    records = [
        {
            "name": "Task",
            "start_ns": 1000,
            "end_ns": 2000,
            "trace_id_hex": "0123456789abcdef0123456789abcdef",
            "span_id_hex": "0123456789abcdef",
            "attributes": {
                "openinference.span.kind": "AGENT",
                "agent.name": "coder",
            },
        }
    ]

    with (
        patch.object(claude_code_tracer, "_otel_imports", return_value=otel_mock),
        patch.object(claude_code_tracer, "_create_exporter", return_value=MagicMock()),
    ):
        claude_code_tracer._build_and_export_spans(
            config=config,
            session_id="test-session-subagent",
            username="test-user",
            span_records=records,
            agent_name="",
            cwd=str(REPO_ROOT),
        )

    called_attrs = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
    assert called_attrs.get("agent.name") == "coder"


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


def test_discover_config_resolves_polecat_target_task():
    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "POLECAT_TARGET_TASK": "aops_940d9db2",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "aops_940d9db2"

    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "POLECAT_TASK": "aops_7b1b67fe",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "aops_7b1b67fe"

    # When GENAI_ENGINE_TASK_ID is set to placeholder 'ns', POLECAT_TARGET_TASK still resolves
    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "GENAI_ENGINE_TASK_ID": "ns",
            "POLECAT_TARGET_TASK": "aops_940d9db2",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "aops_940d9db2"

    # AOPS_TASK_ID takes precedence over POLECAT_TARGET_TASK
    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "AOPS_TASK_ID": "task-123",
            "POLECAT_TARGET_TASK": "aops_940d9db2",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config()
        assert cfg is not None
        assert cfg["task_id"] == "task-123"

    # Explicit data payload takes precedence over environment variables
    with patch.dict(
        "os.environ",
        {
            "GENAI_ENGINE_API_KEY": "test-key",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://localhost:4317",
            "POLECAT_TARGET_TASK": "aops_940d9db2",
        },
        clear=True,
    ):
        cfg = claude_code_tracer.discover_config({"task_id": "task-789"})
        assert cfg is not None
        assert cfg["task_id"] == "task-789"


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
        test_cwd = str(REPO_ROOT / "tests")
        claude_code_tracer._build_and_export_spans(
            config=config,
            session_id="test-session-123",
            username="test-user",
            span_records=records,
            agent_name="sara",
            cwd=test_cwd,
        )

    # Inspect set_attribute calls on the span
    called_attrs = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}

    assert called_attrs.get("service.name") == "academicOps"
    assert called_attrs.get("agent.name") == "sara"
    assert called_attrs.get("cwd") == test_cwd
    assert called_attrs.get("project.dir") == str(REPO_ROOT)
    assert called_attrs.get("aops.repo") == "academicOps"
    assert called_attrs.get("aops.surface") == "claude-code"
    assert called_attrs.get("project.name") == "academicOps"
    assert called_attrs.get("openinference.project.name") == "academicOps"
    assert "task.id" not in called_attrs
    assert "tag.task_id" not in called_attrs


def test_build_and_export_spans_defaults_service_name_and_surface():
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

    config = {
        "endpoint": "localhost:4317",
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
            session_id="test-session-456",
            username="test-user",
            span_records=records,
            agent_name="ida",
            cwd=str(REPO_ROOT),
        )

    called_attrs = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
    assert called_attrs.get("service.name") == "aops-claude-hooks"
    assert called_attrs.get("aops.surface") == "claude-code"
    assert called_attrs.get("aops.repo") == "academicOps"
    assert called_attrs.get("project.dir") == str(REPO_ROOT)
    assert called_attrs.get("project.name") == "academicOps"
    assert called_attrs.get("openinference.project.name") == "academicOps"


def test_build_and_export_spans_detects_ci_surface():
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

    config = {
        "endpoint": "localhost:4317",
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
        patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}),
    ):
        claude_code_tracer._build_and_export_spans(
            config=config,
            session_id="test-session-ci",
            username="test-user",
            span_records=records,
            cwd=str(REPO_ROOT),
        )

    called_attrs = {call[0][0]: call[0][1] for call in mock_span.set_attribute.call_args_list}
    assert called_attrs.get("service.name") == "aops-claude-hooks"
    assert called_attrs.get("aops.surface") == "github-actions"


def test_resolve_project_name_ignores_default_env_var(tmp_path):
    repo_dir = tmp_path / "my-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    with patch.dict(
        "os.environ",
        {
            "PHOENIX_PROJECT_NAME": "default",
            "OTEL_SERVICE_NAME": "default",
            "OTEL_RESOURCE_ATTRIBUTES": "service.name=default",
        },
        clear=True,
    ):
        # 'default' must be ignored and fallback to academicOps (never directory name)
        resolved = claude_code_tracer.resolve_project_name(data={"cwd": str(repo_dir)})
        assert resolved == "academicOps"


def test_resolve_project_name_routes_to_custom_and_test_project():
    with patch.dict(
        "os.environ",
        {"PHOENIX_PROJECT_NAME": "academicOps-test"},
        clear=True,
    ):
        resolved = claude_code_tracer.resolve_project_name()
        assert resolved == "academicOps-test"

    # Explicit non-default project argument takes precedence
    resolved = claude_code_tracer.resolve_project_name(project="custom-proj")
    assert resolved == "custom-proj"


def test_resolve_canonical_project_normalizes_aops():
    assert claude_code_tracer.resolve_canonical_project("aops") == "academicOps"
    assert claude_code_tracer.resolve_canonical_project("academicops") == "academicOps"
    assert claude_code_tracer.resolve_canonical_project("academicOps") == "academicOps"
    assert claude_code_tracer.resolve_canonical_project("aops-task1") == "academicOps-task1"


def test_resolve_checkout_root(tmp_path):
    repo = tmp_path / "my-repo"
    sub = repo / "a" / "b" / "c"
    sub.mkdir(parents=True)
    (repo / ".git").mkdir()

    assert claude_code_tracer.resolve_checkout_root(str(sub)) == str(repo)
    assert claude_code_tracer.resolve_checkout_root(str(repo)) == str(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    assert claude_code_tracer.resolve_checkout_root(str(outside)) == str(outside)


def test_resolve_project_from_git_worktree(tmp_path):
    main_repo = tmp_path / "academicOps"
    main_git = main_repo / ".git"
    worktrees_git = main_git / "worktrees" / "fix-branch"
    worktrees_git.mkdir(parents=True)

    wt_dir = tmp_path / "worktrees" / "academicOps" / "fix-branch"
    wt_dir.mkdir(parents=True)
    git_file = wt_dir / ".git"
    git_file.write_text(f"gitdir: {worktrees_git}\n", encoding="utf-8")

    # Should resolve gitdir pointer to main_repo name 'academicOps'
    resolved = claude_code_tracer.resolve_project_from_dir(str(wt_dir))
    assert resolved == "academicOps"


def test_resolve_cwd_from_agy_workspace_paths(tmp_path):
    ws = str(tmp_path / "from_agy_ws")
    data = {"workspacePaths": [ws]}
    assert claude_code_tracer.resolve_cwd(data) == str(Path(ws).resolve())

    data_snake = {"workspace_paths": [ws]}
    assert claude_code_tracer.resolve_cwd(data_snake) == str(Path(ws).resolve())


def _run_claude_turn(tmp_path, env):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "human", "text": "hello"}) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_records: list[dict] = []
    exported_usernames: list = []
    session_id = "session-claude-user"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("claude_code_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch(
            "claude_code_tracer._save_state",
            side_effect=lambda sid, st: state_store.update({sid: st}),
        ),
        patch(
            "claude_code_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)
        ),
        patch(
            "claude_code_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_records.extend(span_records),
                exported_usernames.append(username),
            ),
        ),
        patch("claude_code_tracer._session_lock"),
        patch.dict("os.environ", env, clear=True),
    ):
        claude_code_tracer.handle_user_prompt_submit(
            {"session_id": session_id, "prompt": "hello", "transcript_path": str(transcript)},
            config,
        )
        claude_code_tracer.handle_stop(
            {
                "session_id": session_id,
                "transcript_path": str(transcript),
                "last_assistant_message": "done",
            },
            config,
        )
    return exported_records, exported_usernames


def test_claude_tracer_omits_user_id_without_username(tmp_path):
    # Cloud containers set neither USER nor USERNAME; no "unknown" placeholder.
    records, usernames = _run_claude_turn(tmp_path, {})
    assert records
    assert "user.id" not in records[0]["attributes"]
    assert all(not u for u in usernames)


def test_claude_tracer_omits_user_id_for_empty_user(tmp_path):
    records, usernames = _run_claude_turn(tmp_path, {"USER": ""})
    assert "user.id" not in records[0]["attributes"]
    assert all(not u for u in usernames)


def test_claude_tracer_sets_user_id_from_env(tmp_path):
    records, usernames = _run_claude_turn(tmp_path, {"USER": "nic"})
    assert records[0]["attributes"].get("user.id") == "nic"
    assert usernames and all(u == "nic" for u in usernames)


def test_agy_tracer_omits_user_id_without_username(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {"step_index": 0, "type": "USER_INPUT", "content": "Explain OTel"},
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "content": "Done",
        },
    ]
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    state_store: dict[str, dict] = {}
    exported_usernames: list = []
    session_id = "session-agy-user"
    config = {"endpoint": "localhost:4317"}

    with (
        patch("agy_tracer._load_state", side_effect=lambda sid: state_store.get(sid, {})),
        patch("agy_tracer._save_state", side_effect=lambda sid, st: state_store.update({sid: st})),
        patch("agy_tracer._delete_state", side_effect=lambda sid: state_store.pop(sid, None)),
        patch(
            "agy_tracer._build_and_export_spans",
            side_effect=lambda config, session_id, username, span_records, **kwargs: (
                exported_usernames.append(username)
            ),
        ),
        patch("agy_tracer._session_lock"),
        patch.dict("os.environ", {}, clear=True),
    ):
        agy_tracer.handle_pre_invocation(
            {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
            config,
        )
        agy_tracer.handle_stop(
            {"conversationId": session_id, "transcriptPath": str(transcript)},
            config,
        )

    assert exported_usernames
    assert all(not u for u in exported_usernames)
