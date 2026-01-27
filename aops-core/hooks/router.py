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

try:
    from hooks.hook_logger import log_hook_event
except ImportError:
    log_hook_event = None

# --- Configuration ---

# Event mapping: Gemini -> Claude
GEMINI_EVENT_MAP = {
    "SessionStart": "SessionStart",
    "BeforeTool": "PreToolUse",
    "AfterTool": "PostToolUse",
    "BeforeAgent": "UserPromptSubmit",
    "AfterAgent": "Stop",
    "SessionEnd": "Stop",
    "Notification": "Notification",
    "PreCompress": "PreCompact",
}

# Hooks Registry
# "gates.py" is the new universal gate runner.
# "unified_logger.py" logs for Claude events.
HOOK_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "SessionStart": [
        {"script": "session_env_setup.sh"},
        {"script": "unified_logger.py"},
    ],
    "PreToolUse": [
        {"script": "unified_logger.py"},
        {"script": "gates.py"},  # Universal gate runner (Hydration)
        {"script": "command_intercept.py"},
        {"script": "task_required_gate.py"},
        {"script": "overdue_enforcement.py"},
    ],
    "PostToolUse": [
        {"script": "unified_logger.py"},
        {"script": "gates.py"},  # Universal gate runner (Custodiet)
        {"script": "task_binding.py"},
        {"script": "handover_gate.py"},
    ],
    "UserPromptSubmit": [
        {"script": "user_prompt_submit.py"},
        {"script": "unified_logger.py"},
    ],
    "SubagentStop": [
        {"script": "unified_logger.py"},
    ],
    "Stop": [
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
        except Exception:
            os.close(fd) if fd else None
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
    except Exception:
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
                    update_data["temp_root"] = temp_root
                else:
                    # Fallback: just use parent
                    update_data["temp_root"] = str(trans_p.parent)
            except Exception:
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
        gemini_output["hookSpecificOutput"]["hookEventName"] = gemini_event
        perm = gemini_output["hookSpecificOutput"].pop("permissionDecision", None)
        if perm:
            gemini_output["decision"] = perm

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
                f"{aops_core_str}{os.pathsep}{current_pp}" if current_pp else aops_core_str
            )

        # Inject Gemini Temp Root if available and valid
        session_data = get_session_data()
        temp_root = session_data.get("temp_root")
        if temp_root and validate_temp_path(temp_root):
            env["AOPS_GEMINI_TEMP_ROOT"] = temp_root

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
        print(f"ERROR: Hook {script_path.name} timed out after {timeout}s", file=sys.stderr)
        return {}, 2
    except FileNotFoundError as e:
        print(f"ERROR: Hook script not found: {script_path}: {e}", file=sys.stderr)
        return {}, 2
    except PermissionError as e:
        print(f"ERROR: Permission denied for hook {script_path.name}: {e}", file=sys.stderr)
        return {}, 2
    except OSError as e:
        print(f"ERROR: OS error running hook {script_path.name}: {e}", file=sys.stderr)
        return {}, 2


def merge_outputs(outputs: List[Dict[str, Any]], event_name: str) -> Dict[str, Any]:
    """Merge outputs from multiple hooks (simplified)."""
    if not outputs:
        return {}

    result: Dict[str, Any] = {}
    system_messages = []
    permission_decisions = []  # deny > ask > allow

    for out in outputs:
        if not out:
            continue

        # Collect system messages
        if "systemMessage" in out:
            system_messages.append(out["systemMessage"])

        # Collect permission decisions
        if "hookSpecificOutput" in out:
            if "permissionDecision" in out["hookSpecificOutput"]:
                permission_decisions.append(
                    out["hookSpecificOutput"]["permissionDecision"]
                )

            # Flatten additionalContext for simple merging
            if "additionalContext" in out["hookSpecificOutput"]:
                # Append as system message for simplicity or merge contexts
                # Just appending to system messages is a safe fallback for general tools
                pass

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

    if final_perm:
        result.setdefault("hookSpecificOutput", {})["permissionDecision"] = final_perm
        result["hookSpecificOutput"]["hookEventName"] = event_name

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
