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
from hooks.hook_logger import log_hook_event
from lib.paths import get_aops_root
from lib.session_reader import extract_router_context
from lib.session_state import set_hydration_pending, clear_hydration_pending

# Paths
HOOK_DIR = Path(__file__).parent
CONTEXT_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydrator-context.md"
INSTRUCTION_TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"
TEMP_DIR = Path("/tmp/claude-hydrator")

# Cleanup threshold: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60

# Intent envelope max length
INTENT_MAX_LENGTH = 500


def load_framework_paths() -> str:
    """Load the Resolved Paths section from FRAMEWORK.md.

    Returns just the path table, not the full file.
    """
    aops_root = get_aops_root()
    framework_path = aops_root / "FRAMEWORK.md"

    if not framework_path.exists():
        return "(FRAMEWORK.md not found - use $AOPS/ and $ACA_DATA/ prefixes)"

    content = framework_path.read_text()

    # Extract the "Resolved Paths" section
    if "## Resolved Paths" in content:
        start = content.index("## Resolved Paths")
        # Find next section or end
        rest = content[start:]
        if "\n## " in rest[10:]:  # Skip the header we just found
            end = rest.index("\n## ", 10)
            return rest[:end].strip()
        return rest.strip()

    return "(Path table not found in FRAMEWORK.md)"


def get_session_id() -> str:
    """Get session ID from environment.

    Returns CLAUDE_SESSION_ID if set, raises ValueError otherwise.
    Session ID is required for state isolation.
    """
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id:
        raise ValueError("CLAUDE_SESSION_ID not set - cannot save session state")
    return session_id


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
    if hydration_pending:
        set_hydration_pending(session_id, prompt)
    else:
        clear_hydration_pending(session_id)


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


def build_hydration_instruction(
    session_id: str, prompt: str, transcript_path: str | None = None
) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Writes full context to temp file, returns short instruction with file path.

    Args:
        session_id: Claude Code session ID for state isolation
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

    # Load framework paths from FRAMEWORK.md (DRY - single source of truth)
    framework_paths = load_framework_paths()

    # Build full context for temp file
    context_template = load_template(CONTEXT_TEMPLATE_FILE)
    full_context = context_template.format(
        prompt=prompt,
        session_context=session_context,
        framework_paths=framework_paths,
    )

    # Write to temp file (raises IOError on failure - fail-fast)
    temp_path = write_temp_file(full_context)

    # Write initial hydrator state for downstream gates
    write_initial_hydrator_state(session_id, prompt)

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
    - Agent/task completion notifications (<agent-notification>, <task-notification>)
    - Skill invocations (prompts starting with '/')
    - User ignore shortcut (prompts starting with '.')
    """
    prompt_stripped = prompt.strip()
    # Agent/task completion notifications from background Task agents
    if prompt_stripped.startswith("<agent-notification>"):
        return True
    if prompt_stripped.startswith("<task-notification>"):
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
    session_id = input_data.get("session_id", "")

    # Require session_id for state isolation
    if not session_id:
        # Fail gracefully - don't block agent if session_id missing
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",
            }
        }
        safe_log_to_debug_file(
            "UserPromptSubmit", input_data, {"skipped": "no_session_id"}
        )
        print(json.dumps(output_data))
        sys.exit(0)

    # Skip hydration for system messages, skill invocations, and user ignore shortcut
    if should_skip_hydration(prompt):
        # Write state with hydration_pending=False so gate doesn't block
        write_initial_hydrator_state(session_id, prompt, hydration_pending=False)
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",  # No hydration needed
            }
        }
        safe_log_to_debug_file(
            "UserPromptSubmit", input_data, {"skipped": "system_message"}
        )
        log_hook_event(
            session_id=session_id,
            hook_event="UserPromptSubmit",
            input_data=input_data,
            output_data=output_data,
            exit_code=0,
        )
        print(json.dumps(output_data))
        sys.exit(0)

    # Build hydration instruction (writes temp file)
    output_data: dict[str, Any] = {}
    exit_code = 0

    if prompt:
        try:
            hydration_instruction = build_hydration_instruction(
                session_id, prompt, transcript_path
            )
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

    # Log to hooks JSONL for transcript visibility
    log_hook_event(
        session_id=session_id,
        hook_event="UserPromptSubmit",
        input_data=input_data,
        output_data=output_data,
        exit_code=exit_code,
    )

    # Output JSON
    print(json.dumps(output_data))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
