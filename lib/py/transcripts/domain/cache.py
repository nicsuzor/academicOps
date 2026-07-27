"""Persistent incremental skip-cache for empty sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from transcripts.model import NormalizedSession

logger = logging.getLogger(__name__)


class SkipCache:
    """Incremental cache for skipping empty sessions."""

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self.empty_sessions: set[str] = set()
        self.load()

    def load(self) -> None:
        if self.cache_file.exists():
            try:
                data = json.loads(self.cache_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.empty_sessions = set(data)
            except Exception:
                logger.warning("Failed to load skip-cache from %s, starting fresh", self.cache_file)
                self.empty_sessions = set()

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(sorted(list(self.empty_sessions)), indent=2), encoding="utf-8"
            )
        except Exception:
            logger.exception("Failed to save skip-cache to %s", self.cache_file)

    def is_skipped(self, session_id: str) -> bool:
        return session_id in self.empty_sessions

    def mark_empty(self, session_id: str) -> None:
        self.empty_sessions.add(session_id)
        self.save()


def is_session_empty(session: NormalizedSession) -> bool:
    """Decide if a session is empty (contains no actual user or model activity)."""
    if not session.events:
        return True

    # Session is not empty if it has user prompts or model responses with meaningful content
    for event in session.events:
        if event.source in ("user", "model") and event.type == "message" and event.content:
            # Filter out generic system message or hooks if they somehow end up mapped as user/model
            if event.content.strip():
                return False
    return True
