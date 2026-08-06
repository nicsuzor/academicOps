"""Empirical verification & edge-case stress test suite for Iteration 2 (Challenger 2 gen2)."""

import os
import shutil
import pytest
from pathlib import Path

from transcripts.runner import find_session_files
from polecat.cli import _sanitize_path_component, _transcript_paths, transcript_evidence

FIXTURES_DIR = Path("/workspace/tests/transcripts/fixtures")
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
AGY_FIXTURE = FIXTURES_DIR / "agy_session.jsonl"


def test_edge_case_deeply_nested_subagents(tmp_path: Path) -> None:
    """Verify that deeply nested subagents directories are filtered out."""
    base_dir = tmp_path / "subagents" / "sessions_root"
    logs_dir = base_dir / "logs" / "20260806" / "session-1" / "proj"
    deep_subagent_dir = logs_dir / "subagents" / "nest1" / "nest2" / "nest3"
    deep_subagent_dir.mkdir(parents=True)

    trunk_file = logs_dir / "trunk.jsonl"
    subagent_file = deep_subagent_dir / "deep_sub.jsonl"

    shutil.copy(CLAUDE_FIXTURE, trunk_file)
    shutil.copy(CLAUDE_FIXTURE, subagent_file)

    found = find_session_files(sessions_dir=base_dir)
    assert trunk_file in found, "Trunk file should be found"
    assert subagent_file not in found, "Deeply nested subagent file should be excluded"


def test_edge_case_subagents_substrings(tmp_path: Path) -> None:
    """Verify that directories containing 'subagents' as a substring (not exact component) are included."""
    base_dir = tmp_path / "sessions"
    logs_dir = base_dir / "logs" / "20260806" / "session-1" / "subagents_v2"
    logs_dir.mkdir(parents=True)

    session_file = logs_dir / "trunk.jsonl"
    shutil.copy(CLAUDE_FIXTURE, session_file)

    found = find_session_files(sessions_dir=base_dir)
    assert session_file in found, "Directory named 'subagents_v2' should NOT be excluded"


def test_edge_case_agy_brain_under_subagents_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify agy brain sessions under a home directory containing 'subagents'."""
    fake_home = tmp_path / "subagents" / "user_home"
    agy_brain = fake_home / ".gemini" / "antigravity-cli" / "brain" / "session-uuid"
    agy_brain.mkdir(parents=True)

    agy_file = agy_brain / "transcript.jsonl"
    shutil.copy(AGY_FIXTURE, agy_file)

    monkeypatch.setattr(Path, "home", lambda: fake_home)

    found = find_session_files()
    assert agy_file in found, "agy session under home with 'subagents' should be discovered"


def test_edge_case_sanitize_path_component_edge_cases() -> None:
    """Adversarial testing of _sanitize_path_component."""
    assert _sanitize_path_component(None, "default") == "default"
    assert _sanitize_path_component("", "default") == "default"
    assert _sanitize_path_component(".", "default") == "default"
    assert _sanitize_path_component("..", "default") == "default"
    assert _sanitize_path_component("../../../", "default") == "default"
    assert _sanitize_path_component("../foo/../bar", "default") == "foo_.._bar"
    assert _sanitize_path_component("my-project_123", "default") == "my-project_123"
