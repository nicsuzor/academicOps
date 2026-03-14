import pytest
import subprocess
from pathlib import Path
import os
import sys
import shutil

@pytest.fixture
def temp_polecat_home(tmp_path, monkeypatch):
    home = tmp_path / "polecat_home"
    home.mkdir()
    import yaml
    config = {"projects": {}}
    (home / "polecat.yaml").write_text(yaml.dump(config))
    return home

@pytest.mark.slow
@pytest.mark.skipif(not shutil.which("docker"), reason="Docker is required for this test")
def test_crew_spawns_docker_container(temp_polecat_home, tmp_path):
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["POLECAT_DOCKER_IMAGE"] = "aops-test-nonexistent-image:latest"
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    
    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    
    result = subprocess.run(
        [sys.executable, "-m", "polecat.cli", "--home", str(temp_polecat_home), "crew", "repo", str(repo)],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd() + "/polecat",
        # Pass a fake tty or nothing. If we pass DEVNULL docker complains about the input device,
        # but we can see the docker command was attempted. 
    )
    
    output = result.stdout + result.stderr
    
    # We should see the docker failure
    assert "aops-test-nonexistent-image:latest" in output or "the input device is not a TTY" in output, f"Should attempt to run docker. Output: {output}"
    if "the input device is not a TTY" not in output:
        assert "Unable to find image" in output or "pull access denied" in output or "does not exist" in output, "Should fail at the docker daemon level"
