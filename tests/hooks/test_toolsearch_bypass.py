#!/usr/bin/env python3
"""Regression test for ToolSearch bypass in gates."""

import sys
from pathlib import Path

# Add aops-core to path for hook imports
AOPS_CORE = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE))

import os

from hooks.router import HookRouter
from hooks.schemas import HookContext
from lib.gate_model import GateVerdict
from lib.gates.registry import GateRegistry
from lib.session_state import SessionState


def test_toolsearch_bypass():
    GateRegistry.initialize()
    router = HookRouter()
    state = SessionState.create("test-bypass")

    # 1. Infrastructure tool search (select:*) should be ALLOWED
    ctx_infra = HookContext(
        session_id="test-bypass",
        hook_event="PreToolUse",
        tool_name="ToolSearch",
        tool_input={"query": "select:Read"},
    )
    result_infra = router._dispatch_gates(ctx_infra, state)
    assert result_infra is None or result_infra.verdict == GateVerdict.ALLOW

    # 2. Keyword discovery ToolSearch should still be WARNED/BLOCKED (unless mode is off)
    ctx_discovery = HookContext(
        session_id="test-bypass",
        hook_event="PreToolUse",
        tool_name="ToolSearch",
        tool_input={"query": "how to edit files"},
    )
    result_discovery = router._dispatch_gates(ctx_discovery, state)

    hydration_mode = os.environ.get("HYDRATION_GATE_MODE", "off")
    if hydration_mode == "off":
        assert result_discovery is None
    else:
        assert result_discovery is not None
        assert result_discovery.verdict in (GateVerdict.WARN, GateVerdict.DENY)

    # 3. Regular read-only tool should still be WARNED/BLOCKED (unless mode is off)
    ctx_read = HookContext(
        session_id="test-bypass",
        hook_event="PreToolUse",
        tool_name="Read",
        tool_input={"file_path": "/some/file.py"},
    )
    result_read = router._dispatch_gates(ctx_read, state)
    if hydration_mode == "off":
        assert result_read is None
    else:
        assert result_read is not None
        assert result_read.verdict in (GateVerdict.WARN, GateVerdict.DENY)

if __name__ == "__main__":
    test_toolsearch_bypass()
    print("Regression test PASSED")
