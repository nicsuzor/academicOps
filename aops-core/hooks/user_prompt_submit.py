#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

This is a thin wrapper that re-exports from lib/hydration/ for backwards
compatibility. The actual implementation has moved to lib/ to fix circular
dependency issues where lib/gates/ was importing from hooks/.

Exit codes:
    0: Success
    1: Infrastructure failure (temp file write failed - fail-fast)
"""

from pathlib import Path

from lib.file_index import get_formatted_relevant_paths
from lib.hook_utils import write_temp_file as _write_temp
from lib.session_reader import extract_router_context
from lib.session_state import SessionState
from lib.template_loader import load_template

# Re-export main functions from lib/hydration/
from lib.hydration import build_hydration_instruction, should_skip_hydration

# Re-export context loaders for backwards compatibility
from lib.hydration.context_loaders import (
    MONITORED_ENV_VARS,
    get_task_work_state,
    load_axioms,
    load_environment_variables_context,
    load_framework_paths,
    load_heuristics,
    load_mcp_tools_context,
    load_project_context_index,
    load_project_paths_context,
    load_project_rules,
    load_scripts_index,
    load_skills_index,
    load_tools_index,
    load_workflows_index,
)

# Re-export builder utilities
from lib.hydration.builder import (
    TEMP_CATEGORY,
    FILE_PREFIX,
    cleanup_old_temp_files,
    get_hydration_temp_dir,
    write_temp_file,
)

# Paths (kept for backwards compatibility)
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"

# Intent envelope max length
INTENT_MAX_LENGTH = 500


def write_initial_hydrator_state(
    session_id: str, prompt: str, hydration_pending: bool = True
) -> None:
    """Write initial hydrator state with pending workflow.

    Called after processing prompt to set hydration pending flag.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: User's original prompt
        hydration_pending: Whether hydration gate should block until hydrator invoked
    """
    state = SessionState.load(session_id)

    # Increment global turn counter
    state.global_turn_count += 1

    if hydration_pending:
        # pending = close gate
        state.close_gate("hydration")
        state.get_gate("hydration").metrics["original_prompt"] = prompt
        # Also set legacy flag for compatibility if needed (though we're moving away from it)
        if hasattr(state, "state") and "hydration_pending" in state.state:
            state.state["hydration_pending"] = True
    else:
        # not pending = open gate
        state.open_gate("hydration")
        if hasattr(state, "state") and "hydration_pending" in state.state:
            del state.state["hydration_pending"]

    state.save()


# Expose all public symbols
__all__ = [
    # Main functions
    "build_hydration_instruction",
    "should_skip_hydration",
    "write_initial_hydrator_state",
    "extract_router_context",
    # Context loaders
    "load_framework_paths",
    "load_tools_index",
    "load_mcp_tools_context",
    "load_environment_variables_context",
    "load_project_paths_context",
    "load_workflows_index",
    "load_project_context_index",
    "load_axioms",
    "load_heuristics",
    "load_skills_index",
    "load_scripts_index",
    "load_project_rules",
    "get_task_work_state",
    # Builder utilities
    "get_hydration_temp_dir",
    "cleanup_old_temp_files",
    "write_temp_file",
    # Constants
    "TEMP_CATEGORY",
    "FILE_PREFIX",
    "MONITORED_ENV_VARS",
    "HOOK_DIR",
    "CONTEXT_TEMPLATE_FILE",
    "INSTRUCTION_TEMPLATE_FILE",
    "INTENT_MAX_LENGTH",
    # Backward-compatible utilities for tests
    "load_template",
    "get_formatted_relevant_paths",
    "_write_temp",
]
