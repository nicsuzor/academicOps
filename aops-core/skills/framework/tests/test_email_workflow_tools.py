"""Test email-capture workflow documentation completeness.

Validates that email-capture.md includes explicit MCP tool names
and parameter structures, not just generic descriptions.
"""

import os
from pathlib import Path

AOPS = os.environ.get("AOPS", os.path.expanduser("~/src/academicOps"))


def test_email_workflow_has_explicit_tool_examples() -> None:
    """Email-capture.md must include explicit MCP tool invocation examples.

    REQUIRED tool examples:
    - Step 1 (Fetch Emails): ~~email.messages_list_recent OR ~~email.messages_index
    - Step 3 (Context from PKB): pkb__search or pkb__get_document
    - Step 6 (Create Tasks): Both task_add.py script format AND MCP tool structure

    Each tool example must include:
    - Exact tool name (not "Use Outlook MCP")
    - Parameter structure with types
    - Example invocation showing all required parameters

    This ensures agents can directly invoke tools without guessing API structure.
    """
    workflow_file = Path(AOPS) / "skills/tasks/workflows/email-capture.md"
    assert workflow_file.exists(), f"Workflow file not found: {workflow_file}"

    content = workflow_file.read_text()

    # Step 1: Fetch Emails - Must show explicit Outlook MCP tool
    outlook_tools = [
        "messages_list_recent",
        "messages_index",
    ]
    has_outlook_tool = any(tool in content for tool in outlook_tools)
    assert has_outlook_tool, (
        "Step 1 (Fetch Recent Emails) must include explicit Outlook MCP tool name.\n"
        f"Expected one of: {outlook_tools}\n"
        "Found: Generic 'Use Outlook MCP' without tool name"
    )

    # Step 3: Context from PKB - Must show explicit PKB tool
    pkb_tools = [
        "pkb__search",
        "pkb__get_document",
        "pkb__list_documents",
    ]
    has_pkb_tool = any(tool in content for tool in pkb_tools)
    assert has_pkb_tool, (
        "Step 3 (Gather Context) must include explicit PKB tool name.\n"
        f"Expected one of: {pkb_tools}\n"
        "Found: No PKB search tool reference"
    )

    # Step 6: Create Tasks - Must show both backend examples with full parameters
    # Scripts backend
    assert "task_add.py" in content, (
        "Step 6 (Create Tasks via Backend) must include task_add.py script example"
    )

    task_script_section_start = content.find("**Scripts backend example**:")
    if task_script_section_start > 0:
        task_script_section_end = content.find("```", task_script_section_start + 200)
        task_script_section = content[task_script_section_start : task_script_section_end + 3]

        # Check all required task_add.py parameters are shown
        required_params = ["--title", "--priority", "--project", "--body"]
        missing_params = [p for p in required_params if p not in task_script_section]
        assert not missing_params, (
            f"task_add.py example must show all required parameters.\n"
            f"Missing: {missing_params}\n"
            f"Required: {required_params}"
        )

    # Tasks MCP backend
    task_mcp_section_start = content.find("**Tasks MCP backend example**:")
    assert task_mcp_section_start > 0, (
        "Step 6 must include Tasks MCP backend example showing tool structure"
    )

    task_mcp_section_end = content.find("```", task_mcp_section_start + 200)
    task_mcp_section = content[task_mcp_section_start : task_mcp_section_end + 3]

    # Check for tool name and parameter structure
    assert "create_task" in task_mcp_section or "Tool:" in task_mcp_section, (
        "Tasks MCP example must show tool name (e.g., 'create_task')"
    )

    required_task_fields = ["title", "priority", "project", "body"]
    missing_fields = [f for f in required_task_fields if f not in task_mcp_section]
    assert not missing_fields, (
        f"Tasks MCP example must show all required parameters.\n"
        f"Missing: {missing_fields}\n"
        f"Required: {required_task_fields}"
    )
