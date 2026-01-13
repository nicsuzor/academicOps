"""Tests for hooks/skill_monitor.py - Domain drift detection and skill injection.

TDD Phase 4: Skill Monitor (PreToolUse)
Tests domain detection from tool args and drift injection.
"""

from __future__ import annotations

from pathlib import Path


class TestDomainDetection:
    """Test domain detection from file paths and tool args."""

    def test_detect_framework_from_hooks_path(self) -> None:
        """Detect framework domain from hooks/ path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Read", {"file_path": "/project/hooks/policy.py"})
        assert result == "framework"

    def test_detect_framework_from_skills_path(self) -> None:
        """Detect framework domain from skills/ path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Edit", {"file_path": "/project/skills/review/SKILL.md"})
        assert result == "framework"

    def test_detect_framework_from_agents_path(self) -> None:
        """Detect framework domain from agents/ path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Read", {"file_path": "/project/agents/custodiet.md"})
        assert result == "framework"

    def test_detect_framework_from_axioms(self) -> None:
        """Detect framework domain from AXIOMS in path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Read", {"file_path": "/project/AXIOMS.md"})
        assert result == "framework"

    def test_detect_python_from_py_extension(self) -> None:
        """Detect python-dev domain from .py file."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Edit", {"file_path": "/project/src/utils.py"})
        assert result == "python-dev"

    def test_detect_python_from_pytest_command(self) -> None:
        """Detect python-dev domain from pytest command."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Bash", {"command": "uv run pytest tests/ -v"})
        assert result == "python-dev"

    def test_detect_python_from_mypy_command(self) -> None:
        """Detect python-dev domain from mypy command."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Bash", {"command": "mypy src/ --strict"})
        assert result == "python-dev"

    def test_detect_analyst_from_dbt_path(self) -> None:
        """Detect analyst domain from dbt/ path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Read", {"file_path": "/project/dbt/models/staging.sql"})
        assert result == "analyst"

    def test_detect_analyst_from_streamlit(self) -> None:
        """Detect analyst domain from streamlit command."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Bash", {"command": "streamlit run app.py"})
        assert result == "analyst"

    def test_detect_analyst_from_sql_file(self) -> None:
        """Detect analyst domain from .sql file."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Edit", {"file_path": "/project/queries/report.sql"})
        assert result == "analyst"

    def test_no_domain_for_generic_file(self) -> None:
        """Return None for files without domain signals."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Read", {"file_path": "/project/README.md"})
        assert result is None

    def test_no_domain_for_empty_args(self) -> None:
        """Return None when tool args have no file path."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Bash", {"command": "ls -la"})
        assert result is None

    def test_framework_takes_priority_over_python(self) -> None:
        """Framework domain takes priority when .py file is in hooks/."""
        from hooks.skill_monitor import detect_domain

        # hooks/policy.py should be framework, not python-dev
        result = detect_domain("Edit", {"file_path": "/project/hooks/policy.py"})
        assert result == "framework"


class TestDriftDetection:
    """Test drift detection comparing active skill to detected domain."""

    def test_no_drift_when_matching(self) -> None:
        """No drift when active_skill matches detected domain."""
        from hooks.skill_monitor import check_drift

        result = check_drift(active_skill="framework", detected_domain="framework")
        assert result is False

    def test_drift_when_mismatched(self) -> None:
        """Drift detected when active_skill differs from domain."""
        from hooks.skill_monitor import check_drift

        result = check_drift(active_skill="python-dev", detected_domain="framework")
        assert result is True

    def test_no_drift_when_no_domain_detected(self) -> None:
        """No drift when domain cannot be detected."""
        from hooks.skill_monitor import check_drift

        result = check_drift(active_skill="python-dev", detected_domain=None)
        assert result is False

    def test_no_drift_when_no_active_skill(self) -> None:
        """No drift when no active skill set (empty string)."""
        from hooks.skill_monitor import check_drift

        result = check_drift(active_skill="", detected_domain="framework")
        assert result is False


class TestSkillContextInjection:
    """Test skill context injection on drift."""

    def test_inject_returns_markdown(self) -> None:
        """Inject returns markdown with skill info."""
        from hooks.skill_monitor import inject_skill_context

        result = inject_skill_context("framework")
        assert "## Skill Context Injection" in result
        assert "framework" in result

    def test_inject_includes_domain(self) -> None:
        """Injected context includes domain name."""
        from hooks.skill_monitor import inject_skill_context

        result = inject_skill_context("python-dev")
        assert "python-dev" in result

    def test_inject_includes_constraints(self) -> None:
        """Injected context includes key constraints."""
        from hooks.skill_monitor import inject_skill_context

        result = inject_skill_context("framework")
        # Framework should mention categorical imperative or similar
        assert "constraint" in result.lower() or "principle" in result.lower()


class TestSkillMonitorIntegration:
    """Integration tests for full skill monitor flow."""

    def test_monitor_returns_none_no_drift(self, tmp_path: Path, monkeypatch) -> None:
        """Monitor returns None when no drift detected."""
        from lib.session_state import HydratorState, save_hydrator_state

        # Set up state with active skill
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",
            "intent_envelope": "test",
            "guardrails": [],
        }
        save_hydrator_state(cwd, state)

        from hooks.skill_monitor import check_skill_monitor

        # Working on .py file with python-dev skill active - no drift
        result = check_skill_monitor(
            tool_name="Edit", tool_input={"file_path": "/project/src/utils.py"}
        )
        assert result is None

    def test_monitor_returns_injection_on_drift(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Monitor returns injection context when drift detected."""
        from lib.session_state import HydratorState, save_hydrator_state

        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        cwd = "/test/project"
        monkeypatch.setenv("CLAUDE_CWD", cwd)

        state: HydratorState = {
            "last_hydration_ts": 0.0,
            "declared_workflow": {
                "gate": "none",
                "pre_work": "none",
                "approach": "direct",
            },
            "active_skill": "python-dev",  # Expecting python work
            "intent_envelope": "test",
            "guardrails": [],
        }
        save_hydrator_state(cwd, state)

        from hooks.skill_monitor import check_skill_monitor

        # Working on hooks/ with python-dev skill - drift to framework
        result = check_skill_monitor(
            tool_name="Edit", tool_input={"file_path": "/project/hooks/policy.py"}
        )
        assert result is not None
        assert "framework" in result
        assert "Skill Context Injection" in result

    def test_monitor_handles_missing_state(self, tmp_path: Path, monkeypatch) -> None:
        """Monitor handles missing hydrator state gracefully."""
        state_dir = tmp_path / "claude-session"
        monkeypatch.setenv("CLAUDE_SESSION_STATE_DIR", str(state_dir))
        monkeypatch.setenv("CLAUDE_CWD", "/nonexistent/project")

        from hooks.skill_monitor import check_skill_monitor

        # No state file exists
        result = check_skill_monitor(
            tool_name="Edit", tool_input={"file_path": "/project/hooks/test.py"}
        )
        # Should return None (no drift enforceable without state)
        assert result is None


class TestSkillMonitorEdgeCases:
    """Edge case tests."""

    def test_handles_task_tool(self) -> None:
        """Task tool with description doesn't cause errors."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain(
            "Task", {"description": "Research something", "prompt": "Find info"}
        )
        assert result is None

    def test_handles_glob_pattern(self) -> None:
        """Glob tool with pattern is handled."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Glob", {"pattern": "**/*.py"})
        assert result == "python-dev"

    def test_handles_grep_path(self) -> None:
        """Grep tool with path is handled."""
        from hooks.skill_monitor import detect_domain

        result = detect_domain("Grep", {"pattern": "def foo", "path": "/project/dbt/"})
        assert result == "analyst"
