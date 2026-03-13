from scripts.build import transform_agent_for_platform, translate_tool_calls


def test_gemini_tool_name_transformation():
    """Test that mcp__server__tool is transformed to server_tool for Gemini."""
    content = """---
name: test-agent
description: Test agent
tools:
  - mcp__pkb__search
  - mcp__pkb__create_task
  - read_file
---
Body with mcp__pkb__search and mcp__pkb__create_task.
"""
    # Transform frontmatter
    transformed = transform_agent_for_platform(content, "gemini", "test-agent.md")

    # Translate body
    final = translate_tool_calls(transformed, "gemini")

    assert "pkb_search" in final
    assert "pkb_create_task" in final
    assert "mcp__pkb__search" not in final
    assert "mcp__pkb__create_task" not in final
    # Ensure it's single underscore
    assert "pkb__search" not in final


def test_claude_tool_name_preservation():
    """Test that tool names are preserved or PascalCased for Claude."""
    content = """---
name: test-agent
description: Test agent
tools:
  - mcp__pkb__search
  - read_file
---
Body.
"""
    transformed = transform_agent_for_platform(content, "claude", "test-agent.md")

    # Claude uses comma-separated string for tools
    assert "mcp__pkb__search" in transformed
    assert "Read" in transformed  # read_file maps to Read for Claude
    assert "pkb_search" not in transformed


def test_translate_tool_calls_body_gemini():
    """Test that tool names in the body are translated for Gemini."""
    body = "Use mcp__pkb__search to find tasks."
    translated = translate_tool_calls(body, "gemini")
    assert translated == "Use pkb_search to find tasks."

    body_list = "Tools: mcp__pkb__list_tasks, mcp__pkb__get_task."
    translated = translate_tool_calls(body_list, "gemini")
    assert translated == "Tools: pkb_list_tasks, pkb_get_task."
