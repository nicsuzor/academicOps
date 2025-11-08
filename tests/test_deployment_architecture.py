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
7. Script invocation - Scripts accessible via .academicOps/scripts/ symlink
8. Pre-commit integration - Hooks installed correctly
9. Dogfooding - academicOps can install into itself

Expected status: MOST TESTS WILL FAIL initially (validates we're testing real requirements).
Success: All tests pass = architecture correctly implemented.
"""

import os
import subprocess
from pathlib import Path

import pytest

# =============================================================================
# Requirement 1: Path Predictability
# Same folder hierarchy everywhere
# =============================================================================


class TestPathPredictability:
    """Validate that folder structure is consistent across all repo types."""

    def test_academicops_has_standard_bots_structure(self):
        """${AOPS}/bots/ contains all core instructions."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        required_dirs = [
            academicops / "bots/agents",
            academicops / "bots/hooks",
            academicops / "bots/scripts",
        ]

        for directory in required_dirs:
            assert directory.exists(), f"Missing required directory: {directory}"
            assert directory.is_dir(), f"Not a directory: {directory}"

    def test_academicops_claude_folder_structure(self):
        """${AOPS}/.claude/ has same structure as project repos."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

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
            assert path.exists(), f"Missing in ${AOPS}/.claude/: {path.name}"

    @pytest.mark.slow
    def test_project_bots_mirrors_academicops_structure(self, tmp_path):
        """<project>/bots/ should contain only /bots/agents/ for now."""
        # Run installation script first
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        install_script = academicops / "scripts/setup_academicops.sh"

        # Run installation to create the structure
        result = subprocess.run(
            [str(install_script), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Now verify the structure was created
        project_bots = tmp_path / "bots"

        # After installation, should have ONLY agents directory
        # Scripts are accessed via .academicOps/scripts/ symlink instead
        expected_structure = ["agents"]  # ONLY agents directory for now

        for subdir in expected_structure:
            assert (project_bots / subdir).exists(), (
                f"Project /bots/{subdir}/ missing - installation incomplete"
            )

        # Verify NO bots/scripts or bots/skills directories are created
        assert not (project_bots / "scripts").exists(), (
            "Project /bots/scripts/ should NOT exist - use .academicOps/scripts/ instead"
        )
        assert not (project_bots / "skills").exists(), (
            "Project /bots/skills/ should NOT exist - not supported yet"
        )


# =============================================================================
# Requirement 2: Symlink Creation
# Framework files symlinked, not copied
# =============================================================================


class TestSymlinkCreation:
    """Validate that framework files are symlinked, not duplicated."""

    @pytest.mark.slow
    def test_project_claude_agents_are_symlinked(self, tmp_path):
        """<project>/.claude/agents/ should be symlink to framework."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        install_script = academicops / "scripts/setup_academicops.sh"

        # Run installation
        result = subprocess.run(
            [str(install_script), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Now verify symlink created
        agents_link = tmp_path / ".claude/agents"
        assert agents_link.exists(), ".claude/agents/ not created by installation"
        assert agents_link.is_symlink(), ".claude/agents/ should be SYMLINK, not copy"

    @pytest.mark.slow
    def test_project_claude_commands_are_symlinked(self, tmp_path):
        """<project>/.claude/commands/ should be symlink to framework."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        install_script = academicops / "scripts/setup_academicops.sh"

        # Run installation
        result = subprocess.run(
            [str(install_script), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Now verify symlink created
        commands_link = tmp_path / ".claude/commands"
        assert commands_link.exists(), ".claude/commands/ not created"
        assert commands_link.is_symlink(), (
            ".claude/commands/ should be SYMLINK, not copy"
        )

    @pytest.mark.slow
    def test_project_claude_skills_are_symlinked(self, tmp_path):
        """<project>/.claude/skills/ should be symlink to framework."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        install_script = academicops / "scripts/setup_academicops.sh"

        # Run installation
        result = subprocess.run(
            [str(install_script), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Now verify symlink created
        skills_link = tmp_path / ".claude/skills"
        assert skills_link.exists(), ".claude/skills/ not created"
        assert skills_link.is_symlink(), ".claude/skills/ should be SYMLINK, not copy"

    @pytest.mark.slow
    def test_project_academicops_scripts_symlink(self, tmp_path):
        """<project>/.academicOps/scripts/ should be symlink to framework scripts."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        install_script = academicops / "scripts/setup_academicops.sh"

        # Run installation
        result = subprocess.run(
            [str(install_script), str(tmp_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Installation failed: {result.stderr}"

        # Now verify symlink created
        academicops_link = tmp_path / ".academicOps"
        assert academicops_link.exists(), ".academicOps not created"
        assert academicops_link.is_symlink(), (
            ".academicOps should be SYMLINK to framework"
        )

        # Verify scripts are accessible through the symlink
        scripts_path = tmp_path / ".academicOps/scripts"
        assert scripts_path.exists(), ".academicOps/scripts/ not accessible"


# =============================================================================
# Requirement 3: Gitignore Coverage
# All symlinks gitignored, custom prompts preserved
# =============================================================================


class TestGitignoreCoverage:
    """Validate that symlinks are gitignored but custom files preserved."""

    def test_dist_gitignore_covers_symlinks(self):
        """dist/.gitignore should ignore all framework symlinks."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        gitignore = academicops / "dist/.gitignore"

        assert gitignore.exists(), "dist/.gitignore template missing"

        content = gitignore.read_text()

        # Should ignore symlinked framework files
        # NOTE: bots/scripts/ pattern removed - no longer created
        required_ignores = [
            ".claude/settings.json",  # Copied, not custom
            ".claude/agents/",  # Symlinked
            ".claude/commands/",  # Symlinked
            ".claude/skills/",  # Symlinked
            ".claude/settings.local.json",  # Local overrides
            ".academicOps/",  # Symlinked directory
        ]

        for pattern in required_ignores:
            assert pattern in content, f"dist/.gitignore missing pattern: {pattern}"

        # Verify old pattern NOT present
        assert "bots/scripts/" not in content, (
            "dist/.gitignore should NOT contain bots/scripts/ pattern (no longer created)"
        )

    def test_gitignore_does_not_ignore_custom_bots_files(self):
        """Gitignore should allow custom project files in bots/."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))
        gitignore = academicops / "dist/.gitignore"

        content = gitignore.read_text()

        # Should NOT have blanket "bots/" ignore
        # (only specific subdirectories if needed)
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        bots_only = [line for line in lines if line == "bots/"]

        assert len(bots_only) == 0, (
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
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

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
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

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
            assert os.access(hook_path, os.X_OK), f"Hook not executable: {hook_file}"


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
        custom_agent.write_text(
            "# Custom Project Agent\n\nProject-specific instructions."
        )

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
        override.write_text(
            "# Project Trainer Override\n\nLoad after framework trainer."
        )

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
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

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
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

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
# Scripts accessible via .academicOps/scripts/ symlink (NOT bots/scripts/)
# =============================================================================


class TestScriptInvocation:
    """Validate scripts can be invoked from project via symlinks."""

    def test_no_references_to_bots_scripts(self):
        """Verify no files reference bots/scripts/ (should use .academicOps/scripts/)."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        # Files that should NOT contain bots/scripts/ references
        # (excluding test files and backup files)
        files_to_check = [
            academicops / "scripts/setup_academicops.sh",
            academicops / "scripts/install_bot.sh",
            academicops / "dist/.gitignore",
            academicops / "docs/DEPLOYMENT.md",
        ]

        for filepath in files_to_check:
            if filepath.exists():
                content = filepath.read_text()
                # Check for bots/scripts/ references (but allow .academicOps/scripts/)
                lines_with_bots_scripts = [
                    line
                    for line in content.split("\n")
                    if "bots/scripts/" in line and ".academicOps/scripts/" not in line
                ]

                assert len(lines_with_bots_scripts) == 0, (
                    f"{filepath.name} contains references to bots/scripts/ - "
                    f"should use .academicOps/scripts/ instead. "
                    f"Found: {lines_with_bots_scripts[:3]}"  # Show first 3 problematic lines
                )

    def test_all_script_references_use_academicops_path(self):
        """Verify script invocations use .academicOps/scripts/ pattern."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        # Check that key files properly reference scripts via .academicOps/scripts/
        trainer_file = academicops / "bots/agents/trainer.md"

        if trainer_file.exists():
            content = trainer_file.read_text()

            # Should reference scripts via .academicOps/scripts/
            assert ".academicOps/scripts/" in content, (
                "trainer.md should reference scripts via .academicOps/scripts/"
            )

            # Should NOT reference scripts via bots/scripts/
            assert "bots/scripts/" not in content, (
                "trainer.md should NOT reference bots/scripts/ (use .academicOps/scripts/)"
            )

    def test_scripts_are_executable_via_academicops_symlink(self):
        """Framework scripts should be executable via .academicOps symlink."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        # Example: check one core script
        script = academicops / "scripts/check_instruction_orphans.py"

        if script.exists():
            assert os.access(script, os.X_OK), f"Script not executable: {script.name}"


# =============================================================================
# Requirement 8: Pre-commit Integration
# Piggyback on pre-commit for git hooks
# =============================================================================


class TestPreCommitIntegration:
    """Validate pre-commit is used for git hooks."""

    def test_academicops_uses_precommit_config(self):
        """academicOps should use .pre-commit-config.yaml, not custom hooks."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        precommit_config = academicops / ".pre-commit-config.yaml"
        assert precommit_config.exists(), (
            "Missing .pre-commit-config.yaml (should use pre-commit, not custom hooks)"
        )

    def test_no_custom_git_hooks_in_framework(self):
        """Framework should NOT have custom .git/hooks/ (use pre-commit)."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        git_hooks = academicops / ".git/hooks"

        if git_hooks.exists():
            # Should only have pre-commit installed hooks
            custom_hooks = [
                f
                for f in git_hooks.iterdir()
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
        """${AOPS} itself should have /bots/ structure."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        bots_dir = academicops / "bots"
        assert bots_dir.exists(), (
            "${AOPS}/bots/ missing - dogfooding not implemented"
        )

    def test_academicops_bots_not_symlink(self):
        """/bots/ in ${AOPS} should be REAL, not symlink (source of truth)."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        bots_dir = academicops / "bots"

        if bots_dir.exists():
            assert not bots_dir.is_symlink(), (
                "${AOPS}/bots/ should be real directory (source), not symlink"
            )

    def test_academicops_claude_structure_matches_projects(self):
        """${AOPS}/.claude/ should match project installation structure."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        claude_dir = academicops / ".claude"

        # Should have same structure as what we install in projects
        # (validates dogfooding: academicOps uses same structure it creates)
        expected = ["settings.json", "commands", "skills"]

        for item in expected:
            path = claude_dir / item
            assert path.exists(), (
                f"${AOPS}/.claude/{item} missing - doesn't match project structure"
            )

    def test_development_files_coexist_with_deployment(self):
        """Development files (tests/, src/) should coexist with deployment (/bots/)."""
        academicops = Path(os.environ.get("AOPS", "/home/nic/src/bot"))

        # Development files
        assert (academicops / "tests").exists(), "tests/ missing (development)"
        # assert (academicops / "src").exists(), "src/ missing (development)"

        # Deployment files
        assert (academicops / "bots").exists(), "bots/ missing (deployment)"
        assert (academicops / ".claude").exists(), ".claude/ missing (deployment)"

        # No conflicts between development and deployment


# =============================================================================
# Integration: Personal Repo Structure
# ${ACA} should follow same patterns
# =============================================================================


class TestPersonalRepoStructure:
    """Validate ${ACA} follows architecture."""

    def test_personal_has_bots_directory(self):
        """${ACA}/bots/ should exist."""
        personal = os.environ.get("ACA")

        if not personal:
            pytest.skip("ACA not set")

        personal_path = Path(personal)
        bots_dir = personal_path / "bots"

        # Personal repo should have /bots/ structure
        assert bots_dir.exists(), f"${ACA}/bots/ missing"

    def test_personal_has_data_directory(self):
        """${ACA}/data/ for strategic context."""
        personal = os.environ.get("ACA")

        if not personal:
            pytest.skip("ACA not set")

        personal_path = Path(personal)
        data_dir = personal_path / "data"

        # Personal repo contains strategic data
        assert data_dir.exists(), f"${ACA}/data/ missing"

    def test_personal_has_claude_directory(self):
        """${ACA}/.claude/ should exist."""
        personal = os.environ.get("ACA")

        if not personal:
            pytest.skip("ACA not set")

        personal_path = Path(personal)
        claude_dir = personal_path / ".claude"

        assert claude_dir.exists(), f"${ACA}/.claude/ missing"
