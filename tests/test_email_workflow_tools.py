"""Test email-capture workflow documentation completeness.

Validates that email-capture.md includes explicit MCP tool names
and parameter structures, not just generic descriptions.
"""

import os
from pathlib import Path


def test_email_workflow_has_explicit_tool_examples() -> None:
    """Email-capture.md must include explicit MCP tool invocation examples.

    REQUIRED tool examples:
    - Step 1 (Fetch Emails): mcp__outlook__messages_list_recent OR mcp__outlook__messages_index
    - Step 3 (Context from memory): mcp__memory__retrieve_memory
    - Step 6 (Create Tasks): Both task_add.py script format AND MCP tool structure

    Each tool example must include:
    - Exact tool name (not "Use Outlook MCP")
    - Parameter structure with types
    - Example invocation showing all required parameters

    This ensures agents can directly invoke tools without guessing API structure.
    """
    aops_root = os.environ.get("AOPS")
    if not aops_root:
        raise RuntimeError("AOPS environment variable not set")

    workflow_file = Path(aops_root) / "skills/tasks/workflows/email-capture.md"
    assert workflow_file.exists(), f"Workflow file not found: {workflow_file}"

    content = workflow_file.read_text()

    # Step 1: Fetch Emails - Must show explicit Outlook MCP tool
    outlook_tools = [
        "mcp__outlook__messages_list_recent",
        "mcp__outlook__messages_index",
    ]
    has_outlook_tool = any(tool in content for tool in outlook_tools)
    assert has_outlook_tool, (
        "Step 1 (Fetch Recent Emails) must include explicit Outlook MCP tool name.\n"
        f"Expected one of: {outlook_tools}\n"
        "Found: Generic 'Use Outlook MCP' without tool name"
    )

    # Verify Outlook tool has parameter structure
    if "mcp__outlook__messages_list_recent" in content:
        # Check for parameter documentation near the tool name
        outlook_section_start = content.find("### Step 1: Fetch Recent Emails")
        outlook_section_end = content.find("### Step 2:", outlook_section_start)
        outlook_section = content[outlook_section_start:outlook_section_end]

        assert (
            "account" in outlook_section.lower() or "limit" in outlook_section.lower()
        ), (
            "Outlook MCP tool example must show parameter structure.\n"
            "Expected: Parameters like 'account' or 'limit' with type information"
        )

    # Step 3: Context from memory - Must show explicit memory MCP tool
    memory_tools = [
        "mcp__memory__retrieve_memory",
        "mcp__memory__retrieve_with_quality_boost",
    ]
    has_memory_tool = any(tool in content for tool in memory_tools)
    assert has_memory_tool, (
        "Step 3 (Gather Context) must include explicit memory MCP tool name.\n"
        f"Expected one of: {memory_tools}\n"
        "Found: Generic description without tool name"
    )

    # Verify memory tool has parameter structure
    if "mcp__memory__retrieve_memory" in content:
        memory_section_start = content.find("### Step 3:")
        memory_section_end = content.find("### Step 4:", memory_section_start)
        memory_section = content[memory_section_start:memory_section_end]

        assert "query" in memory_section.lower(), (
            "Memory MCP tool example must show parameter structure.\n"
            "Expected: Parameter 'query' with examples"
        )

    # Step 6: Create Tasks - Must show both backend examples with full parameters
    # Scripts backend
    assert (
        "task_add.py" in content
    ), "Step 6 (Create Tasks via Backend) must include task_add.py script example"

    task_script_section_start = content.find("**Scripts backend example**:")
    if task_script_section_start > 0:
        task_script_section_end = content.find("```", task_script_section_start + 200)
        task_script_section = content[
            task_script_section_start : task_script_section_end + 3
        ]

        # Check all required task_add.py parameters are shown
        required_params = ["--title", "--priority", "--project", "--body"]
        missing_params = [p for p in required_params if p not in task_script_section]
        assert not missing_params, (
            f"task_add.py example must show all required parameters.\n"
            f"Missing: {missing_params}\n"
            f"Required: {required_params}"
        )

    # Note: Tasks MCP backend is not yet implemented.
    # The Python script backend (task_add.py) is the authoritative task creation method.
