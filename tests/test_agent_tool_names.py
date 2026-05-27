import pytest

from scripts.build import transform_agent_for_platform, translate_tool_calls
from scripts.transforms.agent_schema import claude_mcp_to_gemini


class TestClaudeMcpToGemini:
    """Unit tests for the namespace-aware MCP tool name transform."""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("mcp__pkb__search", "mcp_pkb_search"),
            ("mcp__pkb__create_task", "mcp_pkb_create_task"),
            ("mcp__plugin_aops-core_pkb__get_task", "mcp_pkb_get_task"),
            ("mcp__plugin_aops-core_pkb__append", "mcp_pkb_append"),
            ("mcp__plugin_aops-core_pkb__create_memory", "mcp_pkb_create_memory"),
            ("mcp__playwright__browser_navigate", "mcp_playwright_browser_navigate"),
            ("mcp__plugin_aops-tools_zot__search", "mcp_zot_search"),
        ],
    )
    def test_claude_to_gemini_mcp_name(self, input_name, expected):
        assert claude_mcp_to_gemini(input_name) == expected

    def test_non_mcp_name_unchanged(self):
        assert claude_mcp_to_gemini("Read") == "Read"
        assert claude_mcp_to_gemini("Bash") == "Bash"

    def test_no_double_underscores_in_output(self):
        result = claude_mcp_to_gemini("mcp__plugin_aops-core_pkb__get_task")
        assert "__" not in result

    def test_no_plugin_namespace_in_output(self):
        result = claude_mcp_to_gemini("mcp__plugin_aops-core_pkb__get_task")
        assert "plugin_" not in result
        assert "aops-core" not in result


def test_gemini_tool_name_transformation():
    """Test that plugin-namespaced mcp tools are correctly transformed for Gemini."""
    content = """---
name: test-agent
description: Test agent
tools:
  - mcp__plugin_aops-core_pkb__search
  - mcp__plugin_aops-core_pkb__create_task
  - read_file
---
Body with mcp__plugin_aops-core_pkb__search and mcp__pkb__create_task.
"""
    transformed = transform_agent_for_platform(content, "gemini", "test-agent.md")
    final = translate_tool_calls(transformed, "gemini")

    assert "mcp_pkb_search" in final
    assert "mcp_pkb_create_task" in final
    assert "mcp__" not in final
    assert "plugin_aops-core" not in final


def test_gemini_short_form_tool_names():
    """Test that short-form mcp__pkb__search also works."""
    content = """---
name: test-agent
description: Test agent
tools:
  - mcp__pkb__search
  - mcp__pkb__create_task
---
Body.
"""
    transformed = transform_agent_for_platform(content, "gemini", "test-agent.md")

    assert "mcp_pkb_search" in transformed
    assert "mcp_pkb_create_task" in transformed
    assert "mcp__" not in transformed


def test_claude_tool_name_preservation():
    """Test that tool names are preserved for Claude (no namespace stripping)."""
    content = """---
name: test-agent
description: Test agent
tools:
  - mcp__plugin_aops-core_pkb__search
  - read_file
---
Body.
"""
    transformed = transform_agent_for_platform(content, "claude", "test-agent.md")

    assert "mcp__plugin_aops-core_pkb__search" in transformed
    assert "Read" in transformed
    assert "mcp_pkb_search" not in transformed


def test_translate_tool_calls_body_gemini():
    """Test that MCP tool names in prose are translated for Gemini."""
    body = "Use mcp__plugin_aops-core_pkb__search to find tasks."
    translated = translate_tool_calls(body, "gemini")
    assert "mcp_pkb_search" in translated
    assert "mcp__" not in translated
    assert "plugin_aops-core" not in translated


def test_translate_tool_calls_body_short_form():
    """Short-form mcp names in prose also get translated."""
    body = "Use mcp__pkb__search and mcp__pkb__get_task."
    translated = translate_tool_calls(body, "gemini")
    assert translated == "Use mcp_pkb_search and mcp_pkb_get_task."


def test_translate_plugin_root_gemini():
    """Test that CLAUDE_PLUGIN_ROOT is replaced with extensionPath in Gemini body text."""
    body = "Include @${CLAUDE_PLUGIN_ROOT}/.agents/rules/AXIOMS.md in your context."
    translated = translate_tool_calls(body, "gemini")
    assert "${CLAUDE_PLUGIN_ROOT}" not in translated
    assert "${extensionPath}" in translated
    assert translated == "Include @${extensionPath}/.agents/rules/AXIOMS.md in your context."


def test_translate_plugin_root_claude_unchanged():
    """Test that CLAUDE_PLUGIN_ROOT is NOT replaced when building for Claude."""
    body = "Include @${CLAUDE_PLUGIN_ROOT}/.agents/rules/AXIOMS.md in your context."
    translated = translate_tool_calls(body, "claude")
    assert "${CLAUDE_PLUGIN_ROOT}" in translated
    assert "${extensionPath}" not in translated
