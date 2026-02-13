"""Hydration instruction builder - builds context for prompt hydration.

Moved from hooks/user_prompt_submit.py to fix dependency direction.
Gates (lib/gates/) can now import this without circular dependencies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.file_index import get_formatted_relevant_paths
from lib.hook_utils import (
    cleanup_old_temp_files as _cleanup_temp,
)
from lib.hook_utils import (
    get_hook_temp_dir,
)
from lib.hook_utils import (
    write_temp_file as _write_temp,
)
from lib.session_paths import get_gate_file_path
from lib.hydration.context_loaders import (
    get_task_work_state,
    load_environment_variables_context,
    load_framework_paths,
    load_mcp_tools_context,
    load_project_context_index,
    load_project_paths_context,
    load_project_rules,
    load_scripts_index,
    load_skills_index,
    load_workflows_index,
)
from lib.session_reader import extract_router_context
from lib.session_state import SessionState
from lib.template_loader import load_template

# Temp directory category
TEMP_CATEGORY = "hydrator"
FILE_PREFIX = "hydrate_"

# Paths relative to hooks/ (for template loading)
HOOK_DIR = Path(__file__).parent.parent.parent / "hooks"
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"


def get_hydration_temp_dir(input_data: dict[str, Any] | None = None) -> Path:
    """Get the temporary directory for hydration context."""
    return get_hook_temp_dir(TEMP_CATEGORY, input_data)


def cleanup_old_temp_files(input_data: dict[str, Any] | None = None) -> None:
    """Delete temp files older than 1 hour."""
    try:
        temp_dir = get_hydration_temp_dir(input_data)
        _cleanup_temp(temp_dir, FILE_PREFIX)
    except RuntimeError:
        pass


def write_temp_file(content: str, input_data: dict[str, Any] | None = None) -> Path:
    """Write content to temp file, return path."""
    temp_dir = get_hydration_temp_dir(input_data)
    _cleanup_temp(temp_dir, FILE_PREFIX)
    session_id = input_data.get("session_id") if input_data else None
    return _write_temp(content, temp_dir, FILE_PREFIX, session_id=session_id)


def build_hydration_instruction(
    session_id: str,
    prompt: str,
    transcript_path: str | None = None,
    state: SessionState | None = None,
) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Writes full context to temp file, returns short instruction with file path.

    Args:
        session_id: Claude Code session ID for state isolation
        prompt: The user's original prompt
        transcript_path: Path to session transcript for context extraction
        state: Optional existing SessionState object

    Returns:
        Short instruction string (<300 tokens) with temp file path

    Raises:
        IOError: If temp file write fails (fail-fast per AXIOM #7)
    """
    # Build input_data for hook_utils resolution
    input_data = {"session_id": session_id}
    if transcript_path:
        input_data["transcript_path"] = transcript_path

    # Cleanup old temp files first
    cleanup_old_temp_files(input_data)

    # Extract session context from transcript
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                session_context = f"\n\n{ctx}"
        except FileNotFoundError:
            pass
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(
                f"Context extraction failed (degrading gracefully): {type(e).__name__}: {e}"
            )

    # Load all context components
    framework_paths = load_framework_paths()
    mcp_tools = load_mcp_tools_context()
    env_vars = load_environment_variables_context()
    project_paths = load_project_paths_context()
    workflows_index = load_workflows_index(prompt)
    skills_index = load_skills_index()
    scripts_index = load_scripts_index()
    project_rules = load_project_rules()
    task_state = get_task_work_state()
    relevant_files = get_formatted_relevant_paths(prompt, max_files=10)
    project_context_index = load_project_context_index()

    # Build full context for temp file
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        framework_paths=framework_paths,
        mcp_tools=mcp_tools,
        env_vars=env_vars,
        project_paths=project_paths,
        project_context_index=project_context_index,
        project_rules=project_rules,
        relevant_files=relevant_files,
        workflows_index=workflows_index,
        skills_index=skills_index,
        scripts_index=scripts_index,
        task_state=task_state,
    )

    # Write to predictable gate file path (with temp cleanup for migration)
    temp_path = get_gate_file_path("hydration", session_id, input_data)
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(full_context, encoding="utf-8")

    # Update session state
    if state is None:
        state = SessionState.load(session_id)
        should_save = True
    else:
        should_save = False

    # Increment global turn counter
    state.global_turn_count += 1

    # Set temp path in metrics
    gate = state.get_gate("hydration")
    gate.metrics["temp_path"] = str(temp_path)
    gate.metrics["original_prompt"] = prompt

    # Close gate (pending hydration)
    state.close_gate("hydration")

    if hasattr(state, "state") and "hydration_pending" in state.state:
        state.state["hydration_pending"] = True

    if should_save:
        state.save()

    # Truncate prompt for description
    prompt_preview = prompt[:80].replace("\n", " ").strip()
    if len(prompt) > 80:
        prompt_preview += "..."

    # Build short instruction with file path
    instruction_template = load_template(INSTRUCTION_TEMPLATE_FILE)
    instruction = instruction_template.format(
        prompt_preview=prompt_preview,
        temp_path=str(temp_path),
    )

    return instruction
