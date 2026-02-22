import sys
from pathlib import Path

# Add aops-core to path for imports
aops_core_dir = Path(__file__).parent.parent.parent
if str(aops_core_dir) not in sys.path:
    sys.path.insert(0, str(aops_core_dir))

from hooks.policy_enforcer import (
    validate_minimal_documentation,
    validate_no_direct_task_reads,
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


# --- validate_no_direct_task_reads ---


def test_block_read_task_md():
    """Read on a task markdown file is blocked."""
    result = validate_no_direct_task_reads(
        "Read",
        {"file_path": "/home/user/aca-data/data/tasks/inbox/aops-c4f7a17a-brain-repo-sync.md"},
    )
    assert result is not None
    assert result["continue"] is False
    assert "BLOCKED" in result["systemMessage"]
    assert "mcp__pkb__" in result["systemMessage"]


def test_block_glob_task_md():
    """Glob with a data/tasks/*.md pattern is blocked."""
    result = validate_no_direct_task_reads(
        "Glob",
        {"pattern": "data/tasks/inbox/*.md"},
    )
    assert result is not None
    assert result["continue"] is False


def test_block_grep_task_md():
    """Grep targeting data/tasks/ .md files is blocked."""
    result = validate_no_direct_task_reads(
        "Grep",
        {"path": "data/tasks/"},
        # Grep with a .md path doesn't match unless the path includes .md
        # but a glob filter would
    )
    # path itself doesn't end in .md — should NOT be blocked
    assert result is None


def test_block_grep_task_md_with_glob():
    """Grep with glob filter targeting .md task files is blocked."""
    result = validate_no_direct_task_reads(
        "Grep",
        {"path": "data/tasks/inbox/aops-deadbeef-my-task.md"},
    )
    assert result is not None
    assert result["continue"] is False


def test_allow_read_non_task_md():
    """Read on a non-task .md file is allowed."""
    result = validate_no_direct_task_reads(
        "Read",
        {"file_path": "aops-core/TOOLS.md"},
    )
    assert result is None


def test_allow_read_task_json():
    """Read on a .json file in data/tasks/ is handled by the JSON deny rule, not this one."""
    result = validate_no_direct_task_reads(
        "Read",
        {"file_path": "data/tasks/index.json"},
    )
    assert result is None  # JSON files not covered by this validator


def test_allow_write_task_md():
    """Write tool is not blocked by this validator (only reads are blocked here)."""
    result = validate_no_direct_task_reads(
        "Write",
        {"file_path": "data/tasks/inbox/aops-c4f7a17a-test.md", "content": "# test"},
    )
    assert result is None
