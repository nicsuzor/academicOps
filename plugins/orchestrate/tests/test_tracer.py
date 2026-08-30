"""Unit tests for orchestrate Claude Code OTel tracer hook integration."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Add required search paths
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PLUGIN_ROOT.parent.parent
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
_LIB_HOOKS_DIR = _REPO_ROOT / "lib" / "hooks"

for p in (_LIB_HOOKS_DIR, _PLUGIN_ROOT, _HOOKS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import claude_code_tracer
import handlers
from dispatch import HookContext


@pytest.fixture(autouse=True)
def clean_env(tmp_path, monkeypatch):
    """Clean tracing environment variables and isolate config files for tests."""
    for key in (
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_TRACE_PROTOCOL",
        "PHOENIX_PROJECT_NAME",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL",
        "OTEL_SERVICE_NAME",
        "OTEL_EXPORTER_OTLP_HEADERS",
        "OTEL_EXPORTER_OTLP_TRACES_HEADERS",
        "CLAUDE_PROJECT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))


def test_registered_handlers_mapping():
    """Verify that all 5 required hook handlers are registered in HANDLERS."""
    required_events = [
        "UserPromptSubmit",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "Stop",
    ]
    for event in required_events:
        assert event in handlers.HANDLERS, f"Event {event} missing from HANDLERS"
        registered_funcs = handlers.HANDLERS[event]
        assert len(registered_funcs) >= 1

    # Check function names
    assert handlers.user_prompt_submit in handlers.HANDLERS["UserPromptSubmit"]
    assert handlers.pre_tool in handlers.HANDLERS["PreToolUse"]
    assert handlers.post_tool in handlers.HANDLERS["PostToolUse"]
    assert handlers.post_tool_failure in handlers.HANDLERS["PostToolUseFailure"]
    assert handlers.stop in handlers.HANDLERS["Stop"]


@pytest.mark.parametrize("module_name", ["agy_tracer", "claude_code_tracer"])
def test_handlers_only_reach_for_attributes_the_tracer_module_exports(module_name):
    """handlers.py must never call a tracer-module attribute the module never imported.

    aops_2b8f41d0: every agy hook handler called agy_tracer.discover_config(),
    but agy_tracer's explicit `from claude_code_tracer import (...)` list
    omitted that name, so every agy hook raised AttributeError at call time —
    swallowed by the `except Exception` in each handler as a silent warning.
    No existing test imported both modules and cross-checked the names
    handlers.py actually reaches for, so the mismatch shipped unnoticed.
    """
    import ast
    import importlib

    handlers_source = (_HOOKS_DIR / "handlers.py").read_text()
    tree = ast.parse(handlers_source)
    attrs = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == module_name
    }
    assert attrs, f"expected handlers.py to reference at least one {module_name}.<attr>"

    module = importlib.import_module(module_name)
    missing = sorted(a for a in attrs if not hasattr(module, a))
    assert not missing, (
        f"handlers.py calls {module_name}.{missing} but {module_name} does not export "
        f"{'them' if len(missing) > 1 else 'it'}"
    )


def test_discover_config_absent():
    """Verify discover_config returns None when no env vars or config files exist."""
    assert claude_code_tracer.discover_config() is None


def test_discover_config_genai_env_vars(monkeypatch):
    """Verify discover_config detects GENAI_ENGINE environment variables."""
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "test-key")
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "test-task")
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://localhost:4318/v1/traces")

    cfg = claude_code_tracer.discover_config()
    assert cfg == {
        "api_key": "test-key",
        "task_id": "test-task",
        "endpoint": "http://localhost:4318/v1/traces",
        "project_name": "test-task",
    }


def test_discover_config_otel_env_vars_fallback(monkeypatch):
    """Verify discover_config falls back to standard OTel environment variables."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318/v1/traces")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "custom-claude-service")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Bearer secret-otel-token")

    cfg = claude_code_tracer.discover_config()
    assert cfg == {
        "api_key": "Authorization=Bearer secret-otel-token",
        "task_id": "custom-claude-service",
        "endpoint": "http://otel-collector:4318/v1/traces",
        "project_name": "custom-claude-service",
    }


def test_discover_config_protocol_env_var(monkeypatch, tmp_path):
    """Verify discover_config detects OTEL_EXPORTER_OTLP_PROTOCOL."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")

    cfg = claude_code_tracer.discover_config()
    assert cfg == {
        "api_key": "",
        "task_id": tmp_path.name,
        "endpoint": "http://localhost:4317",
        "project_name": tmp_path.name,
        "protocol": "grpc",
    }


def test_create_exporter_grpc_success():
    """Verify _create_exporter instantiates gRPC OTLPSpanExporter when available."""
    mock_grpc_exporter_cls = MagicMock()
    mock_module = MagicMock()
    mock_module.OTLPSpanExporter = mock_grpc_exporter_cls

    with patch.dict(
        "sys.modules", {"opentelemetry.exporter.otlp.proto.grpc.trace_exporter": mock_module}
    ):
        exp = claude_code_tracer._create_exporter(
            "http://localhost:4317", {"Authorization": "Bearer token"}
        )
        assert exp == mock_grpc_exporter_cls.return_value
        mock_grpc_exporter_cls.assert_called_once_with(
            endpoint="http://localhost:4317",
            headers={"Authorization": "Bearer token"},
            insecure=True,
            timeout=claude_code_tracer._EXPORT_TIMEOUT_S,
        )


def test_create_exporter_grpc_missing_fallback_http():
    """Verify _create_exporter falls back to HTTP exporter when gRPC exporter module is missing."""
    mock_http_exporter_cls = MagicMock()
    mock_http_module = MagicMock()
    mock_http_module.OTLPSpanExporter = mock_http_exporter_cls

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_http_module,
        },
    ):
        exp = claude_code_tracer._create_exporter("http://localhost:4318/v1/traces", None)
        assert exp == mock_http_exporter_cls.return_value
        mock_http_exporter_cls.assert_called_once_with(
            endpoint="http://localhost:4318/v1/traces",
            headers=None,
            timeout=claude_code_tracer._EXPORT_TIMEOUT_S,
        )


def test_create_exporter_both_missing_fallback_console():
    """Verify _create_exporter falls back to ConsoleSpanExporter when gRPC and HTTP are missing."""
    mock_console_exporter_cls = MagicMock()
    mock_sdk_export_module = MagicMock()
    mock_sdk_export_module.ConsoleSpanExporter = mock_console_exporter_cls

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": None,
            "opentelemetry.sdk.trace.export": mock_sdk_export_module,
        },
    ):
        exp = claude_code_tracer._create_exporter("http://localhost:4317", None)
        assert exp == mock_console_exporter_cls.return_value
        mock_console_exporter_cls.assert_called_once()


def test_create_exporter_all_failing_safe():
    """Verify _create_exporter returns None fail-safe when all exporters fail to initialize."""
    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": None,
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": None,
            "opentelemetry.sdk.trace.export": None,
        },
    ):
        exp = claude_code_tracer._create_exporter("http://localhost:4317", None)
        assert exp is None


def test_create_exporter_protocol_http_bypasses_grpc():
    """Verify protocol='http' skips gRPC exporter and uses HTTP exporter directly."""
    mock_grpc_cls = MagicMock()
    mock_grpc_module = MagicMock()
    mock_grpc_module.OTLPSpanExporter = mock_grpc_cls

    mock_http_cls = MagicMock()
    mock_http_module = MagicMock()
    mock_http_module.OTLPSpanExporter = mock_http_cls

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": mock_grpc_module,
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": mock_http_module,
        },
    ):
        exp = claude_code_tracer._create_exporter(
            "http://localhost:4318/v1/traces", None, protocol="http"
        )
        assert exp == mock_http_cls.return_value
        mock_grpc_cls.assert_not_called()
        mock_http_cls.assert_called_once()


def test_handlers_absent_env_vars_fail_safe():
    """Verify all 5 hook handlers run cleanly and return None when env vars are absent."""
    ctx = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id="test-session-123",
        raw={"session_id": "test-session-123", "prompt": "Hello world"},
    )

    assert handlers.user_prompt_submit(ctx) is None
    assert handlers.pre_tool(ctx) is None
    assert handlers.post_tool(ctx) is None
    assert handlers.post_tool_failure(ctx) is None
    assert handlers.stop(ctx) is None


def test_handlers_present_env_vars_export_spans(monkeypatch, tmp_path):
    """Verify all 5 handlers execute and generate span records when env vars are present."""
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "test-api-key")
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "task-abc")
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://localhost:4318/v1/traces")

    exported_records: list[dict] = []

    def mock_export_spans(config, session_id, username, span_records):
        exported_records.extend(span_records)

    monkeypatch.setattr(claude_code_tracer, "_build_and_export_spans", mock_export_spans)

    session_id = "session-test-456"

    # 1. UserPromptSubmit
    ctx_ups = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id=session_id,
        raw={"session_id": session_id, "prompt": "Analyze code"},
    )
    res_ups = handlers.user_prompt_submit(ctx_ups)
    assert res_ups is None

    # 2. PreToolUse
    ctx_pre = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        session_id=session_id,
        raw={"session_id": session_id, "tool_name": "Bash", "tool_input": {"command": "ls -la"}},
    )
    res_pre = handlers.pre_tool(ctx_pre)
    assert res_pre is None

    # 3. PostToolUse
    ctx_post = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Bash",
        session_id=session_id,
        raw={
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_response": {"output": "file1.txt\nfile2.txt"},
        },
    )
    res_post = handlers.post_tool(ctx_post)
    assert res_post is None
    assert len(exported_records) >= 1
    tool_span = exported_records[-1]
    assert tool_span["name"] == "Bash"
    assert tool_span["attributes"]["openinference.span.kind"] == "TOOL"

    # 4. PostToolUseFailure
    ctx_fail = HookContext(
        client="claude",
        event="PostToolUseFailure",
        tool="Bash",
        session_id=session_id,
        raw={
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "invalid-cmd"},
            "tool_response": {"error": "command not found"},
        },
    )
    res_fail = handlers.post_tool_failure(ctx_fail)
    assert res_fail is None
    fail_span = exported_records[-1]
    assert fail_span["name"] == "Bash"
    assert fail_span.get("error") is True
    assert fail_span.get("error_msg") == "command not found"

    # 5. Stop
    ctx_stop = HookContext(
        client="claude",
        event="Stop",
        session_id=session_id,
        raw={"session_id": session_id},
    )
    res_stop = handlers.stop(ctx_stop)
    assert res_stop is None
    chain_span = exported_records[-1]
    assert chain_span["name"] == "claude-code-turn"
    assert chain_span["attributes"]["openinference.span.kind"] == "CHAIN"


def test_handlers_collector_unreachable_fail_safe(monkeypatch):
    """Verify handlers handle collector network errors gracefully without crashing."""
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "test-api-key")
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "task-abc")
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://unreachable-host:9999/v1/traces")

    def mock_export_failing(*args, **kwargs):
        raise ConnectionError("Collector unreachable")

    monkeypatch.setattr(claude_code_tracer, "_build_and_export_spans", mock_export_failing)

    session_id = "session-fail-789"

    for func, event in [
        (handlers.user_prompt_submit, "UserPromptSubmit"),
        (handlers.pre_tool, "PreToolUse"),
        (handlers.post_tool, "PostToolUse"),
        (handlers.post_tool_failure, "PostToolUseFailure"),
        (handlers.stop, "Stop"),
    ]:
        ctx = HookContext(
            client="claude",
            event=event,
            tool="Read",
            session_id=session_id,
            raw={
                "session_id": session_id,
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/test"},
                "tool_response": "data",
                "error": "Failed",
            },
        )
        assert func(ctx) is None, (
            f"Handler for {event} raised or returned non-None on network error"
        )


def test_resolve_project_name(monkeypatch, tmp_path):
    """Verify resolve_project_name respects priority order."""
    # 1. Explicit task_id
    assert claude_code_tracer.resolve_project_name(task_id="explicit-task") == "explicit-task"

    # 2. GENAI_ENGINE_TASK_ID
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "env-genai-task")
    assert claude_code_tracer.resolve_project_name() == "env-genai-task"
    monkeypatch.delenv("GENAI_ENGINE_TASK_ID")

    # 3. PHOENIX_PROJECT_NAME
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "env-phoenix-proj")
    assert claude_code_tracer.resolve_project_name() == "env-phoenix-proj"
    monkeypatch.delenv("PHOENIX_PROJECT_NAME")

    # 4. OTEL_SERVICE_NAME
    monkeypatch.setenv("OTEL_SERVICE_NAME", "env-otel-svc")
    assert claude_code_tracer.resolve_project_name() == "env-otel-svc"
    monkeypatch.delenv("OTEL_SERVICE_NAME")

    # 5. Payload cwd
    payload = {"cwd": "/home/user/code/my-repo"}
    assert claude_code_tracer.resolve_project_name(payload) == "my-repo"

    # 6. CLAUDE_PROJECT_DIR fallback
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/var/projects/awesome-tool")
    assert claude_code_tracer.resolve_project_name() == "awesome-tool"
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")

    # 7. Fallback to cwd basename
    assert claude_code_tracer.resolve_project_name() == Path.cwd().name


def test_resolve_project_name_with_aliases(monkeypatch, tmp_path):
    """Verify resolve_project_name maps project aliases to canonical names."""
    config = {
        "projects": {
            "aops": {"aliases": ["academicOps"]},
        }
    }
    monkeypatch.setattr(claude_code_tracer, "_load_polecat_config", lambda: config)

    # 1. Payload cwd resolving to alias
    payload = {"cwd": "/home/user/code/academicOps"}
    assert claude_code_tracer.resolve_project_name(payload) == "aops"

    # 2. PHOENIX_PROJECT_NAME set to alias
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "academicOps")
    assert claude_code_tracer.resolve_project_name() == "aops"
    monkeypatch.delenv("PHOENIX_PROJECT_NAME")

    # 3. task_id with alias prefix
    assert (
        claude_code_tracer.resolve_project_name(task_id="academicOps-task_123") == "aops-task_123"
    )


def test_build_and_export_spans_resource_attributes(monkeypatch):
    """Verify _build_and_export_spans sets project and host attributes on Resource and Spans."""
    created_resources = []
    created_spans = []

    mock_span = MagicMock()
    created_spans.append(mock_span)

    mock_tracer = MagicMock()
    mock_tracer.start_span.return_value = mock_span

    mock_provider = MagicMock()
    mock_provider.get_tracer.return_value = mock_tracer

    def mock_tracer_provider_cls(**kwargs):
        created_resources.append(kwargs.get("resource"))
        return mock_provider

    mock_exporter = MagicMock()
    monkeypatch.setattr(
        claude_code_tracer, "_create_exporter", lambda *args, **kwargs: mock_exporter
    )

    # Patch TracerProvider
    orig_otel_imports = claude_code_tracer._otel_imports

    def mock_otel_imports():
        imports: list[Any] = list(orig_otel_imports())
        imports[2] = mock_tracer_provider_cls
        return tuple(imports)

    monkeypatch.setattr(claude_code_tracer, "_otel_imports", mock_otel_imports)

    config = {
        "endpoint": "http://localhost:4317",
        "task_id": "test-project",
        "project_name": "test-project",
    }
    records = [
        {
            "trace_id_hex": "11111111111111111111111111111111",
            "span_id_hex": "2222222222222222",
            "name": "test-span",
            "start_ns": 1000,
            "end_ns": 2000,
            "attributes": {"custom.attr": "value"},
        }
    ]

    claude_code_tracer._build_and_export_spans(
        config=config,
        session_id="session-xyz",
        username="tester",
        span_records=records,
    )

    assert len(created_resources) == 1
    res = created_resources[0]
    assert res.attributes["openinference.project.name"] == "test-project"
    assert res.attributes["project.name"] == "test-project"
    assert res.attributes["arthur.task"] == "test-project"
    assert res.attributes["arthur.user"] == "tester"
    assert "host.name" in res.attributes

    # Check span attributes
    span_calls = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
    assert span_calls["project.name"] == "test-project"
    assert span_calls["openinference.project.name"] == "test-project"
    assert span_calls["session.id"] == "session-xyz"
    assert span_calls["user.id"] == "tester"
    assert "host.name" in span_calls


def test_agy_extract_llm_spans_inputs(tmp_path):
    """Verify agy_tracer._extract_llm_spans_for_turn_agy populates input attributes for LLM spans."""
    import agy_tracer

    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "status": "DONE",
            "content": "What is the weather?",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "created_at": "2026-08-25T05:00:00Z",
            "tool_calls": [{"name": "get_weather", "args": {"location": "Sydney"}}],
        },
        {
            "step_index": 2,
            "source": "MODEL",
            "type": "GENERIC",
            "status": "DONE",
            "content": "22C and sunny",
        },
        {
            "step_index": 3,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "created_at": "2026-08-25T05:00:02Z",
            "content": "The weather in Sydney is 22C and sunny.",
        },
    ]
    with open(transcript, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    spans = agy_tracer._extract_llm_spans_for_turn_agy(
        transcript_path=str(transcript),
        human_count_at_start=0,
        trace_id_hex="11111111111111111111111111111111",
        root_span_id_hex="2222222222222222",
    )

    assert len(spans) == 2

    # Span 1: initial model response to user prompt
    span1_attrs = spans[0]["attributes"]
    assert span1_attrs["llm.input_messages.0.message.role"] == "user"
    assert span1_attrs["llm.input_messages.0.message.content"] == "What is the weather?"
    assert "What is the weather?" in span1_attrs["input.value"]

    # Span 2: follow-up model response to tool output
    span2_attrs = spans[1]["attributes"]
    assert span2_attrs["llm.input_messages.0.message.role"] == "tool"
    assert span2_attrs["llm.input_messages.0.message.content"] == "22C and sunny"
    assert "22C and sunny" in span2_attrs["input.value"]


def test_agy_post_tool_extracts_output_from_transcript(tmp_path, monkeypatch):
    """Verify agy_tracer.handle_post_tool extracts tool output from transcript rather than empty {}."""
    import agy_tracer

    transcript = tmp_path / "transcript.jsonl"
    entries = [
        {
            "step_index": 0,
            "source": "USER_EXPLICIT",
            "type": "USER_INPUT",
            "status": "DONE",
            "content": "Run ls",
        },
        {
            "step_index": 1,
            "source": "MODEL",
            "type": "PLANNER_RESPONSE",
            "status": "DONE",
            "created_at": "2026-08-25T05:00:00Z",
            "tool_calls": [{"name": "Bash", "args": {"command": "ls"}}],
        },
        {
            "step_index": 2,
            "source": "MODEL",
            "type": "GENERIC",
            "status": "DONE",
            "content": "file1.txt\nfile2.txt",
        },
    ]
    with open(transcript, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    exported_records = []

    def mock_export(config, session_id, username, span_records):
        exported_records.extend(span_records)

    monkeypatch.setattr(agy_tracer, "_build_and_export_spans", mock_export)

    session_id = "session-agy-test"
    # Pre-invocation to initialize state
    agy_tracer.handle_pre_invocation(
        {"conversationId": session_id, "invocationNum": 0, "transcriptPath": str(transcript)},
        {"endpoint": "http://localhost:4317", "task_id": "test-agy"},
    )
    # Pre-tool
    agy_tracer.handle_pre_tool(
        {"conversationId": session_id, "toolCall": {"name": "Bash", "args": {"command": "ls"}}},
        {"endpoint": "http://localhost:4317", "task_id": "test-agy"},
    )
    # Post-tool (payload without toolResponse)
    agy_tracer.handle_post_tool(
        {
            "conversationId": session_id,
            "toolCall": {"name": "Bash", "args": {"command": "ls"}},
            "transcriptPath": str(transcript),
        },
        {"endpoint": "http://localhost:4317", "task_id": "test-agy"},
    )

    assert len(exported_records) == 1
    tool_span = exported_records[0]
    assert tool_span["name"] == "Bash"
    assert "file1.txt" in tool_span["attributes"]["output.value"]
