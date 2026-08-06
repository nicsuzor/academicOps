#!/usr/bin/env python3
"""Adversarial stress-test script for Milestone R3 (OTEL Telemetry & Error Instrumentation)."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root and rbg hooks to sys.path
repo_root = Path("/workspace")
rbg_hooks = repo_root / "plugins" / "rbg" / "hooks"
lib_hooks = repo_root / "lib" / "hooks"
lib_polecat = repo_root / "lib" / "polecat"

for p in (repo_root, rbg_hooks, lib_hooks, lib_polecat):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from env_contract import format_otel_resource_attributes
from dispatch import HookContext
import evaluator_otel_trace


def test_format_otel_resource_attributes():
    print("--- Test 1: format_otel_resource_attributes edge cases ---")

    # Edge case 1.1: Basic merge
    res1 = format_otel_resource_attributes(
        existing=None, session_id="sess_123", project="proj_abc", task_id="task_456"
    )
    assert res1 == "polecat.session_id=sess_123,polecat.project=proj_abc,polecat.task_id=task_456", f"Failed 1.1: {res1}"

    # Edge case 1.2: Existing attributes without polecat prefix
    res2 = format_otel_resource_attributes(
        existing="env=prod,service.name=my-app", session_id="s1"
    )
    assert res2 == "env=prod,service.name=my-app,polecat.session_id=s1", f"Failed 1.2: {res2}"

    # Edge case 1.3: Override existing polecat attributes
    res3 = format_otel_resource_attributes(
        existing="polecat.session_id=old_s,foo=bar,polecat.project=old_p",
        session_id="new_s",
        project="new_p",
        task_id="t1",
    )
    assert res3 == "polecat.session_id=new_s,foo=bar,polecat.project=new_p,polecat.task_id=t1", f"Failed 1.3: {res3}"

    # Edge case 1.4: Whitespace and empty elements
    res4 = format_otel_resource_attributes(
        existing="  a=1 , , b=2  , ", session_id="s1"
    )
    assert res4 == "a=1,b=2,polecat.session_id=s1", f"Failed 1.4: {res4}"

    # Edge case 1.5: Valueless keys
    res5 = format_otel_resource_attributes(existing="standalone_key,key2=val2", session_id="s1")
    assert res5 == "standalone_key,key2=val2,polecat.session_id=s1", f"Failed 1.5: {res5}"

    # Edge case 1.6: None/Empty inputs
    res6 = format_otel_resource_attributes()
    assert res6 == "", f"Failed 1.6: {res6}"

    # Edge case 1.7: Numeric inputs
    res7 = format_otel_resource_attributes(session_id=12345, project=999, task_id=777)
    assert res7 == "polecat.session_id=12345,polecat.project=999,polecat.task_id=777", f"Failed 1.7: {res7}"

    print("PASS: format_otel_resource_attributes tests passed!\n")


def parse_otlp_spans(file_path: str):
    """Parse spans written by FileSpanExporter in OTLP JSON format."""
    spans = []
    if not os.path.exists(file_path):
        return spans
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            # OTLP JSON structure: resourceSpans -> scopeSpans -> spans
            for r_span in data.get("resourceSpans", []):
                for s_span in r_span.get("scopeSpans", []):
                    for span in s_span.get("spans", []):
                        spans.append(span)
    return spans


def test_tool_plumbing_errors():
    print("--- Test 2: Tool Plumbing Errors & Exception/Status Recording ---")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        config = evaluator_otel_trace.Config(path=Path(tmp_path))

        # Test 2.1: detect_tool_plumbing_error variants
        ctx1 = HookContext(client="claude", event="PreToolUse", tool="ReadFile", raw={"error_type": "unknown_tool", "error_message": "Unknown tool ReadFile"})
        err1 = evaluator_otel_trace.detect_tool_plumbing_error(ctx1)
        assert err1 == ("unknown_tool", "Unknown tool ReadFile"), f"Failed 2.1a: {err1}"

        ctx2 = HookContext(client="claude", event="PreToolUse", tool="unknown_tool", raw={"error": "Tool unknown_tool does not exist"})
        err2 = evaluator_otel_trace.detect_tool_plumbing_error(ctx2)
        assert err2 == ("unknown_tool", "Tool unknown_tool does not exist"), f"Failed 2.1b: {err2}"

        ctx3 = HookContext(client="claude", event="PreToolUse", tool="mcp_call", raw={"tool_error": "missing mcp server connection"})
        err3 = evaluator_otel_trace.detect_tool_plumbing_error(ctx3)
        assert err3 == ("missing_mcp", "missing mcp server connection"), f"Failed 2.1c: {err3}"

        # Test 2.2: record_tool_plumbing_error OTLP emission
        evaluator_otel_trace.record_tool_plumbing_error(
            ctx1, error_type=err1[0], error_message=err1[1], config=config
        )

        spans = parse_otlp_spans(tmp_path)
        assert len(spans) == 1, f"Expected 1 span, got {len(spans)}"
        span = spans[0]

        assert span["name"] == "tool.error.unknown_tool", f"Span name mismatch: {span['name']}"

        # Check StatusCode.ERROR (OTLP status code 2 = ERROR)
        status = span.get("status", {})
        code = status.get("code")
        assert code == 2 or code == "STATUS_CODE_ERROR" or status.get("description") == "Unknown tool ReadFile", f"Status ERROR check failed: {status}"

        # Check recorded exception event
        events = span.get("events", [])
        assert len(events) >= 1, f"Expected at least 1 event (exception), got {len(events)}"
        exc_event = events[0]
        assert exc_event.get("name") == "exception", f"Event name mismatch: {exc_event.get('name')}"

        print("PASS: Tool plumbing error tests passed!\n")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_subagent_stop_unsent_output():
    print("--- Test 3: SubagentStop Unsent Output Handling ---")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        config = evaluator_otel_trace.Config(path=Path(tmp_path))

        # Case 3.1: SubagentStop with unsent output
        ctx_unsent = HookContext(
            client="claude",
            event="SubagentStop",
            session_id="subagent_session_1",
            raw={"unsent_output": "Important analysis result that was not sent via SendMessage"}
        )

        evaluator_otel_trace.record_subagent_stop(ctx_unsent, config=config)

        spans = parse_otlp_spans(tmp_path)
        assert len(spans) == 1, f"Expected 1 span, got {len(spans)}"
        span = spans[0]

        assert span["name"] == "agent.subagent_stop"

        # Check Status code ERROR
        status = span.get("status", {})
        assert status.get("code") == 2 or status.get("description") == "Subagent stopped with unsent output", f"Status error mismatch: {status}"

        # Check warning attribute
        attrs = {attr["key"]: attr["value"].get("stringValue") or attr["value"].get("boolValue") for attr in span.get("attributes", [])}
        assert attrs.get("warning") == "unsent_output_detected", f"Warning attribute missing: {attrs}"
        assert attrs.get("has_unsent_output") is True, f"has_unsent_output attribute mismatch: {attrs}"
        assert attrs.get("unsent_content") == "Important analysis result that was not sent via SendMessage", f"unsent_content mismatch: {attrs}"

        # Check exception event recorded
        events = span.get("events", [])
        assert len(events) >= 1
        assert events[0].get("name") == "exception"

        # Case 3.2: SubagentStop without unsent output
        os.remove(tmp_path)
        ctx_clean = HookContext(client="claude", event="SubagentStop", session_id="subagent_session_2", raw={})
        evaluator_otel_trace.record_subagent_stop(ctx_clean, config=config)

        spans_clean = parse_otlp_spans(tmp_path)
        assert len(spans_clean) == 1
        span_c = spans_clean[0]
        status_c = span_c.get("status", {})
        assert status_c.get("code") in (0, 1, None, "STATUS_CODE_UNSET", "STATUS_CODE_OK")
        assert len(span_c.get("events", [])) == 0

        print("PASS: SubagentStop unsent output tests passed!\n")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_agent_idle_timeout():
    print("--- Test 4: Agent Idle and Timeout Instrumentation ---")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        config = evaluator_otel_trace.Config(path=Path(tmp_path))

        # Timeout event
        ctx_timeout = HookContext(client="claude", event="Stop", session_id="sess_t", raw={"reason": "timeout"})
        idle_type = evaluator_otel_trace.detect_agent_idle_timeout(ctx_timeout)
        assert idle_type == "timeout", f"Failed timeout detection: {idle_type}"

        evaluator_otel_trace.record_agent_idle_timeout(ctx_timeout, event_type=idle_type, config=config)

        spans = parse_otlp_spans(tmp_path)
        assert len(spans) == 1
        span_t = spans[0]
        assert span_t["name"] == "agent.timeout"
        status_t = span_t.get("status", {})
        assert status_t.get("code") == 2 or "timed out" in str(status_t.get("description", ""))
        assert len(span_t.get("events", [])) >= 1  # Exception recorded

        # Idle event
        os.remove(tmp_path)
        ctx_idle = HookContext(client="claude", event="Stop", session_id="sess_i", raw={"reason": "agent idle"})
        idle_type2 = evaluator_otel_trace.detect_agent_idle_timeout(ctx_idle)
        assert idle_type2 == "idle", f"Failed idle detection: {idle_type2}"

        evaluator_otel_trace.record_agent_idle_timeout(ctx_idle, event_type=idle_type2, config=config)

        spans_i = parse_otlp_spans(tmp_path)
        assert len(spans_i) == 1
        span_i = spans_i[0]
        assert span_i["name"] == "agent.idle"

        print("PASS: Agent idle/timeout tests passed!\n")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_send_message_linkage():
    print("--- Test 5: SendMessage Span Linkage & Traceparent Propagation ---")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        config = evaluator_otel_trace.Config(path=Path(tmp_path))

        parent_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        parent_span_id = "00f067aa0ba902b7"
        env_traceparent = f"00-{parent_trace_id}-{parent_span_id}-01"
        os.environ["TRACEPARENT"] = env_traceparent

        ctx_send = HookContext(
            client="claude",
            event="PreToolUse",
            tool="SendMessage",
            session_id="controller_agent_1",
            raw={"tool_input": {"recipient": "worker_agent_4", "content": "Start task"}}
        )

        propagated_tp = evaluator_otel_trace.record_send_message(ctx_send, config=config)
        assert propagated_tp is not None, "record_send_message returned None"
        assert propagated_tp.startswith(f"00-{parent_trace_id}-"), f"Propagated traceparent must retain trace_id! Got: {propagated_tp}"

        parts = propagated_tp.split("-")
        assert len(parts) == 4, f"Invalid W3C format: {propagated_tp}"
        assert parts[0] == "00"
        assert parts[1] == parent_trace_id
        assert parts[2] != parent_span_id  # New span ID generated
        assert parts[3] == "01"

        spans = parse_otlp_spans(tmp_path)
        assert len(spans) == 1
        span = spans[0]

        assert span["name"] == "agent.send_message"
        assert span.get("parentSpanId") == parent_span_id, f"Parent span ID mismatch: expected {parent_span_id}, got {span.get('parentSpanId')}"

        attrs = {attr["key"]: attr["value"].get("stringValue") for attr in span.get("attributes", [])}
        assert attrs.get("parent_agent") == "controller_agent_1", f"parent_agent attribute mismatch: {attrs}"
        assert attrs.get("target_agent") == "worker_agent_4", f"target_agent attribute mismatch: {attrs}"
        assert attrs.get("propagated_traceparent") == propagated_tp, f"propagated_traceparent attribute mismatch: {attrs}"

        print("PASS: SendMessage linkage & traceparent propagation tests passed!\n")
    finally:
        os.environ.pop("TRACEPARENT", None)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def main():
    test_format_otel_resource_attributes()
    test_tool_plumbing_errors()
    test_subagent_stop_unsent_output()
    test_agent_idle_timeout()
    test_send_message_linkage()
    print("ALL ADVERSARIAL TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
