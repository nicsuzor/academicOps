"""Tests for context-map injection caching in router._inject_context_map_hints.

Verifies that the session-level cache in state.state[_CONTEXT_MAP_CACHE_KEY]
correctly serves cached hints on warm hits and invalidates on mtime or cwd changes.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

AOPS_CORE_DIR = Path(__file__).parent.parent.parent / "aops-core"
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import _CONTEXT_MAP_CACHE_KEY, HookRouter
from hooks.schemas import CanonicalHookOutput, HookContext
from lib.session_state import SessionState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_DOCS = [
    {"path": "README.md", "description": "Project overview"},
    {"path": "aops-core/AXIOMS.md", "description": "Inviolable principles"},
]


def _make_ctx(cwd: str | None = "/repo") -> HookContext:
    return HookContext(
        hook_event="UserPromptSubmit",
        session_id="test-session-123",
        cwd=cwd,
        raw_input={},
    )


def _make_state() -> SessionState:
    state = SessionState.create("test-session-123")
    return state


def _make_router(monkeypatch) -> HookRouter:
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


def _write_context_map(tmp_path: Path, docs=None) -> Path:
    """Write a context-map.json under tmp_path/.agents/."""
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir(exist_ok=True)
    map_file = agents_dir / "context-map.json"
    map_file.write_text(json.dumps({"docs": docs or SAMPLE_DOCS}))
    return map_file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestContextMapCacheColdStart:
    def test_cold_start_populates_cache(self, tmp_path, monkeypatch):
        """First call reads from disk and stores entry in state.state."""
        map_file = _write_context_map(tmp_path)
        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        assert result.context_injection is not None
        assert "README.md" in result.context_injection
        cache = state.state.get(_CONTEXT_MAP_CACHE_KEY)
        assert cache is not None
        assert cache["cwd"] == str(tmp_path)
        assert cache["mtime"] == map_file.stat().st_mtime
        assert "README.md" in cache["hint"]

    def test_cold_start_no_file_returns_nothing(self, tmp_path, monkeypatch):
        """No context-map.json → no injection, no cache entry."""
        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        assert result.context_injection is None
        assert _CONTEXT_MAP_CACHE_KEY not in state.state


class TestContextMapCacheWarmHit:
    def test_warm_hit_skips_disk_read(self, tmp_path, monkeypatch):
        """Second call with same cwd + mtime uses cache, not load_context_map."""
        map_file = _write_context_map(tmp_path)
        mtime = map_file.stat().st_mtime

        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        # Pre-populate cache as if a prior invocation already ran
        state.state[_CONTEXT_MAP_CACHE_KEY] = {
            "cwd": str(tmp_path),
            "mtime": mtime,
            "hint": "CACHED_HINT",
        }
        result = CanonicalHookOutput()

        with patch("lib.context_map.load_context_map") as mock_load:
            router._inject_context_map_hints(ctx, state, result)
            mock_load.assert_not_called()

        assert result.context_injection == "CACHED_HINT"

    def test_warm_hit_returns_cached_hint_unchanged(self, tmp_path, monkeypatch):
        """Cached hint string is injected verbatim on warm hit."""
        map_file = _write_context_map(tmp_path)
        expected = "# Cached context map hint"
        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        state.state[_CONTEXT_MAP_CACHE_KEY] = {
            "cwd": str(tmp_path),
            "mtime": map_file.stat().st_mtime,
            "hint": expected,
        }
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        assert result.context_injection == expected


class TestContextMapCacheInvalidation:
    def test_mtime_change_triggers_reload(self, tmp_path, monkeypatch):
        """Stale mtime in cache entry forces a fresh disk read."""
        map_file = _write_context_map(tmp_path)
        stale_mtime = map_file.stat().st_mtime - 1.0

        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        state.state[_CONTEXT_MAP_CACHE_KEY] = {
            "cwd": str(tmp_path),
            "mtime": stale_mtime,
            "hint": "STALE_HINT",
        }
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        # Cache should be refreshed with the current mtime
        cache = state.state.get(_CONTEXT_MAP_CACHE_KEY)
        assert cache["mtime"] == map_file.stat().st_mtime
        assert cache["mtime"] != stale_mtime
        # Fresh hint from disk should contain real content
        assert "README.md" in result.context_injection

    def test_cwd_change_triggers_reload(self, tmp_path, monkeypatch):
        """Different cwd in incoming ctx invalidates the cached entry."""
        map_file = _write_context_map(tmp_path)
        router = _make_router(monkeypatch)

        # Cache entry points at a different directory
        ctx = _make_ctx(cwd=str(tmp_path))
        state = _make_state()
        state.state[_CONTEXT_MAP_CACHE_KEY] = {
            "cwd": "/some/other/repo",
            "mtime": map_file.stat().st_mtime,
            "hint": "WRONG_HINT",
        }
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        cache = state.state.get(_CONTEXT_MAP_CACHE_KEY)
        assert cache["cwd"] == str(tmp_path)
        assert "README.md" in result.context_injection


class TestContextMapCacheSessionStartClear:
    def test_session_start_clears_cache(self, tmp_path, monkeypatch):
        """SessionStart event removes the context-map cache entry from state."""
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()

        state = _make_state()
        state.state[_CONTEXT_MAP_CACHE_KEY] = {
            "cwd": "/old/repo",
            "mtime": 12345.0,
            "hint": "OLD_HINT",
        }
        merged = CanonicalHookOutput()
        ctx = HookContext(
            hook_event="SessionStart",
            session_id="test-session-123",
            cwd=str(tmp_path),
            raw_input={},
        )

        with patch("hooks.session_env_setup.run_session_env_setup", return_value=None):
            router._run_special_handlers(ctx, state, merged)

        assert _CONTEXT_MAP_CACHE_KEY not in state.state

    def test_session_start_no_error_when_cache_absent(self, tmp_path, monkeypatch):
        """SessionStart cache clear is a no-op when no cache entry exists."""
        monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
        router = HookRouter()
        state = _make_state()
        merged = CanonicalHookOutput()
        ctx = HookContext(
            hook_event="SessionStart",
            session_id="test-session-123",
            cwd=str(tmp_path),
            raw_input={},
        )

        with patch("hooks.session_env_setup.run_session_env_setup", return_value=None):
            router._run_special_handlers(ctx, state, merged)

        assert _CONTEXT_MAP_CACHE_KEY not in state.state


class TestContextMapCacheNoCwd:
    def test_no_cwd_returns_early(self, monkeypatch):
        """ctx.cwd is None → no injection, no cache entry created."""
        router = _make_router(monkeypatch)
        ctx = _make_ctx(cwd=None)
        state = _make_state()
        result = CanonicalHookOutput()

        router._inject_context_map_hints(ctx, state, result)

        assert result.context_injection is None
        assert _CONTEXT_MAP_CACHE_KEY not in state.state
