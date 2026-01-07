#!/usr/bin/env python3
"""
Generic hook router for Claude Code.

Consolidates multiple hooks per event into a single invocation, reducing
"success noise" in system-reminders. Routes to sub-scripts based on hook
event type, merges outputs, and returns worst exit code.

Architecture:
- Single router.py in settings.json per hook event
- Router dispatches to registered scripts in HOOK_REGISTRY
- Async hooks dispatched first, collected last
- Outputs merged per consolidation rules

Exit codes:
    0: Success (all hooks succeeded)
    1: Warning (at least one hook warned)
    2: Block (at least one hook blocked - PreToolUse only)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Hook directory (same directory as this script)
HOOK_DIR = Path(__file__).parent

# Registry of hooks per event type
# Each entry can have {"script": "name.py", "async": True/False}
HOOK_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "SessionStart": [
        {"script": "session_env_setup.sh"},
        {"script": "terminal_title.py"},
        {"script": "sessionstart_load_axioms.py"},
        {"script": "unified_logger.py"},
    ],
    "PreToolUse": [
        {"script": "policy_enforcer.py"},
        {"script": "criteria_gate.py"},
        {"script": "unified_logger.py"},
    ],
    "PostToolUse": [
        {"script": "unified_logger.py"},
        {"script": "autocommit_state.py"},
        {"script": "fail_fast_watchdog.py"},
        {"script": "custodiet_gate.py"},
    ],
    "PostToolUse:TodoWrite": [
        {"script": "request_scribe.py"},
    ],
    "UserPromptSubmit": [
        {"script": "user_prompt_submit.py"},
        {"script": "unified_logger.py"},
    ],
    "SubagentStop": [
        {"script": "unified_logger.py"},
    ],
    "Stop": [
        {"script": "unified_logger.py"},
        {"script": "request_scribe.py"},
        {"script": "session_reflect.py"},
    ],
}


def get_hooks_for_event(
    event_name: str, matcher: str | None = None
) -> list[dict[str, Any]]:
    """
    Get registered hooks for an event.

    Args:
        event_name: Hook event name (SessionStart, PreToolUse, etc.)
        matcher: Optional matcher for PostToolUse events (e.g., "TodoWrite")

    Returns:
        List of hook configurations for the event
    """
    # Check for matcher-specific variant first
    if matcher:
        key = f"{event_name}:{matcher}"
        if key in HOOK_REGISTRY:
            return HOOK_REGISTRY[key]

    return HOOK_REGISTRY.get(event_name, [])


def merge_permission_decisions(decisions: list[str]) -> str | None:
    """
    Merge permission decisions with precedence: deny > ask > allow.

    Args:
        decisions: List of permission decisions

    Returns:
        Merged decision, or None if no decisions
    """
    if not decisions:
        return None

    # Precedence order (highest first)
    precedence = {"deny": 0, "ask": 1, "allow": 2}

    # Find the most restrictive (lowest precedence number)
    best = None
    best_rank = float("inf")

    for decision in decisions:
        rank = precedence.get(decision, 3)  # Unknown decisions ranked lowest
        if rank < best_rank:
            best_rank = rank
            best = decision

    return best


def aggregate_exit_codes(codes: list[int]) -> int:
    """
    Aggregate exit codes (worst wins: 2 > 1 > 0).

    Args:
        codes: List of exit codes

    Returns:
        Worst (highest) exit code, or 0 if empty
    """
    if not codes:
        return 0
    return max(codes)


def merge_continue_flags(flags: list[bool]) -> bool:
    """
    Merge continue flags with AND logic.

    Args:
        flags: List of continue flags

    Returns:
        True if all True (or empty), False if any False
    """
    if not flags:
        return True
    return all(flags)


def merge_suppress_flags(flags: list[bool]) -> bool:
    """
    Merge suppressOutput flags with OR logic.

    Args:
        flags: List of suppress flags

    Returns:
        True if any True, False otherwise
    """
    if not flags:
        return False
    return any(flags)


def merge_outputs(outputs: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    """
    Merge outputs from multiple hooks.

    Consolidation rules:
    - additionalContext: Concatenate with separator
    - systemMessage: Concatenate with newlines
    - permissionDecision: Most restrictive wins
    - continue: AND logic
    - suppressOutput: OR logic

    Args:
        outputs: List of hook outputs
        event_name: Hook event name (required for hookSpecificOutput.hookEventName)

    Returns:
        Merged output dictionary
    """
    if not outputs:
        return {}

    result: dict[str, Any] = {}

    # Collect values for merging
    additional_contexts: list[str] = []
    system_messages: list[str] = []
    permission_decisions: list[str] = []
    continue_flags: list[bool] = []
    suppress_flags: list[bool] = []

    for output in outputs:
        if not output:
            continue

        # Extract hookSpecificOutput fields
        hook_specific = output.get("hookSpecificOutput", {})
        if hook_specific:
            ctx = hook_specific.get("additionalContext")
            if ctx:
                additional_contexts.append(ctx)

            perm = hook_specific.get("permissionDecision")
            if perm:
                permission_decisions.append(perm)

        # Extract top-level fields
        msg = output.get("systemMessage")
        if msg:
            system_messages.append(msg)

        if "continue" in output:
            continue_flags.append(output["continue"])

        if "suppressOutput" in output:
            suppress_flags.append(output["suppressOutput"])

    # Build merged result
    if additional_contexts or permission_decisions:
        result["hookSpecificOutput"] = {
            "hookEventName": event_name,  # Required field per Claude Code schema
        }

        if additional_contexts:
            result["hookSpecificOutput"]["additionalContext"] = "\n\n---\n\n".join(
                additional_contexts
            )

        merged_perm = merge_permission_decisions(permission_decisions)
        if merged_perm:
            result["hookSpecificOutput"]["permissionDecision"] = merged_perm

    if system_messages:
        result["systemMessage"] = "\n".join(system_messages)

    if continue_flags:
        merged_continue = merge_continue_flags(continue_flags)
        if not merged_continue:  # Only include if False (default is True)
            result["continue"] = False

    if suppress_flags:
        merged_suppress = merge_suppress_flags(suppress_flags)
        if merged_suppress:  # Only include if True (default is False)
            result["suppressOutput"] = True

    return result


def run_hook_script(
    script_path: Path, input_data: dict[str, Any], timeout: float = 30.0
) -> tuple[dict[str, Any], int]:
    """
    Run a hook script synchronously.

    Args:
        script_path: Path to script
        input_data: Input data to pass via stdin
        timeout: Timeout in seconds

    Returns:
        Tuple of (output dict, exit code)
    """
    try:
        # Determine how to run the script
        if script_path.suffix == ".sh":
            cmd = ["bash", str(script_path)]
        else:
            cmd = ["python", str(script_path)]

        # Run with input on stdin
        result = subprocess.run(
            cmd,
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "")},
            cwd=HOOK_DIR,
        )

        # Parse output
        output = {}
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Non-JSON output - ignore
                pass

        # Log stderr if present
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return output, result.returncode

    except subprocess.TimeoutExpired:
        print(f"WARNING: Hook {script_path.name} timed out", file=sys.stderr)
        return {}, 1
    except Exception as e:
        print(f"WARNING: Hook {script_path.name} failed: {e}", file=sys.stderr)
        return {}, 1


def start_async_hook(
    script_path: Path, input_data: dict[str, Any]
) -> subprocess.Popen[str]:
    """
    Start a hook script asynchronously.

    Args:
        script_path: Path to script
        input_data: Input data to pass via stdin

    Returns:
        Popen process handle
    """
    if script_path.suffix == ".sh":
        cmd = ["bash", str(script_path)]
    else:
        cmd = ["python", str(script_path)]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": os.environ.get("PYTHONPATH", "")},
        cwd=HOOK_DIR,
    )

    # Write input and close stdin
    if proc.stdin:
        proc.stdin.write(json.dumps(input_data))
        proc.stdin.close()

    return proc


def collect_async_result(
    proc: subprocess.Popen[str], timeout: float = 30.0
) -> tuple[dict[str, Any], int]:
    """
    Collect result from async hook.

    Args:
        proc: Popen process handle
        timeout: Timeout in seconds

    Returns:
        Tuple of (output dict, exit code)
    """
    try:
        # stdin already closed in start_async_hook, so use wait() + read()
        # instead of communicate() which tries to flush stdin
        proc.wait(timeout=timeout)

        stdout = proc.stdout.read() if proc.stdout else ""
        stderr = proc.stderr.read() if proc.stderr else ""

        output = {}
        if stdout.strip():
            try:
                output = json.loads(stdout)
            except json.JSONDecodeError:
                pass

        if stderr:
            print(stderr, file=sys.stderr)

        return output, proc.returncode or 0

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print("WARNING: Async hook timed out", file=sys.stderr)
        return {}, 1


def run_sync_hook(
    script: str, input_data: dict[str, Any]
) -> tuple[dict[str, Any], int]:
    """
    Run a synchronous hook by name.

    Args:
        script: Script filename
        input_data: Input data

    Returns:
        Tuple of (output dict, exit code)
    """
    script_path = HOOK_DIR / script
    return run_hook_script(script_path, input_data)


def dispatch_hooks(
    hooks: list[dict[str, Any]], input_data: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[int]]:
    """
    Dispatch hooks with async-first ordering.

    Async hooks are started first, then sync hooks run, then async results collected.

    Args:
        hooks: List of hook configs
        input_data: Input data for all hooks

    Returns:
        Tuple of (outputs list, exit codes list)
    """
    outputs: list[dict[str, Any]] = []
    exit_codes: list[int] = []

    # Separate async and sync hooks
    async_hooks: list[tuple[dict[str, Any], subprocess.Popen[str]]] = []
    sync_hooks: list[dict[str, Any]] = []

    for hook in hooks:
        if hook.get("async", False):
            # Start async hooks immediately
            script_path = HOOK_DIR / hook["script"]
            proc = start_async_hook(script_path, input_data)
            async_hooks.append((hook, proc))
        else:
            sync_hooks.append(hook)

    # Run sync hooks while async hooks execute
    for hook in sync_hooks:
        output, code = run_sync_hook(hook["script"], input_data)
        outputs.append(output)
        exit_codes.append(code)

    # Collect async results
    for hook, proc in async_hooks:
        output, code = collect_async_result(proc)
        outputs.append(output)
        exit_codes.append(code)

    return outputs, exit_codes


def route_hooks(input_data: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """
    Main routing function.

    Args:
        input_data: Hook input data (must contain hook_event_name)

    Returns:
        Tuple of (merged output, aggregated exit code)
    """
    event_name = input_data.get("hook_event_name", "")
    if not event_name:
        # No event name - return empty (noop)
        return {}, 0

    # Check for matcher (PostToolUse events)
    matcher = input_data.get("tool_name") if event_name == "PostToolUse" else None

    # Get hooks for this event
    hooks = get_hooks_for_event(event_name, matcher)
    if not hooks:
        return {}, 0

    # Dispatch all hooks
    outputs, exit_codes = dispatch_hooks(hooks, input_data)

    # Merge outputs
    merged_output = merge_outputs(outputs, event_name)

    # Aggregate exit codes
    final_exit_code = aggregate_exit_codes(exit_codes)

    return merged_output, final_exit_code


def main():
    """Main entry point."""
    # Read input from stdin
    input_data: dict[str, Any] = {}
    try:
        input_data = json.load(sys.stdin)
    except Exception:
        pass

    # Route to appropriate hooks
    output, exit_code = route_hooks(input_data)

    # Output JSON
    print(json.dumps(output))

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
