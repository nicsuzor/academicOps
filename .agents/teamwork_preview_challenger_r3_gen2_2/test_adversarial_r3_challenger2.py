import json
import os
import sys
import tempfile
from pathlib import Path
import pytest

# Add project roots to sys.path
workspace_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(workspace_root / "lib" / "polecat"))
sys.path.insert(0, str(workspace_root / "lib" / "hooks"))
sys.path.insert(0, str(workspace_root / "plugins" / "rbg" / "hooks"))

from env_contract import format_otel_resource_attributes, CONTAINER_SET_ENV
import evaluator_otel_trace as otel_trace
from dispatch import HookContext


def test_container_set_env_agent_teams():
    """R2/R3: Ensure CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS is set to '1' by default."""
    assert CONTAINER_SET_ENV.get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"


def test_format_otel_resource_attributes_adversarial():
    """R3: Resource attribute formatting robust deduplication, empty key filtering, and parameter merging."""
    # Test 1: Duplicate keys and stray commas
    existing = ",,polecat.session_id=old_sess,flag_only,polecat.session_id=older_sess,foo=bar,,"
    result = format_otel_resource_attributes(
        existing=existing,
        session_id="new_sess",
        project="my_project",
        task_id="task_123"
    )
    # Must deduplicate polecat.session_id, replace value with new_sess, keep flag_only and foo=bar
    assert result == "polecat.session_id=new_sess,flag_only,foo=bar,polecat.project=my_project,polecat.task_id=task_123"

    # Test 2: Empty/whitespace session_id / project / task_id should not produce blank attributes or stray commas
    result_empty_updates = format_otel_resource_attributes(
        existing="env=prod,service=test",
        session_id="   ",
        project=None,
        task_id=""
    )
    assert result_empty_updates == "env=prod,service=test"

    # Test 3: Special characters in value (e.g. key=val=with=equals)
    result_equals = format_otel_resource_attributes(
        existing="custom.attr=a=b=c",
        session_id="sess1"
    )
    assert "custom.attr=a=b=c" in result_equals
    assert "polecat.session_id=sess1" in result_equals


def test_detect_and_record_tool_plumbing_error_single_and_batch(tmp_path):
    """R3: Verify tool plumbing error detection (unknown_tool, missing_mcp) in single and PostToolBatch events,
    and verify OTEL span exception recording & StatusCode.ERROR."""
    otel_file = tmp_path / "otel_plumbing_test.json"
    config = otel_trace.Config(path=otel_file)

    # 1. Single unknown_tool error
    ctx_single = HookContext(
        client="claude",
        event="PreToolUse",
        tool="unknown_tool",
        session_id="sess_plumbing_1",
        raw={"error_type": "unknown_tool", "error_message": "No such tool registered"}
    )
    err = otel_trace.detect_tool_plumbing_error(ctx_single)
    assert err == ("unknown_tool", "No such tool registered")

    otel_trace.record_tool_plumbing_error(ctx_single, error_type=err[0], error_message=err[1], config=config)

    # 2. PostToolBatch with missing_mcp inside tool_calls
    ctx_batch = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        session_id="sess_plumbing_2",
        tool_calls=(
            {"tool_name": "Read", "status": "success"},
            {"tool_name": "mcp_missing_tool", "error_type": "missing_mcp", "error_message": "MCP server disconnected"},
        ),
        raw={"tool_calls": [
            {"tool_name": "Read", "status": "success"},
            {"tool_name": "mcp_missing_tool", "error_type": "missing_mcp", "error_message": "MCP server disconnected"},
        ]}
    )
    err_batch = otel_trace.detect_tool_plumbing_error(ctx_batch)
    assert err_batch == ("missing_mcp", "MCP server disconnected")

    otel_trace.record_tool_plumbing_error(ctx_batch, error_type=err_batch[0], error_message=err_batch[1], config=config)

    # Inspect OTLP JSON file output
    content = otel_file.read_text()
    assert content, "OTEL log file should not be empty"

    lines = [json.loads(line) for line in content.strip().splitlines() if line.strip()]
    assert len(lines) == 2

    # Verify first span (single unknown_tool)
    span1 = lines[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span1["name"] == "tool.error.unknown_tool"
    # Status code 2 is Status.ERROR in OTLP JSON
    assert span1["status"]["code"] == 2
    assert span1["status"]["message"] == "No such tool registered"
    # Verify exception event recorded
    events1 = span1.get("events", [])
    assert len(events1) > 0
    assert events1[0]["name"] == "exception"
    evt_attrs1 = {a["key"]: a["value"].get("stringValue") for a in events1[0]["attributes"]}
    assert evt_attrs1["exception.message"] == "No such tool registered"

    # Verify second span (batch missing_mcp)
    span2 = lines[1]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span2["name"] == "tool.error.missing_mcp"
    assert span2["status"]["code"] == 2
    assert span2["status"]["message"] == "MCP server disconnected"


def test_detect_and_record_agent_idle_timeout(tmp_path):
    """R3: Verify agent idle/timeout detection and OTEL event/status recording."""
    otel_file = tmp_path / "otel_agent_idle_timeout.json"
    config = otel_trace.Config(path=otel_file)

    # Timeout case
    ctx_timeout = HookContext(
        client="claude",
        event="Stop",
        session_id="sess_timeout",
        raw={"stop_reason": "timeout_exceeded", "timeout": True}
    )
    assert otel_trace.detect_agent_idle_timeout(ctx_timeout) == "timeout"
    otel_trace.record_agent_idle_timeout(ctx_timeout, event_type="timeout", config=config)

    # Idle case
    ctx_idle = HookContext(
        client="claude",
        event="SubagentStop",
        session_id="sess_idle",
        raw={"status": "idle"}
    )
    assert otel_trace.detect_agent_idle_timeout(ctx_idle) == "idle"
    otel_trace.record_agent_idle_timeout(ctx_idle, event_type="idle", config=config)

    lines = [json.loads(line) for line in otel_file.read_text().strip().splitlines() if line.strip()]
    assert len(lines) == 2

    # Timeout span -> STATUS_CODE_ERROR (code 2) + exception
    span_timeout = lines[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span_timeout["name"] == "agent.timeout"
    assert span_timeout["status"]["code"] == 2
    assert "events" in span_timeout
    assert span_timeout["events"][0]["name"] == "exception"

    # Idle span -> STATUS_CODE_OK (code 1 or no error status)
    span_idle = lines[1]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span_idle["name"] == "agent.idle"
    assert span_idle["status"].get("code", 1) == 1


def test_record_send_message_span_linkage_and_traceparent(tmp_path, monkeypatch):
    """R3: Verify SendMessage span linkage, parent/target agent attributes, and W3C traceparent propagation."""
    otel_file = tmp_path / "otel_send_message.json"
    config = otel_trace.Config(path=otel_file)

    # Set parent TRACEPARENT in env
    fake_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    fake_span_id = "00f067aa0ba902b7"
    fake_tp = f"00-{fake_trace_id}-{fake_span_id}-01"
    monkeypatch.setenv("TRACEPARENT", fake_tp)

    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="SendMessage",
        session_id="parent_agent_main",
        raw={"tool_input": {"recipient": "worker_subagent_1"}}
    )

    propagated_tp = otel_trace.record_send_message(ctx, config=config)
    assert propagated_tp is not None
    assert propagated_tp.startswith(f"00-{fake_trace_id}-")
    assert len(propagated_tp) == 55

    lines = [json.loads(line) for line in otel_file.read_text().strip().splitlines() if line.strip()]
    span = lines[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]

    assert span["name"] == "agent.send_message"
    assert span["traceId"] == fake_trace_id

    attrs = {a["key"]: a["value"].get("stringValue") for a in span["attributes"]}
    assert attrs["parent_agent"] == "parent_agent_main"
    assert attrs["target_agent"] == "worker_subagent_1"
    assert attrs["propagated_traceparent"] == propagated_tp


def test_record_subagent_stop_unsent_output(tmp_path):
    """R3: Verify SubagentStop unsent output inspection, warning attribute, exception event, and ERROR status."""
    otel_file = tmp_path / "otel_subagent_stop.json"
    config = otel_trace.Config(path=otel_file)

    # Case A: SubagentStop with unsent output
    ctx_unsent = HookContext(
        client="claude",
        event="SubagentStop",
        session_id="subagent_42",
        raw={"unsent_output": "Critical unreturned task completion report"}
    )

    otel_trace.record_subagent_stop(ctx_unsent, config=config)

    # Case B: SubagentStop without unsent output
    ctx_clean = HookContext(
        client="claude",
        event="SubagentStop",
        session_id="subagent_43",
        raw={"unsent_output": None}
    )
    otel_trace.record_subagent_stop(ctx_clean, config=config)

    lines = [json.loads(line) for line in otel_file.read_text().strip().splitlines() if line.strip()]
    assert len(lines) == 2

    # Unsent output span -> StatusCode.ERROR, exception event, warning attr
    span_unsent = lines[0]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span_unsent["name"] == "agent.subagent_stop"
    assert span_unsent["status"]["code"] == 2
    assert span_unsent["status"]["message"] == "Subagent stopped with unsent output"

    attrs_unsent = {a["key"]: a["value"].get("stringValue") for a in span_unsent["attributes"]}
    assert attrs_unsent["warning"] == "unsent_output_detected"
    assert attrs_unsent["unsent_content"] == "Critical unreturned task completion report"

    events_unsent = span_unsent.get("events", [])
    assert len(events_unsent) > 0
    assert events_unsent[0]["name"] == "exception"

    # Clean span -> StatusCode.OK
    span_clean = lines[1]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
    assert span_clean["status"].get("code", 1) == 1
