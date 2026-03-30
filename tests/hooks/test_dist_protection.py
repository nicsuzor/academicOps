import sys
from pathlib import Path
from unittest.mock import patch

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.policy_enforcer import (
    validate_branch_protection,
    validate_minimal_documentation,
    validate_protect_artifacts,
    validate_safe_git_usage,
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

    result = validate_branch_protection(tool_name, args)
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
            "content": "{}",
        },
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
            "new_string": "bar",
        },
    }
    result = run_enforcer(input_data)
    assert result["continue"] is False


def test_allow_source_write():
    input_data = {
        "tool_name": "Write",
        "tool_input": {
            "file_path": "aops-core/hooks/new_hook.py",
            "content": "# new hook",
        },
    }
    result = run_enforcer(input_data)
    assert result == {}


def test_block_dist_copy_via_bash():
    """#354: Block cp/mv to dist/ via Bash."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "cp aops-core/commands/new_cmd.md dist/aops-claude/commands/",
        },
    }
    result = run_enforcer(input_data)
    assert result["continue"] is False
    assert "build pipeline" in result["systemMessage"]


def test_block_bulk_rm_rf():
    """#346: Block bulk rm -rf operations."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "rm -rf dir1 dir2 dir3",
        },
    }
    result = run_enforcer(input_data)
    assert result["continue"] is False
    assert "P#50" in result["systemMessage"]


def test_allow_single_rm_rf():
    """Single-target rm -rf should be allowed (user can approve)."""
    input_data = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "rm -rf /tmp/build-cache",
        },
    }
    result = run_enforcer(input_data)
    assert result == {}


def test_block_commit_on_main():
    """#322: Block git commit on main branch."""
    mock_result = type("Result", (), {"stdout": "main\n", "returncode": 0})()
    with patch("subprocess.run", return_value=mock_result):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'git commit -m "some change"',
            },
        }
        result = run_enforcer(input_data)
        assert result["continue"] is False
        assert "protected branch" in result["systemMessage"]


def test_allow_commit_on_feature_branch():
    """Commits on feature branches should be allowed."""
    mock_result = type("Result", (), {"stdout": "feature/my-branch\n", "returncode": 0})()
    with patch("subprocess.run", return_value=mock_result):
        input_data = {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'git commit -m "some change"',
            },
        }
        result = run_enforcer(input_data)
        assert result == {}
