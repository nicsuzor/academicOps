import json
import os
import uuid
import pytest
from pathlib import Path
from hooks.router import HookRouter
from lib.gate_model import GateVerdict

@pytest.mark.integration
def test_custodiet_threshold_in_process():
    """
    Verify custodiet threshold logic by calling the HookRouter object directly in-process.
    This eliminates all infrastructure issues (uv, CLAUDE_PLUGIN_ROOT, etc.)
    """
    aops_root = os.environ.get("AOPS")
    router = HookRouter()
    
    session_id = str(uuid.uuid4())
    # Registry path for sidechain detection
    registry_path = Path("/tmp/aops_session_registry.json")
    if registry_path.exists(): registry_path.unlink()
    
    # 1. Startup and Prompt (Register as main)
    payload_start = {"session_id": session_id, "hook_event_name": "SessionStart"}
    router.execute_hooks(router.normalize_input(payload_start))
    
    payload_ups = {"session_id": session_id, "hook_event_name": "UserPromptSubmit", "tool_input": {"prompt": "Do work"}}
    router.execute_hooks(router.normalize_input(payload_ups))
    
    # 1.5 Unblock Hydration
    payload_hyd = {
        "session_id": session_id, 
        "hook_event_name": "PreToolUse", 
        "tool_name": "Task", 
        "tool_input": {"subagent_type": "aops-core:prompt-hydrator"}
    }
    router.execute_hooks(router.normalize_input(payload_hyd))
    
    payload_hyd_post = {
        "session_id": session_id, 
        "hook_event_name": "PostToolUse", 
        "tool_name": "Task", 
        "tool_input": {"subagent_type": "aops-core:prompt-hydrator"}
    }
    router.execute_hooks(router.normalize_input(payload_hyd_post))
    
    # 2. Run 6 tools (Threshold is 7, Hydrator used 1)
    for i in range(6):
        payload_pre = {"session_id": session_id, "hook_event_name": "PreToolUse", "tool_name": "Bash"}
        res = router.execute_hooks(router.normalize_input(payload_pre))
        assert res.verdict == "allow"
        
        payload_post = {"session_id": session_id, "hook_event_name": "PostToolUse", "tool_name": "Bash"}
        router.execute_hooks(router.normalize_input(payload_post))
        
    # 3. 8th Tool (7th op since start) should be DENIED
    payload_deny = {"session_id": session_id, "hook_event_name": "PreToolUse", "tool_name": "Bash"}
    res = router.execute_hooks(router.normalize_input(payload_deny))
    assert res.verdict == "deny"
    assert "Compliance check required" in res.system_message

@pytest.mark.integration
def test_subagent_bypass_in_process():
    """
    Verify subagent bypass logic in-process.
    """
    router = HookRouter()
    main_session_id = str(uuid.uuid4())
    sub_session_id = str(uuid.uuid4())
    
    # 1. Startup Main Agent
    router.execute_hooks(router.normalize_input({"session_id": main_session_id, "hook_event_name": "SessionStart"}))
    router.execute_hooks(router.normalize_input({"session_id": main_session_id, "hook_event_name": "UserPromptSubmit", "tool_input": {"prompt": "Do work"}}))
    
    # Unblock hydration for main
    router.execute_hooks(router.normalize_input({
        "session_id": main_session_id, 
        "hook_event_name": "PreToolUse", 
        "tool_name": "Task", 
        "tool_input": {"subagent_type": "aops-core:prompt-hydrator"}
    }))
    router.execute_hooks(router.normalize_input({
        "session_id": main_session_id, 
        "hook_event_name": "PostToolUse", 
        "tool_name": "Task", 
        "tool_input": {"subagent_type": "aops-core:prompt-hydrator"}
    }))

    # 2. Hit Threshold for main
    for i in range(6):
        router.execute_hooks(router.normalize_input({"session_id": main_session_id, "hook_event_name": "PreToolUse", "tool_name": "Bash"}))
        router.execute_hooks(router.normalize_input({"session_id": main_session_id, "hook_event_name": "PostToolUse", "tool_name": "Bash"}))
        
    # 3. Main Agent is BLOCKED
    res = router.execute_hooks(router.normalize_input({"session_id": main_session_id, "hook_event_name": "PreToolUse", "tool_name": "Bash"}))
    assert res.verdict == "deny"
    
    # 4. SUBAGENT (different ID, not registered) is ALLOWED
    # It bypasses both hydration AND custodiet because it's a sidechain.
    res_sub = router.execute_hooks(router.normalize_input({"session_id": sub_session_id, "hook_event_name": "PreToolUse", "tool_name": "Read"}))
    assert res_sub.verdict == "allow"
