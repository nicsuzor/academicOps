"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (always_available, read_only, write, meta, stop)
2. Gate execution order per event
3. Subagent bypass rules
4. Gate modes (block/warn)

"""

import os

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize tools by their side effects. This determines which gates must
# pass before the tool can be used.

TOOL_CATEGORIES: dict[str, set[str]] = {
    # Always available: bypass ALL gates, including hydration
    "always_available": {
        "Task",
        "Skill",
        "delegate_to_agent",
        "activate_skill",
        "mcp__pkb__get_task",
        "mcp__pkb__get_task_network",
        "mcp__pkb__create_task",
        "mcp__pkb__update_task",
        "mcp__pkb__complete_task",
        "mcp__pkb__reindex",
        "mcp__pkb__list_tasks",
        "mcp__pkb__task_search",
        "mcp__pkb__get_network_metrics",
        "mcp__pkb__get_blocked_tasks",
        "mcp__pkb__delete_document",
        "mcp__pkb__semantic_search",
        "mcp__pkb__pkb_search",
        "mcp__pkb__pkb_context",
        "create_task",
        "update_task",
        "complete_task",
        "get_task",
        "list_tasks",
        "task_search",
        "prompt-hydrator",
        "aops-core:prompt-hydrator",
        "custodiet",
        "aops-core:custodiet",
        "qa",
        "aops-core:qa",
        "handover",
        "aops-core:handover",
        "dump",
        "aops-core:dump",
        "codebase_investigator",
        "cli_help",
        "effectual-planner",
        "AskUserQuestion",
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
        # Claude Code built-in task tracking tools
        "TaskCreate",
        "TaskUpdate",
        "TaskGet",
        "TaskList",
    },
    # Read-only tools: no side effects
    "read_only": {
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
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
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
    # Write tools: modify USER files/state
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
    """Get the category for a tool. Returns 'unknown' if not categorized."""
    for category, tools in TOOL_CATEGORIES.items():
        if tool_name in tools:
            return category
    # Default: treat unknown tools as write (conservative)
    return "write"
