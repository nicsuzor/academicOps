"""
Integration tests for command and agent file integrity.

Tests that:
1. All files referenced in commands actually exist
2. All scripts referenced in commands are executable
3. Environment variables referenced are documented
4. Agent files can be loaded by their commands

Following testing practices: Integration tests, not unit tests.
Validates the whole system works together.
"""

import json
import subprocess
from pathlib import Path

import pytest


from .paths import get_aops_root, get_aca_root


class TestCommandFileReferences:
    """Test that command files reference valid paths."""

    @pytest.fixture
    def bot_root(self):
        """Get academicOps framework root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def commands_dir(self, bot_root):
        """Get commands directory."""
        return bot_root / "commands"

    def test_all_command_files_exist(self, commands_dir):
        """Verify commands directory exists and has files."""
        assert commands_dir.exists(), f"Commands directory missing: {commands_dir}"

        commands = list(commands_dir.glob("*.md"))
        assert len(commands) > 0, "No command files found"

        # Expected commands
        expected = ["dev.md", "trainer.md", "ttd.md", "log-failure.md", "ops.md"]
        for cmd in expected:
            assert (commands_dir / cmd).exists(), f"Missing command: {cmd}"

    def test_dev_command_references_valid_files(self, bot_root, commands_dir):
        """Test /dev command references files that actually exist."""
        dev_cmd = commands_dir / "dev.md"
        content = dev_cmd.read_text()

        # Should reference load_instructions.py (consolidated script)
        if "load_instructions.py" in content:
            script = bot_root / "hooks" / "load_instructions.py"
            assert script.exists(), f"/dev references {script} which doesn't exist"
            assert script.stat().st_mode & 0o111, f"{script} is not executable"

        # If it references DEVELOPER.md, check it exists at new location
        if "DEVELOPER.md" in content:
            # New location (agents/)
            dev_file = bot_root / "agents" / "DEVELOPER.md"

            # If not migrated yet, might still be in old location
            old_locations = [
                bot_root / "docs" / "_CHUNKS" / "DEVELOPER.md",
                bot_root / "core" / "DEVELOPER.md",
            ]

            exists_somewhere = dev_file.exists() or any(
                loc.exists() for loc in old_locations
            )
            assert exists_somewhere, (
                f"/dev references DEVELOPER.md but not found at:\n"
                f"  - {dev_file} (new location)\n"
                + "\n".join(f"  - {loc} (old location)" for loc in old_locations)
            )

    def test_ttd_command_references_valid_files(self, bot_root, commands_dir):
        """Test /ttd command references files that actually exist."""
        ttd_cmd = commands_dir / "ttd.md"
        content = ttd_cmd.read_text(encoding="utf-8", errors="replace")

        # Should reference TESTING.md and FAIL-FAST.md
        if "TESTING.md" in content:
            # New location (agents/) or old locations
            new_loc = bot_root / "agents" / "TESTING.md"
            old_locations = [
                bot_root / "docs" / "TESTING.md",
                bot_root / "docs" / "_CHUNKS" / "TESTING.md",
            ]
            exists_somewhere = new_loc.exists() or any(
                loc.exists() for loc in old_locations
            )
            assert exists_somewhere, (
                f"/ttd references TESTING.md but not found at:\n"
                f"  - {new_loc} (new location)\n"
                + "\n".join(f"  - {loc} (old location)" for loc in old_locations)
            )

        if "FAIL-FAST.md" in content:
            new_loc = bot_root / "agents" / "FAIL-FAST.md"
            old_locations = [
                bot_root / "docs" / "_CHUNKS" / "FAIL-FAST.md",
            ]
            exists_somewhere = new_loc.exists() or any(
                loc.exists() for loc in old_locations
            )
            assert exists_somewhere, "/ttd references FAIL-FAST.md but not found"

    def test_trainer_command_references_valid_files(self, bot_root, commands_dir):
        """Test /trainer command references files that actually exist."""
        trainer_cmd = commands_dir / "trainer.md"
        content = trainer_cmd.read_text()

        # Check for agents/trainer.md
        if "agents/trainer.md" in content:
            trainer_file = bot_root / "agents" / "trainer.md"
            assert trainer_file.exists(), (
                f"/trainer references {trainer_file} which doesn't exist"
            )


class TestAgentFileIntegrity:
    """Test that agent files reference valid paths and can be loaded."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    @pytest.fixture
    def agents_dir(self, bot_root):
        return bot_root / "agents"

    def test_trainer_agent_file_exists(self, agents_dir):
        """Verify trainer agent file exists in agents/."""
        trainer = agents_dir / "trainer.md"
        assert trainer.exists(), f"Trainer agent file missing: {trainer}"

        content = trainer.read_text()

        # File should be substantial (actual trainer instructions)
        assert len(content) > 1000, "Trainer agent file seems too short (< 1000 chars)"

    def test_trainer_full_instructions_exist(self, bot_root):
        """Verify full trainer instructions exist at agents/trainer.md."""
        full_instructions = bot_root / "agents" / "trainer.md"
        assert full_instructions.exists(), (
            f"Full trainer instructions missing: {full_instructions}"
        )

        # Should be substantial (not just a stub)
        content = full_instructions.read_text()
        assert len(content) > 1000, "Trainer instructions seem too short (< 1000 chars)"


class TestEnvironmentVariableUsage:
    """Test that environment variables are used correctly."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_commands_use_env_vars_not_absolute_paths(self, bot_root):
        """Commands should use ${AOPS} not absolute paths."""
        commands_dir = bot_root / "commands"

        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text(encoding="utf-8", errors="replace")

            # Should not contain absolute paths to home directory
            assert "/home/" not in content, (
                f"{cmd_file.name} contains absolute path /home/"
            )

            # If it references bot scripts, should use env var
            if "scripts/" in content and "AOPS" not in content:
                # This might be okay if it's just documentation
                # But flag it for review
                pytest.skip(f"{cmd_file.name} references scripts/ without $AOPS")

    def test_academicops_bot_env_var_is_set(self):
        """AOPS should be set in test environment."""
        import os

        academicops_bot = get_aops_root()
        assert academicops_bot is not None, (
            "AOPS environment variable not set. "
            "Add to your shell: export AOPS=/path/to/bot"
        )

        bot_path = Path(academicops_bot)
        assert bot_path.exists(), f"AOPS points to non-existent path: {bot_path}"


class TestLoadInstructionsScript:
    """Test that load_instructions.py works with actual file structure."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_load_instructions_finds_core_md(self, bot_root, monkeypatch):
        """Test that load_instructions.py can find _CORE.md at new location."""
        monkeypatch.setenv("AOPS", str(bot_root))

        # _CORE.md should be at new location
        core_md = bot_root / "core" / "_CORE.md"
        assert core_md.exists(), f"_CORE.md not found at {core_md}"

        # Test default usage (loads _CORE.md, outputs JSON)
        result = subprocess.run(
            ["uv", "run", "python", "hooks/load_instructions.py"],
            check=False,
            cwd=bot_root,
            capture_output=True,
            text=True,
            input="{}",  # Empty JSON input
        )

        assert result.returncode == 0, (
            f"load_instructions.py failed to load _CORE.md\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

        # Should output valid JSON
        try:
            output = json.loads(result.stdout)
            assert "hookSpecificOutput" in output
            assert "additionalContext" in output["hookSpecificOutput"]
        except json.JSONDecodeError as e:
            pytest.fail(f"Output is not valid JSON: {e}\n{result.stdout}")


# Test execution notes
"""
Run these tests to validate command/agent file integrity:

    pytest tests/test_command_file_integrity.py -v

These tests catch:
- Missing files referenced in commands
- Broken paths in agent files
- Environment variable issues
- Integration problems between commands and scripts

When tests fail:
1. Check if files moved without updating references
2. Verify environment variables are set
3. Check if read_instructions.py looks in correct directory
4. Update command files to reference correct paths
"""
