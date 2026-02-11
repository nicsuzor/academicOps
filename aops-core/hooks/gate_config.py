"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (always_available, read_only, write, meta, stop)
2. Gate execution order per event
3. Subagent bypass rules
4. Gate modes (block/warn)

Legacy configuration (TOOL_GATE_REQUIREMENTS, etc.) has been migrated to
individual Gate classes in lib/gates/.
"""


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
        "mcp__plugin_aops-core_task_manager__get_task",
        "mcp__plugin_aops-core_task_manager__get_children",
        "mcp__plugin_aops-core_task_manager__get_dependencies",
        "mcp__plugin_aops-core_task_manager__create_task",
        "mcp__plugin_aops-core_task_manager__update_task",
        "mcp__plugin_aops-core_task_manager__complete_task",
        "mcp__plugin_aops-core_task_manager__decompose_task",
        "mcp__plugin_aops-core_task_manager__claim_next_task",
        "mcp__plugin_aops-core_task_manager__rebuild_index",
        "mcp__plugin_aops-core_task_manager__list_tasks",
        "create_task",
        "update_task",
        "complete_task",
        "get_task",
        "list_tasks",
        "search_tasks",
        "get_task_tree",
        "get_children",
        "decompose_task",
        "mcp__plugin_aops-core_memory__retrieve_memory",
        "mcp__plugin_aops-core_memory__recall_memory",
        "mcp__plugin_aops-core_memory__search_by_tag",
        "retrieve_memory",
        "recall_memory",
        "search_by_tag",
        "prompt-hydrator",
        "aops-core:prompt-hydrator",
        "critic",
        "aops-core:critic",
        "custodiet",
        "aops-core:custodiet",
        "qa",
        "aops-core:qa",
        "handover",
        "aops-core:handover",
        "codebase_investigator",
        "cli_help",
        "effectual-planner",
        "AskUserQuestion",
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
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
        "mcp__plugin_aops-core_memory__list_memories",
        "mcp__plugin_aops-core_memory__check_database_health",
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
        "mcp__plugin_aops-core_task_manager__search_tasks",
        "mcp__plugin_aops-core_task_manager__get_task_tree",
        "mcp__plugin_aops-core_task_manager__get_review_tasks",
        "mcp__plugin_aops-core_task_manager__get_blocked_tasks",
        "mcp__plugin_aops-core_task_manager__get_tasks_with_topology",
        "mcp__plugin_aops-core_task_manager__get_task_neighborhood",
        "mcp__plugin_aops-core_task_manager__get_index_stats",
        "mcp__plugin_aops-core_task_manager__get_graph_metrics",
        "mcp__plugin_aops-core_task_manager__get_review_snapshot",
        "mcp__plugin_aops-core_task_manager__complete_tasks",
        "mcp__plugin_aops-core_task_manager__delete_task",
        "mcp__plugin_aops-core_task_manager__reset_stalled_tasks",
        "mcp__plugin_aops-core_task_manager__reorder_children",
        "mcp__plugin_aops-core_task_manager__dedup_tasks",
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
        "mcp__plugin_aops-core_memory__store_memory",
        "mcp__plugin_aops-core_memory__delete_memory",
    },
    "meta": set(),
}

# =============================================================================
# GATE EXECUTION ORDER
# =============================================================================
# Which gates run for each event type, and in what order.
# Order matters: gates run in sequence, first deny wins.

GATE_EXECUTION_ORDER: dict[str, list[str]] = {
    "SessionStart": [
        "session_env_setup",
        "unified_logger",
        "session_start",
        # "gate_init",  # Migrated to session_start (on_session_start)
    ],
    "UserPromptSubmit": [
        "user_prompt_submit",
        "unified_logger",
        # "gate_reset",  # Migrated to user_prompt_submit (on_user_prompt)
    ],
    "PreToolUse": [
        "unified_logger",
        "tool_gate",  # Unified tool gating
    ],
    "PostToolUse": [
        "unified_logger",
        # "task_binding", # Migrated to gate_update
        # "accountant",   # Migrated to gate_update
        "gate_update",  # Unified gate update
        "ntfy_notifier",
    ],
    "AfterAgent": [
        "unified_logger",
        "agent_response",
    ],
    "SubagentStop": [
        "unified_logger",
    ],
    "Stop": [
        "unified_logger",
        "ntfy_notifier",
        "stop_gate",
        "generate_transcript",
    ],
    "SessionEnd": [
        "generate_transcript",
        "unified_logger",
    ],
}

# =============================================================================
# SUBAGENT BYPASS
# =============================================================================
# Gates that should only run for the main agent (bypass for subagents).

MAIN_AGENT_ONLY_GATES: set[str] = {
    "tool_gate",
    "gate_init",  # kept for safety if referenced elsewhere, though dead
    "gate_reset",  # kept for safety
    "gate_update",
    "user_prompt_submit",
    "task_binding",  # kept for safety
    "stop_gate",
    "session_start",
    "agent_response",
}

# =============================================================================
# GATE MODE DEFAULTS
# =============================================================================
# Default enforcement modes for gates. Can be overridden by environment variables.

GATE_MODE_DEFAULTS: dict[str, str] = {
    "hydration": "block",
    "task": "warn",
    "custodiet": "warn",
    "critic": "warn",
    "qa": "warn",
    "handover": "warn",
}

# Environment variable names for gate modes
GATE_MODE_ENV_VARS: dict[str, str] = {
    "hydration": "HYDRATION_GATE_MODE",
    "task": "TASK_GATE_MODE",
    "custodiet": "CUSTODIET_GATE_MODE",
    "critic": "CRITIC_GATE_MODE",
    "qa": "QA_GATE_MODE",
    "handover": "HANDOVER_GATE_MODE",
}

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
