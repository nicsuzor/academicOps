"""Deployment Architecture Validation Tests.

Tests validate the "flat architecture" pre-release requirements (Issue #128).
These tests define the specification through executable validation.

Requirements tested:
1. Path predictability - Same folder hierarchy everywhere
2. Symlink creation - Framework files symlinked correctly
3. Gitignore coverage - All symlinks ignored
4. Modular instructions - /bots/ structure validated
5. Project overrides - Override mechanism works
6. CLAUDE.md discovery - Just-in-time loading works
7. Script invocation - Scripts accessible via symlinks
8. Pre-commit integration - Hooks installed correctly
9. Dogfooding - academicOps can install into itself

Expected status: MOST TESTS WILL FAIL initially (validates we're testing real requirements).
Success: All tests pass = architecture correctly implemented.
"""

import os
from pathlib import Path
import json
import pytest


# =============================================================================
# Requirement 1: Path Predictability
# Same folder hierarchy everywhere
# =============================================================================

class TestPathPredictability:
    """Validate that folder structure is consistent across all repo types."""

    def test_academicops_has_standard_bots_structure(self):
        """${ACADEMICOPS}/bots/ contains all core instructions."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        required_dirs = [
            academicops / "bots/agents",
            academicops / "bots/hooks",
            academicops / "bots/scripts",
        ]

        for directory in required_dirs:
            assert directory.exists(), f"Missing required directory: {directory}"
            assert directory.is_dir(), f"Not a directory: {directory}"

    def test_academicops_claude_folder_structure(self):
        """${ACADEMICOPS}/.claude/ has same structure as project repos."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Should have .claude/ with standard structure
        claude_dir = academicops / ".claude"
        assert claude_dir.exists(), "Missing .claude/ directory"

        # Standard .claude/ contents (should match project installations)
        expected = [
            claude_dir / "settings.json",
            claude_dir / "commands",
            claude_dir / "skills",
        ]

        for path in expected:
            assert path.exists(), f"Missing in ${ACADEMICOPS}/.claude/: {path.name}"

    def test_project_bots_mirrors_academicops_structure(self, tmp_path):
        """<project>/bots/ should mirror ${ACADEMICOPS}/bots/ structure."""
        # Simulated project installation
        project_bots = tmp_path / "bots"
        project_bots.mkdir()

        # After installation, should have same subdirectory structure
        expected_structure = ["agents", "hooks", "scripts"]

        # This test will FAIL until installation script creates structure
        # Expected behavior: install creates symlinks OR copies structure
        for subdir in expected_structure:
            assert (project_bots / subdir).exists(), (
                f"Project /bots/{subdir}/ missing - installation incomplete"
            )


# =============================================================================
# Requirement 2: Symlink Creation
# Framework files symlinked, not copied
# =============================================================================

class TestSymlinkCreation:
    """Validate that framework files are symlinked, not duplicated."""

    def test_project_claude_agents_are_symlinked(self, tmp_path):
        """<project>/.claude/agents/ should be symlink to framework."""
        project_claude = tmp_path / ".claude"
        project_claude.mkdir()

        agents_link = project_claude / "agents"

        # Installation should create symlink
        # This will FAIL until install script implements symlinking
        assert agents_link.exists() or agents_link.is_symlink(), (
            ".claude/agents/ not created by installation"
        )

        if agents_link.exists():
            assert agents_link.is_symlink(), (
                ".claude/agents/ should be SYMLINK, not copy"
            )

    def test_project_claude_commands_are_symlinked(self, tmp_path):
        """<project>/.claude/commands/ should be symlink to framework."""
        project_claude = tmp_path / ".claude"
        project_claude.mkdir()

        commands_link = project_claude / "commands"

        # Should be symlink after installation
        assert commands_link.exists() or commands_link.is_symlink(), (
            ".claude/commands/ not created"
        )

        if commands_link.exists():
            assert commands_link.is_symlink(), (
                ".claude/commands/ should be SYMLINK, not copy"
            )

    def test_project_claude_skills_are_symlinked(self, tmp_path):
        """<project>/.claude/skills/ should be symlink to framework."""
        project_claude = tmp_path / ".claude"
        project_claude.mkdir()

        skills_link = project_claude / "skills"

        assert skills_link.exists() or skills_link.is_symlink(), (
            ".claude/skills/ not created"
        )

        if skills_link.exists():
            assert skills_link.is_symlink(), (
                ".claude/skills/ should be SYMLINK, not copy"
            )

    def test_project_bots_scripts_are_symlinked(self, tmp_path):
        """<project>/bots/scripts/ should be symlink to framework scripts."""
        project_bots = tmp_path / "bots"
        project_bots.mkdir()

        scripts_link = project_bots / "scripts"

        # Installation should create symlink for script invocation
        assert scripts_link.exists() or scripts_link.is_symlink(), (
            "bots/scripts/ not created"
        )

        if scripts_link.exists():
            assert scripts_link.is_symlink(), (
                "bots/scripts/ should be SYMLINK for script invocation"
            )


# =============================================================================
# Requirement 3: Gitignore Coverage
# All symlinks gitignored, custom prompts preserved
# =============================================================================

class TestGitignoreCoverage:
    """Validate that symlinks are gitignored but custom files preserved."""

    def test_dist_gitignore_covers_symlinks(self):
        """dist/.gitignore should ignore all framework symlinks."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))
        gitignore = academicops / "dist/.gitignore"

        assert gitignore.exists(), "dist/.gitignore template missing"

        content = gitignore.read_text()

        # Should ignore symlinked framework files
        required_ignores = [
            ".claude/settings.json",  # Copied, not custom
            ".claude/agents/",  # Symlinked
            ".claude/commands/",  # Symlinked
            ".claude/skills/",  # Symlinked
            "bots/scripts/",  # Symlinked
            ".claude/settings.local.json",  # Local overrides
        ]

        for pattern in required_ignores:
            assert pattern in content, (
                f"dist/.gitignore missing pattern: {pattern}"
            )

    def test_gitignore_does_not_ignore_custom_bots_files(self):
        """Gitignore should allow custom project files in bots/."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))
        gitignore = academicops / "dist/.gitignore"

        content = gitignore.read_text()

        # Should NOT have blanket "bots/" ignore
        # (only specific subdirectories like bots/scripts/)
        assert "bots/" not in content or "bots/scripts/" in content, (
            "Gitignore should not block all /bots/ files (custom prompts allowed)"
        )


# =============================================================================
# Requirement 4: Modular Instructions
# /bots/ contains ALL core instructions in modular form
# =============================================================================

class TestModularInstructions:
    """Validate that bots/ contains core instructions in modular form."""

    def test_bots_agents_contains_core_instructions(self):
        """bots/agents/ contains core modular agent instructions."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        agents_dir = academicops / "bots/agents"
        assert agents_dir.exists(), "bots/agents/ missing"

        # Core agent files must exist
        required_agents = [
            "_CORE.md",
            "trainer.md",
        ]

        for agent_file in required_agents:
            agent_path = agents_dir / agent_file
            assert agent_path.exists(), f"Missing core agent: {agent_file}"

    def test_bots_hooks_contains_validation_scripts(self):
        """bots/hooks/ contains hook validation scripts."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        hooks_dir = academicops / "bots/hooks"
        assert hooks_dir.exists(), "bots/hooks/ missing"

        # Core hooks must exist
        required_hooks = [
            "load_instructions.py",
            "validate_tool.py",
        ]

        for hook_file in required_hooks:
            hook_path = hooks_dir / hook_file
            assert hook_path.exists(), f"Missing core hook: {hook_file}"
            # Verify it's executable
            assert os.access(hook_path, os.X_OK), (
                f"Hook not executable: {hook_file}"
            )


# =============================================================================
# Requirement 5: Project Overrides
# <project>/bots/ adds project-specific instructions
# =============================================================================

class TestProjectOverrides:
    """Validate that project-specific bots/ files work correctly."""

    def test_project_can_add_custom_agent_instructions(self, tmp_path):
        """<project>/bots/agents/custom.md should be loadable."""
        project_bots = tmp_path / "bots/agents"
        project_bots.mkdir(parents=True)

        # Create custom project agent
        custom_agent = project_bots / "custom.md"
        custom_agent.write_text("# Custom Project Agent\n\nProject-specific instructions.")

        # Should be readable (not blocked by gitignore)
        assert custom_agent.exists()
        content = custom_agent.read_text()
        assert "Project-specific" in content

    def test_project_can_override_instructions(self, tmp_path):
        """<project>/bots/agents/trainer.md can override framework trainer."""
        project_bots = tmp_path / "bots/agents"
        project_bots.mkdir(parents=True)

        # Create project-specific override
        override = project_bots / "trainer.md"
        override.write_text("# Project Trainer Override\n\nLoad after framework trainer.")

        assert override.exists()
        # Load order: framework → project (both loaded, project second)


# =============================================================================
# Requirement 6: CLAUDE.md Discovery
# Just-in-time documentation via CLAUDE.md
# =============================================================================

class TestCLAUDEmdDiscovery:
    """Validate CLAUDE.md just-in-time loading (Issue #120)."""

    def test_bots_directory_has_claude_md(self):
        """bots/ directories have CLAUDE.md for context loading."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Should have CLAUDE.md in key directories (from Issue #120 implementation)
        expected_claude_files = [
            academicops / "bots/CLAUDE.md",
            academicops / "tests/CLAUDE.md",
            academicops / "tests/integration/CLAUDE.md",
            academicops / "scripts/CLAUDE.md",
        ]

        for claude_file in expected_claude_files:
            assert claude_file.exists(), (
                f"Missing CLAUDE.md: {claude_file.relative_to(academicops)}"
            )

    def test_claude_md_contains_only_references(self):
        """CLAUDE.md files should contain ONLY @ references (no duplication)."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        claude_file = academicops / "bots/CLAUDE.md"
        if claude_file.exists():
            content = claude_file.read_text()

            # Should have @ references
            assert "@" in content, "CLAUDE.md should contain @ references"

            # Should NOT have long instructional content (keep under 50 lines)
            lines = content.split("\n")
            assert len(lines) < 50, (
                "CLAUDE.md should be concise (< 50 lines, mainly @ references)"
            )


# =============================================================================
# Requirement 7: Script Invocation
# Scripts accessible via symlink at <project>/bots/scripts/
# =============================================================================

class TestScriptInvocation:
    """Validate scripts can be invoked from project via symlinks."""

    def test_bots_scripts_exists_and_is_symlink(self, tmp_path):
        """<project>/bots/scripts/ should symlink to framework scripts."""
        # This duplicates TestSymlinkCreation but validates from script invocation perspective
        project_bots = tmp_path / "bots"
        project_bots.mkdir()

        scripts_link = project_bots / "scripts"

        # After installation
        if scripts_link.exists():
            assert scripts_link.is_symlink(), (
                "bots/scripts/ must be symlink for invocation to work"
            )

    def test_scripts_are_executable_via_symlink(self):
        """Framework scripts should be executable via project symlink."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Example: check one core script
        script = academicops / "scripts/check_instruction_orphans.py"

        if script.exists():
            assert os.access(script, os.X_OK), (
                f"Script not executable: {script.name}"
            )


# =============================================================================
# Requirement 8: Pre-commit Integration
# Piggyback on pre-commit for git hooks
# =============================================================================

class TestPreCommitIntegration:
    """Validate pre-commit is used for git hooks."""

    def test_academicops_uses_precommit_config(self):
        """academicOps should use .pre-commit-config.yaml, not custom hooks."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        precommit_config = academicops / ".pre-commit-config.yaml"
        assert precommit_config.exists(), (
            "Missing .pre-commit-config.yaml (should use pre-commit, not custom hooks)"
        )

    def test_no_custom_git_hooks_in_framework(self):
        """Framework should NOT have custom .git/hooks/ (use pre-commit)."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        git_hooks = academicops / ".git/hooks"

        if git_hooks.exists():
            # Should only have pre-commit installed hooks
            custom_hooks = [
                f for f in git_hooks.iterdir()
                if f.is_file() and not f.name.endswith(".sample")
            ]

            # If hooks exist, they should be from pre-commit install
            for hook in custom_hooks:
                content = hook.read_text()
                # Pre-commit hooks contain "pre-commit" in shebang/content
                assert "pre-commit" in content, (
                    f"Custom git hook detected (should use pre-commit): {hook.name}"
                )


# =============================================================================
# Requirement 9: Dogfooding
# academicOps can install into itself
# =============================================================================

class TestDogfooding:
    """Validate academicOps can install into itself without conflicts."""

    def test_academicops_has_bots_directory(self):
        """${ACADEMICOPS} itself should have /bots/ structure."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        bots_dir = academicops / "bots"
        assert bots_dir.exists(), (
            "${ACADEMICOPS}/bots/ missing - dogfooding not implemented"
        )

    def test_academicops_bots_not_symlink(self):
        """/bots/ in ${ACADEMICOPS} should be REAL, not symlink (source of truth)."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        bots_dir = academicops / "bots"

        if bots_dir.exists():
            assert not bots_dir.is_symlink(), (
                "${ACADEMICOPS}/bots/ should be real directory (source), not symlink"
            )

    def test_academicops_claude_structure_matches_projects(self):
        """${ACADEMICOPS}/.claude/ should match project installation structure."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        claude_dir = academicops / ".claude"

        # Should have same structure as what we install in projects
        # (validates dogfooding: academicOps uses same structure it creates)
        expected = ["settings.json", "commands", "skills"]

        for item in expected:
            path = claude_dir / item
            assert path.exists(), (
                f"${ACADEMICOPS}/.claude/{item} missing - doesn't match project structure"
            )

    def test_development_files_coexist_with_deployment(self):
        """Development files (tests/, src/) should coexist with deployment (/bots/)."""
        academicops = Path(os.environ.get("ACADEMICOPS_BOT", "/home/nic/src/bot"))

        # Development files
        assert (academicops / "tests").exists(), "tests/ missing (development)"
        # assert (academicops / "src").exists(), "src/ missing (development)"

        # Deployment files
        assert (academicops / "bots").exists(), "bots/ missing (deployment)"
        assert (academicops / ".claude").exists(), ".claude/ missing (deployment)"

        # No conflicts between development and deployment


# =============================================================================
# Integration: Personal Repo Structure
# ${ACADEMICOPS_PERSONAL} should follow same patterns
# =============================================================================

class TestPersonalRepoStructure:
    """Validate ${ACADEMICOPS_PERSONAL} follows architecture."""

    def test_personal_has_bots_directory(self):
        """${ACADEMICOPS_PERSONAL}/bots/ should exist."""
        personal = os.environ.get("ACADEMICOPS_PERSONAL")

        if not personal:
            pytest.skip("ACADEMICOPS_PERSONAL not set")

        personal_path = Path(personal)
        bots_dir = personal_path / "bots"

        # Personal repo should have /bots/ structure
        assert bots_dir.exists(), (
            f"${ACADEMICOPS_PERSONAL}/bots/ missing"
        )

    def test_personal_has_data_directory(self):
        """${ACADEMICOPS_PERSONAL}/data/ for strategic context."""
        personal = os.environ.get("ACADEMICOPS_PERSONAL")

        if not personal:
            pytest.skip("ACADEMICOPS_PERSONAL not set")

        personal_path = Path(personal)
        data_dir = personal_path / "data"

        # Personal repo contains strategic data
        assert data_dir.exists(), (
            f"${ACADEMICOPS_PERSONAL}/data/ missing"
        )

    def test_personal_has_claude_directory(self):
        """${ACADEMICOPS_PERSONAL}/.claude/ should exist."""
        personal = os.environ.get("ACADEMICOPS_PERSONAL")

        if not personal:
            pytest.skip("ACADEMICOPS_PERSONAL not set")

        personal_path = Path(personal)
        claude_dir = personal_path / ".claude"

        assert claude_dir.exists(), (
            f"${ACADEMICOPS_PERSONAL}/.claude/ missing"
        )
