#!/usr/bin/env python3
"""
Gemini-specific UserPromptSubmit (BeforeAgent) hook.

Reuses Claude's context building but returns Gemini-compatible instructions.
Key difference: No Task() subagent - tells agent to read temp file directly.

Exit codes:
    0: Success
    1: Infrastructure failure (temp file write failed - fail-fast)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

# Add aops-core and hooks directory to path for imports
AOPS_ROOT = Path(os.getenv("AOPS", ""))
if AOPS_ROOT:
    AOPS_CORE = AOPS_ROOT / "aops-core"
    HOOKS_DIR = AOPS_CORE / "hooks"
    # Add both directories - hooks dir first for hook_debug imports
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    if str(AOPS_CORE) not in sys.path:
        sys.path.insert(0, str(AOPS_CORE))

# Import shared functions from Claude hook
from hooks.user_prompt_submit import (
    cleanup_old_temp_files,
    write_temp_file,
    load_framework_paths,
    load_workflows_index,
    load_skills_index,
    load_axioms,
    load_heuristics,
    get_task_work_state,
    get_formatted_relevant_paths,
    should_skip_hydration,
    write_initial_hydrator_state,
    clear_reflection_output,
    CONTEXT_TEMPLATE_FILE,
)
from hooks.hook_logger import log_hook_event


from lib.session_reader import extract_router_context
from lib.template_loader import load_template


def safe_log_to_debug_file(event: str, input_data: Any, output_data: Any) -> None:
    """No-op debug logging stub (hook_debug module removed)."""
    pass


# Gemini-specific paths
HOOK_DIR = Path(__file__).parent
GEMINI_INSTRUCTION_TEMPLATE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"


def build_gemini_hydration_instruction(
    session_id: str, prompt: str, transcript_path: str | None = None
) -> str:
    """
    Build Gemini-compatible hydration instruction.

    Same as Claude version but uses Gemini template (no Task subagent).
    """
    # Cleanup old temp files first
    cleanup_old_temp_files()

    # Extract session context from transcript
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                session_context = f"\n\n{ctx}"
        except FileNotFoundError:
            pass
        except Exception:
            pass

    # Load framework context (reuse Claude's functions)
    framework_paths = load_framework_paths()
    workflows_index = load_workflows_index()
    skills_index = load_skills_index()
    axioms = load_axioms()
    heuristics = load_heuristics()
    task_state = get_task_work_state()
    relevant_files = get_formatted_relevant_paths(prompt, max_files=10)

    # Build full context for temp file (same as Claude)
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        framework_paths=framework_paths,
        workflows_index=workflows_index,
        skills_index=skills_index,
        axioms=axioms,
        heuristics=heuristics,
        task_state=task_state,
        relevant_files=relevant_files,
    )

    # Write to temp file
    temp_path = write_temp_file(full_context)

    # Write hydrator state for downstream gates
    # For Gemini, hydration is "complete" when we return additionalContext
    # (no separate Task subagent like Claude uses)
    write_initial_hydrator_state(session_id, prompt, hydration_pending=False)

    # Truncate prompt for preview
    prompt_preview = prompt[:80].replace("\n", " ").strip()
    if len(prompt) > 80:
        prompt_preview += "..."

    # Build Gemini-specific instruction (no Task subagent)
    instruction_template = load_template(GEMINI_INSTRUCTION_TEMPLATE)
    instruction = instruction_template.format(
        prompt_preview=prompt_preview,
        temp_path=str(temp_path),
    )

    return instruction


def main():
    """Main entry point for Gemini BeforeAgent hook."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")
    session_id = input_data.get("session_id", "")

    # Require session_id for state isolation
    if not session_id:
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "BeforeAgent",
                "additionalContext": "",
            }
        }
        safe_log_to_debug_file("BeforeAgent", input_data, {"skipped": "no_session_id"})
        print(json.dumps(output_data))
        sys.exit(0)

    # Clear reflection tracking flag for new user prompt
    clear_reflection_output(session_id)

    # Skip hydration for system messages, skill invocations, and user ignore shortcut
    if should_skip_hydration(prompt):
        write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "BeforeAgent",
                "additionalContext": "",
            }
        }
        safe_log_to_debug_file("BeforeAgent", input_data, {"skipped": "system_message"})
        log_hook_event(
            session_id=session_id,
            hook_event="BeforeAgent",
            input_data=input_data,
            output_data=output_data,
            exit_code=0,
        )
        print(json.dumps(output_data))
        sys.exit(0)

    # Build Gemini-specific hydration instruction
    output_data: dict[str, Any] = {}
    exit_code = 0

    if prompt:
        try:
            hydration_instruction = build_gemini_hydration_instruction(
                session_id, prompt, transcript_path
            )
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "BeforeAgent",
                    "additionalContext": hydration_instruction,
                }
            }
        except (IOError, OSError) as e:
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "BeforeAgent",
                    "error": f"Temp file write failed: {e}",
                }
            }
            exit_code = 1

    # Debug log
    safe_log_to_debug_file("BeforeAgent", input_data, output_data)

    # Log to hooks JSONL
    log_hook_event(
        session_id=session_id,
        hook_event="BeforeAgent",
        input_data=input_data,
        output_data=output_data,
        exit_code=exit_code,
    )

    # Output JSON
    print(json.dumps(output_data))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
