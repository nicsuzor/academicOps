"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (always_available, read_only, write, meta)
2. Compliance subagent types (bypass gate policies)
3. Spawn tool detection (cross-platform agent/skill invocation)
4. Gate modes (block/warn)

"""

import os
from typing import Any

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize TOOL NAMES by their side effects. This determines which gates
# must pass before the tool can be used.
#
# IMPORTANT: Only TOOL NAMES go here. Agent/skill names (prompt-hydrator,
# custodiet, etc.) are subagent_type values, not tool names. They belong in
# COMPLIANCE_SUBAGENT_TYPES below.

TOOL_CATEGORIES: dict[str, set[str]] = {
    # Always available: bypass ALL gates, including hydration.
    # These are tools that either invoke agents/skills (needed to satisfy gates)
    # or manage task state (needed for framework lifecycle).
    "always_available": {
        # --- Agent/skill invocation tools (cross-platform) ---
        "Agent",  # Claude Code: spawn subagent (current tool name)
        "Task",  # Claude Code: spawn subagent (legacy/alias)
        "Skill",  # Claude Code: invoke skill in-session
        "delegate_to_agent",  # Gemini CLI: spawn subagent
        "activate_skill",  # Gemini CLI: invoke skill in-session
        # --- PKB task management (write operations, always needed) ---
        "mcp__pkb__get_task",
        "mcp__pkb__create_task",
        "mcp__pkb__update_task",
        "mcp__pkb__complete_task",
        "mcp__pkb__reindex",
        "mcp__pkb__delete_document",
        # Gemini equivalents (bare tool names)
        "create_task",
        "update_task",
        "complete_task",
        "get_task",
        "list_tasks",
        "task_search",
        # --- Claude Code built-in meta tools ---
        "AskUserQuestion",
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
    },
    # Read-only tools: no side effects. Exempt from hydration gate.
    # Hydrator and custodiet subagents use Read to access their context files.
    "read_only": {
        # Claude Code
        "Read",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "ListMcpResourcesTool",
        "ReadMcpResourceTool",
        "TaskOutput",
        "TaskStop",
        "ToolSearch",
        # Gemini CLI
        "read_file",
        "view_file",
        "list_dir",
        "list_directory",
        "find_by_name",
        "grep_search",
        "search_file_content",
        "glob",
        "search_web",
        "google_web_search",
        "web_fetch",
        "read_url_content",
        # Context7 MCP
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
        # PKB read-only tools
        "mcp__pkb__task_search",
        "mcp__pkb__get_task_network",
        "mcp__pkb__list_tasks",
        "mcp__pkb__get_blocked_tasks",
        "mcp__pkb__get_network_metrics",
        "mcp__pkb__semantic_search",
        "mcp__pkb__pkb_search",
        "mcp__pkb__pkb_context",
        "mcp__pkb__get_document",
        "mcp__pkb__list_documents",
    },
    # Write tools: modify USER files/state. Subject to all gates.
    "write": {
        "Edit",
        "Write",
        "Bash",
        "NotebookEdit",
        "MultiEdit",
        "write_file",
        "replace",
        "run_shell_command",
        "execute_code",
        "save_memory",
    },
    "meta": set(),
}

# =============================================================================
# COMPLIANCE SUBAGENT TYPES
# =============================================================================
# Subagent types that are part of the compliance framework itself.
# When detected as the active subagent, their tool calls bypass gate
# POLICIES (but triggers still run to update gate state correctly).
#
# This is conceptually different from tool categories: these are
# subagent_type values (passed via Task/delegate_to_agent params),
# not tool names.

COMPLIANCE_SUBAGENT_TYPES: frozenset[str] = frozenset(
    {
        "hydrator",
        "prompt-hydrator",
        "aops-core:prompt-hydrator",
        "custodiet",
        "aops-core:custodiet",
        "audit",
        "aops-core:audit",
        "butler",
        "aops-core:butler",
    }
)

# =============================================================================
# SPAWN TOOLS — Cross-platform agent/skill detection
# =============================================================================
# Maps tool_name -> (parameter_names_to_check, is_skill)
#
# When a hook event carries one of these tool names, the router extracts
# the subagent_type from the first matching parameter in tool_input.
#
# is_skill=True means the tool runs in the MAIN agent's session (like
# Skill/activate_skill), not as a separate subagent. This prevents
# misclassifying skill invocations as subagent sessions.
#
# To add a new platform: add its agent-spawning and skill-invoking tools
# here with the parameter names they use for the agent/skill identifier.

SPAWN_TOOLS: dict[str, tuple[tuple[str, ...], bool]] = {
    # Claude Code
    "Agent": (("subagent_type",), False),  # Current tool name
    "Task": (("subagent_type",), False),  # Legacy/alias
    "Skill": (("skill",), True),
    # Gemini CLI
    "delegate_to_agent": (("name", "agent_name"), False),
    "activate_skill": (("skill", "name"), True),
    # Codex: add entries when tool names are known
    # GitHub Copilot: add entries when tool names are known
}

# =============================================================================
# GATE MODE DEFAULTS
# =============================================================================
# Default enforcement modes for gates. Can be overridden by environment variables.

GATE_MODE_DEFAULTS: dict[str, str] = {
    "hydration": "warn",
    "custodiet": "block",
    "qa": "block",
    "handover": "warn",
}

# Environment variable names for gate modes
GATE_MODE_ENV_VARS: dict[str, str] = {
    "hydration": "HYDRATION_GATE_MODE",
    "custodiet": "CUSTODIET_GATE_MODE",
    "qa": "QA_GATE_MODE",
    "handover": "HANDOVER_GATE_MODE",
}

HANDOVER_GATE_MODE = os.getenv(GATE_MODE_ENV_VARS["handover"], GATE_MODE_DEFAULTS["handover"])
QA_GATE_MODE = os.getenv(GATE_MODE_ENV_VARS["qa"], GATE_MODE_DEFAULTS["qa"])
CUSTODIET_GATE_MODE = os.getenv(GATE_MODE_ENV_VARS["custodiet"], GATE_MODE_DEFAULTS["custodiet"])
CUSTODIET_TOOL_CALL_THRESHOLD = int(os.getenv("CUSTODIET_TOOL_CALL_THRESHOLD", 50))
HYDRATION_GATE_MODE = os.getenv(GATE_MODE_ENV_VARS["hydration"], GATE_MODE_DEFAULTS["hydration"])

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_tool_category(tool_name: str) -> str:
    """Get the category for a tool. Returns 'write' if not categorized (conservative fallback)."""
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return category
    # Default: treat unknown tools as write (conservative)
    return "write"


def extract_subagent_type(
    tool_name: str | None, tool_input: dict[str, Any]
) -> tuple[str | None, bool]:
    """Extract subagent_type from a tool invocation using SPAWN_TOOLS table.

    Args:
        tool_name: The tool being called (e.g. "Task", "delegate_to_agent").
        tool_input: The tool's input parameters.

    Returns:
        (subagent_type, is_skill) tuple.
        subagent_type is None if this is not a spawn tool or if no
        agent/skill name was found in tool_input.
        is_skill is True for skill-like tools that run in the main session.
    """
    if not tool_name:
        return None, False
    spec = SPAWN_TOOLS.get(tool_name)
    if not spec:
        return None, False
    param_names, is_skill = spec
    for param in param_names:
        value = tool_input.get(param)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped, is_skill
    return None, is_skill
