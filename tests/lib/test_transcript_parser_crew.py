"""Regression tests for crew metadata in transcript_parser (issue #768).

When `transcript.py` (or any caller of `SessionProcessor.parse_session_file`)
runs offline against a previously-captured session file — e.g. inside
`sync_gha_sessions.py`, which is itself often scheduled from a crew worker —
the env var `POLECAT_CREW_NAME` reflects the *transcribing* process, not the
original session. Using it as a fallback for `summary.crew` taints
GHA-sourced transcripts with a bogus crew label.

The fix: drop the env-var fallback entirely. Crew is data-about-the-session
and must be inferred from path-based signals only (filename shortform or
`crew/<name>/` path segment). For github/ and polecats/ paths, crew is
explicitly None.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from lib.transcript_parser import SessionProcessor, reflection_to_insights


@pytest.fixture
def processor() -> SessionProcessor:
    return SessionProcessor()


def _write_empty_jsonl(path: Path) -> None:
    """Write an empty (but valid) JSONL file. parse_session_file accepts this
    and returns a default ParsedSession, which is enough to exercise the
    augmentation logic at the top of the method."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


class TestCrewEnvFallbackRemoved:
    """Issue #768: POLECAT_CREW_NAME must not leak into summary.crew."""

    def test_gha_path_with_env_crew_yields_none(
        self, processor: SessionProcessor, tmp_path: Path
    ) -> None:
        """GHA-sourced transcript: POLECAT_CREW_NAME in env, github/ in path
        → summary.crew MUST be None (not the env value).

        This is the exact regression from issue #768: 131 GHA transcripts
        were stamped with crew=<sync-runner's crew> after #765/#766.
        """
        # Synthetic GHA path: $AOPS_SESSIONS/github/<repo>/<run_id>/<attempt>/<sid>.jsonl
        sid = "abcd1234-test-gha-session"
        jsonl_path = tmp_path / "github" / "academicops" / "123" / "1" / f"{sid}.jsonl"
        _write_empty_jsonl(jsonl_path)

        with patch.dict("os.environ", {"POLECAT_CREW_NAME": "bogus-sync-crew"}):
            summary, _entries, _agents = processor.parse_session_file(str(jsonl_path))

        assert summary.crew is None, (
            f"GHA transcript inherited bogus crew from env: got {summary.crew!r}, "
            "expected None. See issue #768."
        )

    def test_bare_path_with_env_crew_yields_none(
        self, processor: SessionProcessor, tmp_path: Path
    ) -> None:
        """Plain-path transcript: POLECAT_CREW_NAME in env, no crew/ segment
        in path → summary.crew MUST be None. Env never wins."""
        sid = "abcd1234-test-bare-session"
        jsonl_path = tmp_path / f"{sid}.jsonl"
        _write_empty_jsonl(jsonl_path)

        with patch.dict("os.environ", {"POLECAT_CREW_NAME": "bogus-crew"}):
            summary, _entries, _agents = processor.parse_session_file(str(jsonl_path))

        assert summary.crew is None

    def test_crew_path_yields_crew_name_from_path(
        self, processor: SessionProcessor, tmp_path: Path
    ) -> None:
        """Sanity: a genuine crew/<name>/ path still sets summary.crew.
        Path-based inference is the source of truth — and it does work.
        """
        sid = "abcd1234-test-crew-session"
        jsonl_path = tmp_path / "crew" / "real-crew-name" / f"{sid}.jsonl"
        _write_empty_jsonl(jsonl_path)

        # Env crew is something different — must be ignored even when path
        # inference succeeds, but the path value is what should land.
        with patch.dict("os.environ", {"POLECAT_CREW_NAME": "env-crew-not-this"}):
            summary, _entries, _agents = processor.parse_session_file(str(jsonl_path))

        assert summary.crew == "real-crew-name"

    def test_polecats_path_with_env_crew_yields_none(
        self, processor: SessionProcessor, tmp_path: Path
    ) -> None:
        """Polecat-sourced transcript: env set, polecats/ in path
        → summary.crew MUST be None. infer_session_origin_from_path
        explicitly returns crew=None for polecats/<task_id>/... paths."""
        sid = "abcd1234-test-polecat-session"
        jsonl_path = tmp_path / "polecats" / "task-xyz" / f"{sid}.jsonl"
        _write_empty_jsonl(jsonl_path)

        with patch.dict("os.environ", {"POLECAT_CREW_NAME": "host-crew"}):
            summary, _entries, _agents = processor.parse_session_file(str(jsonl_path))

        assert summary.crew is None

    def test_reflection_to_insights_env_crew_yields_none(self, tmp_path: Path) -> None:
        """GHA-sourced transcript -> insights-JSON top-level crew is None.
        Ensures `session_naming.get_session_metadata` doesn't fall back to env
        when path-inference legitimately yields crew=None (issue #768)."""
        sid = "abcd1234"
        jsonl_path = tmp_path / "github" / "repo" / "1" / "1" / f"{sid}.jsonl"

        with patch.dict("os.environ", {"POLECAT_CREW_NAME": "bogus-insights-crew"}):
            insights = reflection_to_insights(
                reflection={},
                session_id=sid,
                date="2026-05-20",
                project="repo",
                session_path=jsonl_path,
            )

        assert insights["crew"] is None, (
            f"Insights inherited bogus crew from env: got {insights['crew']!r}"
        )
