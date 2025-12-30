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
FRAMING_VERSION = "v10-prompt-writer"

# Slash command pattern
SLASH_COMMAND_PATTERN = re.compile(r"^/(\w+)")

# Paths
AOPS = Path(os.environ.get("AOPS", Path(__file__).parent.parent))
ACA_DATA = Path(os.environ.get("ACA_DATA", Path.home() / ".claude"))
PROMPT_WRITER_AGENT = AOPS / "agents" / "prompt-writer.md"
SESSION_GUIDANCE_FILE = ACA_DATA / ".router-config.md"
TEMP_DIR = Path(tempfile.gettempdir()) / "claude-router"


GUIDANCE_INSTRUCTIONS = """# Prompt Enrichment (Guidance Format)

Classify the task and return 2-5 lines of guidance. Do NOT investigate, ask questions, or write files.

## Classification Table

| Pattern | Type | Guidance |
|---------|------|----------|
| skills/, hooks/, AXIOMS, HEURISTICS, framework | Framework | Skill("framework"), Plan Mode, TodoWrite |
| error, bug, broken, debug | Debug | VERIFY STATE FIRST, TodoWrite, cite evidence |
| how, what, where, explain, "?" | Question | Answer then STOP, no implementing |
| implement, build, create, refactor | Multi-step | TodoWrite, commit after logical units |
| pytest, TDD, Python, test | Python | Skill("python-dev"), tests first |
| (simple, single action) | Simple | Just do it |

## Output Format

Return ONLY 2-5 lines like:
```
[Skill to invoke if any]
[Structural requirements: TodoWrite, Plan Mode, etc.]
[Key reminder for this task type]
DO NOT: [failure mode to avoid]
```

Example for "debug this error":
```
VERIFY STATE FIRST. Check actual state before hypothesizing.
Use TodoWrite verification checklist.
Cite evidence for any conclusions.
DO NOT: Guess at causes without checking logs/state.
```
"""


def build_enrichment_request(
    prompt: str,
    session_guidance: str = "",
    per_prompt_context: str = "",
) -> str:
    """Build enrichment request for prompt-writer agent.

    Args:
        prompt: User's prompt text
        session_guidance: Persistent session-level config
        per_prompt_context: Per-prompt context from other sources

    Returns:
        Formatted request string for prompt-writer agent
    """
    parts = [GUIDANCE_INSTRUCTIONS, ""]

    if session_guidance:
        parts.append("## Session Guidance")
        parts.append("")
        parts.append(session_guidance)
        parts.append("")

    if per_prompt_context:
        parts.append("## Additional Context")
        parts.append("")
        parts.append(per_prompt_context)
        parts.append("")

    parts.append("## User Prompt")
    parts.append("")
    parts.append(prompt)

    return "\n".join(parts)


def load_session_guidance() -> str:
    """Load session-level guidance from config file if present."""
    if SESSION_GUIDANCE_FILE.exists():
        return SESSION_GUIDANCE_FILE.read_text()
    return ""




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

    # Build enrichment request and write to temp file
    request = build_enrichment_request(
        prompt=prompt,
        session_guidance=session_guidance,
        per_prompt_context=per_prompt_context,
    )
    temp_path = write_temp_file(request)

    # Instruct main agent to invoke a classifier for guidance
    additional_context = f"""**ENRICH FIRST**: Spawn classifier to get structured guidance for this task.

Task(subagent_type="general-purpose", model="haiku", prompt="Read {temp_path} and follow the instructions to return guidance. Output ONLY 2-5 lines of guidance, no other text.")

Follow the guidance output - it provides skill to invoke, structural requirements, and DO NOTs."""

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
