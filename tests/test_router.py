import os
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from tests.paths import get_hook_script

def test_session_start_hook_env_copy():
    router_path = get_hook_script("router.py")
    
    # Create a temporary file to act as CLAUDE_ENV_FILE
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_env_file:
        temp_env_path = temp_env_file.name
    
    try:
        # Prepare environment variables
        env = os.environ.copy()
        env["CLAUDE_ENV_FILE"] = temp_env_path
        env["AOPS"] = "/mock/aops/root"
        env["AOPS_BOT_GH_TOKEN"] = "mock-bot-token"
        env["PKB_MCP_URL"] = "http://mock-mcp-url"
        
        # Ensure some variables are NOT set to check that they aren't written
        env.pop("GEMINI_API_KEY", None)
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)

        # Prepare JSON input for SessionStart hook
        input_data = {
            "hook_event_name": "SessionStart",
            "session_id": "test-session-12345",
        }
        
        # Run router.py as a subprocess
        cmd = [sys.executable, str(router_path), "claude", "SessionStart"]
        result = subprocess.run(
            cmd,
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        
        # Check that it completed successfully
        assert result.returncode == 0
        
        # Read the written env file
        with open(temp_env_path, "r") as f:
            content = f.read()
            
        # Assertions
        assert "export AOPS_BOT_GH_TOKEN=mock-bot-token\n" in content
        assert "export GH_TOKEN=mock-bot-token\n" in content
        assert "export GITHUB_TOKEN=mock-bot-token\n" in content
        assert "export PKB_MCP_URL=http://mock-mcp-url\n" in content
        
        # Verify that unset variables are not written
        assert "GEMINI_API_KEY" not in content

    finally:
        # Clean up temporary file
        if os.path.exists(temp_env_path):
            os.remove(temp_env_path)

def test_stop_is_not_handled_by_router():
    """The Stop-time handover reminder is owned by the exit_reflection gate
    (gate_dispatch.py); router.py's superseded Stop branch is deleted and
    must stay deleted — no output, no second reminder path."""
    router_path = get_hook_script("router.py")
    input_data = {
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    }
    cmd = [sys.executable, str(router_path), "claude", "Stop"]
    result = subprocess.run(
        cmd,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""


def test_posttooluse_agent_synchronous_emits_reminder():
    """Synchronous Agent tool calls (run_in_background not set or False) emit the verify reminder."""
    router_path = get_hook_script("router.py")
    input_data = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": "do research"},
    }
    cmd = [sys.executable, str(router_path), "claude", "PostToolUse"]
    result = subprocess.run(
        cmd,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "≡ Always check subagent outputs" in parsed.get("systemMessage", "")
    assert "additionalContext" in parsed.get("hookSpecificOutput", {})
    assert "<academicOps deliverable-verify reminder>" in parsed["hookSpecificOutput"]["additionalContext"]


def test_posttooluse_agent_background_suppressed():
    """Background Agent tool calls (run_in_background=True) suppress the verify reminder."""
    router_path = get_hook_script("router.py")
    input_data = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": "do research", "run_in_background": True},
    }
    cmd = [sys.executable, str(router_path), "claude", "PostToolUse"]
    result = subprocess.run(
        cmd,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_pretooluse_ask_question_denied_in_headless_mode():
    """Interactive question tools in PreToolUse must be denied in headless/non-interactive mode."""
    router_path = get_hook_script("router.py")
    input_data = {
        "hook_event_name": "PreToolUse",
        "tool_name": "ask_question",
        "tool_input": {"question": "Should I proceed?"},
    }
    env = os.environ.copy()
    env["NONINTERACTIVE"] = "1"

    cmd = [sys.executable, str(router_path), "claude", "PreToolUse"]
    result = subprocess.run(
        cmd,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "forbidden in a headless / non-interactive context" in parsed["hookSpecificOutput"]["permissionDecisionReason"]


