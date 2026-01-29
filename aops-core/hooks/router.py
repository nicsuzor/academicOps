#!/usr/bin/env python3
"""
Universal Hook Router.

Handles hook events from both Claude Code and Gemini CLI.
Consolidates multiple hooks per event into a single invocation.
Manages session persistence for Gemini.
"""

import json
import os
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Path Setup ---
HOOK_DIR = Path(__file__).parent
AOPS_CORE_DIR = HOOK_DIR.parent

# Add aops-core to path for imports
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

# Adjust imports to work within the aops-core environment
from hooks import hook_logger


# Hook logging is handled by unified_logger.py in the hook registry

# --- Configuration ---

# Event mapping: Gemini -> Claude
GEMINI_EVENT_MAP = {
    "SessionStart": "SessionStart",
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",
    "AfterAgent": "AfterAgent",
    "SessionEnd": "Stop",
    "Notification": "Notification",
    "PreCompress": "PreCompact",
}

# Hooks Registry
# "gates.py" is the universal gate runner - handles all gates via gate_registry.py
# "unified_logger.py" logs for Claude events.
HOOK_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "SessionStart": [
        {"script": "session_env_setup.sh"},
        {"script": "unified_logger.py"},
    ],
    "PreToolUse": [
        {"script": "unified_logger.py"},
        {
            "script": "gates.py"
        },  # Universal gate runner (hydration, task_required, overdue_enforcement)
        {"script": "command_intercept.py"},
        # REMOVED: task_required_gate.py - consolidated into gates.py
        # REMOVED: overdue_enforcement.py - consolidated into gates.py
    ],
    "PostToolUse": [
        {"script": "unified_logger.py"},
        {"script": "gates.py"},  # Universal gate runner (custodiet, handover)
        {"script": "task_binding.py"},
        # REMOVED: handover_gate.py - consolidated into gates.py
    ],
    "UserPromptSubmit": [
        {"script": "user_prompt_submit.py"},
        {"script": "unified_logger.py"},
    ],
    "AfterAgent": [
        {"script": "gates.py"},  # Universal gate runner (agent_response_listener)
        {"script": "unified_logger.py"},
    ],
    "SubagentStop": [
        {"script": "unified_logger.py"},
    ],
    "Stop": [
        {"script": "unified_logger.py"},
        {"script": "gates.py"},  # Universal gate runner (stop_gate, hydration_recency)
        # {"script": "session_end_commit_check.py"},
    ],
    "SessionEnd": [
        {"script": "unified_logger.py"},
    ],
    "PreCompact": [
        {"script": "unified_logger.py"},
    ],
    "Notification": [
        {"script": "unified_logger.py"},
    ],
}

# --- Path Validation ---


def validate_temp_path(path: str) -> bool:
    """Validate that a temp path is safe (no traversal attacks).

    Args:
        path: Path string to validate

    Returns:
        True if path is safe, False otherwise
    """
    if not path:
        return False

    try:
        # Resolve to absolute path and check it's within expected bounds
        resolved = Path(path).resolve()

        # Must be within /tmp or user's home directory
        allowed_prefixes = [
            Path("/tmp"),
            Path.home(),
            Path(os.environ.get("AOPS_SESSIONS", "/tmp")),
        ]

        for prefix in allowed_prefixes:
            try:
                resolved.relative_to(prefix.resolve())
                return True
            except ValueError:
                continue

        return False
    except (OSError, RuntimeError):
        return False


# --- Session Management (Gemini Support) ---


def get_session_file_path() -> Path:
    """Get session metadata file path from $AOPS_SESSIONS environment variable."""
    aops_sessions = Path(os.getenv("AOPS_SESSIONS", ""))
    if not aops_sessions.name:
        # Fallback to tmp location if env not set
        return Path(f"/tmp/gemini-session-{os.getppid()}.json")

    aops_sessions.mkdir(parents=True, exist_ok=True)
    return aops_sessions / f"session-{os.getppid()}.json"


def persist_session_data(data: Dict[str, Any]) -> None:
    """Write session metadata atomically using temp file + rename.

    Uses atomic write pattern to prevent race conditions when
    multiple hook invocations occur concurrently.
    """
    try:
        session_file = get_session_file_path()

        # Merge with existing if possible
        if session_file.exists():
            try:
                existing = json.loads(session_file.read_text())
                existing.update(data)
                data = existing
            except json.JSONDecodeError:
                pass  # Use new data if existing is corrupt

        # Atomic write: write to temp file, then rename
        session_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(
            prefix="session-", suffix=".tmp", dir=str(session_file.parent)
        )
        try:
            os.write(fd, json.dumps(data).encode())
            os.close(fd)
            Path(temp_path).rename(session_file)
        except (IOError, OSError):
            # Clean up temp file on write failure; fd may already be closed
            try:
                os.close(fd)
            except Exception:
                # Fallback
                # The original code had 'pass' here. The instruction implies adding a line.
                # Assuming 'gemini_details' and 'tool_output' are defined in a broader context
                # or this is a placeholder for a specific fallback action.
                # Since they are not defined here, I'll keep the original 'pass'
                # but change the exception type as per the instruction's snippet.
                pass
            Path(temp_path).unlink(missing_ok=True)
            raise

    except OSError as e:
        print(f"WARNING: Failed to write session data: {e}", file=sys.stderr)


def get_session_data() -> Dict[str, Any]:
    """Read session metadata."""
    try:
        session_file = get_session_file_path()
        if session_file.exists():
            content = session_file.read_text().strip()
            # Handle potential legacy plain text ID
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"session_id": content}
    except OSError:
        # Session file read errors are non-fatal; return empty dict
        pass
    return {}


def get_gemini_session_id(event_name: str) -> str:
    """Get or create a persistent session ID details for Gemini."""
    # Check for native Gemini session ID
    env_session_id = os.environ.get("GEMINI_SESSION_ID")
    if env_session_id:
        return env_session_id

    # Read existing ID
    data = get_session_data()
    if data.get("session_id"):
        return data["session_id"]

    if event_name == "SessionStart":
        # Generate new session ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        session_id = f"gemini-{timestamp}-{short_uuid}"
        return session_id

    # Fallback
    return f"gemini-fallback-{str(uuid.uuid4())[:8]}"


# --- Routing Logic ---


def map_gemini_to_claude(
    gemini_event: str, gemini_input: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Map Gemini input format to Claude input format."""
    claude_event = GEMINI_EVENT_MAP.get(gemini_event)
    if not claude_event:
        return None

    claude_input = dict(gemini_input)
    claude_input["hook_event_name"] = claude_event

    session_id = claude_input.get("session_id") or get_gemini_session_id(gemini_event)
    claude_input["session_id"] = session_id

    if gemini_event == "SessionStart":
        update_data = {"session_id": session_id}

        # Extract temp root from transcript_path
        # format: .../tmp/<hash>/chats/session-....json
        transcript_path = gemini_input.get("transcript_path")
        if transcript_path:
            try:
                trans_p = Path(transcript_path)
                # We want the parent of 'chats', i.e. the hash dir
                # If path is .../chats/session.json:
                # parent = chats, parent.parent = hash dir
                if trans_p.parent.name == "chats":
                    temp_root = str(trans_p.parent.parent)
                else:
                    # Fallback: just use parent
                    temp_root = str(trans_p.parent)
                update_data["temp_root"] = temp_root
                claude_input["temp_root"] = temp_root  # Pass directly to hooks
            except (OSError, ValueError, AttributeError):
                # Best-effort extraction of temp_root; if parsing fails,
                # continue without it - hooks can still function
                pass

        persist_session_data(update_data)

    return claude_input


def map_claude_to_gemini(
    claude_output: Dict[str, Any], gemini_event: str
) -> Dict[str, Any]:
    """Map Claude output format to Gemini output format."""
    if not claude_output:
        return {}

    gemini_output = dict(claude_output)

    # Map hookSpecificOutput logic
    if "hookSpecificOutput" in gemini_output:
        hso = gemini_output["hookSpecificOutput"]
        hso["hookEventName"] = gemini_event

        # 1. Decision mapping (Common Field)
        # All known Gemini events use top-level 'decision'
        perm = hso.pop("permissionDecision", None)
        if perm:
            if perm == "block":
                # translate block to 'deny'
                gemini_output["decision"] = "deny"
            else:
                gemini_output["decision"] = perm

            # 2. Reason mapping (BeforeTool, AfterAgent)
            # BeforeTool uses top-level 'reason' for explanations.
            # AfterAgent uses top-level 'reason' for correction prompts.
            # Other events (BeforeAgent, AfterTool) use hookSpecificOutput.additionalContext.
            # CRITICAL: SessionStart uses hookSpecificOutput.additionalContext to inject
            # the first turn of history or prepend to prompt. Do NOT map to 'reason'.
            if gemini_event in ["BeforeTool", "AfterAgent"]:
                context = hso.get("additionalContext")
                if context:
                    gemini_output["reason"] = context

                    # Mirror to systemMessage for user visibility on deny/block
                    # (only if not already set)
                    if (
                        perm in ["deny", "block"]
                        and "systemMessage" not in gemini_output
                    ):
                        gemini_output["systemMessage"] = f"Tool blocked: {context}"

        # 3. SessionStart: Move additionalContext to systemMessage to prevent injection
        # Users want to see the session info but NOT inject it into the prompt.
        if gemini_event == "SessionStart":
            context = hso.pop("additionalContext", None)
            if context:
                current_sys = gemini_output.get("systemMessage", "")
                if current_sys:
                    gemini_output["systemMessage"] = f"{current_sys}\n\n{context}"
                else:
                    gemini_output["systemMessage"] = context

    return gemini_output


# --- Execution Logic ---


def run_hook_script(
    script_path: Path, input_data: Dict[str, Any], timeout: float = 30.0
) -> Tuple[Dict[str, Any], int]:
    """Run a single hook script and return output/exit code."""
    try:
        if script_path.suffix == ".sh":
            cmd = ["bash", str(script_path)]
        else:
            cmd = [sys.executable, str(script_path)]

        # Ensure PYTHONPATH propagates (avoid duplicates)
        env = os.environ.copy()
        current_pp = env.get("PYTHONPATH", "")
        aops_core_str = str(AOPS_CORE_DIR)
        # Only prepend if not already present
        if aops_core_str not in current_pp.split(os.pathsep):
            env["PYTHONPATH"] = (
                f"{aops_core_str}{os.pathsep}{current_pp}"
                if current_pp
                else aops_core_str
            )

        # Set session state directory (required by hooks)
        # First check input_data (direct pass from SessionStart), then session file
        temp_root = input_data.get("temp_root") or get_session_data().get("temp_root")
        if temp_root and validate_temp_path(temp_root):
            # Gemini: use temp_root from transcript_path
            env["AOPS_SESSION_STATE_DIR"] = temp_root
        else:
            # Claude: use ~/.claude/projects/<encoded-cwd>/
            cwd = input_data.get("cwd") or os.getcwd()
            encoded_cwd = "-" + cwd.replace("/", "-")[1:]
            env["AOPS_SESSION_STATE_DIR"] = str(
                Path.home() / ".claude" / "projects" / encoded_cwd
            )

        # Pass hook dir as CWD
        result = subprocess.run(
            cmd,
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=HOOK_DIR,
        )

        output = {}
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                pass

        if result.stderr:
            print(result.stderr, file=sys.stderr)

        return output, result.returncode

    except subprocess.TimeoutExpired as e:
        print(
            f"ERROR: Hook {script_path.name} timed out after {timeout}s",
            file=sys.stderr,
        )
        return {}, 2
    except FileNotFoundError as e:
        print(f"ERROR: Hook script not found: {script_path}: {e}", file=sys.stderr)
        return {}, 2
    except PermissionError as e:
        print(
            f"ERROR: Permission denied for hook {script_path.name}: {e}",
            file=sys.stderr,
        )
        return {}, 2
    except OSError as e:
        print(f"ERROR: OS error running hook {script_path.name}: {e}", file=sys.stderr)
        return {}, 2


def merge_outputs(outputs: List[Dict[str, Any]], event_name: str) -> Dict[str, Any]:
    """Merge outputs from multiple hooks.

    Combines system messages, permission decisions (deny > ask > allow),
    and additionalContext from all hook outputs.
    """
    if not outputs:
        return {}

    result: Dict[str, Any] = {}
    system_messages: List[str] = []
    additional_contexts: List[str] = []
    permission_decisions: List[str] = []  # deny > ask > allow

    for out in outputs:
        if not out:
            continue

        # Collect system messages
        if "systemMessage" in out:
            system_messages.append(out["systemMessage"])

        # Collect from hookSpecificOutput
        if "hookSpecificOutput" in out:
            hso = out["hookSpecificOutput"]

            if "permissionDecision" in hso:
                permission_decisions.append(hso["permissionDecision"])

            # Collect additionalContext - these are injected into model context
            if "additionalContext" in hso:
                additional_contexts.append(hso["additionalContext"])

    # Aggregation
    if system_messages:
        result["systemMessage"] = "\n".join(system_messages)

    # Permission logic: Deny wins
    if "deny" in permission_decisions:
        final_perm = "deny"
    elif "ask" in permission_decisions:
        final_perm = "ask"
    elif "allow" in permission_decisions:
        final_perm = "allow"
    else:
        final_perm = None

    if final_perm or additional_contexts:
        result.setdefault("hookSpecificOutput", {})["hookEventName"] = event_name
        if final_perm:
            result["hookSpecificOutput"]["permissionDecision"] = final_perm
        if additional_contexts:
            # Merge all additional contexts with newline separator
            result["hookSpecificOutput"]["additionalContext"] = "\n\n".join(
                additional_contexts
            )

    return result


def execute_hooks(
    event_name: str, input_data: Dict[str, Any]
) -> Tuple[Dict[str, Any], int]:
    """Execute all configured hooks for an event."""
    hooks = HOOK_REGISTRY.get(event_name, [])
    if not hooks:
        return {}, 0

    outputs = []
    exit_codes = []

    # Simple sync execution for now (simplify async complexity until needed)
    for hook_config in hooks:
        script_name = hook_config["script"]
        script_path = HOOK_DIR / script_name

        # Dispatch
        output, code = run_hook_script(script_path, input_data)

        outputs.append(output)
        exit_codes.append(code)

        # Fail fast on blocks (exit code 2)
        if code == 2:
            break

    # Merge results
    merged_output = merge_outputs(outputs, event_name)
    final_exit_code = max(exit_codes) if exit_codes else 0
    # Log operational trace (restores ~/.gemini/tmp/ logs)
    session_id = input_data.get("session_id")
    if session_id:
        # Enrich input_data with persisted session data (e.g. transcript_path)
        # to ensure logging goes to the correct directory
        session_data = get_session_data()
        if session_data:
            # Only add if missing to avoid overwriting current event data
            for k, v in session_data.items():
                if k not in input_data:
                    input_data[k] = v

        if "hook_logger" in globals() and globals()["hook_logger"]:
            hook_logger.log_hook_event(
                session_id=session_id,
                hook_event=event_name,
                input_data=input_data,
                output_data=merged_output,
                exit_code=final_exit_code,
            )

    return merged_output, final_exit_code


# --- Main Entry Point ---


def main():
    # Detect mode based on arguments
    # invocations:
    #   Claude: python router.py (reads json stdin with hook_event_name)
    #   Gemini: python router.py <EventName> (reads json stdin WITHOUT event name usually)

    is_gemini = len(sys.argv) > 1
    gemini_event = sys.argv[1] if is_gemini else None

    input_data = {}
    try:
        # P#8 Fail-fast: check stdin validity
        if not sys.stdin.isatty():
            input_data = json.load(sys.stdin)
    except Exception as e:
        print(f"ERROR: Failed to parse input JSON: {e}", file=sys.stderr)
        sys.exit(2)

    if is_gemini:
        # Gemini Mode
        claude_input = map_gemini_to_claude(gemini_event, input_data)
        if not claude_input:
            # Unknown event or no mapping
            print(json.dumps({}))
            sys.exit(0)

        # Special case: user_prompt_submit for Gemini (BeforeAgent)
        if gemini_event == "BeforeAgent":
            # Logic is handled by standard UserPromptSubmit hooks now
            pass

        output, exit_code = execute_hooks(claude_input["hook_event_name"], claude_input)
        gemini_output = map_claude_to_gemini(output, gemini_event)

        # Add metadata fields for Gemini acceptance criteria
        gemini_output["hook_event"] = gemini_event
        if gemini_event == "SessionStart":
            gemini_output["source"] = "startup"
        elif gemini_event == "SessionEnd":
            gemini_output["source"] = "exit"

        print(json.dumps(gemini_output))
        sys.exit(exit_code)

    else:
        # Claude Mode
        event_name = input_data.get("hook_event_name")
        if not event_name:
            # Invalid input
            print(json.dumps({}))
            sys.exit(0)

        output, exit_code = execute_hooks(event_name, input_data)
        print(json.dumps(output))
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
