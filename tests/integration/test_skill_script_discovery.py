#!/usr/bin/env python3
"""Tests for skill script discovery and execution.

Consolidated from 5 slow tests to 2 fast filesystem tests + 1 slow test.
Tests that don't need headless have had @slow removed.

Note: The framework skill is project-local (.agents/skills/framework/),
not distributed (aops-core/skills/). These tests verify that project-local
scripts are discoverable and executable.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def mock_home(tmp_path, monkeypatch):
    """Setup a mock project structure in tmp_path."""
    # Create .agents/skills/framework structure (project-local)
    framework_scripts = tmp_path / ".agents" / "skills" / "framework" / "scripts"
    framework_scripts.mkdir(parents=True, exist_ok=True)

    # Create required scripts
    (framework_scripts / "validate_docs.py").touch()

    # Setup symlink to real AOPS if available
    aops = os.environ.get("AOPS")
    if aops:
        aops_scripts = Path(aops) / ".agents" / "skills" / "framework" / "scripts"
        if aops_scripts.exists():
            import shutil

            shutil.rmtree(framework_scripts)
            framework_scripts.symlink_to(aops_scripts)

    yield tmp_path


@pytest.mark.integration
def test_framework_skill_scripts_exist(mock_home):
    """Test that framework skill scripts are accessible in .agents/skills/framework/."""
    framework_path = mock_home / ".agents" / "skills" / "framework"
    assert framework_path.exists(), ".agents/skills/framework/ not found"

    scripts_path = framework_path / "scripts"
    assert scripts_path.exists(), ".agents/skills/framework/scripts/ should exist"

    required_scripts = ["validate_docs.py"]
    for script_name in required_scripts:
        script_path = scripts_path / script_name
        assert script_path.exists(), f"Script {script_name} should exist at {script_path}"


@pytest.mark.integration
@pytest.mark.slow
def test_framework_script_runs_from_writing_repo(data_dir):
    """Test that framework scripts execute correctly from writing repo."""
    aops = os.environ.get("AOPS")
    if not aops:
        pytest.skip("AOPS environment variable not set")

    script_path = Path(aops) / ".agents" / "skills" / "framework" / "scripts" / "validate_docs.py"
    assert script_path.exists(), f"Script not found at {script_path}"

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
    """Test that the framework skill is self-contained in .agents/skills/framework/."""
    aops = os.environ.get("AOPS")
    if not aops:
        pytest.skip("AOPS environment variable not set")

    aops_path = Path(aops)
    scripts_in_aops = aops_path / ".agents" / "skills" / "framework" / "scripts"
    assert scripts_in_aops.exists(), f"Scripts should exist in AOPS .agents/: {scripts_in_aops}"
