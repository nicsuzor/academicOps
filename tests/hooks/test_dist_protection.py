import sys
from pathlib import Path

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.policy_enforcer import (
    validate_minimal_documentation,
    validate_safe_git_usage,
    validate_protect_artifacts
)

def run_enforcer(input_data):
    tool_name = input_data["tool_name"]
    args = input_data["tool_input"]
    
    result = validate_minimal_documentation(tool_name, args)
    if result:
        return result

    result = validate_safe_git_usage(tool_name, args)
    if result:
        return result

    result = validate_protect_artifacts(tool_name, args)
    if result:
        return result

    return {}

def test_block_dist_write():
    input_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "dist/aops-core-gemini/hooks/hooks.json",
            "content": "{}"
        }
    }
    result = run_enforcer(input_data)
    # The functions return a dict with 'continue' and 'systemMessage'
    assert result["continue"] is False
    assert "BLOCKED" in result["systemMessage"]

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
    assert result["continue"] is False

def test_allow_source_write():
    input_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "aops-core/hooks/new_hook.py",
            "content": "# new hook"
        }
    }
    result = run_enforcer(input_data)
    assert result == {}