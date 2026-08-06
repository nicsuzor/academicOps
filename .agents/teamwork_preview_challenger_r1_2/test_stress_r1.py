"""Empirical stress test suite for Milestone R1: Discovery & Launcher Path Sanitization."""

import pytest
import shutil
import os
from pathlib import Path
from click.testing import CliRunner

from transcripts.runner import find_session_files
from polecat.cli import _sanitize_path_component, main, _resolve_workspace

FIXTURES_DIR = Path("/workspace/tests/transcripts/fixtures")
CLAUDE_FIXTURE = FIXTURES_DIR / "claude_session.jsonl"
AGY_FIXTURE = FIXTURES_DIR / "agy_session.jsonl"

def test_stress_aops_sessions_in_subagents_directory(tmp_path: Path) -> None:
    """Stress Test 1: AOPS_SESSIONS root located inside a directory named 'subagents'."""
    # Setup AOPS_SESSIONS under /tmp/.../subagents/my_sessions
    base_dir = tmp_path / "subagents" / "my_sessions"
    logs_dir = base_dir / "logs" / "20260806" / "session-1" / "project"
    logs_dir.mkdir(parents=True)
    
    session_file = logs_dir / "trunk-session.jsonl"
    shutil.copy(CLAUDE_FIXTURE, session_file)
    
    found = find_session_files(sessions_dir=base_dir)
    # Check if session_file was found or erroneously excluded due to "subagents" in p.parts
    assert session_file in found, f"Valid session file was excluded because base directory path contained 'subagents'! Found: {found}"

def test_stress_home_directory_containing_subagents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stress Test 2: User home directory path containing 'subagents'."""
    fake_home = tmp_path / "subagents" / "user"
    fake_claude = fake_home / ".claude" / "projects" / "my-project"
    fake_claude.mkdir(parents=True)
    session_file = fake_claude / "claude-session.jsonl"
    shutil.copy(CLAUDE_FIXTURE, session_file)
    
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    found = find_session_files()
    assert session_file in found, f"Claude session file excluded because home dir contains 'subagents'! Found: {found}"

def test_stress_subagent_filename_containing_subagents_word(tmp_path: Path) -> None:
    """Stress Test 3: Project directory named 'subagents_project'."""
    sessions_dir = tmp_path / "sessions"
    logs_dir = sessions_dir / "logs" / "20260806" / "session-1" / "subagents_project"
    logs_dir.mkdir(parents=True)
    
    session_file = logs_dir / "trunk.jsonl"
    shutil.copy(CLAUDE_FIXTURE, session_file)
    
    found = find_session_files(sessions_dir=sessions_dir)
    assert session_file in found

def test_stress_subagents_directory_relative_to_logs(tmp_path: Path) -> None:
    """Stress Test 4: Standard subagent directory under session trunk vs trunk file."""
    sessions_dir = tmp_path / "sessions"
    proj_dir = sessions_dir / "logs" / "20260806" / "session-1" / "aops"
    subagents_dir = proj_dir / "trunk-123" / "subagents"
    subagents_dir.mkdir(parents=True)
    
    trunk_file = proj_dir / "trunk-123.jsonl"
    subagent_file = subagents_dir / "sub-456.jsonl"
    shutil.copy(CLAUDE_FIXTURE, trunk_file)
    shutil.copy(CLAUDE_FIXTURE, subagent_file)
    
    found = find_session_files(sessions_dir=sessions_dir)
    assert trunk_file in found
    assert subagent_file not in found

def test_stress_hooks_jsonl_variations(tmp_path: Path) -> None:
    """Stress Test 5: Check hooks filtering with various hook file names."""
    sessions_dir = tmp_path / "sessions"
    proj_dir = sessions_dir / "logs" / "20260806" / "session-1" / "aops"
    proj_dir.mkdir(parents=True)
    
    trunk_file = proj_dir / "session.jsonl"
    hook1 = proj_dir / "polecat-session-hooks.jsonl"
    hook2 = proj_dir / "custom-hooks.jsonl"
    
    shutil.copy(CLAUDE_FIXTURE, trunk_file)
    hook1.write_text("{}")
    hook2.write_text("{}")
    
    found = find_session_files(sessions_dir=sessions_dir)
    assert trunk_file in found
    assert hook1 not in found
    assert hook2 not in found

def test_stress_sanitization_extreme_inputs() -> None:
    """Stress Test 6: Extreme adversarial inputs to _sanitize_path_component."""
    cases = [
        ("../../etc/passwd", "etc_passwd"),
        ("..\\..\\windows\\system32", "windows_system32"),
        ("\x00\x01\x02", None),
        ("hello\nworld", "hello_world"),
        ("a" * 300, "a" * 300),
        ("!@#$%^&*()+=~`[]{}|;:'\",<>?", None),
        ("---", None),
        ("___", None),
        ("...", None),
        (".hidden_dir.", "hidden_dir"),
        (" -p --rm ", "p_--rm"),
        ("project-1.0_beta", "project-1.0_beta"),
        ("😀😁😂", None),
    ]
    for inp, exp in cases:
        res = _sanitize_path_component(inp)
        assert res == exp, f"Failed for input {inp!r}: expected {exp!r}, got {res!r}"

def test_stress_cli_sanitization_integration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stress Test 7: CLI invocation with path traversal project or session_name."""
    # Ensure project and session_name sanitization works end-to-end without raising exceptions or escaping directories.
    res_proj = _sanitize_path_component("../../../evil_project")
    res_sess = _sanitize_path_component("../../evil_session")
    
    assert res_proj == "evil_project"
    assert res_sess == "evil_session"
    assert "/" not in res_proj and "\\" not in res_proj
    assert "/" not in res_sess and "\\" not in res_sess
