"""_build_and_export_spans reports whether the OTLP export was acknowledged.

The OTel SDK's SimpleSpanProcessor discards the exporter's return value and
swallows its exceptions, so span.end() and provider.shutdown() return normally
when an export fails. These tests run the real SDK with a stand-in exporter to
check that the outcome still reaches the caller.
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

import claude_code_tracer


class _FakeExporter(SpanExporter):
    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.calls = 0

    def export(self, spans):
        self.calls += 1
        if self.outcome == "raise":
            raise ConnectionError("collector unreachable")
        if self.outcome == "failure":
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


def _records(n: int = 1) -> list[dict]:
    return [
        {
            "name": f"span-{i}",
            "start_ns": 1_000 + i,
            "end_ns": 2_000 + i,
            "trace_id_hex": "0123456789abcdef0123456789abcdef",
            "span_id_hex": f"{i + 1:016x}",
            "attributes": {},
        }
        for i in range(n)
    ]


def _export(exporters: list[_FakeExporter | None], n: int = 1) -> bool:
    config = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}
    with patch.object(claude_code_tracer, "_create_exporter", side_effect=exporters):
        return claude_code_tracer._build_and_export_spans(
            config=config,
            session_id="sess",
            username="u",
            span_records=_records(n),
            agent_name="a",
            cwd="/tmp",
        )


def test_success_is_reported():
    exp = _FakeExporter("success")
    assert _export([exp]) is True
    assert exp.calls == 1


def test_failure_result_is_reported():
    exp = _FakeExporter("failure")
    assert _export([exp]) is False
    assert exp.calls == 1


def test_exporter_exception_is_reported_not_swallowed_into_success():
    exp = _FakeExporter("raise")
    assert _export([exp]) is False
    assert exp.calls == 1


def test_one_failed_record_fails_the_batch():
    assert _export([_FakeExporter("success"), _FakeExporter("failure")], n=2) is False


def test_missing_exporter_is_reported():
    assert _export([None]) is False


@pytest.mark.parametrize("outcome", ["failure", "raise"])
def test_failed_export_flows_through_to_span_emitted(outcome, tmp_path, monkeypatch):
    import premise_check_gate as pcg
    import premise_check_verdict as pcv

    monkeypatch.setenv("AOPS_PREMISE_GATE_DIR", str(tmp_path / "gate"))
    monkeypatch.setenv("AOPS_SESSION_ID", "sess-flow")
    pcg.arm("sess-flow", claim_id="c")
    config = {"endpoint": "http://collector.invalid:4318", "project_name": "test"}

    with (
        patch.object(claude_code_tracer, "discover_config", return_value=config),
        patch.object(claude_code_tracer, "_load_state", return_value={}),
        patch.object(claude_code_tracer, "_create_exporter", return_value=_FakeExporter(outcome)),
    ):
        result = pcv.record_verdict(
            session_id="sess-flow", claim_id="c", answers=["v"], tracer_mod=claude_code_tracer
        )

    assert result["span_emitted"] is False
    assert result["span_error"] is None
