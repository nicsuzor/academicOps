import json
from pathlib import Path


class SkipCache:
    """Persistent incremental cache of already-decided-empty sessions.

    This avoids re-rendering empty/meaningless sessions on every batch run
    (adhoc-sessions-e39d1741).
    """

    def __init__(self, cache_file_path: Path):
        self.cache_file_path = cache_file_path
        self._empty_sessions: set[str] = self._load()

    def _load(self) -> set[str]:
        if not self.cache_file_path.exists():
            return set()
        try:
            data = json.loads(self.cache_file_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return set(data)
        except Exception:
            pass
        return set()

    def save(self) -> None:
        try:
            self.cache_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file_path.write_text(
                json.dumps(sorted(list(self._empty_sessions)), indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def is_empty(self, session_id: str) -> bool:
        return session_id in self._empty_sessions

    def mark_empty(self, session_id: str) -> None:
        self._empty_sessions.add(session_id)
        self.save()

    def unmark_empty(self, session_id: str) -> None:
        if session_id in self._empty_sessions:
            self._empty_sessions.remove(session_id)
            self.save()
