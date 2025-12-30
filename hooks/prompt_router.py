#!/usr/bin/env python3
"""Prompt Intent Router hook for Claude Code.

Writes full router context (template + session guidance + prompt) to temp file.
Tells main agent to invoke intent-router subagent with that file path.

The intent-router (Haiku) enforces framework rules by providing
focused, task-specific guidance to the main agent.

Slash commands are handled by Claude Code directly - we skip them.

Exit codes:
    0: Success (always continues)
"""

import contextlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from hooks.hook_logger import log_hook_event

# Framing version for measurement
FRAMING_VERSION = "v9-tempfile-router"

# Slash command pattern
SLASH_COMMAND_PATTERN = re.compile(r"^/(\w+)")

# Paths
AOPS = Path(os.environ.get("AOPS", Path(__file__).parent.parent))
ACA_DATA = Path(os.environ.get("ACA_DATA", Path.home() / ".claude"))
INTENT_ROUTER_TEMPLATE = AOPS / "hooks" / "prompts" / "intent-router.md"
SESSION_GUIDANCE_FILE = ACA_DATA / ".router-config.md"
TEMP_DIR = Path(tempfile.gettempdir()) / "claude-router"


def load_router_template() -> str:
    """Load intent router prompt template, stripped of frontmatter."""
    if not INTENT_ROUTER_TEMPLATE.exists():
        return "# Intent Router\n\n{session_context}\n\n## User Prompt\n\n{prompt}"

    content = INTENT_ROUTER_TEMPLATE.read_text()

    # Strip frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()

    return content


def load_session_guidance() -> str:
    """Load session-level guidance from config file if present."""
    if SESSION_GUIDANCE_FILE.exists():
        return SESSION_GUIDANCE_FILE.read_text()
    return ""


def build_router_context(
    prompt: str,
    session_guidance: str = "",
    per_prompt_context: str = "",
) -> str:
    """Build complete context for intent router.

    Args:
        prompt: User's prompt text
        session_guidance: Persistent session-level config
        per_prompt_context: Per-prompt context from other sources

    Returns:
        Complete context string with template filled in
    """
    template = load_router_template()

    # Build session context section
    session_context_parts = []
    if session_guidance:
        session_context_parts.append(f"## Session Guidance\n\n{session_guidance}")
    if per_prompt_context:
        session_context_parts.append(f"## Additional Context\n\n{per_prompt_context}")

    session_context = "\n\n".join(session_context_parts)

    return template.format(session_context=session_context, prompt=prompt)


def write_temp_file(content: str) -> Path:
    """Write content to temp file, return path."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = TEMP_DIR / f"router_{timestamp}.md"
    filepath.write_text(content)
    return filepath


def main():
    """Main hook entry point."""
    input_data: dict[str, Any] = {}
    with contextlib.suppress(Exception):
        input_data = json.load(sys.stdin)

    prompt = input_data.get("prompt", "")

    # Slash commands - Claude Code handles, we skip
    if prompt and SLASH_COMMAND_PATTERN.match(prompt):
        output: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "",
                "framingVersion": FRAMING_VERSION,
            }
        }
        print(json.dumps(output))
        sys.exit(0)

    # Load context sources
    session_guidance = load_session_guidance()
    per_prompt_context = input_data.get("additional_context", "")

    # Build complete router context and write to temp file
    context = build_router_context(
        prompt=prompt,
        session_guidance=session_guidance,
        per_prompt_context=per_prompt_context,
    )
    temp_path = write_temp_file(context)

    # Instruct main agent to invoke router with file path
    additional_context = f"""**ROUTE FIRST**: Spawn the intent-router to get structured guidance for this task.

Task(subagent_type="intent-router", model="haiku", prompt="Read {temp_path} and return guidance")

Follow the router's structured output - it provides tailored steps, skill to invoke, and DO NOTs."""

    hook_output: dict[str, Any] = {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": additional_context,
        "framingVersion": FRAMING_VERSION,
        "routerContextFile": str(temp_path),
    }

    output = {"hookSpecificOutput": hook_output}

    # Log
    session_id = input_data.get("session_id", "unknown")
    log_hook_event(
        session_id=session_id,
        hook_event="UserPromptSubmit",
        input_data=input_data,
        output_data=output,
        exit_code=0,
    )

    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
