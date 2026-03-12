"""
End-to-end tests for gate enforcement.

Consolidated from 14 slow tests (7 per CLI) to 4 essential tests (2 per CLI).
Tests actual tool operations and verifies the gate response.
"""

import pytest


@pytest.fixture(autouse=True)
def enforce_strict_gates(monkeypatch):
    """Ensure all gates are explicitly blocking during E2E tests."""
    from lib.gates.definitions import GATE_CONFIGS

    for gate_config in GATE_CONFIGS:
        monkeypatch.setenv(f"{gate_config.name.upper()}_GATE_MODE", "block")


@pytest.mark.slow
class TestHydrationGateE2E:
    """E2E tests for hydration gate enforcement."""

    def test_hydration_blocks_read_tool_before_hydration(self, cli_headless):
        """GIVEN: Fresh session. WHEN: Read tool. THEN: Blocked."""
        runner, platform = cli_headless

        result = runner(
            "Read the file /etc/hosts and tell me what's in it. Do not use any other tools first.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = result.get("output", "")

        from tests.conftest import check_blocked

        is_blocked = check_blocked(result)

        assert is_blocked, (
            f"[{platform}] Expected hydration gate to block Read tool.\nOutput: {output_text[:500]}"
        )

    def test_hydration_allows_safe_git_bash(self, cli_headless):
        """GIVEN: Fresh session. WHEN: git status. THEN: Allowed."""
        runner, platform = cli_headless

        result = runner(
            "Run 'git status' using Bash. Just run that one command and show me the output.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = result.get("output", "")

        git_output_indicators = ["branch", "modified", "untracked", "clean", "changes", "commit"]
        has_git_output = any(ind.lower() in output_text.lower() for ind in git_output_indicators)

        if "BLOCKED" in output_text.upper():
            assert "hydration" not in output_text.lower(), (
                f"[{platform}] Safe git commands should bypass hydration gate"
            )
        else:
            assert has_git_output, (
                f"[{platform}] Expected git status output, got: {output_text[:300]}"
            )


@pytest.mark.slow
class TestHydrationExemptToolsE2E:
    """E2E tests for tools exempt from hydration gate."""

    def test_glob_bypasses_hydration(self, cli_headless):
        """GIVEN: Fresh session. WHEN: Glob tool. THEN: Allowed."""
        runner, platform = cli_headless

        result = runner(
            "Use the Glob tool with pattern '*.py' to find Python files in the current directory.",
            model="haiku" if platform == "claude" else None,
            fail_on_error=False,
        )

        output_text = result.get("output", "")

        from tests.conftest import check_blocked

        blocked_for_hydration = check_blocked(result)

        assert not blocked_for_hydration, (
            f"[{platform}] Glob should bypass hydration gate.\nOutput: {output_text[:500]}"
        )
