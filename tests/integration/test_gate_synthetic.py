import json
import os
import subprocess
import pytest
from pathlib import Path

@pytest.mark.integration
def test_custodiet_threshold_synthetic():
    """
    Verify custodiet threshold logic by calling the router directly.
    This avoids the flakiness of forcing Claude to run many tools.
    """
    aops_root = os.environ.get("AOPS")
    router_path = Path(aops_root) / "aops-core" / "hooks" / "router.py"
    
    import uuid
    session_id = str(uuid.uuid4())
    # Ensure fresh state
    state_file = Path.home() / ".claude" / "projects" / "-tmp-claude-test" / f"{session_id}.json"
    if state_file.exists(): state_file.unlink()
    
    # 1. Start Session
    def call_router(event, tool_name=None, tool_input=None):
        payload = {
            "session_id": session_id,
            "hook_event_name": event,
            "tool_name": tool_name,
            "tool_input": tool_input or {}
        }
        result = subprocess.run(
            ["uv", "run", "--directory", str(Path(aops_root)/"aops-core"), "python", str(router_path), "--client", "claude"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=os.environ
        )
        if result.stderr:
            print(f"DEBUG Router Stderr ({event}): {result.stderr}")
        return json.loads(result.stdout)

    # 1. Startup and Prompt
    call_router("SessionStart")
    call_router("UserPromptSubmit", tool_input={"prompt": "Do work"})
    
    # 1.5 Unblock Hydration
    # This trigger unblocks the hydration gate and RESETS the ops counter!
    call_router("PreToolUse", tool_name="Task", tool_input={"subagent_type": "aops-core:prompt-hydrator"})
    call_router("PostToolUse", tool_name="Task", tool_input={"subagent_type": "aops-core:prompt-hydrator"})
    
    # 2. Run 6 tools (Threshold is 7, Task(hydrator) was #1)
    for i in range(6):
        # Pre
        res = call_router("PreToolUse", tool_name="Bash")
        assert res["hookSpecificOutput"]["permissionDecision"] == "allow"
        # Post
        call_router("PostToolUse", tool_name="Bash")
        
    # 3. 8th Tool (7th op since start) should be DENIED
    res = call_router("PreToolUse", tool_name="Bash")
    assert res["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "Compliance check required" in res["systemMessage"]
    
    # 4. Invoke Custodiet
    call_router("PreToolUse", tool_name="Task", tool_input={"subagent_type": "custodiet"})
    call_router("PostToolUse", tool_name="Task", tool_input={"subagent_type": "custodiet"})
    
    # 5. Next Tool should be ALLOWED again
    res = call_router("PreToolUse", tool_name="Bash")
    assert res["hookSpecificOutput"]["permissionDecision"] == "allow"

@pytest.mark.integration
def test_subagent_bypass_synthetic():
    """
    Verify that subagents bypass gates even when threshold is hit.
    """
    aops_root = os.environ.get("AOPS")
    router_path = Path(aops_root) / "aops-core" / "hooks" / "router.py"
    
    import uuid
    session_id = str(uuid.uuid4())
    
    def call_router(event, tool_name=None, tool_input=None, sub_session_id=None):
        payload = {
            "session_id": sub_session_id or session_id,
            "hook_event_name": event,
            "tool_name": tool_name,
            "tool_input": tool_input or {}
        }
        result = subprocess.run(
            ["uv", "run", "--directory", str(Path(aops_root)/"aops-core"), "python", str(router_path), "--client", "claude"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=os.environ
        )
        if result.stderr:
            print(f"DEBUG Router Stderr ({event}): {result.stderr}")
        return json.loads(result.stdout)

    # 1. Startup Main Agent
    call_router("SessionStart")
    call_router("UserPromptSubmit", tool_input={"prompt": "Do work"})
    
    # 1.5 Unblock Hydration
    call_router("PreToolUse", tool_name="Task", tool_input={"subagent_type": "aops-core:prompt-hydrator"})
    call_router("PostToolUse", tool_name="Task", tool_input={"subagent_type": "aops-core:prompt-hydrator"})
    
    # 2. Hit Threshold (6 more tools + hydrator = 7)
    for i in range(6):
        call_router("PreToolUse", tool_name="Bash")
        call_router("PostToolUse", tool_name="Bash")
        
    # 3. Main Agent is BLOCKED
    res = call_router("PreToolUse", tool_name="Bash")
    assert res["hookSpecificOutput"]["permissionDecision"] == "deny"
    
    # 4. SUBAGENT (with different ID) is ALLOWED (because it's not registered as main)
    res = call_router("PreToolUse", tool_name="Read", sub_session_id="agent-sub-1")
    assert res["hookSpecificOutput"]["permissionDecision"] == "allow"
