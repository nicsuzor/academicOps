"""Shared utilities for hook implementations.

Provides DRY infrastructure for:
- Temp file management (unified temp directory, write, cleanup)
- Session ID extraction
- Subagent detection
- Hook output formatting

All gates should use these utilities instead of duplicating code.
"""

from __future__ import annotations

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
from lib.session_paths import get_session_status_dir
from lib.template_loader import load_template

# DEFAULT_HOOK_TMP removed - now using ~/.claude/projects/... or ~/.gemini/...

# Cleanup age: 1 hour in seconds
CLEANUP_AGE_SECONDS = 60 * 60


class HookOutput(TypedDict, total=False):
    """Standard hook output format."""

    hookSpecificOutput: dict[str, Any]


def get_hook_temp_dir(category: str, input_data: dict[str, Any] | None = None) -> Path:
    """Get temporary directory for hook files.

    Unified temp directory resolution using session_paths logic.
    """
    # 1. Check for standard temp dir env var (highest priority - host CLI provided)
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

    # 3. Use unified session status directory resolution
    session_id = (input_data.get("session_id") if input_data else None) or os.environ.get(
        "CLAUDE_SESSION_ID"
    )
    status_dir = get_session_status_dir(session_id, input_data)

    # Platform-specific temp sub-structure
    # Gemini uses flat category directories in state dir (~/.gemini/tmp/<hash>/<category>)
    # Claude uses tmp subdirectory (~/.claude/projects/<project>/tmp/<category>)
    if ".gemini" in str(status_dir):
        path = status_dir / category
    else:
        path = status_dir / "tmp" / category

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
    session_id: str | None = None,
) -> Path:
    """Write content to temp file, return path.

    When session_id is provided, uses a deterministic filename based on the
    session hash. This ensures a single temp file per session (P#102), with
    subsequent writes overwriting the same file.

    Args:
        content: Content to write
        temp_dir: Target directory
        prefix: File name prefix (e.g., "hydrate_", "audit_")
        suffix: File extension (default: ".md")
        session_id: Optional session identifier for consistent naming

    Returns:
        Path to created temp file

    Raises:
        OSError: If temp file cannot be written (fail-fast, no silent fallback)
    """
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Use consistent session hash in filename when available (P#102)
    # This ensures one temp file per session, overwritten on each trigger
    sid = session_id or os.environ.get("CLAUDE_SESSION_ID")
    if sid:
        from lib.session_paths import get_session_short_hash

        short_hash = get_session_short_hash(sid)
        # prefix already contains trailing underscore if intended
        path = temp_dir / f"{prefix}{short_hash}{suffix}"
        path.write_text(content)  # Fail-fast: no silent fallback to random names
        return path

    # Fallback only when no session_id: Generate random unique filename
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
    1. CLAUDE_AGENT_TYPE env var (if Claude passes it)
    2. CLAUDE_SUBAGENT_TYPE env var (alternative Claude env var)
    3. Transcript path contains /subagents/ (Claude Code stores subagent transcripts there)
    4. Transcript path contains /agent- (subagent filename pattern)
    5. Session ID starts with agent- (subagent ID format)

    Args:
        input_data: Hook input data containing transcript_path (optional)

    Returns:
        True if this appears to be a subagent session
    """
    # Method 1: Env vars (check all known variants)
    if os.environ.get("CLAUDE_AGENT_TYPE"):
        return True
    if os.environ.get("CLAUDE_SUBAGENT_TYPE"):
        return True

    # Method 2: Check transcript path for /subagents/ directory
    # Claude Code stores subagent transcripts at:
    #   ~/.claude/projects/<project>/<session-uuid>/subagents/agent-<hash>.jsonl
    if input_data:
        transcript_path = str(input_data.get("transcript_path", ""))
        if "/subagents/" in transcript_path:
            return True
        # Also check for agent- prefix in filename (subagent transcripts often have this)
        if "/agent-" in transcript_path:
            return True

    # Method 3: Check if session_id looks like a subagent ID
    # (Main sessions are UUIDs, subagents may have different format)
    if input_data:
        session_id = str(input_data.get("session_id", ""))
        if session_id.startswith("agent-"):
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
