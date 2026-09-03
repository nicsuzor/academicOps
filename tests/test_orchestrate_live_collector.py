"""Integration tests for orchestrate live OTel collector export."""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

# Add required search paths
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PLUGIN_ROOT = _REPO_ROOT / "plugins" / "aops"
_HOOKS_DIR = _PLUGIN_ROOT / "hooks"
_LIB_HOOKS_DIR = _REPO_ROOT / "lib" / "hooks"

for p in (_LIB_HOOKS_DIR, _PLUGIN_ROOT, _HOOKS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import claude_code_tracer
from dispatch import HookContext


def _load_plugin_module(name: str, path: Path):
    """Import a plugin hook module under a name of our choosing — ``handlers``
    collides across plugins in a shared pytest session. See
    ``tests/test_orchestrate_tracer.py`` for the full note."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load {path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


handlers = _load_plugin_module("orchestrate_handlers", _HOOKS_DIR / "handlers.py")


def _get_target_endpoint() -> str | None:
    return os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT")


TARGET_ENDPOINT = _get_target_endpoint()

pytestmark = pytest.mark.skipif(
    not TARGET_ENDPOINT,
    reason="No OTel collector endpoint configured (OTEL_EXPORTER_OTLP_ENDPOINT or GENAI_ENGINE_TRACE_ENDPOINT)",
)


@pytest.fixture(autouse=True)
def clean_env(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr(claude_code_tracer, "STATE_DIR", fake_home / ".claude" / "tracer")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))


def _endpoint() -> str:
    """The configured endpoint, narrowed to `str`.

    `pytestmark` skips this whole module when the endpoint is unset, so no test
    body here ever runs with `None` — the assert states that invariant rather
    than defending against it.
    """
    assert TARGET_ENDPOINT is not None
    return TARGET_ENDPOINT


def test_live_collector_create_exporter():
    """Verify _create_exporter initializes successfully against the live target endpoint."""
    endpoint = _endpoint()
    protocol = os.environ.get("GENAI_ENGINE_TRACE_PROTOCOL", "")

    exporter = claude_code_tracer._create_exporter(
        endpoint=endpoint,
        protocol=protocol,
    )
    assert exporter is not None, f"Failed to create exporter for live endpoint {endpoint}"


def test_live_collector_build_and_export_spans():
    """Verify _build_and_export_spans sends span to live collector endpoint."""
    endpoint = _endpoint()
    protocol = os.environ.get("GENAI_ENGINE_TRACE_PROTOCOL", "")
    service_name = "orchestrate-live-integration-test"
    span_name = "live_collector_verification_span"
    attributes = {"test.marker": "live_collector_verification_test"}

    config = {
        "endpoint": endpoint,
        "task_id": service_name,
        "service_name": service_name,
        "protocol": protocol,
    }

    now_ns = time.time_ns()
    span_record = {
        "name": span_name,
        "start_ns": now_ns - 100_000_000,
        "end_ns": now_ns,
        "trace_id_hex": "1234567890abcdef1234567890abcdef",
        "span_id_hex": "1234567890abcdef",
        "attributes": attributes,
    }

    # Execute export against live collector endpoint
    claude_code_tracer._build_and_export_spans(
        config=config,
        session_id="live-collector-verification-session",
        username="live-integration-test",
        span_records=[span_record],
    )


def test_live_collector_standard_tracer_handlers():
    """Verify standard tracer handlers execute against the live collector endpoint with required parameters."""
    endpoint = _endpoint()
    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "")
    service_name = "orchestrate-live-integration-test"
    span_name = "live_collector_verification_span"
    attributes = {"test.marker": "live_collector_verification_test"}

    os.environ["OTEL_SERVICE_NAME"] = service_name
    os.environ["GENAI_ENGINE_TASK_ID"] = service_name
    if not os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT"):
        os.environ["GENAI_ENGINE_TRACE_ENDPOINT"] = endpoint

    session_id = "live-collector-handlers-session"

    # 1. UserPromptSubmit
    ctx_ups = HookContext(
        client="claude",
        event="UserPromptSubmit",
        session_id=session_id,
        raw={"session_id": session_id, "prompt": "live collector prompt verification"},
    )
    assert handlers.user_prompt_submit(ctx_ups) is None

    # 2. PreToolUse
    ctx_pre = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Bash",
        session_id=session_id,
        raw={
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "echo live test"},
        },
    )
    assert handlers.pre_tool(ctx_pre) is None

    # 3. PostToolUse
    ctx_post = HookContext(
        client="claude",
        event="PostToolUse",
        tool="Bash",
        session_id=session_id,
        raw={
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "echo live test"},
            "tool_response": {"output": "live test\n"},
        },
    )
    assert handlers.post_tool(ctx_post) is None

    # 4. PostToolUseFailure
    ctx_fail = HookContext(
        client="claude",
        event="PostToolUseFailure",
        tool="Bash",
        session_id=session_id,
        raw={
            "session_id": session_id,
            "tool_name": "Bash",
            "tool_input": {"command": "false"},
            "tool_response": {"error": "live test failure command error"},
        },
    )
    assert handlers.post_tool_failure(ctx_fail) is None

    # 5. Stop
    ctx_stop = HookContext(
        client="claude",
        event="Stop",
        session_id=session_id,
        raw={"session_id": session_id},
    )
    assert handlers.stop(ctx_stop) is None

    # Directly execute handle_* methods with custom verification span_name & attributes
    config = {
        "endpoint": endpoint,
        "task_id": service_name,
        "service_name": service_name,
        "protocol": protocol,
    }
    data = {
        "session_id": session_id,
        "tool_name": span_name,
        "tool_input": {"command": "test"},
        "tool_response": {"output": "ok"},
        "attributes": attributes,
    }
    claude_code_tracer.handle_user_prompt_submit(data, config)
    claude_code_tracer.handle_pre_tool(data, config)
    claude_code_tracer.handle_post_tool(data, config)
    claude_code_tracer.handle_post_tool_failure(data, config)
    claude_code_tracer.handle_stop(data, config)
