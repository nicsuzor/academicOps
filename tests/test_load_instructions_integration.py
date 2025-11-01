"""
Integration tests for consolidated load_instructions.py script.

Tests the complete workflow:
1. 3-tier hierarchy loading (framework → personal → project)
2. Environment variable substitution (${ACADEMICOPS})
3. Two output modes (JSON for hooks, text for commands)
4. Files in new location (core/)
5. No legacy fallbacks

Following testing practices: Integration tests, not unit tests.
Tests validate the whole system works together.
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestLoadInstructionsBasics:
    """Test basic functionality of load_instructions.py."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_load_instructions_exists_and_executable(self, bot_root):
        """Verify load_instructions.py exists and is executable."""
        script = bot_root / "hooks" / "load_instructions.py"
        assert script.exists(), f"Script not found: {script}"
        assert script.stat().st_mode & 0o111, f"Script not executable: {script}"

    def test_core_md_at_new_location(self, bot_root):
        """Verify _CORE.md is at core/ (new standard location)."""
        core_md = bot_root / "core" / "_CORE.md"
        assert core_md.exists(), f"_CORE.md not at new location: {core_md}"

        # Old location (bots/) should NOT exist
        old_location = bot_root / "bots" / "_CORE.md"
        assert not old_location.exists(), (
            f"_CORE.md still at old location: {old_location}"
        )


class TestThreeTierHierarchy:
    """Test 3-tier loading: framework → personal → project."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_loads_from_framework_tier(self, bot_root, monkeypatch, tmp_path):
        """Test loading from framework tier only."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))
        monkeypatch.delenv("ACADEMICOPS_PERSONAL", raising=False)

        # Run from empty project (no project tier)
        empty_project = tmp_path / "empty"
        empty_project.mkdir()
        monkeypatch.chdir(empty_project)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"

        # Should output valid JSON
        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should contain _CORE.md content from framework
        assert "_CORE.md" in result.stderr or "framework" in result.stderr.lower()
        assert "FRAMEWORK" in context or "Core Rules" in context

    def test_loads_from_all_three_tiers(self, bot_root, monkeypatch, tmp_path):
        """Test loading from framework + personal + project tiers."""
        # Setup framework
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))

        # Setup personal tier
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()
        (personal_repo / "core").mkdir(parents=True)
        (personal_repo / "core" / "_CORE.md").write_text(
            "# Personal Preferences\nTEST_PERSONAL_CONTENT"
        )
        monkeypatch.setenv("ACADEMICOPS_PERSONAL", str(personal_repo))

        # Setup project tier
        project_repo = tmp_path / "project"
        project_repo.mkdir()
        (project_repo / "docs" / "bots").mkdir(parents=True)
        (project_repo / "docs" / "bots" / "_CORE.md").write_text(
            "# Project Context\nTEST_PROJECT_CONTENT"
        )
        monkeypatch.chdir(project_repo)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Should contain content from all three tiers
        assert "TEST_PERSONAL_CONTENT" in context, "Personal tier not loaded"
        assert "TEST_PROJECT_CONTENT" in context, "Project tier not loaded"
        # Framework tier should also be present
        assert "FRAMEWORK" in context or "framework" in result.stderr.lower()

    def test_project_tier_appears_first_in_output(self, bot_root, monkeypatch, tmp_path):
        """Test that project tier has highest priority in output order."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))

        # Setup personal tier
        personal_repo = tmp_path / "personal"
        personal_repo.mkdir()
        (personal_repo / "core").mkdir(parents=True)
        (personal_repo / "core" / "_CORE.md").write_text(
            "PERSONAL_MARKER"
        )
        monkeypatch.setenv("ACADEMICOPS_PERSONAL", str(personal_repo))

        # Setup project tier
        project_repo = tmp_path / "project"
        project_repo.mkdir()
        (project_repo / "docs" / "bots").mkdir(parents=True)
        (project_repo / "docs" / "bots" / "_CORE.md").write_text(
            "PROJECT_MARKER"
        )
        monkeypatch.chdir(project_repo)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]

        # Project should appear before personal
        project_pos = context.index("PROJECT_MARKER")
        personal_pos = context.index("PERSONAL_MARKER")
        assert project_pos < personal_pos, "Project tier should appear first"


class TestTwoOutputModes:
    """Test JSON output mode (hooks) and text output mode (commands)."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_json_output_mode_for_core_md(self, bot_root, monkeypatch, tmp_path):
        """Test JSON output mode (default for _CORE.md)."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        assert result.returncode == 0

        # Should output valid JSON
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in output["hookSpecificOutput"]

    def test_text_output_mode_for_custom_file(self, bot_root, monkeypatch, tmp_path):
        """Test text output mode (custom file like DEVELOPER.md)."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))
        monkeypatch.chdir(tmp_path)

        # DEVELOPER.md should exist at new location
        dev_file = bot_root / "agents" / "DEVELOPER.md"
        if not dev_file.exists():
            pytest.skip("DEVELOPER.md not found in agents/ directory")

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py", "DEVELOPER.md"],
            cwd=bot_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Text mode: stdout should have user-friendly status
        assert "Loaded DEVELOPER.md" in result.stdout
        assert "framework" in result.stdout.lower()

        # Text mode: stderr should have full content
        assert "FRAMEWORK: DEVELOPER.md" in result.stderr

    def test_explicit_format_flag(self, bot_root, monkeypatch, tmp_path):
        """Test --format flag to override default."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))
        monkeypatch.chdir(tmp_path)

        # Force text output for _CORE.md (normally JSON)
        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py", "--format=text"],
            cwd=bot_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

        # Should output text, not JSON
        assert "Loaded _CORE.md" in result.stdout
        assert "hookSpecificOutput" not in result.stdout


class TestNoLegacyFallbacks:
    """Test that script does NOT look in legacy locations."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_does_not_load_from_old_agents_location(self, bot_root, monkeypatch, tmp_path):
        """Test that script ignores old agents/ location."""
        # Setup: Put file ONLY in old location
        fake_bot = tmp_path / "fake_bot"
        fake_bot.mkdir()

        # Old location
        old_agents = fake_bot / "agents"
        old_agents.mkdir()
        (old_agents / "_CORE.md").write_text("OLD_LOCATION_CONTENT")

        # New location DOES NOT EXIST
        new_core = fake_bot / "core"
        assert not new_core.exists()

        monkeypatch.setenv("ACADEMICOPS", str(fake_bot))
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        # Should FAIL (not fall back to old location)
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()

    def test_does_not_load_from_docs_chunks(self, bot_root, monkeypatch, tmp_path):
        """Test that script ignores docs/_CHUNKS/ location."""
        fake_bot = tmp_path / "fake_bot"
        fake_bot.mkdir()

        # Old _CHUNKS location
        chunks_dir = fake_bot / "docs" / "_CHUNKS"
        chunks_dir.mkdir(parents=True)
        (chunks_dir / "DEVELOPER.md").write_text("OLD_CHUNKS_LOCATION")

        # New location DOES NOT EXIST
        new_location = fake_bot / "agents" / "DEVELOPER.md"
        assert not new_location.exists()

        monkeypatch.setenv("ACADEMICOPS", str(fake_bot))
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py", "DEVELOPER.md"],
            cwd=bot_root,
            capture_output=True,
            text=True,
        )

        # Should FAIL (not fall back to docs/_CHUNKS/)
        assert result.returncode != 0
        assert "not found" in result.stderr.lower()


class TestEnvironmentVariables:
    """Test environment variable requirements."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_fails_without_academicops_bot(self, bot_root, monkeypatch, tmp_path):
        """Test that script fails without ACADEMICOPS env var."""
        monkeypatch.delenv("ACADEMICOPS", raising=False)
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        # Should fail with clear error message
        assert result.returncode != 0
        assert "ACADEMICOPS" in result.stderr
        assert "not set" in result.stderr.lower()

    def test_works_without_academicops_personal(self, bot_root, monkeypatch, tmp_path):
        """Test that script works without ACADEMICOPS_PERSONAL (optional)."""
        monkeypatch.setenv("ACADEMICOPS", str(bot_root))
        monkeypatch.delenv("ACADEMICOPS_PERSONAL", raising=False)
        monkeypatch.chdir(tmp_path)

        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",
        )

        # Should succeed (personal tier is optional)
        assert result.returncode == 0


# Test execution summary
"""
Test Coverage:

1. **Basics**: Script exists, executable, files at new location
2. **3-Tier Hierarchy**: Framework, personal, project loading and priority
3. **Output Modes**: JSON (hooks), text (commands), --format flag
4. **No Legacy Fallbacks**: Ignores old locations (agents/, docs/_CHUNKS/)
5. **Environment Variables**: Required (ACADEMICOPS), optional (ACADEMICOPS_PERSONAL)

Run tests:
    pytest tests/test_load_instructions_integration.py -v

These tests validate the complete consolidation work from Issue #135.
"""
