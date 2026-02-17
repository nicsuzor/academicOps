"""Session insights generation library.

Provides unified functions for generating session insights via LLM (Claude/Gemini).
Used by both automatic generation (Stop hook) and manual generation (skill).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from lib.paths import get_aops_home, get_plugin_root
from lib.session_reader import extract_gate_context, find_sessions


class InsightsValidationError(Exception):
    pass


def load_prompt_template() -> str:
    """Load shared prompt template from specs/.

    Returns:
        Prompt template string with {session_id}, {date}, {project} placeholders

    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_plugin_root() / "specs" / "session-insights-prompt.md"
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
        session_id: Session identifier (full ID, short hash, or file path)
        max_turns: Maximum number of conversation turns to extract

    Returns:
        Recent conversation as markdown string, or empty string if unavailable
    """
    # 1. Determine session file path
    session_path = None

    # Check if session_id is already a path to an existing file
    potential_path = Path(session_id)
    if potential_path.exists() and potential_path.is_file():
        session_path = potential_path
    else:
        # Search for the session by ID or short hash
        short_hash = extract_short_hash(session_id)
        sessions = find_sessions()
        for s in sessions:
            sid_lower = s.session_id.lower()
            input_lower = session_id.lower()
            # Match by:
            # 1. Exact ID
            # 2. Input is a prefix of the session ID (common UX for hashes)
            # 3. Session ID matches the extracted short hash of the input
            if (
                sid_lower == input_lower
                or sid_lower.startswith(input_lower)
                or sid_lower == short_hash.lower()
            ):
                session_path = s.path
                break

    if not session_path:
        return ""

    # 2. Extract recent conversation context
    try:
        ctx = extract_gate_context(session_path, include={"conversation"}, max_turns=max_turns)
        conversation = ctx.get("conversation", [])
        if not conversation:
            return ""

        # Join turns with double newlines for markdown readability
        return "\n\n".join(conversation)
    except Exception:
        # Fail gracefully
        return ""


def _validate_framework_reflections(reflections: list[dict[str, Any]]) -> None:
    """Validate framework_reflections array structure.

    Expected structure for each reflection:
    {
        "prompts": str,
        "guidance_received": str | None,
        "followed": bool,
        "outcome": "success" | "partial" | "failure",
        "accomplishments": list[str],
        "friction_points": list[str],
        "root_cause": str | None,
        "proposed_changes": list[str],
        "next_step": str | None,
        "quick_exit": bool (optional)
    }

    Args:
        reflections: List of reflection dictionaries to validate

    Raises:
        InsightsValidationError: If validation fails
    """
    if not isinstance(reflections, list):
        raise InsightsValidationError(
            f"Field 'framework_reflections' must be a list, got {type(reflections).__name__}"
        )

    valid_outcomes = {"success", "partial", "failure"}

    for i, reflection in enumerate(reflections):
        if not isinstance(reflection, dict):
            raise InsightsValidationError(
                f"Field 'framework_reflections[{i}]' must be a dict, got {type(reflection).__name__}"
            )

        # Validate outcome if present
        if "outcome" in reflection and reflection["outcome"] is not None:
            if reflection["outcome"] not in valid_outcomes:
                raise InsightsValidationError(
                    f"Field 'framework_reflections[{i}].outcome' must be one of {valid_outcomes}, "
                    f"got '{reflection['outcome']}'"
                )

        # Validate and coerce followed to boolean if present
        # Accept: bool, int (0/1), strings ("true"/"false", "yes"/"no", "1"/"0")
        if "followed" in reflection and reflection["followed"] is not None:
            val = reflection["followed"]
            if isinstance(val, bool):
                pass  # Already valid
            elif isinstance(val, int):
                reflection["followed"] = bool(val)
            elif isinstance(val, str):
                lower_val = val.lower().strip()
                if lower_val in ("true", "yes", "1", "y"):
                    reflection["followed"] = True
                elif lower_val in ("false", "no", "0", "n", ""):
                    reflection["followed"] = False
                else:
                    raise InsightsValidationError(
                        f"Field 'framework_reflections[{i}].followed' cannot be coerced "
                        f"to boolean from string '{val}'"
                    )
            else:
                raise InsightsValidationError(
                    f"Field 'framework_reflections[{i}].followed' must be a boolean "
                    f"or coercible value, got {type(val).__name__}"
                )

        # Validate list fields
        list_fields = ["accomplishments", "friction_points", "proposed_changes"]
        for field in list_fields:
            if field in reflection and reflection[field] is not None:
                if not isinstance(reflection[field], list):
                    raise InsightsValidationError(
                        f"Field 'framework_reflections[{i}].{field}' must be a list"
                    )


def _validate_token_metrics(token_metrics: dict[str, Any]) -> None:
    """Validate token_metrics nested structure.

    Expected structure:
    {
        "totals": {"input_tokens": int, "output_tokens": int, ...},
        "by_model": {"model_name": {"input": int, "output": int}, ...},
        "by_agent": {"agent_name": {"input": int, "output": int}, ...},
        "efficiency": {"cache_hit_rate": float, "tokens_per_minute": float, ...}
    }

    Args:
        token_metrics: token_metrics dictionary to validate

    Raises:
        InsightsValidationError: If validation fails
    """
    if not isinstance(token_metrics, dict):
        raise InsightsValidationError(
            f"Field 'token_metrics' must be a dict, got {type(token_metrics).__name__}"
        )

    # Validate 'totals' sub-object (optional but must be dict if present)
    if "totals" in token_metrics:
        totals = token_metrics["totals"]
        if not isinstance(totals, dict):
            raise InsightsValidationError(
                f"Field 'token_metrics.totals' must be a dict, got {type(totals).__name__}"
            )
        # Validate numeric fields in totals
        totals_numeric_fields = [
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_create_tokens",
        ]
        for field in totals_numeric_fields:
            if field in totals and totals[field] is not None:
                if not isinstance(totals[field], int | float):
                    raise InsightsValidationError(
                        f"Field 'token_metrics.totals.{field}' must be numeric"
                    )

    # Validate 'by_model' sub-object (optional but must be dict if present)
    if "by_model" in token_metrics:
        by_model = token_metrics["by_model"]
        if not isinstance(by_model, dict):
            raise InsightsValidationError(
                f"Field 'token_metrics.by_model' must be a dict, got {type(by_model).__name__}"
            )
        # Each model entry should be a dict with numeric values
        for model_name, model_data in by_model.items():
            if not isinstance(model_data, dict):
                raise InsightsValidationError(
                    f"Field 'token_metrics.by_model.{model_name}' must be a dict"
                )

    # Validate 'by_agent' sub-object (optional but must be dict if present)
    if "by_agent" in token_metrics:
        by_agent = token_metrics["by_agent"]
        if not isinstance(by_agent, dict):
            raise InsightsValidationError(
                f"Field 'token_metrics.by_agent' must be a dict, got {type(by_agent).__name__}"
            )
        # Each agent entry should be a dict with numeric values
        for agent_name, agent_data in by_agent.items():
            if not isinstance(agent_data, dict):
                raise InsightsValidationError(
                    f"Field 'token_metrics.by_agent.{agent_name}' must be a dict"
                )

    # Validate 'efficiency' sub-object (optional but must be dict if present)
    if "efficiency" in token_metrics:
        efficiency = token_metrics["efficiency"]
        if not isinstance(efficiency, dict):
            raise InsightsValidationError(
                f"Field 'token_metrics.efficiency' must be a dict, got {type(efficiency).__name__}"
            )
        # Validate numeric fields in efficiency
        efficiency_numeric_fields = [
            "cache_hit_rate",
            "tokens_per_minute",
            "session_duration_minutes",
        ]
        for field in efficiency_numeric_fields:
            if field in efficiency and efficiency[field] is not None:
                if not isinstance(efficiency[field], int | float):
                    raise InsightsValidationError(
                        f"Field 'token_metrics.efficiency.{field}' must be numeric"
                    )
        # Validate cache_hit_rate range if present (0.0 to 1.0)
        if "cache_hit_rate" in efficiency and efficiency["cache_hit_rate"] is not None:
            rate = efficiency["cache_hit_rate"]
            if isinstance(rate, int | float) and not (0.0 <= rate <= 1.0):
                raise InsightsValidationError(
                    f"Field 'token_metrics.efficiency.cache_hit_rate' must be between 0.0 and 1.0, got {rate}"
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
            f"Field 'outcome' must be one of {valid_outcomes}, got '{insights['outcome']}'"
        )

    # Validate date format (ISO 8601: YYYY-MM-DD or full timestamp with tz)
    date_val = insights["date"]
    # Accept YYYY-MM-DD or full ISO 8601 (e.g., 2026-01-20T14:30:00+00:00)
    if not (
        re.match(r"^\d{4}-\d{2}-\d{2}$", date_val)
        or re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", date_val)
    ):
        raise InsightsValidationError(
            f"Field 'date' must be ISO 8601 format (YYYY-MM-DD or full timestamp), got '{date_val}'"
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
        "framework_reflections",
        "timeline_events",
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
            if not isinstance(insights[field], int | float):
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

    # Validate token_metrics structure (optional)
    if "token_metrics" in insights and insights["token_metrics"] is not None:
        _validate_token_metrics(insights["token_metrics"])

    # Validate framework_reflections structure (optional)
    if "framework_reflections" in insights and insights["framework_reflections"] is not None:
        _validate_framework_reflections(insights["framework_reflections"])


def get_summaries_dir() -> Path:
    """Get summaries directory (~/.aops/summaries/).

    Returns:
        Path to summaries directory
    """
    summaries_dir = get_aops_home() / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    return summaries_dir


def find_existing_insights(date: str, session_id: str) -> Path | None:
    """Find existing insights file for a session ID.

    Args:
        date: Date string (YYYY-MM-DD format or ISO 8601)
        session_id: 8-character session hash

    Returns:
        Path to existing insights file if found, None otherwise
    """
    summaries_dir = get_summaries_dir()
    date_compact = date[:10].replace("-", "") if "T" in date else date.replace("-", "")

    # Search for insights with this session_id
    # v3.7.0+ format: YYYYMMDD-HH-project-session_id-slug.json
    # v3.6.0 format: YYYYMMDD-project-session_id-slug.json
    # v3.5.0 format: YYYYMMDD-session_id-slug.json
    # Legacy formats also supported for backwards compatibility
    patterns = [
        f"{date_compact}-??-*-{session_id}-*.json",  # v3.7.0: date-hour-project-sessionid-slug
        f"{date_compact}-??-*-{session_id}.json",  # v3.7.0: date-hour-project-sessionid (no slug)
        f"{date_compact}-??-{session_id}-*.json",  # v3.7.0: date-hour-sessionid-slug
        f"{date_compact}-??-{session_id}.json",  # v3.7.0: date-hour-sessionid (no slug)
        f"{date_compact}-*-{session_id}-*.json",  # v3.6.0: date-project-sessionid-slug
        f"{date_compact}-*-{session_id}.json",  # v3.6.0: date-project-sessionid (no slug)
        f"{date_compact}-{session_id}-*.json",  # v3.5.0: date-sessionid-slug
        f"{date_compact}-{session_id}.json",  # v3.5.0: date-sessionid (no slug)
        f"{date_compact}-*{session_id}*.json",  # Legacy: session_id anywhere
        f"{date[:10]}-{session_id}.json",  # Old format with dashes in date
    ]

    for pattern in patterns:
        matches = list(summaries_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def _sanitize_filename_segment(segment: str) -> str:
    """Sanitize a string for use in filenames.

    Args:
        segment: Raw string (e.g., project name)

    Returns:
        Lowercase string with only alphanumeric chars and hyphens
    """
    # Replace spaces and underscores with hyphens
    sanitized = segment.lower().replace(" ", "-").replace("_", "-")
    # Keep only alphanumeric and hyphens
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
    # Collapse multiple hyphens
    sanitized = re.sub(r"-+", "-", sanitized)
    # Strip leading/trailing hyphens
    return sanitized.strip("-")


def get_insights_file_path(
    date: str,
    session_id: str,
    slug: str = "",
    index: int | None = None,
    project: str = "",
    hour: str | None = None,
) -> Path:
    """Get path to unified session JSON file in summaries/.

    Args:
        date: Date string (YYYY-MM-DD format or ISO 8601 with timezone)
        session_id: 8-character session hash
        slug: Short descriptive slug for the session (e.g., "refactor-insights")
        index: Optional index for multi-reflection sessions (0, 1, 2, etc.)
               If None or 0 with single reflection, uses base filename.
        project: Project name to include in filename for traceability
        hour: Optional 2-digit hour (24-hour format). If not provided, extracted from
              ISO 8601 date or defaults to current hour.

    Returns:
        Path to session file: summaries/YYYYMMDD-HH-{project}-{session_id}-{slug}.json
        or YYYYMMDD-HH-{project}-{session_id}-{slug}-{index}.json for multi-reflection sessions

    Note:
        v3.4.0: Output moved to summaries/ subdirectory, filename uses YYYYMMDD-slug format.
        v3.5.0: Always include session_id in filename to prevent collisions.
        v3.6.0: Include project name for relationship traceability with transcripts.
        v3.7.0: Include 24-hour component (HH) for better sorting and timezone awareness.
    """
    summaries_dir = get_summaries_dir()

    # Extract date and hour components
    if "T" in date:
        # ISO 8601 format: 2026-01-24T17:30:00+10:00
        date_compact = date[:10].replace("-", "")
        if hour is None:
            hour = date[11:13]
    else:
        # Simple YYYY-MM-DD format
        date_compact = date.replace("-", "")
        if hour is None:
            hour = datetime.now().astimezone().strftime("%H")

    # Sanitize project name for filesystem safety
    safe_project = _sanitize_filename_segment(project) if project else ""

    # Build filename: YYYYMMDD-HH-project-session_id-slug.json
    # Matches transcript format: YYYYMMDD-HH-project-sessionid-slug-full.md
    parts = [date_compact, hour]
    if safe_project:
        parts.append(safe_project)
    parts.append(session_id)
    if slug:
        parts.append(slug)

    base = "-".join(parts)

    if index is not None and index > 0:
        return summaries_dir / f"{base}-{index}.json"
    return summaries_dir / f"{base}.json"


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


def write_insights_file(
    path: Path, insights: dict[str, Any], session_id: str | None = None
) -> None:
    """Atomically write insights JSON file.

    Uses temp file + rename pattern for atomic writes.
    Optionally loads and merges base information from session status file.

    Args:
        path: Target file path
        insights: Insights dictionary to write
        session_id: Optional session ID to load status file for enrichment

    Raises:
        Exception: If write fails
    """
    # Merge with status file data if session_id provided
    if session_id:
        status_dir = Path.home() / "writing" / "sessions" / "status"
        # Try to find status file by session_id with various naming patterns
        # Status files may be named YYYYMMDD-sessionid.json or just sessionid.json
        status_path = None

        # First, extract date from insights if available for pattern matching
        date_str = insights.get("date", "")
        date_compact = date_str.replace("-", "") if date_str else ""

        # Try patterns (with date first since that's more specific)
        patterns_to_try = []
        if date_compact:
            patterns_to_try.append(status_dir / f"{date_compact}-{session_id}.json")
        patterns_to_try.append(status_dir / f"{session_id}.json")
        # Fallback: search with glob for pattern matching (handles renamed files)
        if date_compact:
            patterns_to_try.extend(status_dir.glob(f"{date_compact}-*{session_id}*.json"))
        patterns_to_try.extend(status_dir.glob(f"*{session_id}*.json"))

        for candidate in patterns_to_try:
            if isinstance(candidate, Path) and candidate.exists():
                status_path = candidate
                break

        if status_path:
            try:
                with open(status_path, encoding="utf-8") as f:
                    status_data = json.load(f)
                # Extract insights from status and merge into insights dict
                # Handle both formats:
                # - New format: {"session_id": ..., "insights": {...}}
                # - Old format: {"session_id": ..., "outcome": ..., "accomplishments": ...}
                if "insights" in status_data:
                    # New format: nested insights object
                    status_insights = status_data["insights"]
                else:
                    # Old format: insights data at top level
                    status_insights = status_data
                # Merge: status insights provide base info, new insights override
                insights = {**status_insights, **insights}
            except (json.JSONDecodeError, OSError) as e:
                print(f"⚠️  Warning: Could not load status file {status_path}: {e}")

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory
    fd, temp_path_str = tempfile.mkstemp(suffix=".json", prefix="insights-", dir=str(path.parent))
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
