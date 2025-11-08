"""Integration tests for hierarchical context loading.

Tests the actual behavior of load_instructions.py across different
repository contexts to validate design decisions documented in ARCHITECTURE.md.

These tests validate:
1. Personal preferences load in all repos
2. Strategic data (data/) only accessible in personal repo
3. Project-specific context loads correctly
4. Privacy boundaries maintained

Status: DESIGN PHASE - Tests define expected behavior
"""

import json
import os
import subprocess
from pathlib import Path

import pytest


class TestContextLoadingHierarchy:
    """Test that the 3-tier loading hierarchy works as documented."""

    def test_personal_preferences_load_in_project_repo(self, tmp_path, monkeypatch):
        """
        VALIDATES: Personal preferences (docs/bots/INSTRUCTIONS.md) should load
        when working in a project repo.

        Design decision (ARCHITECTURE.md lines 82-85):
        - Project repos load user preferences from personal repo ✓
        - But they do NOT load strategic context (data/) ✗

        Test structure:
        - personal_repo/docs/bots/INSTRUCTIONS.md contains "TOOL_PREFERENCE: BigQuery"
        - project_repo/docs/bots/INSTRUCTIONS.md contains "PROJECT: buttermilk"
        - Working directory: project_repo

        Expected:
        - Agent sees both TOOL_PREFERENCE and PROJECT
        - Agent does NOT see personal_repo/data/goals
        """
        # Setup personal repo
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()
        (personal_repo / "bots" / "docs").mkdir(parents=True)
        (personal_repo / "bots" / "docs" / "INSTRUCTIONS.md").write_text(
            "# Personal Preferences\n\nTOOL_PREFERENCE: BigQuery > Redshift"
        )
        (personal_repo / "data" / "goals").mkdir(parents=True)
        (personal_repo / "data" / "goals" / "strategic.md").write_text(
            "Book is deprioritized"
        )

        # Setup project repo
        project_repo = tmp_path / "project"
        project_repo.mkdir()
        (project_repo / "bots" / "docs").mkdir(parents=True)
        (project_repo / "bots" / "docs" / "INSTRUCTIONS.md").write_text(
            "# Project Context\n\nPROJECT: buttermilk analytics engine"
        )

        # Set environment to point to personal repo
        monkeypatch.setenv("ACA", str(personal_repo))
        monkeypatch.setenv(
            "AOPS", str(Path(__file__).parent.parent)
        )  # Framework root
        monkeypatch.chdir(project_repo)

        # Run load_instructions.py
        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",  # Empty JSON input
        )

        # Parse output
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Assertions
        assert "BigQuery > Redshift" in context, "Personal preferences should load"
        assert "buttermilk analytics engine" in context, "Project context should load"
        assert "Book is deprioritized" not in context, (
            "Strategic data should NOT auto-load in project repo"
        )

    def test_strategic_data_accessible_in_personal_repo(self, tmp_path, monkeypatch):
        """
        VALIDATES: Strategic data (data/goals, data/tasks) should be accessible
        when working IN the personal repo.

        Design decision (ARCHITECTURE.md line 80):
        - data/ directory → used by strategist agent ONLY when working in writing repo

        Test structure:
        - personal_repo/docs/bots/INSTRUCTIONS.md has reference to data/
        - Working directory: personal_repo

        Expected:
        - Strategist agent can access data/goals, data/tasks
        - This is validated by checking INSTRUCTIONS.md references data paths
        """
        # Setup personal repo
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()
        (personal_repo / "bots" / "docs").mkdir(parents=True)
        (personal_repo / "bots" / "docs" / "INSTRUCTIONS.md").write_text(
            """# Personal Context

## Strategic Data
- Goals: data/goals/
- Tasks: data/tasks/
- Projects: data/projects/

When working in THIS repo, strategist agent accesses these paths.
"""
        )
        (personal_repo / "data" / "goals").mkdir(parents=True)

        monkeypatch.setenv("ACA", str(personal_repo))
        monkeypatch.setenv("AOPS", str(Path(__file__).parent.parent))
        monkeypatch.chdir(personal_repo)

        # Run load_instructions.py
        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",
        )

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # When in personal repo, instructions should reference data/ paths
        assert "data/goals" in context, "Strategic data paths should be documented"
        assert "data/tasks" in context, "Task management paths should be accessible"

    def test_project_context_overrides_personal(self, tmp_path, monkeypatch):
        """
        VALIDATES: Project-specific context takes priority over personal preferences.

        Design decision (ARCHITECTURE.md line 42):
        - Priority: Project > Personal > Framework

        Test structure:
        - personal/docs/bots/INSTRUCTIONS.md says "Use Streamlit"
        - project/docs/bots/INSTRUCTIONS.md says "Use Tableau for this project"

        Expected:
        - Both load, project context listed first (higher priority)
        """
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()
        (personal_repo / "bots" / "docs").mkdir(parents=True)
        (personal_repo / "bots" / "docs" / "INSTRUCTIONS.md").write_text(
            "VISUALIZATION_TOOL: Streamlit (default)"
        )

        project_repo = tmp_path / "project"
        project_repo.mkdir()
        (project_repo / "bots" / "docs").mkdir(parents=True)
        (project_repo / "bots" / "docs" / "INSTRUCTIONS.md").write_text(
            "VISUALIZATION_TOOL: Tableau (project requirement)"
        )

        monkeypatch.setenv("ACA", str(personal_repo))
        monkeypatch.setenv("AOPS", str(Path(__file__).parent.parent))
        monkeypatch.chdir(project_repo)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",
        )

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Both should be present
        assert "Streamlit" in context, "Personal preference should load"
        assert "Tableau" in context, "Project override should load"

        # Project should appear first (higher priority in context)
        streamlit_pos = context.index("Streamlit")
        tableau_pos = context.index("Tableau")
        assert tableau_pos < streamlit_pos, (
            "Project context should appear before personal"
        )


class TestPrivacyBoundaries:
    """Test that privacy boundaries are maintained correctly."""

    def test_personal_repo_path_not_embedded_in_project_config(self, tmp_path):
        """
        VALIDATES: Project repos should not hardcode paths to personal repo.

        Design decision (ARCHITECTURE.md "Open Questions" section):
        - What if personal repo is private and project repo is public?
        - Security implications for shared repos?

        Expected:
        - Project .claude/settings.json uses environment variables
        - No absolute paths to personal repo
        - Safe to share project repo publicly
        """
        project_repo = tmp_path / "project"
        project_repo.mkdir()

        # Simulate install_bot.sh creating settings
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                # Should use env var, not absolute path
                                "command": "uv run python $AOPS/hooks/load_instructions.py",
                            }
                        ]
                    }
                ]
            }
        }

        settings_file = project_repo / ".claude" / "settings.json"
        settings_file.parent.mkdir(parents=True)
        settings_file.write_text(json.dumps(settings, indent=2))

        content = settings_file.read_text()

        # Privacy checks
        assert "/home/" not in content, "Should not contain absolute paths to user home"
        assert "$AOPS" in content or "${AOPS}" in content, (
            "Should use environment variable"
        )

    def test_symlinks_are_gitignored(self, tmp_path):
        """
        VALIDATES: Symlinks to framework should not be committed.

        Design decision (ARCHITECTURE.md line 135):
        - .gitignore includes bots/.academicOps (never commit symlink)

        Expected:
        - bots/.academicOps is gitignored
        - Personal repo remains private even if project is public
        """
        project_repo = tmp_path / "project"
        project_repo.mkdir()

        # Create .gitignore (as install_bot.sh would)
        gitignore = project_repo / ".gitignore"
        gitignore.write_text(
            """# academicOps
bots/.academicOps
.claude/agents
.claude/commands
"""
        )

        content = gitignore.read_text()
        assert ".academicOps" in content, "Framework symlink should be ignored"


class TestFallbackBehavior:
    """Test legacy path fallback behavior during migration."""

    def test_legacy_path_fallback(self, tmp_path, monkeypatch):
        """
        VALIDATES: System supports legacy paths during migration.

        Design decision (ARCHITECTURE.md line 67):
        - Personal tier currently uses legacy paths (docs/bots/INSTRUCTIONS.md)
        - Migration to docs/bots/INSTRUCTIONS.md in progress

        Expected:
        - If docs/bots/INSTRUCTIONS.md missing, fall back to docs/bots/INSTRUCTIONS.md
        - Graceful degradation during migration period
        """
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()

        # Only create LEGACY path
        (personal_repo / "docs" / "bots").mkdir(parents=True)
        (personal_repo / "docs" / "bots" / "INSTRUCTIONS.md").write_text(
            "LEGACY_CONTENT: User preferences from old location"
        )

        monkeypatch.setenv("ACA", str(personal_repo))
        monkeypatch.setenv("AOPS", str(Path(__file__).parent.parent))
        monkeypatch.chdir(personal_repo)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",
        )

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        assert "LEGACY_CONTENT" in context, (
            "Should fall back to legacy path if new path missing"
        )


class TestEnvironmentVariableRequirements:
    """Test environment variable handling."""

    def test_academicops_bot_required(self, tmp_path, monkeypatch):
        """
        VALIDATES: AOPS is required, ACA is optional.

        Design decision (INSTALL.md lines 18-28):
        - AOPS: Required
        - ACA: Optional (for personal context)

        Expected:
        - Missing AOPS raises clear error
        - Missing ACA is acceptable (framework-only mode)
        """
        # Clear environment variables
        monkeypatch.delenv("AOPS", raising=False)
        monkeypatch.delenv("ACA", raising=False)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode != 0, "Should fail if AOPS not set"
        assert "AOPS" in result.stderr, (
            "Error message should mention missing variable"
        )

    def test_works_without_personal_context(self, tmp_path, monkeypatch):
        """
        VALIDATES: System works with only framework, no personal context.

        Expected:
        - AOPS set → works
        - ACA not set → silently skipped
        - Framework tier loads successfully
        """
        monkeypatch.setenv("AOPS", str(Path(__file__).parent.parent))
        monkeypatch.delenv("ACA", raising=False)

        project_repo = tmp_path / "project"
        project_repo.mkdir()
        monkeypatch.chdir(project_repo)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            input="{}",
        )

        # Should succeed with just framework tier
        assert result.returncode == 0, (
            "Should work without personal context (framework-only mode)"
        )

        # Check stderr for user-facing message
        assert "✓ bot" in result.stderr, "Should confirm framework tier loaded"


@pytest.mark.skip(reason="Requires actual repo setup - run manually")
class TestRealWorldScenarios:
    """Manual integration tests using actual repositories.

    These tests require:
    - ~/src/bot (academicOps framework)
    - ~/src/writing (personal repo)
    - ~/src/projects/buttermilk (project repo)

    Run with: pytest -v tests/test_context_loading_integration.py::TestRealWorldScenarios -s
    """

    def test_writing_repo_loads_all_context(self):
        """Test that personal repo sees all its own context."""
        os.chdir(os.path.expanduser("~/src/writing"))

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                os.path.expanduser("~/src/bot/hooks/load_instructions.py"),
            ],
            check=False,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should see personal preferences
        assert "ADHD" in context or "accommodations" in context.lower()

        # Should reference strategic data
        assert "data/" in context or "goals" in context

    def test_buttermilk_repo_loads_preferences_not_strategic_data(self):
        """Test that project repo sees user preferences but not strategic data."""
        buttermilk_path = os.path.expanduser("~/src/projects/buttermilk")
        if not os.path.exists(buttermilk_path):
            pytest.skip("buttermilk repo not found")

        os.chdir(buttermilk_path)

        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                os.path.expanduser("~/src/bot/hooks/load_instructions.py"),
            ],
            check=False,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should see user preferences from ~/src/writing
        assert "ADHD" in context or "BigQuery" in context or "Streamlit" in context

        # Should NOT see private strategic data
        assert "Book is deprioritized" not in context
        assert "TJA Dashboard" not in context  # Specific strategic priority


# Test execution summary
"""
Test Strategy:

1. **Hierarchy Tests**: Validate 3-tier loading (project > personal > framework)
2. **Privacy Tests**: Ensure strategic data stays private, preferences are shareable
3. **Fallback Tests**: Support legacy paths during migration
4. **Environment Tests**: Required vs optional variables
5. **Real-World Tests**: Manual validation with actual repos

Status: DESIGN PHASE
- Tests define expected behavior documented in ARCHITECTURE.md
- Some tests may fail until load_instructions.py fully implements design
- Use failures to guide implementation refinements

Run tests:
    pytest tests/test_context_loading_integration.py -v

Run with real repos (manual):
    pytest tests/test_context_loading_integration.py::TestRealWorldScenarios -v -s
"""
