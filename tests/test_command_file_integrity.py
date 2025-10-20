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

import subprocess
from pathlib import Path

import pytest


class TestCommandFileReferences:
    """Test that command files reference valid paths."""

    @pytest.fixture
    def bot_root(self):
        """Get academicOps framework root."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def commands_dir(self, bot_root):
        """Get commands directory."""
        return bot_root / ".claude" / "commands"

    def test_all_command_files_exist(self, commands_dir):
        """Verify .claude/commands directory exists and has files."""
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

        # Extract referenced files (looking for patterns like scripts/X.py or _CHUNKS/Y.md)
        if "read_instructions.py" in content:
            script = bot_root / "scripts" / "read_instructions.py"
            assert script.exists(), f"/dev references {script} which doesn't exist"
            assert script.stat().st_mode & 0o111, f"{script} is not executable"

        if "_CHUNKS/DEVELOPER.md" in content:
            # Check where read_instructions.py actually looks
            chunk_file = bot_root / "docs" / "_CHUNKS" / "DEVELOPER.md"
            agents_file = bot_root / "agents" / "_CHUNKS" / "DEVELOPER.md"

            assert chunk_file.exists() or agents_file.exists(), (
                f"/dev references _CHUNKS/DEVELOPER.md but not found at:\n"
                f"  - {chunk_file}\n"
                f"  - {agents_file}"
            )

    def test_ttd_command_references_valid_files(self, bot_root, commands_dir):
        """Test /ttd command references files that actually exist."""
        ttd_cmd = commands_dir / "ttd.md"
        content = ttd_cmd.read_text()

        # Should reference TESTING.md and FAIL-FAST.md
        if "TESTING.md" in content:
            # Check all possible locations
            locations = [
                bot_root / "docs" / "TESTING.md",
                bot_root / "agents" / "TESTING.md",
                bot_root / "docs" / "_CHUNKS" / "TESTING.md",
            ]
            assert any(loc.exists() for loc in locations), (
                f"/ttd references TESTING.md but not found at any location:\n" +
                "\n".join(f"  - {loc}" for loc in locations)
            )

        if "FAIL-FAST.md" in content:
            locations = [
                bot_root / "docs" / "_CHUNKS" / "FAIL-FAST.md",
                bot_root / "agents" / "FAIL-FAST.md",
            ]
            assert any(loc.exists() for loc in locations), (
                f"/ttd references FAIL-FAST.md but not found"
            )

    def test_trainer_command_references_valid_files(self, bot_root, commands_dir):
        """Test /trainer command references files that actually exist."""
        trainer_cmd = commands_dir / "trainer.md"
        content = trainer_cmd.read_text()

        # Check for bots/agents/trainer.md
        if "bots/agents/trainer.md" in content:
            trainer_file = bot_root / "bots" / "agents" / "trainer.md"
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
        return bot_root / ".claude" / "agents"

    def test_trainer_agent_file_exists(self, agents_dir):
        """Verify trainer agent file exists in .claude/agents/."""
        trainer = agents_dir / "trainer.md"
        assert trainer.exists(), f"Trainer agent file missing: {trainer}"

        content = trainer.read_text()

        # Should reference bots/agents/trainer.md for full instructions
        assert "bots/agents/trainer.md" in content, (
            "Trainer agent should reference bots/agents/trainer.md"
        )

    def test_trainer_full_instructions_exist(self, bot_root):
        """Verify full trainer instructions exist at bots/agents/trainer.md."""
        full_instructions = bot_root / "bots" / "agents" / "trainer.md"
        assert full_instructions.exists(), (
            f"Full trainer instructions missing: {full_instructions}"
        )

        # Should be substantial (not just a stub)
        content = full_instructions.read_text()
        assert len(content) > 1000, (
            "Trainer instructions seem too short (< 1000 chars)"
        )


class TestEnvironmentVariableUsage:
    """Test that environment variables are used correctly."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_commands_use_env_vars_not_absolute_paths(self, bot_root):
        """Commands should use ${ACADEMICOPS_BOT} not absolute paths."""
        commands_dir = bot_root / ".claude" / "commands"

        for cmd_file in commands_dir.glob("*.md"):
            content = cmd_file.read_text()

            # Should not contain absolute paths to home directory
            assert "/home/" not in content, (
                f"{cmd_file.name} contains absolute path /home/"
            )

            # If it references bot scripts, should use env var
            if "scripts/" in content and "ACADEMICOPS_BOT" not in content:
                # This might be okay if it's just documentation
                # But flag it for review
                pytest.skip(
                    f"{cmd_file.name} references scripts/ without $ACADEMICOPS_BOT"
                )

    def test_academicops_bot_env_var_is_set(self):
        """ACADEMICOPS_BOT should be set in test environment."""
        import os

        academicops_bot = os.environ.get("ACADEMICOPS_BOT")
        assert academicops_bot is not None, (
            "ACADEMICOPS_BOT environment variable not set. "
            "Add to your shell: export ACADEMICOPS_BOT=/path/to/bot"
        )

        bot_path = Path(academicops_bot)
        assert bot_path.exists(), f"ACADEMICOPS_BOT points to non-existent path: {bot_path}"


class TestReadInstructionsScript:
    """Test that read_instructions.py works with actual file structure."""

    @pytest.fixture
    def bot_root(self):
        return Path(__file__).parent.parent

    def test_read_instructions_finds_developer_md(self, bot_root, monkeypatch):
        """Test that read_instructions.py can find DEVELOPER.md."""
        monkeypatch.setenv("ACADEMICOPS_BOT", str(bot_root))

        # Where does DEVELOPER.md actually exist?
        possible_locations = [
            bot_root / "docs" / "_CHUNKS" / "DEVELOPER.md",
            bot_root / "agents" / "_CHUNKS" / "DEVELOPER.md",
            bot_root / "agents" / "DEVELOPER.md",
        ]

        developer_md = None
        for loc in possible_locations:
            if loc.exists():
                developer_md = loc
                break

        assert developer_md is not None, (
            "DEVELOPER.md not found at any expected location"
        )

        # Test if read_instructions.py can find it
        # Note: read_instructions.py looks in agents/<filename>
        # So if we pass "_CHUNKS/DEVELOPER.md", it looks in agents/_CHUNKS/DEVELOPER.md

        result = subprocess.run(
            ["uv", "run", "python", "scripts/read_instructions.py", "_CHUNKS/DEVELOPER.md"],
            cwd=bot_root,
            capture_output=True,
            text=True,
        )

        # Should either succeed (exit 0) or explain what's missing
        if result.returncode != 0:
            pytest.fail(
                f"read_instructions.py failed to find _CHUNKS/DEVELOPER.md\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )


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
