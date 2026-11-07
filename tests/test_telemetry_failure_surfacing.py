"""Tests for OpenTelemetry failure surfacing across emitters and hooks.

Covers AC-1.1 through AC-4.2 of specs/observability/telemetry-failure-surfacing.md.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.sdk.trace.export import SpanExportResult

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
RBG_HOOKS = REPO_ROOT / "plugins" / "rbg" / "hooks"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Make sure IDA_HOOKS is first in sys.path so handlers imports from ida
for p in (str(SCRIPTS_DIR), str(RBG_HOOKS), str(IDA_HOOKS)):
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import ci_otel_hooks
import claude_code_tracer
import dispatch
import evaluator_otel_trace
import handlers
import premise_check_gate
import premise_check_verdict
import report_argument as ra

_ANY_BASIS = ra.load_vocabulary().basis[0].phrase


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    """Isolate environment variables and state directories for each test."""
    monkeypatch.setenv("AOPS_STATE_DIR", str(tmp_path / "aops_state"))
    monkeypatch.setenv("AOPS_TRACER_STATE_DIR", str(tmp_path / "tracer_state"))
    monkeypatch.setenv("AOPS_SESSION_POINTER_DIR", str(tmp_path / "pointer_dir"))
    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate_state"))
    monkeypatch.setenv("PKB_MCP_URL", "http://localhost:8000/sse")
    for var in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "BETA_TRACING_ENDPOINT",
        "GENAI_ENGINE_TRACE_ENDPOINT",
        "GENAI_ENGINE_API_KEY",
        "AOPS_TELEMETRY_FAILURE_MODE",
        "PREMISE_CHECK_VERDICT_TRACING",
        "COPE_EVALUATOR_OTEL_TRACE_PATH",
    ):
        monkeypatch.delenv(var, raising=False)


# ==============================================================================
# 1. Unconfigured Telemetry (Empty Endpoint / Unset Credentials)
# ==============================================================================


def test_unconfigured_session_start_warns_and_injects_notice(capsys, tmp_path):
    """AC-1.1: Emitter detecting unconfigured endpoint at session start logs warning to stderr

    and injects diagnostic notice into session context.
    """
    ctx = dispatch.HookContext(
        client="claude",
        event="SessionStart",
        session_id="test-sess-unconfigured-1",
        cwd=str(tmp_path),
    )

    result = handlers.session_start(ctx)
    captured = capsys.readouterr()

    assert "WARNING: OpenTelemetry tracing unconfigured" in captured.err
    assert "Telemetry will NOT be exported" in captured.err

    assert result is not None
    assert result.kind is dispatch.Kind.ADVISE
    assert "WARNING: OpenTelemetry tracing is unconfigured" in result.inject_text
    assert "Spans and metrics for this session are dropped" in result.inject_text
    assert result.user_text is not None
    assert "WARNING: OpenTelemetry tracing is unconfigured" in result.user_text


def test_unconfigured_session_start_blocks_when_mode_is_block(monkeypatch, capsys, tmp_path):
    """AC-1.2: In mandatory/block mode, unconfigured telemetry returns refusal."""
    monkeypatch.setenv("AOPS_TELEMETRY_FAILURE_MODE", "block")
    ctx = dispatch.HookContext(
        client="claude",
        event="SessionStart",
        session_id="test-sess-block-1",
        cwd=str(tmp_path),
    )

    result = handlers.session_start(ctx)
    captured = capsys.readouterr()

    assert "WARNING: OpenTelemetry tracing unconfigured" in captured.err
    assert result is not None
    assert result.kind is dispatch.Kind.REFUSE
    assert "WARNING: OpenTelemetry tracing is unconfigured" in result.inject_text


def test_unconfigured_tracer_cli_exit_code(monkeypatch, capsys):
    """AC-1.2: CLI execution exits 0 in warn mode, 1 in block mode when unconfigured."""
    # 1. warn mode -> exit 0
    monkeypatch.setenv("AOPS_TELEMETRY_FAILURE_MODE", "warn")
    with pytest.raises(SystemExit) as exc_warn:
        claude_code_tracer.main(["claude_code_tracer.py", "pre_tool"])
    assert exc_warn.value.code == 0
    captured = capsys.readouterr()
    assert "WARNING: OpenTelemetry tracing unconfigured" in captured.err

    # 2. block mode -> exit 1
    monkeypatch.setenv("AOPS_TELEMETRY_FAILURE_MODE", "block")
    with pytest.raises(SystemExit) as exc_block:
        claude_code_tracer.main(["claude_code_tracer.py", "pre_tool"])
    assert exc_block.value.code == 1


def test_unconfigured_ci_emits_notice(capsys, tmp_path):
    """AC-1.3: In CI workflows, unconfigured endpoint emits notice annotation and stdout."""
    base = {"settings": "base"}
    # Endpoint unset
    settings = ci_otel_hooks.build_settings(
        aops_root=REPO_ROOT,
        out_dir=tmp_path,
        project="academicOps",
        base=base,
        python=sys.executable,
    )
    captured = capsys.readouterr()
    assert "::notice::Trace endpoint unset; run untraced" in captured.out
    assert "NOTICE: OpenTelemetry tracing unconfigured in CI" in captured.out
    assert settings == base


def test_unconfigured_rbg_evaluator_emits_notice(capsys, tmp_path):
    """AC-4.1: rbg-evaluator emits notice on stderr once when unconfigured."""
    ctx = dispatch.HookContext(
        client="claude",
        event="PreToolUse",
        session_id="test-rbg-1",
        tool="Bash",
    )
    eval_config = MagicMock()
    # Reset warned state if previously set
    evaluator_otel_trace.sink_for._unconfigured_warned = False

    sink = evaluator_otel_trace.sink_for(
        config=None,
        ctx=ctx,
        eval_config=eval_config,
        loaded={},
    )
    assert sink is None
    captured = capsys.readouterr()
    assert "NOTICE: rbg evaluator OTel tracing unconfigured" in captured.err


# ==============================================================================
# 2. HTTP 401/403 (Collector Rejection / Expired Auth) & Scrubbing
# ==============================================================================


def test_http_401_403_collector_rejection_logs_error_and_scrubs_secrets(capsys, monkeypatch):
    """AC-2.1: HTTP 401/403 logs error with endpoint, HTTP code, and scrubbed secrets."""
    endpoint = "https://user:password123@collector.example.com/v1/traces?token=urlsecret#frag"
    secret_token = "secret-super-sensitive-token-12345"
    config = {
        "endpoint": endpoint,
        "headers": {
            "Authorization": f"Bearer {secret_token}",
            "cf-access-client-secret": "cf-secret-xyz",
            "x-custom-key": "normal-val",
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Forbidden: Expired token"
    mock_resp.headers = {
        "Content-Type": "text/plain",
        "WWW-Authenticate": "Bearer error=invalid_token",
    }

    with patch("requests.Session.post", return_value=mock_resp):
        exporter = claude_code_tracer.ErrorReportingExporter(
            config=config, session_id="sess-403-test"
        )
        res = exporter.export([])
        assert res == SpanExportResult.FAILURE

    captured = capsys.readouterr()
    assert "ERROR: OpenTelemetry export refused by collector (HTTP 403)" in captured.err
    assert "https://collector.example.com/v1/traces" in captured.err
    assert "Authentication invalid or expired" in captured.err

    # Scrubbing check
    assert secret_token not in captured.err
    assert "cf-secret-xyz" not in captured.err
    assert "password123" not in captured.err
    assert "urlsecret" not in captured.err
    assert "user:" not in captured.err


def test_http_403_injects_diagnostic_notice_into_session(capsys, monkeypatch, tmp_path):
    """AC-2.2: Session context is injected with a diagnostic notice on 403 rejection."""
    session_id = "sess-diag-test-403"
    state_dir = Path(os.environ["AOPS_TRACER_STATE_DIR"])
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{session_id}.json"

    # Simulate error recorded by ErrorReportingExporter
    state_file.write_text(
        json.dumps(
            {
                "telemetry_error": {
                    "type": "auth_refusal",
                    "status_code": 403,
                    "endpoint": "https://collector.example.com",
                }
            }
        ),
        encoding="utf-8",
    )

    ctx = dispatch.HookContext(
        client="claude",
        event="PostToolUse",
        session_id=session_id,
        tool="Bash",
        cwd=str(tmp_path),
    )

    res = handlers.telemetry_diagnostic_handler(ctx)
    assert res is not None
    assert (
        "ERROR: OpenTelemetry export refused by collector (HTTP 403) at https://collector.example.com"
        in res.inject_text
    )
    assert "Authentication invalid or expired" in res.inject_text

    # Second call should return None (throttled/avoid spamming every turn)
    res_second = handlers.telemetry_diagnostic_handler(ctx)
    assert res_second is None


def test_repeated_403_is_throttled_without_network_roundtrips(capsys):
    """AC-2.3: Repeated 401/403 rejections are throttled with zero subsequent network calls."""
    endpoint = "https://collector.example.com/v1/traces"
    config = {"endpoint": endpoint, "headers": {}}
    session_id = "sess-throttle-test"

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("requests.Session.post", return_value=mock_resp) as mock_post:
        exp1 = claude_code_tracer.ErrorReportingExporter(config=config, session_id=session_id)
        res1 = exp1.export([])
        assert res1 == SpanExportResult.FAILURE
        assert mock_post.call_count == 1

        span_record = {
            "name": "span-test",
            "start_ns": 1000,
            "end_ns": 2000,
            "trace_id_hex": "0123456789abcdef0123456789abcdef",
            "span_id_hex": "0123456789abcdef",
            "attributes": {},
        }
        for _ in range(10):
            res_sub = claude_code_tracer._build_and_export_spans(
                config=config,
                session_id=session_id,
                username="u",
                span_records=[span_record],
            )
            assert res_sub is False

        assert mock_post.call_count == 1

    captured = capsys.readouterr()
    assert (
        "WARNING: OpenTelemetry export throttled due to persistent authorization rejection (HTTP 401)"
        in captured.err
    )


# ==============================================================================
# 3. Network Errors, Timeouts, 5xx Server Errors & Bounded Timeout
# ==============================================================================


def test_network_timeout_surfacing(capsys):
    """AC-3.1: Network timeout logs error with error type, endpoint, and elapsed duration."""
    endpoint = "https://slow-collector.example.com/v1/traces"
    config = {"endpoint": endpoint}
    session_id = "sess-timeout-test"

    with patch("requests.Session.post", side_effect=TimeoutError("Connection timed out")):
        exp = claude_code_tracer.ErrorReportingExporter(config=config, session_id=session_id)
        res = exp.export([])
        assert res == SpanExportResult.FAILURE

    captured = capsys.readouterr()
    assert "ERROR: OpenTelemetry export failed (network error): TimeoutError" in captured.err
    assert endpoint in captured.err
    assert "elapsed:" in captured.err


def test_server_500_error_surfacing(capsys):
    """AC-3.2: 5xx server errors log HTTP status and response snippet."""
    endpoint = "https://error-collector.example.com/v1/traces"
    config = {"endpoint": endpoint}
    session_id = "sess-500-test"

    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_resp.text = "Bad Gateway: upstream collector down"

    with patch("requests.Session.post", return_value=mock_resp):
        exp = claude_code_tracer.ErrorReportingExporter(config=config, session_id=session_id)
        res = exp.export([])
        assert res == SpanExportResult.FAILURE

    captured = capsys.readouterr()
    assert (
        "ERROR: OpenTelemetry export failed (collector server error HTTP 502): endpoint https://error-collector.example.com/v1/traces, response: Bad Gateway: upstream collector down"
        in captured.err
    )


def test_export_timeout_bounding():
    """AC-3.3: Exporter enforces timeout bounded <= 2.0s per request."""
    config = {"endpoint": "https://collector.example.com"}

    with patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "OK"
        exp = claude_code_tracer.ErrorReportingExporter(config=config, session_id="sess-to-test")
        exp.export([])
        assert mock_post.called
        kwargs = mock_post.call_args[1]
        assert "timeout" in kwargs
        assert kwargs["timeout"] <= 2.0


# ==============================================================================
# 4. Premise-Check Verdict Tracing Policy (Required Fail-Closed)
# ==============================================================================


def test_verdict_tracing_required_fails_closed_on_unconfigured(monkeypatch, capsys):
    """AC-4.2: When unconfigured, recording verdict raises RuntimeError and leaves gate armed."""
    session_id = "sess-verdict-req"
    claim_id = "claim-test-01"

    premise_check_gate.arm(
        session_id,
        claim_id=claim_id,
        judged_text="Sample judged text",
        judged_ref=claim_id,
    )
    assert premise_check_gate.is_armed(session_id)

    reason = (
        f"Judged: {claim_id}; asks tg-1\n"
        "Valid: (2) fails #missing -- condition not met\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (2)\n"
        "Sufficient: (2) material\n"
        "Waived: none\n"
        "Relay: none"
    )

    with pytest.raises(RuntimeError) as exc:
        premise_check_verdict.record_verdict(
            session_id=session_id,
            claim_id=claim_id,
            verdict="FAIL",
            reason=reason,
        )

    assert "tracing is not configured" in str(exc.value)
    # Gate remains armed!
    assert premise_check_gate.is_armed(session_id)

    captured = capsys.readouterr()
    assert "ERROR: Premise-check verdict cannot be recorded" in captured.err
    assert "Gate remains armed" in captured.err


def test_verdict_tracing_export_failure_fails_closed(monkeypatch, capsys):
    """AC-4.2: When span export fails, recording verdict raises RuntimeError and leaves gate armed."""
    session_id = "sess-verdict-fail"
    claim_id = "claim-test-02"

    premise_check_gate.arm(
        session_id,
        claim_id=claim_id,
        judged_text="Sample judged text",
        judged_ref=claim_id,
    )
    assert premise_check_gate.is_armed(session_id)

    reason = (
        f"Judged: {claim_id}; asks tg-1\n"
        "Valid: (2) fails #missing -- condition not met\n"
        f"Supported: weakest {_ANY_BASIS} -- (1)\n"
        "Answered: tg-1 ← (2)\n"
        "Sufficient: (2) material\n"
        "Waived: none\n"
        "Relay: none"
    )

    with (
        patch("claude_code_tracer._build_and_export_spans", return_value=False),
        patch(
            "claude_code_tracer.discover_config",
            return_value={"endpoint": "https://collector.example.com"},
        ),
    ):
        with pytest.raises(RuntimeError) as exc:
            premise_check_verdict.record_verdict(
                session_id=session_id,
                claim_id=claim_id,
                verdict="FAIL",
                reason=reason,
            )

    assert "OTel span export failed" in str(exc.value)
    assert premise_check_gate.is_armed(session_id)

    captured = capsys.readouterr()
    assert (
        "ERROR: Premise-check verdict cannot be recorded: OpenTelemetry span export was not acknowledged"
        in captured.err
    )
    assert "Gate remains armed" in captured.err
