"""Unit tests for orchestrate Claude Code OTel tracer hook integration."""

from __future__ import annotations

import sys
from pathlib import Path
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
    }


def test_discover_config_protocol_env_var(monkeypatch):
    """Verify discover_config detects OTEL_EXPORTER_OTLP_PROTOCOL."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")

    cfg = claude_code_tracer.discover_config()
    assert cfg == {
        "api_key": "",
        "task_id": "claude-code",
        "endpoint": "http://localhost:4317",
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
