"""Tests for Docker container tooling and entrypoint configuration.

Verifies that all required tools are installed and available on PATH, the
entrypoint configures credentials and isolation correctly, and the aops-core
plugin/extension is baked into the image.

These tests run `docker run` directly — no LLM invocation needed.

Optimization: tool-availability checks are batched into a single container
invocation via a class-scoped fixture. Only tests that need special env vars
or volume mounts run their own container.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from tests.conftest import _docker_available

# --- Batched tool checks (single container) ---


@pytest.mark.slow
@pytest.mark.integration
class TestDockerTooling:
    """Tools and framework components in the Docker environment."""

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    @pytest.fixture(scope="class")
    def tooling_results(self):
        """Run ALL tool checks in a single docker container, return parsed results."""
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

        script = (
            'echo "NODE=$(node --version 2>&1)"\n'
            'echo "NPM=$(npm --version 2>&1)"\n'
            'echo "CARGO=$(cargo --version 2>&1)"\n'
            'echo "RUSTC=$(rustc --version 2>&1)"\n'
            'echo "GIT=$(git --version 2>&1)"\n'
            'echo "PYTHON=$(python3 --version 2>&1)"\n'
            'echo "PKB=$(pkb --version 2>&1)"\n'
            'echo "GH=$(gh --version 2>&1 | head -1)"\n'
            'echo "CLAUDE_PLUGIN=$(claude plugin list 2>/dev/null | grep -i aops || echo NOTFOUND)"\n'
            'echo "GEMINI_EXT=$(ls /home/worker/.gemini/extensions/aops-core/GEMINI.md 2>&1)"\n'
            'echo "DNS_GOOGLE=$(getent hosts oauth2.googleapis.com 2>&1 | head -1)"\n'
            'echo "DNS_ANTHROPIC=$(getent hosts api.anthropic.com 2>&1 | head -1)"\n'
            'echo "DNS_GITHUB=$(getent hosts github.com 2>&1 | head -1)"\n'
        )
        result = subprocess.run(
            ["docker", "run", "--rm", "aops-crew", "bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, (
            f"Batch tool check container failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Parse KEY=VALUE lines into dict
        results = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, _, value = line.partition("=")
                results[key] = value
        return results

    # --- Tool availability ---

    def test_node_available(self, tooling_results):
        """Node.js and npm are on PATH."""
        assert tooling_results["NODE"].startswith("v"), (
            f"Unexpected node output: {tooling_results['NODE']}"
        )
        assert tooling_results["NPM"], f"npm --version returned empty: {tooling_results['NPM']}"

    def test_rust_available(self, tooling_results):
        """Rust (cargo/rustc) is on PATH."""
        assert "cargo" in tooling_results["CARGO"].lower(), (
            f"Unexpected cargo output: {tooling_results['CARGO']}"
        )
        assert "rustc" in tooling_results["RUSTC"].lower(), (
            f"Unexpected rustc output: {tooling_results['RUSTC']}"
        )

    def test_git_available(self, tooling_results):
        """Git is installed."""
        assert "git version" in tooling_results["GIT"].lower(), (
            f"Unexpected git output: {tooling_results['GIT']}"
        )

    def test_python_available(self, tooling_results):
        """Python 3 is on PATH."""
        assert "Python 3" in tooling_results["PYTHON"], (
            f"Unexpected python output: {tooling_results['PYTHON']}"
        )

    def test_pkb_binary_available(self, tooling_results):
        """pkb binary is on PATH and responds to --version."""
        assert tooling_results["PKB"], f"pkb --version returned empty: {tooling_results['PKB']}"

    def test_gh_cli_available(self, tooling_results):
        """GitHub CLI (gh) is on PATH."""
        assert "gh version" in tooling_results["GH"].lower(), (
            f"Unexpected gh output: {tooling_results['GH']}"
        )

    def test_claude_plugin_installed(self, tooling_results):
        """academicOps Claude plugin is baked into the image."""
        output = tooling_results["CLAUDE_PLUGIN"]
        assert "aops" in output.lower() and "NOTFOUND" not in output, (
            f"academicOps plugin not found in claude plugin list: {output}"
        )

    def test_gemini_extension_installed(self, tooling_results):
        """academicOps Gemini extension files are baked into the image."""
        assert "GEMINI.md" in tooling_results["GEMINI_EXT"], (
            f"academicOps extension not found: {tooling_results['GEMINI_EXT']}"
        )

    # --- Network connectivity (DNS resolution from inside the container) ---

    def test_dns_resolves_google_oauth(self, tooling_results):
        """Container can resolve oauth2.googleapis.com (Gemini auth)."""
        assert tooling_results.get("DNS_GOOGLE", "").strip(), (
            "Cannot resolve oauth2.googleapis.com from inside container. "
            "Gemini auth will fail with EAI_AGAIN. "
            f"getent output: {tooling_results.get('DNS_GOOGLE', '<missing>')}"
        )

    def test_dns_resolves_anthropic_api(self, tooling_results):
        """Container can resolve api.anthropic.com (Claude auth)."""
        assert tooling_results.get("DNS_ANTHROPIC", "").strip(), (
            "Cannot resolve api.anthropic.com from inside container. "
            "Claude API calls will fail. "
            f"getent output: {tooling_results.get('DNS_ANTHROPIC', '<missing>')}"
        )

    def test_dns_resolves_github(self, tooling_results):
        """Container can resolve github.com (git push/pull)."""
        assert tooling_results.get("DNS_GITHUB", "").strip(), (
            "Cannot resolve github.com from inside container. "
            "Git operations will fail. "
            f"getent output: {tooling_results.get('DNS_GITHUB', '<missing>')}"
        )


# --- Tests requiring special env/mounts (separate containers) ---


@pytest.mark.slow
@pytest.mark.integration
class TestDockerEntrypoint:
    """Entrypoint credential and staging configuration."""

    @pytest.fixture(autouse=True)
    def _require_docker(self):
        if not _docker_available():
            pytest.skip("Docker not available or aops-crew image not built")

    def test_entrypoint_configures_git_auth(self):
        """Entrypoint sets up git credentials, SSH isolation, and HTTPS rewrite.

        Runs a shell command inside the container with GH_TOKEN set, verifying
        the full entrypoint credential chain works. This is the single most
        important container smoke test — if this fails, no git operations work.
        """
        test_token = "ghp_test_e2e_credential_check_12345"
        docker_cmd = ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}"]
        docker_cmd.extend(["-e", f"GH_TOKEN={test_token}", "-e", "SSH_AUTH_SOCK="])
        docker_cmd.extend(
            [
                "aops-crew",
                "bash",
                "-c",
                (
                    "echo HELPER=$(git config --global credential.helper) && "
                    'echo CRED=$(printf "protocol=https\\nhost=github.com\\n" '
                    "| git credential fill 2>/dev/null | grep password) && "
                    "echo SSH=$SSH_AUTH_SOCK && "
                    "echo REWRITE=$(git config --global --get "
                    "url.https://github.com/.insteadOf)"
                ),
            ]
        )
        result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30, check=False)
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
        # Use a path under $HOME — on macOS with Colima, only /Users is shared
        # via virtiofs. Python's tempfile uses /private/var/folders/ which is
        # invisible to the Docker daemon.
        docker_visible_tmp = Path.home() / ".aops" / "tmp" / "test-staging"
        docker_visible_tmp.mkdir(parents=True, exist_ok=True)
        staging_dir = tempfile.mkdtemp(dir=docker_visible_tmp)
        try:
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
        finally:
            import shutil

            shutil.rmtree(staging_dir, ignore_errors=True)
