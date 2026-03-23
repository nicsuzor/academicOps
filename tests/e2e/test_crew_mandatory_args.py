import os
import subprocess
import sys

import pytest


@pytest.fixture
def temp_polecat_home(tmp_path):
    home = tmp_path / "polecat_home"
    home.mkdir()
    import yaml

    config = {"projects": {"aops": {"path": "/tmp/dummy"}}}
    (home / "polecat.yaml").write_text(yaml.dump(config))
    return home


@pytest.mark.integration
def test_crew_fails_without_args(temp_polecat_home):
    """
    E2E test: running 'polecat crew' without args should fail.
    """
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

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
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

    # Setup a real dummy repo for 'aops'
    repo = tmp_path / "aops_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    # Update config to point to real dummy repo
    import yaml

    config = {"projects": {"aops": {"path": str(repo)}}}
    (temp_polecat_home / "polecat.yaml").write_text(yaml.dump(config))

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
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

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
