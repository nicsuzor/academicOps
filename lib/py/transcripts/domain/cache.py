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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from transcripts.model import NormalizedSession

logger = logging.getLogger(__name__)

EXPIRATION_SECONDS = 30 * 24 * 3600  # 30 days (~1 month)


def _file_content_hash(path: Path) -> str:
    """Hash a single file based on st_size + sha256(first_1KB + last_1KB).

    Immune to filesystem timestamp changes (e.g. git pull, checkout, or touch).
    """
    try:
        stat = path.stat()
    except OSError:
        return f"{path}:missing"

    size = stat.st_size
    if size == 0:
        return f"{path}:0:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    try:
        with path.open("rb") as f:
            if size <= 2048:
                chunk = f.read()
            else:
                head = f.read(1024)
                f.seek(-1024, 2)
                tail = f.read(1024)
                chunk = head + tail
            digest = hashlib.sha256(chunk).hexdigest()
            return f"{path}:{size}:{digest}"
    except OSError:
        return f"{path}:error"


def source_fingerprint(paths: Iterable[Path]) -> str:
    """Fingerprint the source files a session was reconstructed from.

    Uses st_size + sha256(first_1KB + last_1KB) content hashing, making the digest
    invariant across git pull, git checkout, or filesystem timestamp touches.
    """
    parts = [_file_content_hash(p) for p in sorted(paths, key=str)]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


class SkipCache:
    """Skip sessions that rendered to nothing, until their source files change.

    Entries expire after 30 days (1 month).
    """

    def __init__(self, cache_file: Path, expiration_seconds: float = EXPIRATION_SECONDS) -> None:
        self.cache_file = cache_file
        self.expiration_seconds = expiration_seconds
        self.empty_sessions: dict[str, dict[str, Any]] = {}
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

        now = datetime.now(UTC).timestamp()
        if isinstance(data, dict):
            cleaned: dict[str, dict[str, Any]] = {}
            for key, val in data.items():
                if isinstance(val, str):
                    # Legacy string fingerprint format: convert to dict with current timestamp
                    cleaned[str(key)] = {"fingerprint": val, "ts": now}
                elif isinstance(val, dict) and "fingerprint" in val:
                    ts = float(val.get("ts", now))
                    if now - ts < self.expiration_seconds:
                        cleaned[str(key)] = {"fingerprint": str(val["fingerprint"]), "ts": ts}
            self.empty_sessions = cleaned
        else:
            # Legacy cache format: drop and re-examine
            logger.info(
                "skip-cache at %s has legacy format; re-examining every session once",
                self.cache_file,
            )
            self.empty_sessions = {}

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.cache_file.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(self.empty_sessions, indent=2, sort_keys=True), encoding="utf-8"
            )
            tmp_path.replace(self.cache_file)
        except Exception:
            logger.exception("Failed to save skip-cache to %s", self.cache_file)

    def is_skipped(self, key: str, fingerprint: str) -> bool:
        """True only if `key` was recorded empty, unchanged, and not expired."""
        entry = self.empty_sessions.get(key)
        if not entry:
            return False
        if entry.get("fingerprint") != fingerprint:
            return False
        ts = float(entry.get("ts", 0))
        now = datetime.now(UTC).timestamp()
        if now - ts >= self.expiration_seconds:
            self.empty_sessions.pop(key, None)
            self.save()
            return False
        return True

    def mark_empty(self, key: str, fingerprint: str) -> None:
        now = datetime.now(UTC).timestamp()
        self.empty_sessions[key] = {"fingerprint": fingerprint, "ts": now}
        self.save()

    def mark_processed(self, key: str, fingerprint: str) -> None:
        """Record a successfully rendered session so unchanged runs skip re-parsing."""
        now = datetime.now(UTC).timestamp()
        self.empty_sessions[key] = {"fingerprint": fingerprint, "ts": now}
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
