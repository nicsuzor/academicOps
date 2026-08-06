#!/usr/bin/env python3
"""Expanded adversarial stress-test suite for Milestone R3 Iteration 2."""

import sys
from pathlib import Path
import pytest

# Add project roots to sys.path
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "lib" / "polecat"))
sys.path.insert(0, str(repo_root / "lib" / "hooks"))
sys.path.insert(0, str(repo_root / "plugins" / "rbg" / "hooks"))

from env_contract import format_otel_resource_attributes
import evaluator_otel_trace
from dispatch import HookContext


# =====================================================================
# Test 1: format_otel_resource_attributes() Edge Cases
# =====================================================================

def test_format_otel_multiple_duplicate_keys():
    """Test format_otel_resource_attributes with many duplicate keys in existing."""
    existing = "keyA=1,keyB=2,keyA=3,keyC=4,keyA=5,keyB=6,polecat.session_id=s_old1,polecat.session_id=s_old2"
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="s_new",
        project="proj_x",
        task_id="task_y"
    )
    print(f"Result multiple duplicates: {res!r}")
    
    # Verify no key is repeated in the output
    tokens = res.split(",")
    keys = [t.split("=", 1)[0] for t in tokens if t]
    assert len(keys) == len(set(keys)), f"Duplicate keys found in result: {keys}"
    
    # Verify updated values
    assert "polecat.session_id=s_new" in tokens
    assert "polecat.project=proj_x" in tokens
    assert "polecat.task_id=task_y" in tokens
    assert "keyA=1" in tokens  # first occurrence of keyA preserved
    assert "keyB=2" in tokens  # first occurrence of keyB preserved
    assert "keyC=4" in tokens


def test_format_otel_whitespace_variations():
    """Test format_otel_resource_attributes with whitespace, tabs, and newlines."""
    existing = " \t key1 = val1 \n, \r key2 = val2 with spaces \t,  key3=val3  "
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="  sess_ws  ",
        project="proj_ws",
    )
    print(f"Result whitespace variations: {res!r}")
    
    tokens = res.split(",")
    assert "key1=val1" in tokens
    assert "key2=val2 with spaces" in tokens
    assert "key3=val3" in tokens
    # session_id passed was "  sess_ws  ", which converts to string as-is or stripped
    assert "polecat.session_id=  sess_ws  " in tokens or "polecat.session_id=sess_ws" in tokens
    assert "polecat.project=proj_ws" in tokens


def test_format_otel_quotes():
    """Test format_otel_resource_attributes with quoted keys and values."""
    existing = 'key1="val1", key2=\'val2\', "key3"="val3", key4=\'"val4"\''
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="sess_quotes",
    )
    print(f"Result quotes: {res!r}")
    
    tokens = res.split(",")
    assert 'key1="val1"' in tokens
    assert "key2='val2'" in tokens
    assert '"key3"="val3"' in tokens
    assert 'key4=\'"val4"\'' in tokens
    assert "polecat.session_id=sess_quotes" in tokens


def test_format_otel_colons_and_urls():
    """Test format_otel_resource_attributes with colons and URLs in keys and values."""
    existing = "endpoint=http://localhost:4317,arn=arn:aws:iam::123456789012:role/service,scope=service:module:sub"
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="sess:123",
        project="proj:abc",
    )
    print(f"Result colons: {res!r}")
    
    tokens = res.split(",")
    assert "endpoint=http://localhost:4317" in tokens
    assert "arn=arn:aws:iam::123456789012:role/service" in tokens
    assert "scope=service:module:sub" in tokens
    assert "polecat.session_id=sess:123" in tokens
    assert "polecat.project=proj:abc" in tokens


def test_format_otel_underscores():
    """Test format_otel_resource_attributes with single and multiple underscores."""
    existing = "my_custom_service_name=app_v1_0,polecat_extra_attr=foo_bar_baz"
    res = format_otel_resource_attributes(
        existing=existing,
        session_id="sess_1_2_3",
        project="proj_a_b_c",
        task_id="task_x_y_z"
    )
    print(f"Result underscores: {res!r}")
    
    tokens = res.split(",")
    assert "my_custom_service_name=app_v1_0" in tokens
    assert "polecat_extra_attr=foo_bar_baz" in tokens
    assert "polecat.session_id=sess_1_2_3" in tokens
    assert "polecat.project=proj_a_b_c" in tokens
    assert "polecat.task_id=task_x_y_z" in tokens


# =====================================================================
# Test 2: detect_tool_plumbing_error() on PostToolBatch Edge Cases
# =====================================================================

def test_detect_tool_plumbing_error_post_tool_batch_complex():
    """Test PostToolBatch with mixed valid tools, unknown_tool, missing_mcp, and malformed calls."""
    # 1. Complex tool_calls with valid tools first, then unknown_tool in middle
    ctx1 = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=(
            {"tool_name": "ReadFile", "path": "/foo.txt"},
            {"tool_name": "Bash", "command": "echo hi"},
            {"tool_name": "unknown_tool", "error": "Tool unknown_tool not found"},
            {"tool_name": "WriteFile", "path": "/bar.txt"}
        ),
        raw={}
    )
    err1 = evaluator_otel_trace.detect_tool_plumbing_error(ctx1)
    assert err1 is not None
    assert err1[0] == "unknown_tool"

    # 2. Complex tool_calls with valid tools and missing_mcp error_type
    ctx2 = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=[
            {"tool_name": "Bash", "command": "ls"},
            {"tool_name": "mcp_custom_tool", "error_type": "missing_mcp", "error_message": "MCP server disconnected"}
        ],
        raw={}
    )
    err2 = evaluator_otel_trace.detect_tool_plumbing_error(ctx2)
    assert err2 == ("missing_mcp", "MCP server disconnected")

    # 3. PostToolBatch with non-dict elements inside tool_calls (robustness check)
    ctx3 = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=[
            "not a dict",
            None,
            12345,
            {"tool_name": "Bash", "error": "Command failed exit status 1"},
            {"tool_name": "some_missing_tool", "tool_error": "Error: missing mcp server for tool"}
        ],
        raw={}
    )
    err3 = evaluator_otel_trace.detect_tool_plumbing_error(ctx3)
    assert err3 is not None
    assert err3[0] == "missing_mcp"

    # 4. PostToolBatch with only valid tool errors (e.g. file not found, non-zero exit code)
    ctx4 = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=[
            {"tool_name": "ReadFile", "error": "FileNotFoundError: /missing.txt"},
            {"tool_name": "Bash", "error": "Command 'false' returned non-zero exit status 1"}
        ],
        raw={}
    )
    err4 = evaluator_otel_trace.detect_tool_plumbing_error(ctx4)
    assert err4 is None

    # 5. PostToolBatch where tool_calls is in raw["tool_calls"] instead of ctx.tool_calls
    ctx5 = HookContext(
        client="claude",
        event="PostToolBatch",
        tool="",
        tool_calls=None,
        raw={
            "tool_calls": [
                {"tool": "unknown_tool", "error_code": "unknown_tool", "error": "Unknown tool invocation"}
            ]
        }
    )
    err5 = evaluator_otel_trace.detect_tool_plumbing_error(ctx5)
    assert err5 == ("unknown_tool", "Unknown tool invocation")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
