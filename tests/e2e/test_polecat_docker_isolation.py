import json
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


def _init_test_repo(tmp_path):
    """Create a minimal git repo suitable for polecat crew."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _crew_env(polecat_home):
    """Build an env dict for running polecat crew."""
    env = os.environ.copy()
    env["POLECAT_HOME"] = str(polecat_home)
    # PYTHONPATH must include the repo root (not polecat/ itself) so that
    # `python -m polecat.cli` can resolve `polecat` as a package.
    env["PYTHONPATH"] = os.getcwd() + ":" + os.getcwd() + "/aops-core"
    return env


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
    fake_gemini.write_text(
        "#!/bin/sh\n"
        'echo "GEMINI_SANDBOX_IMAGE=${GEMINI_SANDBOX_IMAGE:-}"\n'
        'echo "GEMINI_CLI_HOME=${GEMINI_CLI_HOME:-}"\n'
        "echo 'ARGS:' $@\n"
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
    assert gemini_home_match, f"GEMINI_CLI_HOME not found in output:\n{output}"
    settings_path = Path(gemini_home_match.group(1).strip()) / "settings.json"
    assert settings_path.exists(), f"settings.json not found at {settings_path}"
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


# Real-image Claude crew test moved to test_crew_docker_session.py
# (TestCrewDockerSession) which shares a single LLM invocation with
# other Docker session assertions (binaries, extensions, hooks, persistence).


@pytest.mark.slow
@pytest.mark.integration
def test_crew_gemini_sandbox_config(temp_polecat_home, tmp_path):
    """Full E2E: polecat crew -g configures Gemini sandbox with correct settings.

    The Gemini path does NOT use _build_docker_cmd() — it configures
    SANDBOX_FLAGS, SANDBOX_MOUNTS, and _replicate_gemini_auth(), then
    delegates to gemini CLI. This test intercepts the gemini call and
    verifies the sandbox configuration is correct.

    Checks:
    - GEMINI_SANDBOX_IMAGE=aops-crew
    - Replicated settings.json has sandbox enabled + networkAccess
    - No mcpServers or hooks leaked into replicated settings
    - .gitconfig has embedded token (not ${GH_TOKEN} placeholder)
    """
    env = _crew_env(temp_polecat_home)
    env["AOPS_BOT_GH_TOKEN"] = "test-token-sandbox-config"

    # Create a fake ~/.gemini/settings.json so _replicate_gemini_auth runs
    # and sets GEMINI_CLI_HOME. Without this, auth replication is skipped.
    fake_home = tmp_path / "fakehome"
    fake_home.mkdir()
    gemini_dir = fake_home / ".gemini"
    gemini_dir.mkdir(parents=True)
    (gemini_dir / "settings.json").write_text(
        json.dumps(
            {
                "security": {"auth": {"selectedType": "oauth-personal"}},
                "mcpServers": {"should-be-stripped": {}},
            }
        )
    )
    # Create minimal extension dir so replication has something to copy
    ext_dir = gemini_dir / "extensions" / "aops-core"
    ext_dir.mkdir(parents=True)
    (ext_dir / "GEMINI.md").write_text("fake extension")
    (gemini_dir / "extensions" / "extension-enablement.json").write_text(
        json.dumps({"aops-core": {"overrides": ["/fake/*"]}})
    )
    env["HOME"] = str(fake_home)

    repo = _init_test_repo(tmp_path)

    # Fake gemini that dumps env and settings for verification.
    # The replicated GEMINI_CLI_HOME dir is cleaned up after the gemini process
    # exits, so we must dump settings.json content from inside the fake gemini.
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_gemini = fake_bin / "gemini"
    fake_gemini.write_text(
        "#!/bin/sh\n"
        'echo "GEMINI_SANDBOX_IMAGE=${GEMINI_SANDBOX_IMAGE:-}"\n'
        'echo "GEMINI_CLI_HOME=${GEMINI_CLI_HOME:-}"\n'
        'echo "SANDBOX_MOUNTS=${SANDBOX_MOUNTS:-}"\n'
        'echo "SANDBOX_FLAGS=${SANDBOX_FLAGS:-}"\n'
        # Dump settings.json before polecat cleans up the temp dir
        'if [ -f "${GEMINI_CLI_HOME}/.gemini/settings.json" ]; then\n'
        '  echo "SETTINGS_JSON_BEGIN"\n'
        '  cat "${GEMINI_CLI_HOME}/.gemini/settings.json"\n'
        '  echo "SETTINGS_JSON_END"\n'
        "fi\n"
        # Dump credential file contents
        "IFS=, ; for mount in $SANDBOX_MOUNTS; do\n"
        "  src=$(echo $mount | cut -d: -f1)\n"
        "  dst=$(echo $mount | cut -d: -f2)\n"
        '  echo "MOUNT_CONTENT_BEGIN:$dst"\n'
        "  cat $src 2>/dev/null\n"
        '  echo "MOUNT_CONTENT_END:$dst"\n'
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
            "gemini-config-test",
            "-g",
        ],
        env=env,
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )

    output = result.stdout + result.stderr

    # 1. Sandbox image set correctly
    assert "GEMINI_SANDBOX_IMAGE=aops-crew" in output, (
        f"GEMINI_SANDBOX_IMAGE not set. Output:\n{output}"
    )

    # 2. Settings.json has sandbox enabled + networkAccess, no baggage
    # Parse settings from stdout (file is cleaned up after gemini exits)
    gemini_home_match = re.search(r"GEMINI_CLI_HOME=(\S+)", output)
    assert gemini_home_match, f"GEMINI_CLI_HOME not found. Output:\n{output}"

    assert "SETTINGS_JSON_BEGIN" in output, (
        f"Settings.json not dumped by fake gemini. Output:\n{output}"
    )
    settings_raw = output.split("SETTINGS_JSON_BEGIN")[1].split("SETTINGS_JSON_END")[0].strip()
    settings = json.loads(settings_raw)

    sandbox_cfg = settings.get("tools", {}).get("sandbox", {})
    assert sandbox_cfg.get("enabled") is True, f"Sandbox not enabled. Got: {sandbox_cfg}"
    assert sandbox_cfg.get("networkAccess") is True, (
        f"networkAccess not enabled (needed for OAuth). Got: {sandbox_cfg}"
    )

    # No user baggage leaked
    assert "mcpServers" not in settings, (
        f"mcpServers leaked into sandbox settings: {list(settings.get('mcpServers', {}).keys())}"
    )

    # 3. Token embedded in .gitconfig (not env var placeholder)
    def extract_mount_content(out: str, dst_path: str) -> str:
        begin = f"MOUNT_CONTENT_BEGIN:{dst_path}"
        end = f"MOUNT_CONTENT_END:{dst_path}"
        if begin not in out:
            return ""
        return out.split(begin, 1)[1].split(end, 1)[0].strip()

    gitconfig_content = extract_mount_content(output, str(Path.home() / ".gitconfig"))
    assert gitconfig_content, (
        ".gitconfig mount not found in sandbox output — token embedding is unverified. "
        "If apply_env_mappings() failed to map AOPS_BOT_GH_TOKEN to GH_TOKEN, "
        "no gitconfig would be mounted and this security property is untested."
    )
    if gitconfig_content:
        assert "test-token-sandbox-config" in gitconfig_content, (
            "Token must be embedded in .gitconfig, not via ${GH_TOKEN}. "
            f"Content: {gitconfig_content!r}"
        )
        assert "${GH_TOKEN}" not in gitconfig_content, (
            ".gitconfig must not use ${GH_TOKEN} placeholder"
        )


@pytest.mark.slow
@pytest.mark.integration
def test_crew_env_reaches_container(temp_polecat_home, tmp_path):
    """Full E2E: env vars from _make_worker_env() reach the docker command.

    Uses a fake docker binary to intercept the docker command that polecat
    crew constructs, then verifies the -e flags contain the critical
    security and configuration variables. No API key or real Docker needed.

    This catches bugs where crew() or _make_worker_env() drops an env var
    that _build_docker_cmd() would have forwarded correctly in isolation.
    """
    repo = _init_test_repo(tmp_path)
    env = _crew_env(temp_polecat_home)
    # Set both GH_TOKEN and AOPS_BOT_GH_TOKEN — apply_env_mappings() maps
    # AOPS_BOT_GH_TOKEN → GH_TOKEN, so the test token must be set on both.
    env["GH_TOKEN"] = "ghp_test_env_reaches_container"
    env["AOPS_BOT_GH_TOKEN"] = "ghp_test_env_reaches_container"

    # Create a fake docker that dumps its arguments to a file
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    args_file = tmp_path / "docker_args.txt"
    fake_docker = fake_bin / "docker"
    fake_docker.write_text(
        "#!/bin/sh\n"
        # Write all args to file for inspection
        f'echo "$@" > {args_file}\n'
        # Also print env vars passed via -e flags
        'for arg in "$@"; do\n'
        '  echo "ARG:$arg"\n'
        "done\n"
    )
    fake_docker.chmod(0o755)
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
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=os.getcwd(),
        stdin=subprocess.DEVNULL,
    )

    output = result.stdout + result.stderr

    # Verify the docker command was intercepted
    assert args_file.exists(), f"Fake docker was not invoked. Output:\n{output}"
    docker_args = args_file.read_text()

    # SSH must be disabled (empty SSH_AUTH_SOCK)
    assert "SSH_AUTH_SOCK=" in docker_args, f"SSH_AUTH_SOCK not in docker -e flags:\n{docker_args}"

    # Git terminal prompt must be disabled
    assert "GIT_TERMINAL_PROMPT=0" in docker_args, (
        f"GIT_TERMINAL_PROMPT=0 not in docker -e flags:\n{docker_args}"
    )

    # GH_TOKEN must be forwarded
    assert "GH_TOKEN=ghp_test_env_reaches_container" in docker_args, (
        f"GH_TOKEN not forwarded to docker:\n{docker_args}"
    )

    # Polecat session type must be set
    assert "POLECAT_SESSION_TYPE=crew" in docker_args, (
        f"POLECAT_SESSION_TYPE not in docker -e flags:\n{docker_args}"
    )

    # GIT_ASKPASS must be set (enables credential helper)
    assert "GIT_ASKPASS=true" in docker_args, f"GIT_ASKPASS not in docker -e flags:\n{docker_args}"
