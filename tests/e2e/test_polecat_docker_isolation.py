import os
import subprocess
import sys

import pytest


@pytest.fixture
def temp_polecat_home(tmp_path):
    home = tmp_path / "polecat_home"
    home.mkdir()
    import yaml

    config = {"projects": {}}
    (home / "polecat.yaml").write_text(yaml.dump(config))
    return home


@pytest.mark.slow
@pytest.mark.integration
def test_crew_spawns_docker_container_claude(temp_polecat_home, tmp_path):
    """
    E2E test: running polecat crew wraps claude in docker.
    Since we don't have docker installed in the test sandbox, we verify that it
    fails complaining about 'docker'.
    """
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["POLECAT_DOCKER_IMAGE"] = "aops-test-nonexistent-image:latest"
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(temp_polecat_home),
            "crew",
            "repo",
            str(repo),
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd() + "/polecat",
        stdin=subprocess.DEVNULL,
    )

    output = result.stdout + result.stderr
    assert "docker" in output.lower(), f"Should attempt to invoke docker. Output: {output}"
    # Depending on the environment, we either get 'command not found', 'pull access denied' or 'TTY' errors.
    # All of them indicate the wrapper executed the 'docker run' command instead of native 'claude'
    assert "not found" in output.lower() or "denied" in output.lower() or "tty" in output.lower(), (
        "Should fail executing docker"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_crew_spawns_docker_container_gemini(temp_polecat_home, tmp_path):
    """
    E2E test: running polecat crew -g delegates sandboxing to Gemini CLI via GEMINI_SANDBOX_IMAGE.
    """
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    # We write a fake 'gemini' executable in our PATH to intercept the call and echo the env vars
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gemini = fake_bin / "gemini"
    fake_gemini.write_text("#!/bin/sh\nprintenv | grep GEMINI_SANDBOX_IMAGE\necho 'ARGS:' $@\n")
    fake_gemini.chmod(0o755)

    env["PATH"] = f"{fake_bin}:{env.get('PATH', '')}"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polecat.cli",
            "--home",
            str(temp_polecat_home),
            "crew",
            "repo",
            str(repo),
            "-n",
            "gemini-worker",
            "-g",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd() + "/polecat",
    )

    output = result.stdout + result.stderr
    assert "GEMINI_SANDBOX_IMAGE=aops-sandbox" in output, (
        "Should set GEMINI_SANDBOX_IMAGE for gemini CLI"
    )
    assert "ARGS: --sandbox" in output, "Should invoke gemini with --sandbox flag"
