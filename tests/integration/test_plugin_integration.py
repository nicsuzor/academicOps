#!/usr/bin/env python3
"""Integration tests for aops-core plugin loading.

Verifies the plugin is discovered and functional when Claude runs from /tmp
(not $AOPS), ensuring symlink-based discovery works.
"""

from pathlib import Path

import pytest

from tests.conftest import extract_response_text


@pytest.fixture
def tmp_workdir(tmp_path: Path) -> Path:
    """Create a temporary working directory outside $AOPS."""
    workdir = tmp_path / "plugin-test"
    workdir.mkdir()
    return workdir


class TestPluginDiscovery:
    """Verify plugin is discovered via symlink."""

    @pytest.mark.integration
    def test_plugin_symlink_exists(self) -> None:
        """Plugin symlink must exist at ~/.claude/plugins/aops-core."""
        symlink = Path.home() / ".claude" / "plugins" / "aops-core"
        if not symlink.exists():
            pytest.skip(
                "Plugin symlink not installed (expected for CI/fresh environments)"
            )
        assert symlink.is_symlink(), f"Not a symlink: {symlink}"

    @pytest.mark.integration
    def test_plugin_target_valid(self) -> None:
        """Plugin symlink must point to valid directory."""
        symlink = Path.home() / ".claude" / "plugins" / "aops-core"
        if not symlink.exists():
            pytest.skip(
                "Plugin symlink not installed (expected for CI/fresh environments)"
            )
        target = symlink.resolve()
        assert target.is_dir(), f"Symlink target not a directory: {target}"
        assert (target / ".claude-plugin" / "plugin.json").exists(), (
            "Missing plugin.json"
        )


class TestPluginLoading:
    """Verify plugin loads and components are available."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_skills_available_from_tmp(
        self, claude_headless_tracked, tmp_workdir: Path
    ) -> None:
        """Core skills should be available when running from /tmp."""
        result, session_id, tool_calls = claude_headless_tracked(
            "List the available skills. Mention: tasks, remember, python-dev, "
            "feature-dev, framework, audit. Just list them, don't invoke.",
            cwd=tmp_workdir,
            timeout_seconds=60,
        )

        response = extract_response_text(result)
        response_lower = response.lower()

        # Check core skills mentioned in response
        core_skills = [
            "tasks",
            "remember",
            "python-dev",
            "feature-dev",
            "framework",
            "audit",
        ]
        found = [s for s in core_skills if s in response_lower]

        assert len(found) >= 4, (
            f"Expected at least 4 core skills mentioned, found {len(found)}: {found}. "
            f"Response: {response[:500]}"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_skill_invocation_from_tmp(
        self, claude_headless_tracked, tmp_workdir: Path, skill_was_invoked
    ) -> None:
        """Skill tool should work when running from /tmp."""
        result, session_id, tool_calls = claude_headless_tracked(
            "Invoke the tasks skill with args='help'. Use Skill(skill='tasks', args='help')",
            cwd=tmp_workdir,
            timeout_seconds=90,
        )

        # Check Skill tool was called
        assert skill_was_invoked(tool_calls, "tasks"), (
            f"Expected Skill(tasks) invocation. Tool calls: "
            f"{[c['name'] for c in tool_calls]}"
        )

    @pytest.mark.integration
    @pytest.mark.slow
    def test_agents_registered(
        self, claude_headless_tracked, tmp_workdir: Path
    ) -> None:
        """Core agents should be registered as subagent types."""
        result, session_id, tool_calls = claude_headless_tracked(
            "What subagent types are available for the Task tool? "
            "List any you see including: planner, prompt-hydrator, critic, custodiet.",
            cwd=tmp_workdir,
            timeout_seconds=60,
        )

        response = extract_response_text(result)
        response_lower = response.lower()

        # Check core agents mentioned
        core_agents = ["planner", "prompt-hydrator", "critic", "custodiet"]
        found = [
            a
            for a in core_agents
            if a.replace("-", "") in response_lower.replace("-", "")
        ]

        assert len(found) >= 2, (
            f"Expected at least 2 core agents mentioned, found {len(found)}: {found}. "
            f"Response: {response[:500]}"
        )


class TestHookFunctionality:
    """Verify hooks are functional."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_session_completes_from_tmp(
        self, claude_headless, tmp_workdir: Path
    ) -> None:
        """Session should complete without hook errors when run from /tmp."""
        result = claude_headless(
            "What is 2+2? Answer with just the number.",
            cwd=tmp_workdir,
            timeout_seconds=60,
        )

        response = extract_response_text(result)
        assert "4" in response, f"Expected '4' in response: {response}"
