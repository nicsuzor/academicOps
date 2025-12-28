"""
Unit tests for sync_web_bundle.py

Tests cover:
- get_skills_for_bundle: Skill metadata extraction
- sync_to_self: Symlink creation for academicOps
- sync_to_project: File copying for external projects
- install_git_hook: Hook installation with backup logic
- dry_run mode: No filesystem modifications
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from sync_web_bundle import (
    get_skills_for_bundle,
    sync_to_self,
    sync_to_project,
    install_git_hook,
    generate_claude_md,
    get_aops_version,
    write_version_file,
    _extract_aops_logic,
    AOPS_ROOT,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_aops_root(tmp_path, monkeypatch):
    """Create a mock AOPS_ROOT structure for testing."""
    aops = tmp_path / "academicOps"
    aops.mkdir()

    # Create skills directory with sample skills
    skills_dir = aops / "skills"
    skills_dir.mkdir()

    # Skill 1: Valid skill with all fields
    skill1 = skills_dir / "analyst"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: analyst
description: Support academic research data analysis using dbt and Streamlit.
version: 2.0.0
---

# Analyst

Content here.
""")

    # Skill 2: Skill with long description (should be truncated)
    skill2 = skills_dir / "pdf"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: pdf
description: Convert markdown documents to professionally formatted PDFs with academic-style typography and proper page layouts.
---

# PDF Converter
""")

    # Skill 3: Skill using 'title' instead of 'name'
    skill3 = skills_dir / "garden"
    skill3.mkdir()
    (skill3 / "SKILL.md").write_text("""---
title: garden
description: Incremental PKM maintenance.
---

# Garden
""")

    # Skill 4: Malformed YAML (should be skipped gracefully)
    skill4 = skills_dir / "broken"
    skill4.mkdir()
    (skill4 / "SKILL.md").write_text("""---
name: [invalid yaml
description: This should fail parsing
---
""")

    # Skill 5: No SKILL.md file (should be skipped)
    skill5 = skills_dir / "empty"
    skill5.mkdir()

    # Skill 6: File, not directory (should be skipped)
    (skills_dir / "not-a-skill.md").write_text("Just a file")

    # Create commands directory
    commands_dir = aops / "commands"
    commands_dir.mkdir()
    (commands_dir / "test.md").write_text("# Test Command")

    # Create agents directory
    agents_dir = aops / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("# Test Agent")

    # Create config directory
    config_dir = aops / "config" / "claude"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.json").write_text('{"full": true}')
    (config_dir / "settings-web.json").write_text('{"web": true}')

    # Create hooks directory
    hooks_dir = aops / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "git-post-commit-sync-aops").write_text("""#!/usr/bin/env bash
# Git post-commit hook to auto-sync aOps bundle
# Header comment

if [ -z "$AOPS" ]; then
    exit 0
fi

echo "Running sync"
""")

    # Create CLAUDE.md
    (aops / "CLAUDE.md").write_text("# Framework CLAUDE.md")

    # Mock git to return a fake commit hash
    git_dir = aops / ".git"
    git_dir.mkdir()

    # Monkeypatch AOPS_ROOT
    monkeypatch.setattr("sync_web_bundle.AOPS_ROOT", aops)

    return aops


@pytest.fixture
def target_project(tmp_path):
    """Create a target project directory for sync_to_project tests."""
    project = tmp_path / "my-project"
    project.mkdir()

    # Make it a git repo
    git_dir = project / ".git"
    git_dir.mkdir()
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir()

    return project


# =============================================================================
# TestGetSkillsForBundle
# =============================================================================


class TestGetSkillsForBundle:
    """Test skill metadata extraction from SKILL.md files."""

    def test_scans_skills_directory(self, mock_aops_root):
        """Test that it scans skills directory and returns skill metadata."""
        skills = get_skills_for_bundle()

        # Should find valid skills (not broken ones)
        skill_names = [s["name"] for s in skills]
        assert "analyst" in skill_names
        assert "pdf" in skill_names
        assert "garden" in skill_names

        # Broken skill should be skipped
        assert "broken" not in skill_names
        assert "empty" not in skill_names

    def test_handles_malformed_yaml(self, mock_aops_root):
        """Test that malformed YAML is skipped gracefully without crashing."""
        # Should not raise exception
        skills = get_skills_for_bundle()

        # Should have found the valid skills
        assert len(skills) >= 3

    def test_description_truncation(self, mock_aops_root):
        """Test that long descriptions are truncated to 60 chars + ellipsis."""
        skills = get_skills_for_bundle()

        pdf_skill = next((s for s in skills if s["name"] == "pdf"), None)
        assert pdf_skill is not None
        assert len(pdf_skill["description"]) <= 63  # 60 chars + "..."
        assert pdf_skill["description"].endswith("...")

    def test_uses_title_field_as_fallback(self, mock_aops_root):
        """Test that 'title' field is used if 'name' is not present."""
        skills = get_skills_for_bundle()

        garden_skill = next((s for s in skills if s["name"] == "garden"), None)
        assert garden_skill is not None
        assert garden_skill["description"] == "Incremental PKM maintenance."

    def test_skips_non_directories(self, mock_aops_root):
        """Test that files in skills/ are skipped (only directories processed)."""
        skills = get_skills_for_bundle()

        # Should not have picked up not-a-skill.md as a skill
        skill_names = [s["name"] for s in skills]
        assert "not-a-skill" not in skill_names

    def test_returns_empty_if_no_skills_dir(self, tmp_path, monkeypatch):
        """Test graceful handling when skills directory doesn't exist."""
        monkeypatch.setattr("sync_web_bundle.AOPS_ROOT", tmp_path / "nonexistent")
        skills = get_skills_for_bundle()
        assert skills == []


# =============================================================================
# TestSyncToSelf
# =============================================================================


class TestSyncToSelf:
    """Test sync_to_self creates symlinks in .claude/ directory."""

    def test_creates_symlinks(self, mock_aops_root):
        """Test that sync_to_self creates relative symlinks."""
        result = sync_to_self(dry_run=False)

        assert result == 0

        claude_dir = mock_aops_root / ".claude"
        assert claude_dir.exists()

        # Check symlinks exist
        assert (claude_dir / "skills").is_symlink()
        assert (claude_dir / "commands").is_symlink()
        assert (claude_dir / "agents").is_symlink()
        assert (claude_dir / "CLAUDE.md").is_symlink()
        assert (claude_dir / "settings.json").is_symlink()

        # Check symlink targets are relative
        assert str((claude_dir / "skills").readlink()) == "../skills"
        assert str((claude_dir / "commands").readlink()) == "../commands"

    def test_updates_existing_symlinks(self, mock_aops_root):
        """Test that existing symlinks are updated if target differs."""
        claude_dir = mock_aops_root / ".claude"
        claude_dir.mkdir()

        # Create a symlink with wrong target
        wrong_link = claude_dir / "skills"
        wrong_link.symlink_to("../wrong_path")

        result = sync_to_self(dry_run=False)

        assert result == 0
        assert str((claude_dir / "skills").readlink()) == "../skills"

    def test_replaces_regular_files(self, mock_aops_root):
        """Test that regular files are replaced with symlinks."""
        claude_dir = mock_aops_root / ".claude"
        claude_dir.mkdir()

        # Create a regular file where symlink should be
        regular_file = claude_dir / "skills"
        regular_file.write_text("Not a symlink")

        result = sync_to_self(dry_run=False)

        assert result == 0
        assert (claude_dir / "skills").is_symlink()

    def test_replaces_directories(self, mock_aops_root):
        """Test that directories are replaced with symlinks."""
        claude_dir = mock_aops_root / ".claude"
        claude_dir.mkdir()

        # Create a directory where symlink should be
        dir_to_replace = claude_dir / "skills"
        dir_to_replace.mkdir()
        (dir_to_replace / "file.txt").write_text("content")

        result = sync_to_self(dry_run=False)

        assert result == 0
        assert (claude_dir / "skills").is_symlink()

    def test_dry_run_no_changes(self, mock_aops_root, capsys):
        """Test that dry_run mode doesn't create any files."""
        result = sync_to_self(dry_run=True)

        assert result == 0

        # .claude directory should not exist
        claude_dir = mock_aops_root / ".claude"
        assert not claude_dir.exists()

        # Check output mentions dry run
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# TestSyncToProject
# =============================================================================


class TestSyncToProject:
    """Test sync_to_project copies files to external projects."""

    def test_copies_files_not_symlinks(self, mock_aops_root, target_project):
        """Test that sync_to_project copies files (not symlinks)."""
        result = sync_to_project(target_project, force=False, install_hook=False)

        assert result == 0

        claude_dir = target_project / ".claude"
        assert claude_dir.exists()

        # Should be directories, not symlinks
        assert (claude_dir / "skills").is_dir()
        assert not (claude_dir / "skills").is_symlink()

        # Check files were actually copied
        assert (claude_dir / "skills" / "analyst" / "SKILL.md").exists()

    def test_creates_aops_bundle_marker(self, mock_aops_root, target_project):
        """Test that .aops-bundle marker file is created."""
        sync_to_project(target_project, force=False, install_hook=False)

        marker = target_project / ".claude" / ".aops-bundle"
        assert marker.exists()
        assert "sync_web_bundle.py" in marker.read_text()

    def test_refuses_overwrite_without_force(self, mock_aops_root, target_project):
        """Test that it refuses to overwrite non-aops .claude/ without --force."""
        # Create existing .claude without marker
        claude_dir = target_project / ".claude"
        claude_dir.mkdir()
        (claude_dir / "custom-file.txt").write_text("User's custom content")

        result = sync_to_project(target_project, force=False, install_hook=False)

        assert result == 1  # Error
        # Custom file should still exist
        assert (claude_dir / "custom-file.txt").exists()

    def test_overwrites_with_force(self, mock_aops_root, target_project):
        """Test that --force allows overwriting non-aops .claude/."""
        # Create existing .claude without marker
        claude_dir = target_project / ".claude"
        claude_dir.mkdir()
        (claude_dir / "custom-file.txt").write_text("User's custom content")

        result = sync_to_project(target_project, force=True, install_hook=False)

        assert result == 0
        # Custom file should be gone
        assert not (claude_dir / "custom-file.txt").exists()
        # New content should exist
        assert (claude_dir / "skills").exists()

    def test_overwrites_existing_aops_bundle(self, mock_aops_root, target_project):
        """Test that existing aops bundles can be overwritten without --force."""
        # Create existing .claude with marker
        claude_dir = target_project / ".claude"
        claude_dir.mkdir()
        (claude_dir / ".aops-bundle").write_text("Previous sync")
        (claude_dir / "old-file.txt").write_text("Old content")

        result = sync_to_project(target_project, force=False, install_hook=False)

        assert result == 0
        # Old content should be gone
        assert not (claude_dir / "old-file.txt").exists()

    def test_generates_claude_md(self, mock_aops_root, target_project):
        """Test that CLAUDE.md is generated with skills table."""
        sync_to_project(target_project, force=False, install_hook=False)

        claude_md = target_project / ".claude" / "CLAUDE.md"
        assert claude_md.exists()

        content = claude_md.read_text()
        assert "aOps Framework Bundle" in content
        assert "analyst" in content  # Skills table should include analyst

    def test_includes_project_specific_content(self, mock_aops_root, target_project):
        """Test that existing CLAUDE.md content is included."""
        # Create project-specific CLAUDE.md
        (target_project / "CLAUDE.md").write_text("# My Project\n\nCustom instructions.")

        sync_to_project(target_project, force=False, install_hook=False)

        content = (target_project / ".claude" / "CLAUDE.md").read_text()
        assert "Project-Specific Instructions" in content
        assert "Custom instructions" in content

    def test_writes_version_file(self, mock_aops_root, target_project):
        """Test that .aops-version file is created."""
        with patch("sync_web_bundle.get_aops_version", return_value="abc123def456"):
            sync_to_project(target_project, force=False, install_hook=False)

        version_file = target_project / ".claude" / ".aops-version"
        assert version_file.exists()
        assert "abc123def456" in version_file.read_text()

    def test_copies_web_settings(self, mock_aops_root, target_project):
        """Test that web-compatible settings.json is copied."""
        sync_to_project(target_project, force=False, install_hook=False)

        settings = target_project / ".claude" / "settings.json"
        assert settings.exists()
        assert "web" in settings.read_text()  # Should be settings-web.json content

    def test_error_on_nonexistent_path(self, mock_aops_root, tmp_path):
        """Test error handling for non-existent project path."""
        result = sync_to_project(
            tmp_path / "does-not-exist", force=False, install_hook=False
        )
        assert result == 1

    def test_error_on_file_path(self, mock_aops_root, tmp_path):
        """Test error handling when path is a file, not directory."""
        file_path = tmp_path / "a-file.txt"
        file_path.write_text("content")

        result = sync_to_project(file_path, force=False, install_hook=False)
        assert result == 1

    def test_dry_run_no_changes(self, mock_aops_root, target_project, capsys):
        """Test that dry_run mode doesn't create any files."""
        result = sync_to_project(
            target_project, force=False, install_hook=False, dry_run=True
        )

        assert result == 0

        # .claude directory should not exist
        claude_dir = target_project / ".claude"
        assert not claude_dir.exists()

        # Check output mentions dry run
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# TestHookInstallation
# =============================================================================


class TestHookInstallation:
    """Test git hook installation and backup logic."""

    def test_installs_fresh_hook(self, mock_aops_root, target_project):
        """Test that hook is installed when none exists."""
        hooks_dir = target_project / ".git" / "hooks"
        hook_path = hooks_dir / "post-commit"

        # Ensure no hook exists
        assert not hook_path.exists()

        result = install_git_hook(target_project)

        assert result is True
        assert hook_path.exists()
        assert os.access(hook_path, os.X_OK)  # Executable
        assert "aOps sync hook" in hook_path.read_text()

    def test_backs_up_existing_non_aops_hook(self, mock_aops_root, target_project):
        """Test that existing hooks are backed up."""
        hooks_dir = target_project / ".git" / "hooks"
        hook_path = hooks_dir / "post-commit"

        # Create existing non-aops hook
        hook_path.write_text("#!/bin/bash\necho 'Custom hook'")

        result = install_git_hook(target_project)

        assert result is True

        # Backup should exist
        backups = list(hooks_dir.glob("post-commit.backup.*"))
        assert len(backups) == 1
        assert "Custom hook" in backups[0].read_text()

        # Original hook should now have aops content appended
        content = hook_path.read_text()
        assert "Custom hook" in content
        assert "aOps sync hook" in content

    def test_skips_if_aops_already_installed(self, mock_aops_root, target_project):
        """Test that aOps hooks are detected and skipped."""
        hooks_dir = target_project / ".git" / "hooks"
        hook_path = hooks_dir / "post-commit"

        # Create hook with aOps marker
        hook_path.write_text("#!/bin/bash\n# aOps sync hook\necho 'Already installed'")

        result = install_git_hook(target_project)

        assert result is True

        # No backup should be created
        backups = list(hooks_dir.glob("post-commit.backup.*"))
        assert len(backups) == 0

        # Content should be unchanged
        assert "Already installed" in hook_path.read_text()

    def test_skips_if_bundle_marker_present(self, mock_aops_root, target_project):
        """Test that 'aOps bundle' marker is also detected."""
        hooks_dir = target_project / ".git" / "hooks"
        hook_path = hooks_dir / "post-commit"

        # Create hook with different marker
        hook_path.write_text("#!/bin/bash\n# aOps bundle sync\necho 'Marker variant'")

        result = install_git_hook(target_project)

        assert result is True

        # No backup should be created
        backups = list(hooks_dir.glob("post-commit.backup.*"))
        assert len(backups) == 0

    def test_skips_non_git_repo(self, mock_aops_root, tmp_path):
        """Test that hook installation is skipped for non-git repos."""
        project = tmp_path / "not-a-repo"
        project.mkdir()

        result = install_git_hook(project)

        assert result is False

    def test_handles_missing_hook_source(self, mock_aops_root, target_project):
        """Test graceful handling when hook source file doesn't exist."""
        # Remove the hook source
        hook_src = mock_aops_root / "hooks" / "git-post-commit-sync-aops"
        hook_src.unlink()

        result = install_git_hook(target_project)

        assert result is False


# =============================================================================
# TestDryRunMode
# =============================================================================


class TestDryRunMode:
    """Test that --dry-run doesn't modify any files."""

    def test_sync_to_self_dry_run(self, mock_aops_root, capsys):
        """Test sync_to_self with dry_run=True."""
        result = sync_to_self(dry_run=True)

        assert result == 0

        # No .claude directory should be created
        assert not (mock_aops_root / ".claude").exists()

        # Output should indicate dry run
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_sync_to_project_dry_run(self, mock_aops_root, target_project, capsys):
        """Test sync_to_project with dry_run=True."""
        result = sync_to_project(
            target_project, force=False, install_hook=True, dry_run=True
        )

        assert result == 0

        # No .claude directory should be created
        assert not (target_project / ".claude").exists()

        # No hooks should be installed
        hook_path = target_project / ".git" / "hooks" / "post-commit"
        assert not hook_path.exists()

        # Output should indicate dry run
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_write_version_file_dry_run(self, tmp_path, capsys):
        """Test write_version_file with dry_run=True."""
        target = tmp_path / ".claude"
        target.mkdir()

        with patch("sync_web_bundle.get_aops_version", return_value="abc123"):
            write_version_file(target, dry_run=True)

        # Version file should not be created
        assert not (target / ".aops-version").exists()

        # Output should indicate dry run
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out


# =============================================================================
# TestHelperFunctions
# =============================================================================


class TestHelperFunctions:
    """Test helper functions."""

    def test_extract_aops_logic(self):
        """Test that _extract_aops_logic strips shebang and header comments."""
        hook_content = """#!/usr/bin/env bash
# Git post-commit hook
# Another comment

if [ -z "$AOPS" ]; then
    exit 0
fi

echo "Running sync"
"""
        result = _extract_aops_logic(hook_content)

        # Should not have shebang
        assert not result.startswith("#!")
        # Should not have header comments
        assert "Git post-commit hook" not in result
        # Should have the logic
        assert 'if [ -z "$AOPS" ]' in result
        assert "echo" in result

    def test_get_aops_version_handles_error(self, monkeypatch):
        """Test that get_aops_version returns 'unknown' on git error."""
        # Mock subprocess.run to raise exception
        def mock_run(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "git")

        monkeypatch.setattr("subprocess.run", mock_run)

        version = get_aops_version()
        assert version == "unknown"

    def test_generate_claude_md_limits_skills(self, mock_aops_root, target_project):
        """Test that generate_claude_md limits skills to 10."""
        # Add more skills to exceed 10
        skills_dir = mock_aops_root / "skills"
        for i in range(15):
            skill_dir = skills_dir / f"skill{i}"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"""---
name: skill{i}
description: Description {i}
---
""")

        content = generate_claude_md(target_project)

        # Should mention there are more skills
        assert "more skills available" in content
