"""Shared utilities for hook implementations.

Provides DRY infrastructure for:
- Temp file management (unified temp directory, write, cleanup)
- Session ID extraction
- Subagent detection
- Hook output formatting

All gates should use these utilities instead of duplicating code.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from pathlib import Path
from typing import Any, TypedDict

from lib.paths import (
    get_axioms_file,
    get_heuristics_file,
    get_skills_file,
)
from lib.session_paths import get_claude_project_folder
from lib.template_loader import load_template

# DEFAULT_HOOK_TMP removed - now using ~/.claude/projects/... or ~/.gemini/...

# Cleanup age: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60


class HookOutput(TypedDict, total=False):
    """Standard hook output format."""

    hookSpecificOutput: dict[str, Any]


def get_hook_temp_dir(category: str, input_data: dict[str, Any] | None = None) -> Path:
    """Get temporary directory for hook files.

    Unified temp directory resolution:
    1. TMPDIR env var (highest priority - host CLI provided)
    2. AOPS_GEMINI_TEMP_ROOT env var (Gemini router provided)
    3. Claude-specific check (SSoT for Claude Code)
    4. Gemini-specific check (transcript_path contains .gemini)
    5. Gemini-specific check (GEMINI_CLI or .gemini in cwd)
    6. Default: Claude fallback path

    Args:
        category: Subdirectory name for this hook type (e.g., "hydrator", "compliance", "session")
        input_data: Hook input data (optional). Used to extract transcript_path or session_id.

    Returns:
        Path to temp directory (created if doesn't exist)

    Raises:
        RuntimeError: If GEMINI_CLI is set but temp root not found
    """
    import uuid

    # 1. Check for standard temp dir env var
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir:
        path = Path(tmpdir) / category
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2. Check for Gemini router provided temp root
    gemini_root = os.environ.get("AOPS_GEMINI_TEMP_ROOT")
    if gemini_root:
        path = Path(gemini_root) / category
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 3. Claude-specific check (SSoT for Claude Code)
    # Priority: If we have a valid UUID session ID, it MUST be Claude
    session_id = (input_data.get("session_id") if input_data else None) or os.environ.get("CLAUDE_SESSION_ID")
    
    is_claude_uuid = False
    if session_id:
        try:
            # Claude session IDs are standard UUIDs
            uuid.UUID(str(session_id))
            is_claude_uuid = True
        except (ValueError, TypeError):
            is_claude_uuid = False

    if is_claude_uuid or os.environ.get("CLAUDE_SESSION_ID") or os.environ.get("CLAUDE_PLUGIN_ROOT"):
        # Double check: if it looks like Gemini, don't use Claude path
        # Unless we are SURE it's Claude
        if not (input_data and "transcript_path" in input_data and ".gemini" in str(input_data["transcript_path"])):
            project_folder = get_claude_project_folder()
            path = Path.home() / ".claude" / "projects" / project_folder / "tmp" / category
            path.mkdir(parents=True, exist_ok=True)
            return path

    # 4. Check transcript_path for Gemini CLI detection
    if input_data:
        transcript_path = input_data.get("transcript_path")
        if transcript_path and ".gemini" in str(transcript_path):
            t_path = Path(transcript_path)
            # Path is usually ~/.gemini/tmp/<hash>/chats/session.json
            project_hash_dir = t_path.parent.parent if t_path.suffix in (".jsonl", ".json") else t_path.parent

            if not project_hash_dir.exists():
                raise RuntimeError(
                    f"Gemini transcript_path provided but hash directory missing: {project_hash_dir}\n"
                    f"Expected: ~/.gemini/tmp/<hash>/ to exist before hooks run."
                )
            path = project_hash_dir / category
            path.mkdir(parents=True, exist_ok=True)
            return path

    # 5. Gemini-specific discovery logic (CWD hash fallback)
    # ONLY if we haven't already identified as Claude
    if os.environ.get("GEMINI_CLI") or (Path.cwd() / ".gemini").exists():
        project_root = str(Path.cwd().resolve())
        project_hash = hashlib.sha256(project_root.encode()).hexdigest()
        gemini_tmp = Path.home() / ".gemini" / "tmp" / project_hash

        if gemini_tmp.exists():
            path = gemini_tmp / category
            path.mkdir(parents=True, exist_ok=True)
            return path

        # If GEMINI_CLI is set but we can't find the directory, AND we might be Claude,
        # fall through to Claude default.
        if not is_claude_uuid:
            raise RuntimeError(
                f"GEMINI_CLI is set but temp root not found at: {gemini_tmp}. "
                "Ensure you are running inside a Gemini project."
            )

    # 6. Default: Claude behavior
    project_folder = get_claude_project_folder()
    path = Path.home() / ".claude" / "projects" / project_folder / "tmp" / category
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_old_temp_files(
    temp_dir: Path,
    prefix: str,
    age_seconds: int = CLEANUP_AGE_SECONDS,
) -> int:
    """Delete temp files older than specified age.

    Args:
        temp_dir: Directory to clean
        prefix: File prefix pattern (e.g., "hydrate_", "audit_")
        age_seconds: Max file age in seconds (default: 1 hour)

    Returns:
        Number of files deleted
    """
    if not temp_dir.exists():
        return 0

    deleted = 0
    cutoff = time.time() - age_seconds
    for f in temp_dir.glob(f"{prefix}*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except OSError:
            pass  # Ignore cleanup errors

    return deleted


def load_framework_content() -> tuple[str, str, str]:
    """Load framework content (axioms, heuristics, skills).

    Returns:
        tuple: (axioms_text, heuristics_text, skills_text)
    """
    axioms = load_template(get_axioms_file())
    heuristics = load_template(get_heuristics_file())
    skills = load_template(get_skills_file())
    return axioms, heuristics, skills


def write_temp_file(
    content: str,
    temp_dir: Path,
    prefix: str,
    suffix: str = ".md",
) -> Path:
    """Write content to temp file, return path.

    Args:
        content: Content to write
        temp_dir: Target directory
        prefix: File name prefix (e.g., "hydrate_", "audit_")
        suffix: File extension (default: ".md")

    Returns:
        Path to created temp file

    Raises:
        IOError: If temp file cannot be written (fail-fast)
    """
    temp_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix=prefix,
        suffix=suffix,
        dir=temp_dir,
        delete=False,
    ) as f:
        f.write(content)
        return Path(f.name)


def get_session_id(input_data: dict[str, Any], require: bool = False) -> str:
    """Get session ID from hook input data or environment.

    Args:
        input_data: Hook input data dict
        require: If True, raise ValueError when session_id not found

    Returns:
        Session ID string, or empty string if not found and not required

    Raises:
        ValueError: If require=True and session_id not found
    """
    session_id = input_data.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    if not session_id:
        if require:
            raise ValueError(
                "session_id is required in hook input_data or CLAUDE_SESSION_ID env var. "
                "If you're seeing this error, the hook invocation is missing required context."
            )
        return ""
    return session_id


def is_subagent_session(input_data: dict[str, Any] | None = None) -> bool:
    """Check if this is a subagent session.

    Uses multiple detection methods since env vars may not be passed to hook subprocesses:
    1. parent_tool_use_id presence (Definitive Claude subagent marker)
    2. UUID validation (Claude main sessions are ALWAYS UUIDs)
    3. CLAUDE_AGENT_TYPE / CLAUDE_SUBAGENT_TYPE env vars
    4. Transcript path contains /subagents/ or /agent-
    5. Session ID starts with agent- or has sidechain markers

    Args:
        input_data: Hook input data containing transcript_path (optional)

    Returns:
        True if this appears to be a subagent session
    """
    import json
    session_id = (input_data.get("session_id") if input_data else None) or os.environ.get("CLAUDE_SESSION_ID")
    
    # Forensic logging for detection
    forensic_path = Path("/tmp/subagent_detection.jsonl")
    try:
        with forensic_path.open("a") as f:
            log_entry = {
                "ts": time.time(),
                "session_id": session_id,
                "input_keys": list(input_data.keys()) if input_data else [],
                "parent_id": input_data.get("parent_tool_use_id") if input_data else None,
                "CLAUDE_AGENT_TYPE": os.environ.get("CLAUDE_AGENT_TYPE"),
                "is_registered_main": Path("/tmp/aops_session_registry.json").exists() and (session_id in json.loads(Path("/tmp/aops_session_registry.json").read_text()) if session_id else False)
            }
            f.write(json.dumps(log_entry) + "\n")
    except: pass

    # Method 0: Explicit parent marker (Claude Code)
    if input_data and input_data.get("parent_tool_use_id"):
        return True

    # Method 1: Session ID validation (Claude Code)
    # If we have a session_id, and it is NOT a valid UUID, then it's a sidechain
    # (Claude main sessions are always UUIDs)
    session_id = (input_data.get("session_id") if input_data else None) or os.environ.get("CLAUDE_SESSION_ID")
    if session_id:
        try:
            uuid.UUID(str(session_id))
            # It's a UUID, so it COULD be a main session.
            # But wait, some sidechains might also use UUIDs.
            # So we only return False if it's a UUID AND none of the other checks match.
            pass
        except (ValueError, TypeError):
            # NOT a UUID -> DEFINITELY a sidechain in Claude context
            # (Unless it's Gemini, but Gemini session IDs handled separately)
            if not str(session_id).startswith("gemini-"):
                return True

    # Method 2: Env vars (check all known variants)
    if os.environ.get("CLAUDE_AGENT_TYPE"):
        return True
    if os.environ.get("CLAUDE_SUBAGENT_TYPE"):
        return True

    # Method 3: Check transcript path for /subagents/ directory
    if input_data:
        transcript_path = str(input_data.get("transcript_path", ""))
        if "/subagents/" in transcript_path:
            return True
        if "/agent-" in transcript_path:
            return True

    # Method 4: ID prefix check
    if session_id and str(session_id).startswith("agent-"):
        return True

    return False


# ============================================================================
# Hook Output Helpers
# ============================================================================


def make_deny_output(
    message: str,
    event_name: str = "PreToolUse",
) -> HookOutput:
    """Build JSON output for deny/block decision.

    Args:
        message: Block message to display
        event_name: Hook event name (default: "PreToolUse")

    Returns:
        Hook output dict with permissionDecision: deny
    """
    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "additionalContext": message,
        }
    }


def make_allow_output(
    message: str = "",
    event_name: str = "PreToolUse",
) -> HookOutput:
    """Build JSON output for allow with optional context.

    Args:
        message: Optional context message
        event_name: Hook event name (default: "PreToolUse")

    Returns:
        Hook output dict with permissionDecision: allow
    """
    if not message:
        return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "allow",
            "additionalContext": message,
        }
    }


def make_context_output(
    message: str,
    event_name: str = "PostToolUse",
    wrap_in_reminder: bool = True,
) -> HookOutput:
    """Build JSON output for injecting context (no permission decision).

    Args:
        message: Context message to inject
        event_name: Hook event name (default: "PostToolUse")
        wrap_in_reminder: If True, wrap message in <system-reminder> tags

    Returns:
        Hook output dict with additionalContext
    """
    if wrap_in_reminder:
        message = f"<system-reminder>\n{message}\n</system-reminder>"

    return {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": message,
        }
    }


def make_empty_output() -> dict:
    """Return empty output dict (allow without context).

    Returns:
        Empty dict {} which signals allow
    """
    return {}


# ============================================================================
# Task ID Extraction
# ============================================================================


def get_task_id_from_result(tool_result: dict[str, Any]) -> str | None:
    """Extract task_id from MCP tool result.

    Supports both Claude and Gemini response formats:
    - Claude: {"success": true, "task": {"id": "..."}}
    - Gemini: {"returnDisplay": '{"task": {"id": "..."}}'} (JSON in string)

    Args:
        tool_result: The tool_result dict from hook input

    Returns:
        Task ID string or None if not found
    """
    import json as _json

    # Handle Gemini tool_response structure (JSON in returnDisplay string)
    if "returnDisplay" in tool_result:
        try:
            content = tool_result["returnDisplay"]
            if isinstance(content, str):
                data = _json.loads(content)
                return data.get("task", {}).get("id")
        except (_json.JSONDecodeError, TypeError):
            pass

    # MCP task tools return {"success": true, "task": {"id": "...", ...}}
    task = tool_result.get("task", {})
    return task.get("id")
