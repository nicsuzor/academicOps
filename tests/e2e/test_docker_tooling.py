"""Tests for Docker container tooling and entrypoint configuration.

Verifies that all required tools are installed and available on PATH, the
entrypoint configures credentials and isolation correctly, and the aops-core
plugin/extension is baked into the image.

These tests run `docker run` directly — no LLM invocation needed.
"""

import os
import subprocess
import tempfile

import pytest

from tests.conftest import _docker_available


@pytest.mark.slow
@pytest.mark.integration
class TestDockerTooling:
    """Tools, entrypoint, and framework components in the Docker environment."""

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    def _docker_run(self, *cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a command inside the aops-crew Docker image."""
        return subprocess.run(
            ["docker", "run", "--rm", "aops-crew", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _docker_run_with_env(
        self, env: dict, cmd: str, timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """Run a bash command inside aops-crew with environment variables set."""
        docker_cmd = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}"]
        for k, v in env.items():
            docker_cmd.extend(["-e", f"{k}={v}"])
        docker_cmd.extend(["aops-crew", "bash", "-c", cmd])
        return subprocess.run(
            docker_cmd, capture_output=True, text=True, timeout=timeout, check=False
        )

    # --- Tool availability ---

    def test_node_available(self):
        """Verify Node.js and npm are on PATH."""
        result = self._docker_run("node", "--version")
        assert result.returncode == 0, f"node --version failed: {result.stderr}"
        assert result.stdout.strip().startswith("v"), f"Unexpected node output: {result.stdout}"

        result = self._docker_run("npm", "--version")
        assert result.returncode == 0, f"npm --version failed: {result.stderr}"

    def test_rust_available(self):
        """Verify Rust (cargo/rustc) is on PATH."""
        result = self._docker_run("cargo", "--version")
        assert result.returncode == 0, f"cargo --version failed: {result.stderr}"
        assert "cargo" in result.stdout.lower(), f"Unexpected cargo output: {result.stdout}"

        result = self._docker_run("rustc", "--version")
        assert result.returncode == 0, f"rustc --version failed: {result.stderr}"

    def test_git_credential_helper(self):
        """Verify git is installed and credential helpers are available."""
        result = self._docker_run("git", "--version")
        assert result.returncode == 0, f"git --version failed: {result.stderr}"

    def test_python_available(self):
        """Verify Python 3 is on PATH."""
        result = self._docker_run("python3", "--version")
        assert result.returncode == 0, f"python3 --version failed: {result.stderr}"
        assert "Python 3" in result.stdout, f"Unexpected python output: {result.stdout}"

    # --- Framework binaries ---

    def test_pkb_binary_available(self):
        """pkb binary is on PATH and responds to --version."""
        result = self._docker_run("pkb", "--version")
        assert result.returncode == 0, f"pkb --version failed: {result.stderr}"

    def test_gh_cli_available(self):
        """GitHub CLI (gh) is on PATH."""
        result = self._docker_run("gh", "--version")
        assert result.returncode == 0, f"gh --version failed: {result.stderr}"

    # --- Plugin and extension installed ---

    def test_claude_plugin_installed(self):
        """aops-core Claude plugin is baked into the image."""
        result = self._docker_run("bash", "-c", "claude plugin list 2>&1 | grep -i aops")
        assert result.returncode == 0, (
            f"aops-core plugin not found in claude plugin list: {result.stdout}{result.stderr}"
        )

    def test_gemini_extension_installed(self):
        """aops-core Gemini extension files are baked into the image."""
        result = self._docker_run(
            "bash", "-c", "ls /home/worker/.gemini/extensions/aops-core/GEMINI.md 2>&1"
        )
        assert result.returncode == 0, (
            f"aops-core extension not found: {result.stdout}{result.stderr}"
        )

    # --- Entrypoint configuration ---

    def test_entrypoint_configures_git_auth(self):
        """Entrypoint sets up git credentials, SSH isolation, and HTTPS rewrite.

        Runs a shell command inside the container with GH_TOKEN set, verifying
        the full entrypoint credential chain works. This is the single most
        important container smoke test — if this fails, no git operations work.
        """
        test_token = "ghp_test_e2e_credential_check_12345"
        result = self._docker_run_with_env(
            env={"GH_TOKEN": test_token, "SSH_AUTH_SOCK": ""},
            cmd=(
                "echo HELPER=$(git config --global credential.helper) && "
                'echo CRED=$(printf "protocol=https\\nhost=github.com\\n" '
                "| git credential fill 2>/dev/null | grep password) && "
                "echo SSH=$SSH_AUTH_SOCK && "
                "echo REWRITE=$(git config --global --get "
                "url.https://github.com/.insteadOf)"
            ),
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, f"Container exited {result.returncode}:\n{output}"

        # Credential helper is configured
        assert "HELPER=" in output, f"No credential helper configured:\n{output}"
        helper_line = [ln for ln in output.splitlines() if ln.startswith("HELPER=")][0]
        assert "credential" in helper_line.lower() or "!" in helper_line, (
            f"Credential helper not set up:\n{output}"
        )

        # Token resolves through the credential helper
        assert f"password={test_token}" in output, (
            f"Credential helper did not resolve token:\n{output}"
        )

        # SSH is disabled
        ssh_lines = [ln for ln in output.splitlines() if ln.startswith("SSH=")]
        assert ssh_lines and ssh_lines[0] == "SSH=", (
            f"SSH_AUTH_SOCK should be empty (disabled):\n{output}"
        )

        # Git URL rewriting to HTTPS
        assert "REWRITE=git@github.com:" in output, (
            f"SSH→HTTPS URL rewrite not configured:\n{output}"
        )

    def test_staging_copy_to_home(self):
        """Entrypoint copies files from /tmp/staging to $HOME.

        This is the mechanism used to stage auth files (.credentials.json, etc.)
        into the container at runtime. If this breaks, all auth fails.
        """
        with tempfile.TemporaryDirectory() as staging_dir:
            # Create a test file in the staging directory
            test_file = os.path.join(staging_dir, "test_staging_file.txt")
            with open(test_file, "w") as f:
                f.write("staging-test-content-12345")

            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--user",
                    f"{os.getuid()}:{os.getgid()}",
                    "-v",
                    f"{staging_dir}:/tmp/staging:ro",
                    "aops-crew",
                    "bash",
                    "-c",
                    "cat $HOME/test_staging_file.txt 2>&1 || echo STAGING_COPY_FAILED",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            output = result.stdout + result.stderr
            assert "staging-test-content-12345" in output, (
                f"Staging copy to $HOME failed. Output:\n{output}"
            )
