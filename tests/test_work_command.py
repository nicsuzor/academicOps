import sys
from pathlib import Path

# Ensure we can import from scripts
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from scripts.convert_commands_to_toml import convert_command, extract_frontmatter

WORK_CMD_PATH = root_dir / "aops-core/commands/work.md"


def test_work_command_exists():
    """Verify that the work command markdown file exists."""
    assert WORK_CMD_PATH.exists(), f"File not found: {WORK_CMD_PATH}"


def test_work_command_frontmatter():
    """Verify the frontmatter contains required fields."""
    content = WORK_CMD_PATH.read_text()
    fm, body = extract_frontmatter(content)

    assert fm.get("name") == "work"
    assert "AskUserQuestion" in fm.get("allowed-tools", "")
    assert "Do NOT auto-execute" in body
    assert "Explicit Completion" in body


def test_work_command_toml_conversion():
    """Verify that the command can be converted to TOML format."""
    toml = convert_command(WORK_CMD_PATH)

    # Check structure
    assert "description =" in toml
    assert "prompt = '''" in toml

    # Check content preservation
    assert "Collaborative Task Execution" in toml
    assert "mcp__plugin_aops-tools_task_manager__update_task" in toml
