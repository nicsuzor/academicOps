"""Session insights generation library.

Provides unified functions for generating session insights via LLM (Claude/Gemini).
Used by both automatic generation (Stop hook) and manual generation (skill).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class InsightsValidationError(Exception):
    """Raised when insights JSON fails validation."""

    pass


def get_aops_root() -> Path:
    """Get aops-core root directory from AOPS env var or relative path."""
    aops_env = os.environ.get("AOPS")
    if aops_env:
        return Path(aops_env)
    # Fallback: assume we're in aops-core/lib/
    return Path(__file__).parent.parent


def load_prompt_template() -> str:
    """Load shared prompt template from specs/.

    Returns:
        Prompt template string with {session_id}, {date}, {project} placeholders

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_aops_root() / "specs" / "session-insights-prompt.md"
    return template_path.read_text()


def substitute_prompt_variables(template: str, metadata: dict[str, str]) -> str:
    """Replace {session_id}, {date}, {project} placeholders in template.

    Args:
        template: Prompt template with {var} placeholders
        metadata: Dict with 'session_id', 'date', 'project' keys

    Returns:
        Template with placeholders replaced
    """
    for key, value in metadata.items():
        template = template.replace(f"{{{key}}}", value)
    return template


def extract_project_name() -> str:
    """Extract project name from current working directory.

    Returns:
        Project name (last component of cwd) or 'unknown'
    """
    try:
        cwd = Path.cwd()
        return cwd.name
    except Exception:
        return "unknown"


def extract_short_hash(session_id: str) -> str:
    """Extract 8-char hash from session_id.

    Args:
        session_id: Full session ID (may be long path-like string)

    Returns:
        8-character hash, or last 8 chars if not standard format
    """
    # Session IDs are typically 8-char hex strings or longer paths
    # Try to extract 8-char hex pattern first
    match = re.search(r"([0-9a-f]{8})", session_id.lower())
    if match:
        return match.group(1)
    # Fallback: return last 8 characters
    return session_id[-8:] if len(session_id) >= 8 else session_id


def extract_recent_context(session_id: str, max_turns: int = 20) -> str:
    """Extract recent conversation context from session.

    Args:
        session_id: Session identifier
        max_turns: Maximum number of conversation turns to extract

    Returns:
        Recent conversation as markdown string, or empty string if unavailable

    Note:
        This is a simplified implementation. For full transcript extraction,
        use session_reader.py or generate full transcript via session_transcript.py
    """
    # TODO: Implement actual transcript extraction
    # For now, return placeholder
    # In production, would use session_reader.extract_context_from_session()
    return f"[Recent context for session {session_id} - max {max_turns} turns]"


def call_claude_for_insights(
    prompt: str,
    transcript: str,
    operational_metrics: dict[str, Any],
    model: str = "claude-3-5-haiku-20241022",
) -> str:
    """Call Claude API to generate insights JSON.

    Args:
        prompt: Prepared prompt with metadata substituted
        transcript: Recent session transcript or context
        operational_metrics: Dict with workflows_used, subagents_invoked, etc.
        model: Claude model to use (default: haiku for speed/cost)

    Returns:
        JSON string from Claude response

    Raises:
        Exception: If API call fails or times out

    Note:
        This is a placeholder. Actual implementation needs Claude API integration.
        Consider using existing framework infrastructure if available.
    """
    # TODO: Implement actual Claude API call
    # For now, return mock response for testing
    raise NotImplementedError(
        "Claude API integration not yet implemented. "
        "This function needs to call Claude API with prompt + transcript + metrics."
    )


def validate_insights_schema(insights: dict[str, Any]) -> None:
    """Validate insights structure and types.

    Args:
        insights: Insights dictionary to validate

    Raises:
        InsightsValidationError: If validation fails
    """
    # Required fields with expected types
    required_fields = {
        "session_id": str,
        "date": str,
        "project": str,
        "summary": str,
        "outcome": str,
        "accomplishments": list,
    }

    # Check required fields exist and have correct types
    for field, expected_type in required_fields.items():
        if field not in insights:
            raise InsightsValidationError(f"Missing required field: {field}")
        if not isinstance(insights[field], expected_type):
            raise InsightsValidationError(
                f"Field '{field}' must be {expected_type.__name__}, "
                f"got {type(insights[field]).__name__}"
            )

    # Validate outcome enum
    valid_outcomes = {"success", "partial", "failure"}
    if insights["outcome"] not in valid_outcomes:
        raise InsightsValidationError(
            f"Field 'outcome' must be one of {valid_outcomes}, "
            f"got '{insights['outcome']}'"
        )

    # Validate date format (YYYY-MM-DD)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", insights["date"]):
        raise InsightsValidationError(
            f"Field 'date' must be YYYY-MM-DD format, got '{insights['date']}'"
        )

    # Validate optional array fields
    array_fields = [
        "accomplishments",
        "friction_points",
        "proposed_changes",
        "workflows_used",
        "subagents_invoked",
        "learning_observations",
        "context_gaps",
        "conversation_flow",
        "user_prompts",
        "workflow_improvements",
        "jit_context_needed",
        "context_distractions",
    ]
    for field in array_fields:
        if field in insights and not isinstance(insights[field], list):
            raise InsightsValidationError(f"Field '{field}' must be an array")

    # Validate numeric fields
    numeric_fields = [
        "subagent_count",
        "custodiet_blocks",
        "acceptance_criteria_count",
        "user_mood",
    ]
    for field in numeric_fields:
        if field in insights and insights[field] is not None:
            if not isinstance(insights[field], (int, float)):
                raise InsightsValidationError(f"Field '{field}' must be numeric")

    # Validate user_mood range if present
    if "user_mood" in insights and insights["user_mood"] is not None:
        mood = insights["user_mood"]
        if not (-1.0 <= mood <= 1.0):
            raise InsightsValidationError(
                f"Field 'user_mood' must be between -1.0 and 1.0, got {mood}"
            )

    # Validate bead tracking fields (optional, must be string or null)
    bead_tracking_fields = ["current_bead_id", "worker_name"]
    for field in bead_tracking_fields:
        if field in insights and insights[field] is not None:
            if not isinstance(insights[field], str):
                raise InsightsValidationError(
                    f"Field '{field}' must be a string or null, "
                    f"got {type(insights[field]).__name__}"
                )


def get_insights_file_path(
    date: str, session_id: str, index: int | None = None
) -> Path:
    """Get path to unified session JSON file in $ACA_SESSIONS.

    Args:
        date: Date string (YYYY-MM-DD format)
        session_id: 8-character session hash
        index: Optional index for multi-reflection sessions (0, 1, 2, etc.)
               If None or 0 with single reflection, uses base filename.

    Returns:
        Path to unified session file: $ACA_SESSIONS/{date}-{session_id}.json
        or {date}-{session_id}-{index}.json for multi-reflection sessions

    Note:
        As of v3.2.0, uses unified path combining insights + dashboard data.
        Legacy paths (sessions/insights/, sessions/dashboard/) are deprecated.
        v3.3.0: Uses $ACA_SESSIONS (sibling of $ACA_DATA, not inside it).
    """
    # Require $ACA_SESSIONS to be set - fail fast if not configured
    aca_sessions = os.environ.get("ACA_SESSIONS")
    if not aca_sessions:
        raise RuntimeError(
            "$ACA_SESSIONS environment variable not set.\n"
            "Add to ~/.bashrc or ~/.zshrc:\n"
            "  export ACA_SESSIONS='$HOME/writing/sessions'"
        )
    sessions_dir = Path(aca_sessions)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    if index is not None and index > 0:
        return sessions_dir / f"{date}-{session_id}-{index}.json"
    return sessions_dir / f"{date}-{session_id}.json"


def merge_insights(existing: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Merge new insights into existing insights.

    Strategy:
    1. Append list items (accomplishments, learnings, etc.)
    2. Overwrite scalars (summary, outcome, etc.)

    Args:
        existing: Existing insights dictionary
        new: New insights dictionary

    Returns:
        Merged insights dictionary
    """
    merged = existing.copy()

    for key, value in new.items():
        if key in merged and isinstance(merged[key], list) and isinstance(value, list):
            # Append new items to existing list
            # Avoid duplicates if possible? Simple append for now
            # TODO: Add deduplication logic if needed
            merged[key].extend(value)
        else:
            # Overwrite scalars or new keys
            merged[key] = value

    return merged


def write_insights_file(path: Path, insights: dict[str, Any]) -> None:
    """Atomically write insights JSON file.

    Uses temp file + rename pattern for atomic writes.

    Args:
        path: Target file path
        insights: Insights dictionary to write

    Raises:
        Exception: If write fails
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory
    fd, temp_path_str = tempfile.mkstemp(
        suffix=".json", prefix="insights-", dir=str(path.parent)
    )
    temp_path = Path(temp_path_str)

    try:
        # Write JSON with pretty formatting
        os.write(fd, json.dumps(insights, indent=2).encode())
        os.close(fd)
        # Atomic rename
        temp_path.rename(path)
    except Exception:
        # Cleanup on failure
        try:
            os.close(fd)
        except Exception:
            pass
        temp_path.unlink(missing_ok=True)
        raise


def generate_fallback_insights(
    metadata: dict[str, str], operational_metrics: dict[str, Any]
) -> dict[str, Any]:
    """Generate minimal fallback insights when LLM generation fails.

    Args:
        metadata: Dict with session_id, date, project
        operational_metrics: Dict with workflows_used, subagents_invoked, etc.

    Returns:
        Minimal valid insights dictionary
    """
    return {
        **metadata,
        **operational_metrics,
        "summary": "Session completed",
        "outcome": "partial",
        "accomplishments": [],
        "friction_points": [],
        "proposed_changes": [],
    }


def extract_json_from_response(response: str) -> str:
    """Extract JSON from LLM response (may be wrapped in markdown fence).

    Args:
        response: LLM response text

    Returns:
        Extracted JSON string

    Note:
        Handles both plain JSON and JSON wrapped in ```json...``` fence
    """
    # Check for markdown code fence
    if "```json" in response:
        # Extract content between ```json and ```
        match = re.search(r"```json\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return match.group(1)
    elif "```" in response:
        # Generic code fence
        match = re.search(r"```\s*\n(.*?)\n```", response, re.DOTALL)
        if match:
            return match.group(1)

    # No fence found, assume plain JSON
    return response.strip()
