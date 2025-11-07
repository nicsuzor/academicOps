#!/usr/bin/env python3
"""
SubagentStop/Stop hook for Claude Code: Workflow chaining validator.

This script logs subagent workflow transitions for debugging and will eventually
be used to chain subagent workflows together in the modular agent framework.

SAFEGUARDS (Issue #138):
1. Max iteration counter to prevent infinite recursion
2. Robust error handling to prevent cascading failures
3. Safe logging that won't crash on failures

Exit codes:
    0: Success (continue normal execution)
    1: Warning (logged but execution continues)
    2: Error (execution may be affected)

Input: JSON with hook event data from Claude Code
Output: JSON response for Claude Code hooks system
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from hook_debug import safe_log_to_debug_file

# SAFEGUARD: Max iterations to prevent infinite recursion
MAX_ITERATIONS_FILE = "/tmp/claude_stop_hook_iterations.txt"
MAX_ALLOWED_ITERATIONS = 10


def check_iteration_limit() -> bool:
    """
    Check if we've exceeded the max iteration limit.

    Returns:
        True if within limits, False if exceeded
    """
    try:
        # Read current iteration count
        if os.path.exists(MAX_ITERATIONS_FILE):
            with open(MAX_ITERATIONS_FILE) as f:
                count = int(f.read().strip())

            # Check against limit
            if count >= MAX_ALLOWED_ITERATIONS:
                print(
                    f"ERROR: Stop hook iteration limit exceeded ({count}/{MAX_ALLOWED_ITERATIONS})",
                    file=sys.stderr,
                )
                # Reset counter for next session
                with open(MAX_ITERATIONS_FILE, "w") as f:
                    f.write("0")
                return False

            # Increment counter
            with open(MAX_ITERATIONS_FILE, "w") as f:
                f.write(str(count + 1))
        else:
            # Initialize counter
            with open(MAX_ITERATIONS_FILE, "w") as f:
                f.write("1")

        return True
    except Exception as e:
        print(f"Warning: Failed to check iteration limit: {e}", file=sys.stderr)
        # Fail open - allow execution if we can't check
        return True


def reset_iteration_counter():
    """Reset the iteration counter after successful execution."""
    try:
        with open(MAX_ITERATIONS_FILE, "w") as f:
            f.write("0")
    except Exception:
        # Ignore errors in resetting
        pass


def get_repo_root() -> Path:
    """Find the repository root (parent of bot/ submodule)."""
    try:
        script_path = Path(__file__).resolve()
        # Go up until we find .git or reach root
        current = script_path.parent
        while current != current.parent:
            if (current / ".git").exists():
                return current
            current = current.parent
        # Fallback to parent of script
        return script_path.parent.parent
    except Exception:
        # Safeguard: return a sensible default
        return Path("/home/nic/src/bot")


def extract_context_info(input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Extract relevant context information from hook input.

    Args:
        input_data: Input data from Claude Code hook

    Returns:
        Dictionary of extracted context information
    """
    try:
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
    except Exception as e:
        # Return minimal context on error
        return {
            "hook_event": "unknown",
            "subagent": "unknown",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "error": str(e),
        }


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
    """Main hook entry point with robust error handling."""

    # SAFEGUARD: Check iteration limit first
    if not check_iteration_limit():
        # Return success to prevent further recursion
        print("{}")  # Empty JSON response
        return 0

    try:
        # Try to read input
        try:
            input_data = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            # Return valid empty response on bad input
            print("{}")
            print(f"Warning: Invalid JSON input: {e}", file=sys.stderr)
            return 0  # Return success to prevent recursion
        except Exception as e:
            # Return valid empty response on any input error
            print("{}")
            print(f"Warning: Failed to read input: {e}", file=sys.stderr)
            return 0  # Return success to prevent recursion

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
        output = {}

        if not is_valid and error_message:
            # Block the stop event
            output["decision"] = "block"
            output["reason"] = error_message
        # Otherwise, return empty {} to allow (default behavior)

        # Log to debug file (safe - won't crash on failure)
        safe_log_to_debug_file(hook_event, input_data, output)

        # Output JSON to stdout for Claude Code
        print(json.dumps(output))

        # Print human-readable info to stderr for user visibility
        print(f"✓ {hook_event} hook executed", file=sys.stderr)
        print(f"  Subagent: {context.get('subagent', 'unknown')}", file=sys.stderr)

        # Reset iteration counter on successful execution
        if is_valid:
            reset_iteration_counter()

        return 0 if is_valid else 1

    except Exception as e:
        # SAFEGUARD: Catch-all to prevent any uncaught exception from crashing
        try:
            print("{}")  # Always output valid JSON
            print(f"Warning: Unexpected error in Stop hook: {e}", file=sys.stderr)
        except Exception:
            # Even if printing fails, don't crash
            pass

        # Reset counter on error to prevent getting stuck
        reset_iteration_counter()

        # Return success to prevent recursion
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Ultimate safeguard: catch everything
        try:
            print("{}")  # Try to output valid JSON
        except Exception:
            pass
        sys.exit(0)  # Always exit cleanly to prevent recursion
