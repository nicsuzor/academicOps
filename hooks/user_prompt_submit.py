#!/usr/bin/env python3
"""
UserPromptSubmit hook for Claude Code.

Injects prompt-hydrator instruction to enrich every prompt with context
and workflow guidance.

Exit codes:
    0: Success (always continues)
"""

import json
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file
from lib.session_reader import extract_router_context

# Paths (absolute, fail-fast if missing)
HOOK_DIR = Path(__file__).parent
TEMPLATE_FILE = HOOK_DIR / "templates" / "prompt-hydration-instruction.md"


def load_instruction_template() -> str:
    """Load instruction template from file, extracting content after --- separator."""
    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_FILE}")

    content = TEMPLATE_FILE.read_text()

    # Extract content after the --- separator (skip frontmatter/docs)
    if "\n---\n" in content:
        content = content.split("\n---\n", 1)[1]

    return content.strip()


def build_hydration_instruction(prompt: str, transcript_path: str | None = None) -> str:
    """
    Build instruction for main agent to invoke prompt-hydrator.

    Args:
        prompt: The user's original prompt
        transcript_path: Path to session transcript for context extraction

    Returns:
        Instruction string to inject into agent context
    """
    # Truncate prompt for description (avoid huge strings)
    prompt_preview = prompt[:80].replace("\n", " ").strip()
    if len(prompt) > 80:
        prompt_preview += "..."

    # Escape quotes in prompt for embedding
    escaped_prompt = prompt.replace('"', '\\"').replace("\n", "\\n")

    # Extract session context from transcript
    session_context = ""
    if transcript_path:
        try:
            ctx = extract_router_context(Path(transcript_path))
            if ctx:
                # Escape for embedding in prompt string
                session_context = "\\n\\n## Session Context\\n\\n" + ctx.replace('"', '\\"').replace("\n", "\\n")
        except Exception:
            pass  # Graceful degradation - proceed without context

    # Load template and substitute placeholders
    template = load_instruction_template()
    instruction = template.format(
        prompt_preview=prompt_preview,
        escaped_prompt=escaped_prompt,
        session_context=session_context,
    )

    return instruction


def main():
    """Main hook entry point - injects hydration instruction."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
        input_data["argv"] = sys.argv
    except Exception:
        # If no stdin or parsing fails, continue with empty input
        pass

    # Extract user prompt and transcript path
    prompt = input_data.get("prompt", "")
    transcript_path = input_data.get("transcript_path")

    # Build hydration instruction with session context
    if prompt:
        hydration_instruction = build_hydration_instruction(prompt, transcript_path)
    else:
        hydration_instruction = ""

    # Build output with hydration context
    output_data: dict[str, Any] = {}
    if hydration_instruction:
        output_data = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": hydration_instruction,
            }
        }

    # Debug log hook execution
    safe_log_to_debug_file("UserPromptSubmit", input_data, output_data)

    # Output JSON
    print(json.dumps(output_data))

    sys.exit(0)


if __name__ == "__main__":
    main()
