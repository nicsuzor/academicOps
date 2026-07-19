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

def test_stop_hook_block():
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
    output = json.loads(result.stdout)
    assert "systemMessage" in output
