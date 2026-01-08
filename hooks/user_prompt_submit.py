#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Writes hydration context to temp file for token efficiency.
Returns short instruction telling main agent to spawn prompt-hydrator
with the temp file path.

Exit codes:
    0: Success
    1: Infrastructure failure (temp file write failed - fail-fast)
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file
from lib.session_reader import extract_router_context
from lib.session_state import HydratorState, save_hydrator_state

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"
TEMP_DIR = Path("/tmp/claude-hydrator")

# Cleanup threshold: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60

# Intent envelope max length
INTENT_MAX_LENGTH = 500


def get_cwd() -> str:
    """Get current working directory from environment.

    Returns CLAUDE_CWD if set, otherwise os.getcwd().
    """
    return os.environ.get("CLAUDE_CWD", os.getcwd())


def write_initial_hydrator_state(prompt: str) -> None:
    """Write initial hydrator state with pending workflow.

    Called after processing prompt to persist intent_envelope for
    downstream gates (custodiet, skill monitor).

    Args:
        prompt: User's original prompt (will be truncated for intent)
    """
    cwd = get_cwd()

    # Truncate prompt for intent_envelope
    intent = prompt[:INTENT_MAX_LENGTH]
    if len(prompt) > INTENT_MAX_LENGTH:
        intent = intent.rsplit(" ", 1)[0] + "..."  # Break at word boundary

    state: HydratorState = {
        "last_hydration_ts": time.time(),
        "declared_workflow": {
            "gate": "pending",
            "pre_work": "pending",
            "approach": "pending",
        },
        "active_skill": "",  # To be filled by prompt-hydrator
        "intent_envelope": intent,
        "guardrails": [],  # To be filled by prompt-hydrator
    }

    save_hydrator_state(cwd, state)


def cleanup_old_temp_files() -> None:
    """Delete temp files older than 1 hour.

    Called on each hook invocation to prevent disk accumulation.
    """
    if not TEMP_DIR.exists():
        return

    cutoff = time.time() - CLEANUP_AGE_SECONDS
    for f in TEMP_DIR.glob("hydrate_*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
        except OSError:
            pass  # Ignore cleanup errors


def load_template(template_path: Path) -> str:
    """Load template from file, extracting content after --- separator."""
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    content = template_path.read_text()

    # Extract content after the --- separator (skip frontmatter/docs)
    if "\n---\n" in content:
        content = content.split("\n---\n", 1)[1]

    return content.strip()


def write_temp_file(content: str) -> Path:
    """Write content to temp file, return path.

    Raises:
        IOError: If temp file cannot be written (fail-fast)
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Use NamedTemporaryFile for unique names and proper handling
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="hydrate_",
        suffix=".md",
        dir=TEMP_DIR,
        delete=False,
    ) as f:
        f.write(content)
        return Path(f.name)


def build_hydration_instruction(prompt: str, transcript_path: str | None = None) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Writes full context to temp file, returns short instruction with file path.

    Args:
        prompt: The user's original prompt
        transcript_path: Path to session transcript for context extraction

    Returns:
        Short instruction string (<300 tokens) with temp file path

    Raises:
        IOError: If temp file write fails (fail-fast per AXIOM #7)
    """
    # Cleanup old temp files first
    cleanup_old_temp_files()

    # Extract session context from transcript
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                # ctx already includes "## Session Context" header
                session_context = f"\n\n{ctx}"
        except Exception:
            pass  # Graceful degradation for context gathering only

    # Build full context for temp file
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
    )

    # Write to temp file (raises IOError on failure - fail-fast)
    temp_path = write_temp_file(full_context)

    # Write initial hydrator state for downstream gates
    write_initial_hydrator_state(prompt)

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


def should_skip_hydration(prompt: str) -> bool:
    """Check if prompt should skip hydration.

    Returns True for:
    - Agent completion notifications (<agent-notification>)
    - Skill invocations (prompts starting with '/')
    - User ignore shortcut (prompts starting with '.')
    """
    prompt_stripped = prompt.strip()
    # Agent completion notifications from background Task agents
    if prompt_stripped.startswith("<agent-notification>"):
        return True
    # Skill invocations - already have instructions, don't need routing
    if prompt_stripped.startswith("/"):
        return True
    # User ignore shortcut - user explicitly wants no hydration
    if prompt_stripped.startswith("."):
        return True
    return False


def main():
    """Main hook entry point - writes context to temp file, returns short instruction."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        pass

    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")

    # Skip hydration for system messages, skill invocations, and user ignore shortcut
    if should_skip_hydration(prompt):
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",  # No hydration needed
            }
        }
        safe_log_to_debug_file(
            "UserPromptSubmit", input_data, {"skipped": "system_message"}
        )
        print(json.dumps(output_data))
        sys.exit(0)

    # Build hydration instruction (writes temp file)
    output_data: dict[str, Any] = {}
    exit_code = 0

    if prompt:
        try:
            hydration_instruction = build_hydration_instruction(prompt, transcript_path)
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": hydration_instruction,
                }
            }
        except (IOError, OSError) as e:
            # Fail-fast on infrastructure errors
            output_data = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "error": f"Temp file write failed: {e}",
                }
            }
            exit_code = 1

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output JSON
    print(json.dumps(output_data))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
