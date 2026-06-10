"""Refresh-in-place / backfill behaviour for session summaries (aops-efffc1f7).

Older summaries on disk predate the ``initial_prompt`` field and were written
with empty ``user_prompt`` descriptions. The distiller must enrich them in place
on a later pass — even when the timeline event *count* is unchanged — without
churning the filename or downgrading already-populated fields back to empty.

``transcript.py`` is not importable as a module (it lives under aops-core/scripts
and is not on sys.path), so we load it dynamically the same way the other
transcript-script tests do.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def transcript_script():
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "aops-core" / "scripts" / "transcript.py"
    spec = importlib.util.spec_from_file_location("transcript_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcript_script"] = module
    spec.loader.exec_module(module)
    return module


def _events(*descriptions: str) -> list[dict]:
    return [{"type": "user_prompt", "timestamp": "t", "description": d} for d in descriptions]


class TestShouldOverwriteExisting:
    def test_initial_prompt_appeared_triggers_refresh(self, transcript_script) -> None:
        new = {"timeline_events": _events("hi"), "initial_prompt": "hi"}
        existing = {"timeline_events": _events("hi")}  # no initial_prompt
        assert (
            transcript_script._should_overwrite_existing(new, existing) == "initial_prompt appeared"
        )

    def test_descriptions_populated_triggers_refresh_at_same_count(self, transcript_script) -> None:
        # Same number of events, but old descriptions were empty.
        new = {"timeline_events": _events("real prompt")}
        existing = {"timeline_events": _events("")}
        assert (
            transcript_script._should_overwrite_existing(new, existing)
            == "timeline descriptions populated"
        )

    def test_no_change_skips(self, transcript_script) -> None:
        events = _events("same")
        new = {"timeline_events": events, "initial_prompt": "same"}
        existing = {"timeline_events": events, "initial_prompt": "same"}
        assert transcript_script._should_overwrite_existing(new, existing) is None

    def test_jsonl_growth_still_wins(self, transcript_script) -> None:
        new = {"timeline_events": _events("a", "b")}
        existing = {"timeline_events": _events("a")}
        assert transcript_script._should_overwrite_existing(new, existing) == "jsonl grew"


class TestPreserveDoesNotDowngrade:
    def test_initial_prompt_preserved_when_new_empty(self, transcript_script) -> None:
        new = {"initial_prompt": ""}
        existing = {"initial_prompt": "the original intent"}
        merged = transcript_script._preserve_reflection_fields(new, existing)
        assert merged["initial_prompt"] == "the original intent"

    def test_new_initial_prompt_wins_when_present(self, transcript_script) -> None:
        new = {"initial_prompt": "fresh"}
        existing = {"initial_prompt": "stale"}
        merged = transcript_script._preserve_reflection_fields(new, existing)
        assert merged["initial_prompt"] == "fresh"

    def test_is_empty_value(self, transcript_script) -> None:
        assert transcript_script._is_empty_value("")
        assert transcript_script._is_empty_value(None)
        assert transcript_script._is_empty_value([])
        assert not transcript_script._is_empty_value("x")
