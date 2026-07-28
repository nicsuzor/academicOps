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
from transcripts.domain.slug import get_stable_slug
from transcripts.domain.sync import git_sync_sessions
from transcripts.domain.time import get_event_timestamps
from transcripts.domain.view import select_recent_interactive

__all__ = [
    "get_stable_slug",
    "has_user_context",
    "get_event_timestamps",
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
]
