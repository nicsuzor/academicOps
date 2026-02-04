import json
import subprocess
import pytest
from pathlib import Path

def run_enforcer(input_data):
    process = subprocess.Popen(
        ["python3", "aops-core/hooks/policy_enforcer.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=json.dumps(input_data))
    return json.loads(stdout)

def test_block_dist_write():
    input_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "dist/aops-core-gemini/hooks/hooks.json",
            "content": "{}"
        }
    }
    result = run_enforcer(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "protected by project-local rule" in result["hookSpecificOutput"]["additionalContext"]

def test_block_dist_edit():
    input_data = {
        "tool_name": "Edit",
        "tool_input": {
            "file_path": "dist/aops-core-gemini/AXIOMS.md",
            "old_string": "foo",
            "new_string": "bar"
        }
    }
    result = run_enforcer(input_data)
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_allow_source_write():
    input_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "aops-core/hooks/new_hook.py",
            "content": "# new hook"
        }
    }
    result = run_enforcer(input_data)
    # result should be empty or contain allow
    assert "hookSpecificOutput" not in result or result["hookSpecificOutput"]["permissionDecision"] != "deny"

if __name__ == "__main__":
    # Simple manual run
    try:
        test_block_dist_write()
        print("test_block_dist_write passed")
        test_block_dist_edit()
        print("test_block_dist_edit passed")
        test_allow_source_write()
        print("test_allow_source_write passed")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
