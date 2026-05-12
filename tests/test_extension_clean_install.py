import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

# Known built-in tools allowed in Gemini CLI and Claude Code agents.
# Everything else must be an MCP tool (starting with mcp_ or mcp__)
BUILTIN_TOOLS = {
    # Gemini CLI built-ins (lowercase)
    "read_file",
    "run_shell_command",
    "bash",
    "grep_search",
    "glob",
    "replace",
    "write_file",
    "web_fetch",
    "save_memory",
    "google_web_search",
    "ask_user",
    "enter_plan_mode",
    "str_replace_editor",
    "brave_web_search",
    "list_directory",
    # Claude Code built-ins (PascalCase)
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "NotebookEdit",
    "WebFetch",
    "WebSearch",
    "Task",
    "TodoWrite",
    "ExitPlanMode",
    "AskUserQuestion",
    "Skill",
    "ToolSearch",
    # Specific agent tools
    "codebase_investigator",
    "cli_help",
    "generalist",
    "dev-standards",
    "framework-ops",
    "james",
    "pauli",
    "rbg",
    "activate_skill",
    # Claude Code built-in tools (PascalCase)
    "Agent",
    "TodoRead",
    "NotebookRead",
}


def test_agent_tool_names_are_valid():
    """
    Catch errors like:
    Validation failed: Agent Definition: tools.2: Invalid tool name

    The Gemini CLI requires tools to either be registered built-ins
    or properly namespaced MCP tools (e.g., mcp_playwright_...).
    """
    agents_dir = REPO_ROOT / "aops-core" / "agents"
    if not agents_dir.exists():
        pytest.skip("Agents directory not found")

    for agent_file in agents_dir.glob("*.md"):
        content = agent_file.read_text()
        if not content.startswith("---"):
            continue

        try:
            parts = content.split("---")
            if len(parts) < 3:
                continue
            frontmatter_str = parts[1]
            frontmatter = yaml.safe_load(frontmatter_str)
        except Exception as e:
            pytest.fail(f"Failed to parse frontmatter in {agent_file.name}: {e}")

        if not frontmatter:
            continue

        tools = frontmatter.get("tools", [])
        if not tools:
            continue

        for i, tool in enumerate(tools):
            is_builtin = tool in BUILTIN_TOOLS
            is_mcp = tool.startswith("mcp_") or tool.startswith("mcp__")

            assert is_builtin or is_mcp, (
                f"Invalid tool name '{tool}' at tools.{i} in {agent_file.name}. "
                f"Tool must be a known built-in or start with 'mcp_' prefix."
            )


def test_gemini_md_imports_resolve():
    """
    Catch errors like:
    [ImportProcessor] Failed to import CORE.md: ENOENT: no such file or directory

    Gemini CLI ImportProcessor looks for lines starting with @filename.
    """
    import_pattern = re.compile(r"^@([a-zA-Z0-9_/.-]+)\b", re.MULTILINE)

    # Check all GEMINI.md files in the repository
    for gemini_file in REPO_ROOT.rglob("GEMINI.md"):
        # Ignore things in dist/, .gemini/ or .claude/ if they somehow got in there
        if any(part in (".gemini", "dist", ".claude", ".aops") for part in gemini_file.parts):
            continue
        content = gemini_file.read_text()
        for match in import_pattern.finditer(content):
            imported_filename = match.group(1)
            target_path = gemini_file.parent / imported_filename

            assert target_path.exists(), (
                f"Broken import in {gemini_file.relative_to(REPO_ROOT)}: "
                f"Failed to import '{imported_filename}'. File does not exist at {target_path.relative_to(REPO_ROOT)}"
            )
