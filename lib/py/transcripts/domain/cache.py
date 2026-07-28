"""Persistent incremental skip-cache for empty sessions.

The cache records *what the source looked like* when a session rendered to
nothing, not merely that it did. A session caught seconds after it started is
empty then and interesting a minute later; keying on a fingerprint of its
source files means the next run re-examines it as soon as anything is written,
while a session that is genuinely finished and genuinely empty stays skipped
for free.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Iterable
from pathlib import Path

from transcripts.model import NormalizedSession

logger = logging.getLogger(__name__)


def source_fingerprint(paths: Iterable[Path]) -> str:
    """Fingerprint the source files a session was reconstructed from.

    Any append, truncation, or newly added subagent log changes the digest and
    therefore invalidates the cache entry.
    """
    parts: list[str] = []
    for path in sorted(paths, key=str):
        try:
            stat = path.stat()
        except OSError:
            parts.append(f"{path}:missing")
        else:
            parts.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


class SkipCache:
    """Skip sessions that rendered to nothing, until their source files change."""

    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self.empty_sessions: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if not self.cache_file.exists():
            return
        try:
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to load skip-cache from %s, starting fresh", self.cache_file)
            self.empty_sessions = {}
            return

        if isinstance(data, dict):
            self.empty_sessions = {
                str(key): str(value) for key, value in data.items() if isinstance(value, str)
            }
        else:
            # A cache written before entries carried a fingerprint cannot say
            # whether its sessions have since grown. Drop it and re-examine.
            logger.info(
                "skip-cache at %s has no source fingerprints; re-examining every session once",
                self.cache_file,
            )
            self.empty_sessions = {}

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(
                json.dumps(self.empty_sessions, indent=2, sort_keys=True), encoding="utf-8"
            )
        except Exception:
            logger.exception("Failed to save skip-cache to %s", self.cache_file)

    def is_skipped(self, key: str, fingerprint: str) -> bool:
        """True only if `key` was recorded empty and its sources are unchanged since."""
        return self.empty_sessions.get(key) == fingerprint

    def mark_empty(self, key: str, fingerprint: str) -> None:
        self.empty_sessions[key] = fingerprint
        self.save()

    def forget(self, key: str) -> None:
        """Drop a key that has since produced output, so the cache stays honest."""
        if self.empty_sessions.pop(key, None) is not None:
            self.save()


def is_session_empty(session: NormalizedSession) -> bool:
    """Decide if a session is empty (contains no actual user or model activity)."""
    if not session.events and not session.subagents:
        return True

    # Session is not empty if it has user prompts or model responses with meaningful content
    for events in (session.events, *(sub.events for sub in session.subagents)):
        for event in events:
            if event.source in ("user", "model") and event.type == "message" and event.content:
                # Filter out generic system message or hooks if they somehow end up mapped as user/model
                if event.content.strip():
                    return False
    return True
