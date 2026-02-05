"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (read_only, write, stop)
2. Gate requirements for each category
3. Gate execution order per event
4. Subagent bypass rules

All gate configuration should live here, not scattered across router.py,
gate_registry.py, or gates.py.
"""

from typing import Dict, List, Set

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize tools by their side effects. This determines which gates must
# pass before the tool can be used.

TOOL_CATEGORIES: Dict[str, Set[str]] = {
    # Read-only tools: no side effects, safe to run after hydration
    "read_only": {
        # Claude tools
        "Read",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
        "ListMcpResourcesTool",
        "ReadMcpResourceTool",
        "TaskOutput",
        # Gemini tools
        "read_file",
        "view_file",
        "list_dir",
        "find_by_name",
        "grep_search",
        "search_web",
        "read_url_content",
        # MCP retrieval tools (read-only)
        "mcp__plugin_aops-core_memory__retrieve_memory",
        "mcp__plugin_aops-core_memory__recall_memory",
        "mcp__plugin_aops-core_memory__search_by_tag",
        "mcp__plugin_aops-core_memory__list_memories",
        "mcp__plugin_aops-core_memory__check_database_health",
        "mcp__plugin_aops-core_task_manager__get_task",
        "mcp__plugin_aops-core_task_manager__list_tasks",
        "mcp__plugin_aops-core_task_manager__search_tasks",
        "mcp__plugin_aops-core_task_manager__get_task_tree",
        "mcp__plugin_aops-core_task_manager__get_children",
        "mcp__plugin_aops-core_task_manager__get_dependencies",
        "mcp__plugin_aops-core_task_manager__get_blocked_tasks",
        "mcp__plugin_aops-core_task_manager__get_review_tasks",
        "mcp__plugin_aops-core_task_manager__get_tasks_with_topology",
        "mcp__plugin_aops-core_task_manager__get_task_neighborhood",
        "mcp__plugin_aops-core_task_manager__get_index_stats",
        "mcp__plugin_aops-core_task_manager__get_graph_metrics",
        "mcp__plugin_aops-core_task_manager__get_review_snapshot",
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
    },
    # Write tools: modify files/state, require task binding and critic approval
    "write": {
        # Claude tools
        "Edit",
        "Write",
        "Bash",
        "NotebookEdit",
        "MultiEdit",
        # Gemini tools
        "write_file",
        "replace",
        "run_shell_command",
        "execute_code",
        # MCP mutating tools
        "mcp__plugin_aops-core_memory__store_memory",
        "mcp__plugin_aops-core_memory__delete_memory",
        "mcp__plugin_aops-core_task_manager__create_task",
        "mcp__plugin_aops-core_task_manager__update_task",
        "mcp__plugin_aops-core_task_manager__complete_task",
        "mcp__plugin_aops-core_task_manager__complete_tasks",
        "mcp__plugin_aops-core_task_manager__delete_task",
        "mcp__plugin_aops-core_task_manager__decompose_task",
        "mcp__plugin_aops-core_task_manager__claim_next_task",
        "mcp__plugin_aops-core_task_manager__reset_stalled_tasks",
        "mcp__plugin_aops-core_task_manager__reorder_children",
        "mcp__plugin_aops-core_task_manager__dedup_tasks",
        "mcp__plugin_aops-core_task_manager__rebuild_index",
    },
    # Meta tools: affect agent behavior but don't modify user files
    # These are allowed after hydration (like read_only)
    "meta": {
        "Task",
        "Skill",
        "TodoWrite",
        "AskUserQuestion",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
        # Gemini equivalents
        "activate_skill",
        "delegate_to_agent",
    },
}

# =============================================================================
# GATE REQUIREMENTS
# =============================================================================
# Which gates must have passed for each tool category to be allowed?
# Gates are checked in order; all listed gates must be in "passed" state.

TOOL_GATE_REQUIREMENTS: Dict[str, List[str]] = {
    # Read-only tools: just need hydration
    "read_only": ["hydration"],
    # Meta tools: same as read_only (planning/questioning is safe)
    "meta": ["hydration"],
    # Write tools: need hydration + task binding + critic approval
    "write": ["hydration", "task", "critic"],
    # Stop event: need all gates including QA and handover
    "stop": ["hydration", "task", "critic", "qa", "handover"],
}

# =============================================================================
# GATE EXECUTION ORDER
# =============================================================================
# Which gates run for each event type, and in what order.
# Order matters: gates run in sequence, first deny wins.

GATE_EXECUTION_ORDER: Dict[str, List[str]] = {
    "SessionStart": [
        "session_env_setup",
        "unified_logger",
        "session_start",
    ],
    "UserPromptSubmit": [
        "user_prompt_submit",
        "unified_logger",
    ],
    "PreToolUse": [
        "unified_logger",
        "subagent_restrictions",
        "tool_gate",  # NEW: unified tool gating based on TOOL_GATE_REQUIREMENTS
    ],
    "PostToolUse": [
        "unified_logger",
        "task_binding",
        "accountant",
        "post_hydration",
        "post_critic",
        "post_qa",
        "skill_activation",
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
        "stop_gate",
        "generate_transcript",
        "session_end_commit",
    ],
    "SessionEnd": [
        "unified_logger",
    ],
}

# =============================================================================
# SUBAGENT BYPASS
# =============================================================================
# Gates that should only run for the main agent (bypass for subagents).
# Prevents recursive loops and reduces overhead.

MAIN_AGENT_ONLY_GATES: Set[str] = {
    "tool_gate",
    "hydration",
    "task_required",
    "custodiet",
    "qa_enforcement",
    "axiom_enforcer",
    "user_prompt_submit",
    "post_hydration",
    "post_critic",
    "post_qa",
    "skill_activation",
    "task_binding",
    "stop_gate",
    "session_end_commit",
    "session_start",
    "agent_response",
}

# =============================================================================
# GATE MODE DEFAULTS
# =============================================================================
# Default enforcement modes for gates. Can be overridden by environment variables.

GATE_MODE_DEFAULTS: Dict[str, str] = {
    "hydration": "block",  # HYDRATION_GATE_MODE env var
    "task": "warn",  # TASK_GATE_MODE env var
    "custodiet": "warn",  # CUSTODIET_MODE env var
    "critic": "warn",  # CRITIC_GATE_MODE env var (new)
    "qa": "warn",  # QA_GATE_MODE env var (new)
}

# Environment variable names for gate modes
GATE_MODE_ENV_VARS: Dict[str, str] = {
    "hydration": "HYDRATION_GATE_MODE",
    "task": "TASK_GATE_MODE",
    "custodiet": "CUSTODIET_MODE",
    "critic": "CRITIC_GATE_MODE",
    "qa": "QA_GATE_MODE",
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


def get_required_gates(tool_name: str) -> List[str]:
    """Get the gates that must pass before this tool can be used."""
    category = get_tool_category(tool_name)
    return TOOL_GATE_REQUIREMENTS.get(category, TOOL_GATE_REQUIREMENTS["write"])


def get_gates_for_event(event: str) -> List[str]:
    """Get the ordered list of gates to run for an event."""
    return GATE_EXECUTION_ORDER.get(event, [])


def is_main_agent_only(gate_name: str) -> bool:
    """Check if a gate should only run for the main agent."""
    return gate_name in MAIN_AGENT_ONLY_GATES
