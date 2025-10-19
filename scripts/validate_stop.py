#!/usr/bin/env python3
"""
SubagentStop/Stop hook for Claude Code: Workflow chaining validator.

This script logs subagent workflow transitions for debugging and will eventually
be used to chain subagent workflows together in the modular agent framework.

Exit codes:
    0: Success (continue normal execution)
    1: Warning (logged but execution continues)
    2: Error (execution may be affected)

Input: JSON with hook event data from Claude Code
Output: JSON response for Claude Code hooks system
"""

import datetime
import json
import sys
from pathlib import Path
from typing import Any


def get_repo_root() -> Path:
    """Find the repository root (parent of bot/ submodule)."""
    # This script is at bot/validate_tool.py
    # Repo root is one level up
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def log_to_debug_file(
    hook_event: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
) -> None:
    """
    Log hook invocation to a timestamped debug file.

    Args:
        hook_event: Name of the hook event (SubagentStop, Stop)
        input_data: Input data received from Claude Code
        output_data: Output data being sent back to Claude Code
    """
    _repo_root = get_repo_root()
    # log_dir = repo_root / "data" / "logs" / "hooks"
    # log_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path("/tmp")

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S_%f")
    log_file = log_dir / f"{hook_event.lower()}_{timestamp}.json"

    debug_data = {
        "hook_event": hook_event,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "input": input_data,
        "output": output_data,
    }

    with log_file.open("w") as f:
        json.dump(debug_data, f, indent=2)
        f.write("\n")


def extract_context_info(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract relevant context information from hook input.

    Args:
        input_data: Input data from Claude Code hook

    Returns:
        Dictionary of extracted context information
    """
    context = {
        "hook_event": input_data.get("hook_event", "unknown"),
        "subagent": input_data.get("subagent", "unknown"),
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "argv": input_data.get("argv", []),
    }

    # Extract subagent-specific information if available
    if "subagent_result" in input_data:
        context["subagent_result"] = input_data["subagent_result"]

    if "conversation_context" in input_data:
        context["conversation_context"] = input_data["conversation_context"]

    return context


def validate_workflow_transition(
    _hook_event: str, _context: dict[str, Any]
) -> tuple[bool, str | None]:
    """
    Validate workflow transition logic (placeholder for future implementation).

    This function will eventually enforce workflow chaining rules such as:
    - Required pre-conditions for subagent invocation
    - Post-conditions after subagent completion
    - Workflow state management
    - Inter-agent communication patterns

    Args:
        hook_event: Name of the hook event
        context: Extracted context information

    Returns:
        (is_valid: bool, error_message: str | None)
    """
    # Placeholder for future workflow validation logic
    # For now, always return success
    return (True, None)


def main() -> int:
    """Main hook entry point."""
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        error_msg = f"Error: Invalid JSON input: {e}"
        print(error_msg, file=sys.stderr)
        return 2

    # Add command-line arguments to input data for debugging
    input_data["argv"] = sys.argv

    # Determine which hook triggered this script
    hook_event = input_data.get("hook_event", "Unknown")
    if len(sys.argv) > 1:
        # Hook event might be passed as argument
        hook_event = (
            sys.argv[1] if sys.argv[1] in ["SubagentStop", "Stop"] else hook_event
        )

    # Extract context information
    context = extract_context_info(input_data)

    # Validate workflow transition (future: enforce chaining rules)
    is_valid, error_message = validate_workflow_transition(hook_event, context)

    # Prepare output for Claude Code
    # Stop hook schema per https://gist.github.com/FrancisBourre/50dca37124ecc43eaf08328cdcccdb34
    # Output schema:
    # {
    #   "decision": "block" | null,  // optional
    #   "reason": "string"           // required if decision = "block"
    # }
    # Exit code 2 also blocks the stop event
    output = {}

    if not is_valid and error_message:
        # Block the stop event
        output["decision"] = "block"
        output["reason"] = error_message
    # Otherwise, return empty {} to allow (default behavior)

    # Log to debug file
    try:
        log_to_debug_file(hook_event, input_data, output)
    except Exception as e:
        # Don't fail if logging fails - just print to stderr
        print(f"Warning: Failed to write debug log: {e}", file=sys.stderr)

    # Output JSON to stdout for Claude Code
    print(json.dumps(output))

    # Print human-readable info to stderr for user visibility
    print(f"✓ {hook_event} hook executed", file=sys.stderr)
    print(f"  Subagent: {context.get('subagent', 'unknown')}", file=sys.stderr)
    print(f"  Timestamp: {context.get('timestamp', 'unknown')}", file=sys.stderr)
    print(
        f"  Log: data/logs/hooks/{hook_event.lower()}_*.json",
        file=sys.stderr,
    )

    return 0 if is_valid else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Warning: Unknown error: {e}", file=sys.stderr)
        sys.exit(2)
