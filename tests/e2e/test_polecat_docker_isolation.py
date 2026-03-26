import os
import re
import subprocess
import sys
from pathlib import Path

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
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
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
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    # We write a fake 'gemini' executable in our PATH to intercept the call.
    # Polecat crew now configures sandbox via settings.json (not --sandbox flag),
    # so the fake gemini just needs to succeed — we verify settings.json afterwards.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gemini = fake_bin / "gemini"
    fake_gemini.write_text("#!/bin/sh\nprintenv | grep GEMINI\necho 'ARGS:' $@\n")
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
    assert "GEMINI_SANDBOX_IMAGE=aops-crew" in output, (
        "Should set GEMINI_SANDBOX_IMAGE for gemini CLI"
    )

    # Sandbox is now configured via settings.json, not --sandbox flag.
    # Verify the replicated gemini home has sandbox enabled in settings.
    # The fake gemini prints all GEMINI_* env vars — GEMINI_CLI_HOME tells us where to look.
    gemini_home_match = re.search(r"GEMINI_CLI_HOME=(.*)", output)
    if gemini_home_match:
        settings_path = Path(gemini_home_match.group(1).strip()) / "settings.json"
        if settings_path.exists():
            import json

            settings = json.loads(settings_path.read_text())
            sandbox_cfg = settings.get("tools", {}).get("sandbox", {})
            assert sandbox_cfg.get("enabled") is True, (
                f"Sandbox should be enabled in settings.json. Got: {sandbox_cfg}"
            )


@pytest.mark.slow
@pytest.mark.integration
def test_crew_gemini_mounts_aca_data_when_exists(temp_polecat_home, tmp_path):
    """
    Gemini crew: when ACA_DATA exists on host, it is mounted via SANDBOX_MOUNTS
    AND forwarded as an env var via SANDBOX_FLAGS.
    """
    brain_dir = tmp_path / "brain"
    brain_dir.mkdir()

    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    env["ACA_DATA"] = str(brain_dir)

    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gemini = fake_bin / "gemini"
    fake_gemini.write_text("#!/bin/sh\nprintenv\necho 'ARGS:' $@\n")
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
    brain = str(brain_dir)
    assert f"ACA_DATA={brain}" in output, (
        f"ACA_DATA should be forwarded via SANDBOX_FLAGS. Output:\n{output}"
    )
    assert f"{brain}:{brain}:rw" in output, (
        f"ACA_DATA should be mounted via SANDBOX_MOUNTS. Output:\n{output}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_gemini_crew_git_credentials_are_file_based(temp_polecat_home, tmp_path):
    """
    Regression test: Gemini crew must set up file-based git/gh credentials.

    SANDBOX_FLAGS -e env forwarding is unreliable in the Gemini sandbox (the
    sandbox only forwards a hardcoded allowlist). Credentials must be mounted
    as files via SANDBOX_MOUNTS so they work regardless of env forwarding.

    Verifies:
    - SANDBOX_MOUNTS contains a .gitconfig mount
    - SANDBOX_MOUNTS contains a gh hosts.yml mount
    - The mounted .gitconfig has the token embedded (not ${GH_TOKEN})
    - The mounted hosts.yml has the token embedded
    """
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"
    env["AOPS_BOT_GH_TOKEN"] = "test-token-abc123"
    # Suppress Gemini auth replication (no ~/.gemini in test env)
    env["POLECAT_GEMINI_AUTH_DISABLED"] = "1"

    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo, check=True)

    # Fake gemini that prints SANDBOX_MOUNTS and cats mounted credential files
    # so the test can verify content before polecat cleans up the temp files.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gemini = fake_bin / "gemini"
    fake_gemini.write_text(
        "#!/bin/sh\n"
        "echo SANDBOX_MOUNTS=$SANDBOX_MOUNTS\n"
        "echo SANDBOX_FLAGS=$SANDBOX_FLAGS\n"
        "echo 'ARGS:' $@\n"
        # Print each mounted file's contents so the test can verify token embedding
        "IFS=, ; for mount in $SANDBOX_MOUNTS; do\n"
        "  src=$(echo $mount | cut -d: -f1)\n"
        "  dst=$(echo $mount | cut -d: -f2)\n"
        "  echo MOUNT_CONTENT_BEGIN:$dst\n"
        "  cat $src\n"
        "  echo MOUNT_CONTENT_END:$dst\n"
        "done\n"
    )
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
            "gemini-cred-worker",
            "-g",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd() + "/polecat",
    )

    output = result.stdout + result.stderr

    # Extract SANDBOX_MOUNTS value from fake gemini output.
    # The line may be prefixed by an OSC terminal-title escape sequence
    # (set_terminal_title writes \033]0;...\007 to stdout), so use regex.
    sandbox_mounts = ""
    m = re.search(r"SANDBOX_MOUNTS=(\S+)", output)
    if m:
        sandbox_mounts = m.group(1)

    assert sandbox_mounts, f"SANDBOX_MOUNTS should be set. Output:\n{output}"

    # Verify .gitconfig mount is present
    assert ".gitconfig" in sandbox_mounts, (
        f"SANDBOX_MOUNTS should include a .gitconfig mount. Got: {sandbox_mounts}"
    )

    # Verify gh hosts.yml mount is present
    assert "hosts.yml" in sandbox_mounts, (
        f"SANDBOX_MOUNTS should include a gh hosts.yml mount. Got: {sandbox_mounts}"
    )

    # Extract mounted file contents from fake gemini output (printed before cleanup)
    def extract_mount_content(out: str, dst_path: str) -> str:
        begin = f"MOUNT_CONTENT_BEGIN:{dst_path}"
        end = f"MOUNT_CONTENT_END:{dst_path}"
        if begin not in out:
            return ""
        return out.split(begin, 1)[1].split(end, 1)[0].strip()

    # Verify .gitconfig has token embedded (not ${GH_TOKEN})
    # Use Path.home() to build the absolute destination path dynamically
    gitconfig_content = extract_mount_content(output, str(Path.home() / ".gitconfig"))
    assert gitconfig_content, f".gitconfig mount content not found in output:\n{output}"
    assert "test-token-abc123" in gitconfig_content, (
        "Token must be embedded directly in .gitconfig (not via ${GH_TOKEN}). "
        f"Content: {gitconfig_content!r}"
    )
    assert "${GH_TOKEN}" not in gitconfig_content, (
        ".gitconfig must not use ${GH_TOKEN} — token must be embedded for sandbox reliability"
    )

    # Verify gh hosts.yml has token embedded
    # Use Path.home() to build the absolute destination path dynamically
    gh_hosts_content = extract_mount_content(
        output, str(Path.home() / ".config" / "gh" / "hosts.yml")
    )
    assert gh_hosts_content, f"gh hosts.yml mount content not found in output:\n{output}"
    assert "test-token-abc123" in gh_hosts_content, (
        f"Token must be embedded directly in gh hosts.yml. Content: {gh_hosts_content!r}"
    )


@pytest.mark.slow
@pytest.mark.integration
def test_crew_interactive_shell_spawns_docker(temp_polecat_home, tmp_path):
    """
    E2E test: running polecat crew -i wraps bash in docker (same as claude path).
    Verifies that -i flag routes through _build_docker_cmd with 'bash' as the command.
    """
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(temp_polecat_home)
    env["POLECAT_DOCKER_IMAGE"] = "aops-test-nonexistent-image:latest"
    env["PYTHONPATH"] = os.getcwd() + "/polecat" + ":" + os.getcwd() + "/aops-core"

    repo = tmp_path / "dummy_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
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
            "-i",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd() + "/polecat",
        stdin=subprocess.DEVNULL,
    )

    output = result.stdout + result.stderr
    # Verify it's launching shell mode, not claude or gemini
    assert "Starting shell crew session" in output, (
        f"Should indicate shell session. Output: {output}"
    )
    # Should attempt docker run — either docker runs (TTY error from bash) or docker not found.
    # On hosts with docker: bash inside container fails with "not a TTY" since stdin is DEVNULL.
    # On hosts without docker: we get a "not found" or "denied" error.
    assert (
        "not a tty" in output.lower()
        or "not found" in output.lower()
        or "denied" in output.lower()
        or "docker" in output.lower()
    ), f"Should route through docker. Output: {output}"
