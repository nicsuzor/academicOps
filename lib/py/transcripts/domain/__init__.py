"""Layer B Domain modules for transcripts.

This subpackage contains all academicOps domain logic, including:
- stable slug generation
- semantic user context classification
- event-derived timestamps extraction
- skip-cache checking and management
- interactive sessions selection
- correlation inference
- insights extraction
- rendering (markdown, HTML, JSON)
- git sync automation
- prompt ledger generation
"""

from transcripts.domain.cache import SkipCache, is_session_empty, source_fingerprint
from transcripts.domain.context import has_user_context
from transcripts.domain.correlation import infer_correlation
from transcripts.domain.insights import infer_insights
from transcripts.domain.ledger import generate_prompt_ledger
from transcripts.domain.renderer import render_session_to_all_formats, render_to_full_markdown
from transcripts.domain.skills import (
    DELIBERATELY_REMOVED_SKILLS,
    SkillStatus,
    diagnose_skill,
    diagnose_skill_status,
    get_all_skills_diagnostics,
    is_deliberately_removed,
)
from transcripts.domain.slug import get_stable_slug
from transcripts.domain.sync import git_sync_sessions
from transcripts.domain.tasks import (
    create_task,
    list_tasks,
    update_task,
    validate_task_timestamps,
)
from transcripts.domain.time import (
    BRISBANE_TZ,
    bucket_due_date,
    bucket_tasks_by_due_date,
    format_iso_utc,
    get_brisbane_today,
    get_event_timestamps,
    parse_due_date,
    parse_iso_utc,
)
from transcripts.domain.view import select_recent_interactive

__all__ = [
    "get_stable_slug",
    "has_user_context",
    "get_event_timestamps",
    "get_brisbane_today",
    "parse_due_date",
    "bucket_due_date",
    "bucket_tasks_by_due_date",
    "BRISBANE_TZ",
    "format_iso_utc",
    "parse_iso_utc",
    "create_task",
    "update_task",
    "validate_task_timestamps",
    "list_tasks",
    "SkipCache",
    "is_session_empty",
    "source_fingerprint",
    "select_recent_interactive",
    "infer_correlation",
    "infer_insights",
    "render_session_to_all_formats",
    "render_to_full_markdown",
    "git_sync_sessions",
    "generate_prompt_ledger",
    "SkillStatus",
    "DELIBERATELY_REMOVED_SKILLS",
    "is_deliberately_removed",
    "diagnose_skill_status",
    "diagnose_skill",
    "get_all_skills_diagnostics",
]
