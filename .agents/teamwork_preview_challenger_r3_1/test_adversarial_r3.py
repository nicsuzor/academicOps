#!/usr/bin/env python3
"""Adversarial stress-test suite for Milestone R3 implementation."""

import os
import sys
import tempfile
import json
import shutil
import pytest
from pathlib import Path

# Add project roots to sys.path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "lib" / "polecat"))
sys.path.insert(0, str(repo_root / "lib" / "hooks"))
sys.path.insert(0, str(repo_root / "plugins" / "rbg" / "hooks"))

from env_contract import format_otel_resource_attributes
import evaluator_otel_trace
import dispatch
from dispatch import HookContext


# =====================================================================
# Challenge Area 1: format_otel_resource_attributes()
# =====================================================================

def test_format_otel_duplicate_keys():
    """Test duplicate keys in existing OTEL_RESOURCE_ATTRIBUTES string."""
    existing = "polecat.session_id=old_s1,polecat.session_id=old_s2,env=prod"
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="new_s",
        project="proj1",
        task_id="task1"
    )
    print(f"Duplicate keys result: {res!r}")
    count = res.count("polecat.session_id=")
    assert count == 1, f"Expected polecat.session_id to appear once, got {count}: {res}"

def test_format_otel_special_characters():
    """Test special characters, commas, equals, quotes, and whitespace in inputs."""
    existing = "  key1 = val1 , key2 = val2=with=equals , key_empty= "
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="sess,ion=123",
        project="proj key=val",
        task_id="task\nline2"
    )
    print(f"Special characters result: {res!r}")
    assert "polecat.session_id=sess,ion=123" in res or "polecat.session_id=" in res
    assert "key1=val1" in res
    assert "key2=val2=with=equals" in res

def test_format_otel_malformed_and_empty():
    """Test malformed, empty, and non-string inputs."""
    assert format_otel_resource_attributes(existing=None) == ""
    assert format_otel_resource_attributes(existing="") == ""

    # Malformed empty pair input ", ,, = ,="
    res_malformed = format_otel_resource_attributes(existing=", ,, = ,=")
    print(f"Malformed input result: {res_malformed!r}")
    assert res_malformed == "", f"Expected empty string for malformed empty pairs, got {res_malformed!r}"

    # Optional fields empty strings vs None
    res_empty_str = format_otel_resource_attributes(session_id="", project="", task_id="")
    assert res_empty_str == ""

    # Numeric inputs
    res_num = format_otel_resource_attributes(session_id=12345, task_id=67890)
    assert "polecat.session_id=12345" in res_num
    assert "polecat.task_id=67890" in res_num


# =====================================================================
# Challenge Area 2: Tool Plumbing Errors & OTEL Trace Plumbing Error Handling
# =====================================================================

def test_tool_plumbing_error_detection():
    """Test detect_tool_plumbing_error under various edge cases."""
    # 1. Standard raw error_type
    ctx1 = HookContext(client="claude", event="PreToolUse", tool="unknown_tool", raw={"error_type": "unknown_tool", "error_message": "No such tool"})
    err1 = evaluator_otel_trace.detect_tool_plumbing_error(ctx1)
    assert err1 == ("unknown_tool", "No such tool")

    # 2. Tool name is missing_mcp
    ctx2 = HookContext(client="claude", event="PreToolUse", tool="missing_mcp", raw={})
    err2 = evaluator_otel_trace.detect_tool_plumbing_error(ctx2)
    assert err2 == ("missing_mcp", "missing_mcp")

    # 3. Tool error string contains 'unknown tool'
    ctx3 = HookContext(client="claude", event="PreToolUse", tool="some_tool", raw={"tool_error": "Error: unknown tool 'foo'"})
    err3 = evaluator_otel_trace.detect_tool_plumbing_error(ctx3)
    assert err3 == ("unknown_tool", "Error: unknown tool 'foo'")

    # 4. Non-plumbing error
    ctx4 = HookContext(client="claude", event="PreToolUse", tool="Bash", raw={"error": "Command failed with code 1"})
    err4 = evaluator_otel_trace.detect_tool_plumbing_error(ctx4)
    assert err4 is None

def test_post_tool_batch_plumbing_error_detection():
    """Test detect_tool_plumbing_error when error is in tool_calls array (PostToolBatch)."""
    ctx_batch = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=(
            {"tool_name": "unknown_tool", "error": "Tool unknown_tool not found"},
            {"tool_name": "Bash", "command": "ls"}
        ),
        raw={"tool_calls": [{"tool_name": "unknown_tool", "error": "Tool unknown_tool not found"}]}
    )
    err = evaluator_otel_trace.detect_tool_plumbing_error(ctx_batch)
    print(f"PostToolBatch plumbing error detection result: {err!r}")
    assert err is not None, "detect_tool_plumbing_error failed to detect unknown_tool in PostToolBatch tool_calls!"

def test_otel_trace_invalid_path(monkeypatch, tmp_path):
    """Test behavior when COPE_EVALUATOR_OTEL_TRACE_PATH is an uncreatable/invalid path."""
    invalid_path = str(tmp_path / "nonexistent_dir_file" / "sub" / "trace.json")
    (tmp_path / "nonexistent_dir_file").touch()

    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", invalid_path)

    ctx = HookContext(client="claude", event="PreToolUse", tool="unknown_tool", session_id="s123", raw={"error_type": "unknown_tool", "error_message": "Bad tool"})

    try:
        dispatch._instrument_otel_events(ctx)
        print("Invalid path test passed fail-open")
    except Exception as e:
        pytest.fail(f"_instrument_otel_events raised exception on invalid trace path: {e}")

def test_otel_trace_readonly_path(monkeypatch, tmp_path):
    """Test behavior when COPE_EVALUATOR_OTEL_TRACE_PATH parent directory is read-only."""
    ro_dir = tmp_path / "ro_dir"
    ro_dir.mkdir()
    ro_file = ro_dir / "trace.json"

    os.chmod(ro_dir, 0o555)

    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(ro_file))

    ctx = HookContext(client="claude", event="PreToolUse", tool="unknown_tool", session_id="s123", raw={"error_type": "unknown_tool"})

    try:
        dispatch._instrument_otel_events(ctx)
        print("Read-only path test completed without crash")
    except Exception as e:
        pytest.fail(f"_instrument_otel_events raised exception on read-only trace path: {e}")
    finally:
        os.chmod(ro_dir, 0o755)


# =====================================================================
# Challenge Area 3: SendMessage Linkage & SubagentStop Unsent Output
# =====================================================================

def test_send_message_missing_and_corrupted_traceparent(monkeypatch, tmp_path):
    """Test record_send_message with missing and corrupted TRACEPARENT."""
    trace_path = tmp_path / "trace.json"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))

    # 1. Missing TRACEPARENT
    monkeypatch.delenv("TRACEPARENT", raising=False)
    ctx1 = HookContext(client="claude", event="PreToolUse", tool="SendMessage", session_id="sess_parent", raw={"tool_input": {"recipient": "subagent_1"}})
    tp1 = evaluator_otel_trace.record_send_message(ctx1)
    assert tp1 is not None
    assert tp1.startswith("00-")

    # 2. Corrupted TRACEPARENT strings
    corrupted_inputs = [
        "invalid-traceparent",
        "00-short-span-01",
        "00-00000000000000000000000000000000-0000000000000000-00",
        "99-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "not-even-hex-ffffffffffffffffffffffffffffffffffff",
    ]
    for bad_tp in corrupted_inputs:
        monkeypatch.setenv("TRACEPARENT", bad_tp)
        tp_res = evaluator_otel_trace.record_send_message(ctx1)
        assert tp_res is not None
        assert tp_res.startswith("00-")
        print(f"Corrupted TRACEPARENT {bad_tp!r} degraded safely to new traceparent: {tp_res}")

def test_send_message_nested_subagent_linkage(monkeypatch, tmp_path):
    """Test parent/target span linkage across nested subagents."""
    trace_path = tmp_path / "trace.json"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))

    # Level 1: Root agent sends to Subagent A
    monkeypatch.delenv("TRACEPARENT", raising=False)
    ctx_root = HookContext(client="claude", event="PreToolUse", tool="SendMessage", session_id="root_sess", raw={"tool_input": {"recipient": "subagent_A"}})
    tp_root_to_A = evaluator_otel_trace.record_send_message(ctx_root)
    assert tp_root_to_A is not None

    root_trace_id = tp_root_to_A.split("-")[1]

    # Level 2: Subagent A runs with TRACEPARENT=tp_root_to_A and sends to Subagent B
    monkeypatch.setenv("TRACEPARENT", tp_root_to_A)
    ctx_A = HookContext(client="claude", event="PreToolUse", tool="SendMessage", session_id="sub_A_sess", raw={"tool_input": {"recipient": "subagent_B"}})
    tp_A_to_B = evaluator_otel_trace.record_send_message(ctx_A)
    assert tp_A_to_B is not None

    sub_A_trace_id = tp_A_to_B.split("-")[1]

    print(f"Root trace ID: {root_trace_id}, Subagent A trace ID: {sub_A_trace_id}")
    assert root_trace_id == sub_A_trace_id, "Nested subagent did not inherit parent trace ID!"

def test_subagent_stop_large_unsent_output(monkeypatch, tmp_path):
    """Test SubagentStop with a very large unsent output string."""
    trace_path = tmp_path / "trace.json"
    monkeypatch.setenv("COPE_EVALUATOR_OTEL_TRACE_PATH", str(trace_path))

    large_output = "X" * (5 * 1024 * 1024)
    ctx = HookContext(
        client="claude",
        event="SubagentStop",
        session_id="subagent_large",
        raw={"unsent_output": large_output}
    )

    try:
        evaluator_otel_trace.record_subagent_stop(ctx)
        assert trace_path.exists()
        size = trace_path.stat().st_size
        print(f"SubagentStop large unsent output trace file size: {size} bytes")
        assert size > 5 * 1024 * 1024, "Trace file should contain the large unsent output"
    except Exception as e:
        pytest.fail(f"record_subagent_stop failed on large unsent output: {e}")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
