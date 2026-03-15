#!/usr/bin/env python3
"""Tests for skill script discovery and execution.

Consolidated from 5 slow tests to 2 fast filesystem tests + 1 slow test.
Tests that don't need headless have had @slow removed.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_home(tmp_path, monkeypatch):
    """Setup a mock ~/.claude/ structure in tmp_path."""
    # Create structure
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Create framework skill
    framework_scripts = skills_dir / "framework" / "scripts"
    framework_scripts.mkdir(parents=True, exist_ok=True)

    # Create required scripts
    (framework_scripts / "validate_docs.py").touch()

    # Setup symlink to real AOPS if available
    aops = os.environ.get("AOPS")
    if aops:
        aops_scripts = Path(aops) / "aops-core" / "skills" / "framework" / "scripts"
        if aops_scripts.exists():
            import shutil

            shutil.rmtree(framework_scripts.parent)
            framework_scripts.parent.mkdir(parents=True, exist_ok=True)
            framework_scripts.symlink_to(aops_scripts)

    with patch.object(Path, "home", return_value=tmp_path):
        yield


@pytest.mark.integration
def test_skill_scripts_exist_via_symlink():
    """Test that skill scripts are accessible via skills dir."""
    from lib.paths import get_skills_dir
    skills_path = get_skills_dir()
    assert skills_path.exists(), "skills dir not found"
    assert skills_path.is_symlink() or skills_path.is_dir(), (
        "~/.claude/skills/ should be symlink or directory"
    )

    framework_skill_path = skills_path / "framework"
    assert framework_skill_path.exists(), "~/.claude/skills/framework/ not found"
    assert framework_skill_path.exists(), "~/.claude/skills/framework/ should exist"

    scripts_path = framework_skill_path / "scripts"
    assert scripts_path.exists(), "~/.claude/skills/framework/scripts/ should exist"

    required_scripts = ["validate_docs.py"]
    for script_name in required_scripts:
        script_path = scripts_path / script_name
        assert script_path.exists(), f"Script {script_name} should exist at {script_path}"


@pytest.mark.integration
@pytest.mark.slow
def test_framework_script_runs_from_writing_repo(data_dir):
    """Test that framework scripts execute correctly from writing repo."""
    from lib.paths import get_skills_dir
    script_path = get_skills_dir() / "framework" / "scripts" / "validate_docs.py"
    if not script_path.exists():
        pytest.skip(f"Script not found at {script_path}")

    aops = os.environ.get("AOPS")
    if not aops:
        pytest.skip("AOPS environment variable not set")

    cmd = ["uv", "run", "python", str(script_path), "--help"]
    env = os.environ.copy()
    env["PYTHONPATH"] = aops

    result = subprocess.run(
        cmd,
        cwd=data_dir,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        check=False,
    )

    assert result.returncode == 0, (
        f"Script should execute successfully\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "usage:" in result.stdout.lower(), "Should show usage information"


@pytest.mark.integration
def test_skill_self_contained_architecture():
    """Test that skills are self-contained with their own scripts."""
    aops = os.environ.get("AOPS")
    if not aops:
        pytest.skip("AOPS environment variable not set")

    aops_path = Path(aops)
    scripts_in_aops = aops_path / "aops-core" / "skills" / "framework" / "scripts"
    assert scripts_in_aops.exists(), f"Scripts should exist in AOPS: {scripts_in_aops}"

    from lib.paths import get_skills_dir
    symlink_path = get_skills_dir() / "framework" / "scripts"
    assert symlink_path.exists(), f"Symlink path not found at {symlink_path}"

    symlink_resolved = symlink_path.resolve()
    scripts_resolved = scripts_in_aops.resolve()

    assert symlink_resolved == scripts_resolved, (
        f"Symlink should point to AOPS scripts\n"
        f"Symlink resolves to: {symlink_resolved}\n"
        f"AOPS scripts at: {scripts_resolved}"
    )
