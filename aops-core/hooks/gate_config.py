"""
Gate Configuration: Single source of truth for gate behavior.

This module defines:
1. Tool categories (always_available, read_only, write, meta, stop)
2. Gate requirements for each category
3. Gate execution order per event
4. Subagent bypass rules

All gate configuration should live here, not scattered across router.py,
gate_registry.py, or gates.py.
"""

from typing import Any, Dict, List, Set

# =============================================================================
# TOOL CATEGORIES
# =============================================================================
# Categorize tools by their side effects. This determines which gates must
# pass before the tool can be used.

TOOL_CATEGORIES: Dict[str, Set[str]] = {
    # Always available: bypass ALL gates, including hydration
    # These are framework infrastructure tools, not user file modifications.
    # They're required to bootstrap the session (hydration, task binding, context).
    "always_available": {
        # Agent/skill invocation for hydration bootstrap
        "Task",
        "Skill",
        "delegate_to_agent",
        "activate_skill",
        # ALL task manager tools - framework infrastructure, not user data
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
        # Gemini short names for task manager
        "create_task",
        "update_task",
        "complete_task",
        "get_task",
        "list_tasks",
        "search_tasks",
        "get_task_tree",
        "get_children",
        "decompose_task",
        # Memory retrieval for context
        "mcp__plugin_aops-core_memory__retrieve_memory",
        "mcp__plugin_aops-core_memory__recall_memory",
        "mcp__plugin_aops-core_memory__search_by_tag",
        # Gemini short names for memory
        "retrieve_memory",
        "recall_memory",
        "search_by_tag",
        # User interaction: must never be blocked (essential for agent-user communication)
        "AskUserQuestion",
        # Meta tools: affect agent behavior but don't modify user files
        # These are always available to allow planning and questioning at any time
        "TodoWrite",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
    },
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
        # Note: memory retrieval and task manager reads are in always_available
        "mcp__plugin_aops-core_memory__list_memories",
        "mcp__plugin_aops-core_memory__check_database_health",
        "mcp__plugin_context7-plugin_context7__resolve-library-id",
        "mcp__plugin_context7-plugin_context7__query-docs",
    },
    # Write tools: modify USER files/state, require task binding and critic approval
    # Note: Task manager tools are in always_available (framework infrastructure)
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
        # Memory mutation (store needs /remember skill routing)
        "mcp__plugin_aops-core_memory__store_memory",
        "mcp__plugin_aops-core_memory__delete_memory",
    },
    # Meta tools: now merged into always_available
    # These affect agent behavior but don't modify user files, so they're
    # always available to allow planning and questioning at any time.
    # Keeping empty set for backwards compatibility with gate requirement lookups.
    "meta": set(),
}

# =============================================================================
# GATE REQUIREMENTS
# =============================================================================
# Which gates must have passed for each tool category to be allowed?
# Gates are checked in order; all listed gates must be in "passed" state.

TOOL_GATE_REQUIREMENTS: Dict[str, List[str]] = {
    # Always available: no gates required (bootstrap tools)
    "always_available": [],
    # Read-only tools: just need hydration
    "read_only": ["hydration"],
    # Meta tools: same as read_only (planning/questioning is safe)
    "meta": ["hydration"],
    # Write tools: need hydration + task binding + critic + custodiet approval
    "write": ["hydration", "task", "critic", "custodiet"],
    # Stop event: need all gates including QA and handover
    "stop": ["hydration", "task", "critic", "custodiet", "qa", "handover"],
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
        "gate_init",  # Initialize gate states from GATE_INITIAL_STATE
    ],
    "UserPromptSubmit": [
        "user_prompt_submit",
        "unified_logger",
        "gate_reset",  # Close gates that re-close on new prompt
    ],
    "PreToolUse": [
        "unified_logger",
        "tool_gate",  # Unified tool gating based on TOOL_GATE_REQUIREMENTS
    ],
    "PostToolUse": [
        "unified_logger",
        "task_binding",
        "accountant",
        "gate_update",  # Open/close gates based on GATE_OPENING_CONDITIONS/GATE_CLOSURE_TRIGGERS
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
    "gate_init",
    "gate_reset",
    "gate_update",
    "user_prompt_submit",
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
    "handover": "warn",  # HANDOVER_GATE_MODE env var (new)
}

# Environment variable names for gate modes
GATE_MODE_ENV_VARS: Dict[str, str] = {
    "hydration": "HYDRATION_GATE_MODE",
    "task": "TASK_GATE_MODE",
    "custodiet": "CUSTODIET_GATE_MODE",
    "critic": "CRITIC_GATE_MODE",
    "qa": "QA_GATE_MODE",
    "handover": "HANDOVER_GATE_MODE",
}


# =============================================================================
# GATE LIFECYCLE: INITIAL STATE
# =============================================================================
# What state does each gate start in at SessionStart?
# "closed" = gate check will fail, tool blocked
# "open" = gate check will pass, tool allowed

GATE_INITIAL_STATE: Dict[str, str] = {
    "hydration": "closed",  # Must hydrate before any work
    "task": "open",  # Must bind a task before writes, but allow planning and answers first
    "critic": "open",  # Must get approval before writes, but allow planning and answers first
    "custodiet": "open",  # Must get compliance check before writes, but allow planning first
    "qa": "closed",  # Must verify before stop
    "handover": "open",  # Starts open; closes on uncommitted changes
}


# =============================================================================
# GATE LIFECYCLE: OPENING CONDITIONS
# =============================================================================
# What triggers each gate to transition from closed → open?
# Each gate has an event type and conditions that must be met.

GATE_OPENING_CONDITIONS: Dict[str, Dict[str, Any]] = {
    "hydration": {
        "event": "PostToolUse",
        "tool_pattern": r"^Task$",
        "subagent_type": "aops-core:prompt-hydrator",
        "output_contains": "HYDRATION RESULT",
        "description": "Opens when hydrator agent completes successfully",
    },
    "task": {
        "event": "PostToolUse",
        "tool_pattern": r"mcp.*task_manager.*(create|claim|update)_task",
        "result_key": "success",
        "result_value": True,
        "description": "Opens when a task is created, claimed, or updated",
    },
    "critic": {
        "event": "PostToolUse",
        "tool_pattern": r"^Task$",
        "subagent_type": "aops-core:critic",
        "output_contains": "APPROVED",
        "description": "Opens when critic agent approves the plan",
    },
    "custodiet": {
        "event": "PostToolUse",
        "tool_pattern": r"^Task$",
        "subagent_type": "aops-core:custodiet",
        "output_contains": "OK",
        "description": "Opens when custodiet agent confirms no ultra vires activity",
    },
    "qa": {
        "event": "PostToolUse",
        "tool_pattern": r"^Task$|^Skill$",
        "subagent_or_skill": ["aops-core:qa", "qa"],
        "description": "Opens when QA verification completes",
    },
    "handover": {
        "event": "PostToolUse",
        "tool_pattern": r"^Skill$",
        "skill_name": "aops-core:handover",
        "description": "Opens when handover skill is invoked with clean repo",
    },
}


# =============================================================================
# GATE LIFECYCLE: CLOSURE TRIGGERS
# =============================================================================
# What causes gates to re-close (transition from open → closed) mid-session?
# This enforces re-approval workflows, e.g., "critic must approve each batch".
# Gates not listed here stay open once opened.

GATE_CLOSURE_TRIGGERS: Dict[str, List[Dict[str, Any]]] = {
    "hydration": [
        {
            "event": "UserPromptSubmit",
            "description": "Re-close on new user prompt to require fresh hydration",
        },
    ],
    "task": [
        {
            "event": "PostToolUse",
            "tool_pattern": r"mcp.*task_manager.*complete_task",
            "result_key": "success",
            "result_value": True,
            "description": "Re-close when task is completed/released",
        },
    ],
    "critic": [
        {
            "event": "UserPromptSubmit",
            "description": "Re-close on new user prompt (new intent = new approval)",
        },
        {
            "event": "PostToolUse",
            "tool_pattern": r"mcp.*task_manager.*complete_task",
            "result_key": "success",
            "result_value": True,
            "description": "Re-close on task change (completed = need new approval)",
        },
    ],
    "custodiet": [
        {
            "event": "UserPromptSubmit",
            "description": "Re-close on new user prompt (fresh compliance check required)",
        },
        {
            "event": "PostToolUse",
            "tool_category": "write",
            "threshold_counter": "tool_calls_since_custodiet",
            "threshold_value": 7,
            "description": "Re-close after N write operations (periodic re-verification)",
        },
    ],
    "handover": [
        {
            "event": "PostToolUse",
            "tool_category": "write",
            "condition": "git_dirty",
            "description": "Re-close when repo has uncommitted changes",
        },
    ],
    # qa: Does not re-close (verified once is sufficient for session)
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


def get_gate_initial_state(gate_name: str) -> str:
    """Get the initial state of a gate at SessionStart.

    Returns 'closed' or 'open'. Defaults to 'closed' for unknown gates.
    """
    return GATE_INITIAL_STATE.get(gate_name, "closed")


def get_gate_opening_condition(gate_name: str) -> Dict[str, Any]:
    """Get the conditions that open a gate.

    Returns dict with event type and conditions, or empty dict if not configured.
    """
    return GATE_OPENING_CONDITIONS.get(gate_name, {})


def get_gate_closure_triggers(gate_name: str) -> List[Dict[str, Any]]:
    """Get the triggers that re-close a gate.

    Returns list of trigger definitions, or empty list if gate doesn't re-close.
    """
    return GATE_CLOSURE_TRIGGERS.get(gate_name, [])


def should_gate_close_on_tool(gate_name: str, tool_name: str, event: str) -> bool:
    """Check if a gate should close based on a tool use.

    Args:
        gate_name: Name of the gate to check
        tool_name: Name of the tool that was used
        event: Event type (e.g., 'PostToolUse')

    Returns:
        True if the gate should transition from open to closed.
    """
    triggers = get_gate_closure_triggers(gate_name)
    if not triggers:
        return False

    tool_category = get_tool_category(tool_name)

    for trigger in triggers:
        if trigger.get("event") != event:
            continue

        # Check tool category match
        if "tool_category" in trigger:
            if trigger["tool_category"] == tool_category:
                return True

        # Check tool pattern match (if specified)
        if "tool_pattern" in trigger:
            import re

            if re.match(trigger["tool_pattern"], tool_name):
                return True

    return False
