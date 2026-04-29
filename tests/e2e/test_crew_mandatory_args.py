import os
import subprocess
import sys

import pytest


def _write_registry(sessions_dir, projects):
    import yaml

    sessions_dir.mkdir(parents=True, exist_ok=True)
    (sessions_dir / "projects.yaml").write_text(yaml.dump({"projects": projects}))


def _write_overlay(home, paths):
    import yaml

    (home / "local.yaml").write_text(yaml.dump({"paths": paths}))


@pytest.fixture
def temp_polecat_home(tmp_path):
    home = tmp_path / "polecat_home"
    home.mkdir()
    sessions = tmp_path / "sessions"
    # Default: a dummy repo so PolecatManager bootstraps cleanly.
    dummy = tmp_path / "dummy_repo"
    dummy.mkdir()
    subprocess.run(["git", "init"], cwd=dummy, check=True, capture_output=True)
    _write_registry(sessions, {"aops": {"default_branch": "main"}})
    _write_overlay(home, {"aops": str(dummy)})
    return home


def _env(temp_polecat_home):
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["AOPS_SESSIONS"] = str(temp_polecat_home.parent / "sessions")
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    return env


@pytest.mark.integration
def test_crew_fails_without_args(temp_polecat_home):
    """
    E2E test: running 'polecat crew' without args should fail.
    """
    env = _env(temp_polecat_home)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(temp_polecat_home),
            "crew",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode != 0
    assert "Error: 'crew' requires a target project or --resume." in result.stderr


@pytest.mark.integration
def test_crew_succeeds_with_args(temp_polecat_home, tmp_path):
    """
    E2E test: 'polecat crew aops' should succeed (or at least attempt to setup).
    """
    env = _env(temp_polecat_home)

    # Setup a real dummy repo for 'aops' and point overlay at it.
    repo = tmp_path / "aops_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    _write_overlay(temp_polecat_home, {"aops": str(repo)})

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(temp_polecat_home),
            "crew",
            "aops",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        stdin=subprocess.DEVNULL,
    )

    # It should pass the "target check" and try to setup the crew session.
    assert "Error: 'crew' requires a target project or --resume." not in result.stderr
    assert "Crew worker:" in result.stdout


@pytest.mark.integration
def test_crew_succeeds_with_resume(temp_polecat_home, tmp_path):
    """
    E2E test: 'polecat crew --resume <name>' should succeed even without target.
    """
    env = _env(temp_polecat_home)

    # Create an "active" crew directory
    crew_name = "test-crew"
    crew_dir = temp_polecat_home / "crew" / crew_name
    crew_dir.mkdir(parents=True)
    # Add a dummy project worktree inside it
    (crew_dir / "aops").mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(temp_polecat_home),
            "crew",
            "--resume",
            crew_name,
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
        stdin=subprocess.DEVNULL,
    )

    # It should pass the "target check" because --resume is provided.
    assert "Error: 'crew' requires a target project or --resume." not in result.stderr
    assert f"Crew worker: {crew_name}" in result.stdout
