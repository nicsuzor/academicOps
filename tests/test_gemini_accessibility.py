import json
import sys
from pathlib import Path

import pytest

# Add repo root to path for scripts imports
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build import (
    _generate_gemini_hooks_json,
    transform_agent_for_platform,
    translate_tool_calls,
)


@pytest.mark.parametrize("agent_name", ["rbg", "marsha"])
def test_core_agent_transformation_for_gemini(agent_name):
    """Verify core agents are correctly transformed for Gemini."""
    agent_src = REPO_ROOT / "aops-core" / "agents" / f"{agent_name}.md"
    assert agent_src.exists()

    content = agent_src.read_text()

    # 1. Transform for Gemini
    transformed = transform_agent_for_platform(content, "gemini", f"{agent_name}.md")
    # 2. Translate tool calls in body
    final = translate_tool_calls(transformed, "gemini")

    # We check for the presence of the mapped tools in the frontmatter
    frontmatter_part = final.split("---")[1]

    # All core agents should have at least some of these tools
    if agent_name == "rbg":
        assert "read_file" in frontmatter_part
        assert "grep_search" in frontmatter_part
        assert "glob" in frontmatter_part
        assert "replace" in frontmatter_part
        assert "write_file" in frontmatter_part

        # Verify Claude-specific tools are NOT in Gemini frontmatter
        assert "Read" not in frontmatter_part
        assert "Edit" not in frontmatter_part
        assert "Grep" not in frontmatter_part

    # Verify path replacement (${CLAUDE_PLUGIN_ROOT} -> ${extensionPath}) in the whole file
    assert "${CLAUDE_PLUGIN_ROOT}" not in final
    if "${CLAUDE_PLUGIN_ROOT}" in content:
        assert "${extensionPath}" in final
    if "AXIOMS.md" in content:
        # Axioms are co-shipped INTO the plugin payload at
        # <plugin>/.agents/rules/AXIOMS.md, so the import must resolve at
        # ${extensionPath}/.agents/rules/AXIOMS.md (no parent-of-root path).
        # Regression guard for #aops-75543e66.
        assert "@${extensionPath}/.agents/rules/AXIOMS.md" in final
        assert "/../.agents/rules/" not in final


@pytest.mark.parametrize("agent_name", ["junior", "rbg", "james", "pauli", "marsha"])
def test_core_agent_transformation_for_antigravity(agent_name):
    """Antigravity build must translate mcp__* tool names to mcp_* form in frontmatter."""
    agent_src = REPO_ROOT / "aops-core" / "agents" / f"{agent_name}.md"
    if not agent_src.exists():
        pytest.skip(f"Agent {agent_name} not found")

    content = agent_src.read_text()

    transformed = transform_agent_for_platform(content, "antigravity", f"{agent_name}.md")
    final = translate_tool_calls(transformed, "antigravity")

    frontmatter_part = final.split("---")[1]

    # No Claude-form MCP names should survive
    assert "mcp__plugin_aops-core_pkb__" not in frontmatter_part, (
        f"{agent_name}: Claude MCP name mcp__plugin_aops-core_pkb__* found in antigravity frontmatter"
    )
    assert "mcp__" not in frontmatter_part, (
        f"{agent_name}: untranslated mcp__* name found in antigravity frontmatter"
    )

    # If the source had PKB tools, the translated form must be present
    if "mcp__plugin_aops-core_pkb__" in content:
        assert "mcp_pkb_" in frontmatter_part, (
            f"{agent_name}: expected mcp_pkb_* in antigravity frontmatter after translation"
        )

    # Wildcard form must also be translated
    if "mcp__plugin_aops-core_pkb__*" in content:
        assert "mcp_pkb_*" in frontmatter_part, (
            f"{agent_name}: wildcard mcp_pkb_* missing from antigravity frontmatter"
        )


def test_antigravity_translate_tool_calls_mcp_names():
    """translate_tool_calls for antigravity rewrites mcp__plugin_*__tool in body text."""
    body = (
        "Use `mcp__plugin_aops-core_pkb__search` to look things up. "
        "Also see `mcp__plugin_aops-core_pkb__*` for all PKB tools. "
        "Non-MCP tools like Read and Bash stay unchanged."
    )
    result = translate_tool_calls(body, "antigravity")

    assert "mcp__plugin_aops-core_pkb__" not in result
    assert "mcp_pkb_search" in result
    assert "mcp_pkb_*" in result
    assert "Read" in result
    assert "Bash" in result


def test_antigravity_transform_preserves_non_mcp_tools():
    """Antigravity transform must leave Claude built-in tool names intact."""
    content = """\
---
name: test-agent
description: A test agent
tools:
  - Read
  - Write
  - Bash
  - mcp__plugin_aops-core_pkb__search
  - mcp__plugin_aops-core_pkb__*
  - mcp__outlook__*
---
Body text here.
"""
    result = transform_agent_for_platform(content, "antigravity", "test-agent.md")

    frontmatter_part = result.split("---")[1]
    assert "Read" in frontmatter_part
    assert "Write" in frontmatter_part
    assert "Bash" in frontmatter_part
    assert "mcp_pkb_search" in frontmatter_part
    assert "mcp_pkb_*" in frontmatter_part
    assert "mcp_outlook_*" in frontmatter_part
    assert "mcp__" not in frontmatter_part


def test_gemini_hooks_parameter_replacement(tmp_path):
    """Verify hooks.json is correctly transformed for Gemini with required parameters."""
    hooks_src = REPO_ROOT / "aops-core" / "hooks" / "hooks.json"
    assert hooks_src.exists()

    dst_path = tmp_path / "hooks.json"
    _generate_gemini_hooks_json(hooks_src, dst_path)

    assert dst_path.exists()
    hooks_config = json.loads(dst_path.read_text())

    # Verify all hooks are present and use ${extensionPath} and --client gemini
    # Let's check a specific event
    assert "SessionStart" in hooks_config["hooks"]
    session_start_hooks = hooks_config["hooks"]["SessionStart"]

    found_extension_path = False
    found_gemini_client = False
    found_event_arg = False

    for entry in session_start_hooks:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            if "${extensionPath}" in cmd:
                found_extension_path = True
            if "--client gemini" in cmd:
                found_gemini_client = True
            if "SessionStart" in cmd:
                found_event_arg = True

    assert found_extension_path, "Hooks must use ${extensionPath} in Gemini"
    assert found_gemini_client, "Hooks must use --client gemini in Gemini"
    assert found_event_arg, "Hooks must include event name as argument for Gemini"


def test_gemini_extension_manifest_parameters():
    """Verify gemini-extension.json contains required MCP parameters."""
    manifest_path = REPO_ROOT / "templates" / "aops-core.gemini-extension.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())

    assert "mcpServers" in manifest
    assert "pkb" in manifest["mcpServers"]

    pkb_config = manifest["mcpServers"]["pkb"]
    assert pkb_config["command"] == "bash"
    assert any("run-mcp.sh" in arg for arg in pkb_config["args"])

    # Verify environment variables
    assert "env" in pkb_config
    assert pkb_config["env"].get("ACA_DATA") == "${ACA_DATA}"
    assert pkb_config["env"].get("PKB_MCP_URL") == "${PKB_MCP_URL}"
