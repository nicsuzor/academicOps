"""Tests for package_deployment.py script.

Validates the packaging script that creates distributable archives for GitHub releases.

Requirements tested:
1. should_exclude() correctly filters development files
2. get_version() retrieves git tags or generates date-based versions
3. create_manifest() generates valid package metadata
4. create_install_guide() produces valid installation documentation
5. create_archive() creates valid tar.gz archives
6. Integration: Full packaging workflow creates usable archives
"""

import json
import tarfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import the script functions
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from package_deployment import (
    create_archive,
    create_install_guide,
    create_manifest,
    get_files_to_package,
    get_git_commit,
    get_version,
    should_exclude,
)


class TestShouldExclude:
    """Test file exclusion logic."""

    def test_excludes_git_directory(self, tmp_path):
        """Exclude .git/ directory."""
        repo_root = tmp_path
        git_path = repo_root / ".git" / "config"
        git_path.parent.mkdir(parents=True)
        git_path.touch()

        assert should_exclude(git_path, repo_root) is True

    def test_excludes_pycache(self, tmp_path):
        """Exclude __pycache__/ directories."""
        repo_root = tmp_path
        cache_path = repo_root / "lib" / "__pycache__" / "module.pyc"
        cache_path.parent.mkdir(parents=True)
        cache_path.touch()

        assert should_exclude(cache_path, repo_root) is True

    def test_excludes_tests_directory(self, tmp_path):
        """Exclude tests/ directory."""
        repo_root = tmp_path
        test_path = repo_root / "tests" / "test_example.py"
        test_path.parent.mkdir(parents=True)
        test_path.touch()

        assert should_exclude(test_path, repo_root) is True

    def test_excludes_experiments_directory(self, tmp_path):
        """Exclude experiments/ directory."""
        repo_root = tmp_path
        exp_path = repo_root / "experiments" / "2024-01-01_test.md"
        exp_path.parent.mkdir(parents=True)
        exp_path.touch()

        assert should_exclude(exp_path, repo_root) is True

    def test_excludes_claude_directory(self, tmp_path):
        """Exclude .claude/ directory (source development directory)."""
        repo_root = tmp_path
        claude_path = repo_root / ".claude" / "settings.json"
        claude_path.parent.mkdir(parents=True)
        claude_path.touch()

        assert should_exclude(claude_path, repo_root) is True

    def test_excludes_venv_directories(self, tmp_path):
        """Exclude .venv/ and venv/ directories."""
        repo_root = tmp_path
        venv1 = repo_root / ".venv" / "bin" / "python"
        venv2 = repo_root / "venv" / "lib" / "site-packages"

        for venv_path in [venv1, venv2]:
            venv_path.parent.mkdir(parents=True)
            venv_path.touch()
            assert should_exclude(venv_path, repo_root) is True

    def test_excludes_pyc_files(self, tmp_path):
        """Exclude .pyc files."""
        repo_root = tmp_path
        pyc_path = repo_root / "lib" / "module.pyc"
        pyc_path.parent.mkdir(parents=True)
        pyc_path.touch()

        assert should_exclude(pyc_path, repo_root) is True

    def test_excludes_env_files(self, tmp_path):
        """Exclude .env files."""
        repo_root = tmp_path
        env_path = repo_root / ".env"
        env_path.touch()

        assert should_exclude(env_path, repo_root) is True

    def test_excludes_gitignore_files(self, tmp_path):
        """Exclude .gitignore files."""
        repo_root = tmp_path
        gitignore = repo_root / ".gitignore"
        gitignore.touch()

        assert should_exclude(gitignore, repo_root) is True

    def test_excludes_docs_unused(self, tmp_path):
        """Exclude docs/_UNUSED/ directory."""
        repo_root = tmp_path
        unused_path = repo_root / "docs" / "_UNUSED" / "old.md"
        unused_path.parent.mkdir(parents=True)
        unused_path.touch()

        assert should_exclude(unused_path, repo_root) is True

    def test_excludes_docs_unsorted(self, tmp_path):
        """Exclude docs/unsorted/ directory."""
        repo_root = tmp_path
        unsorted_path = repo_root / "docs" / "unsorted" / "notes.md"
        unsorted_path.parent.mkdir(parents=True)
        unsorted_path.touch()

        assert should_exclude(unsorted_path, repo_root) is True

    def test_includes_normal_files(self, tmp_path):
        """Include normal project files."""
        repo_root = tmp_path
        normal_files = [
            repo_root / "README.md",
            repo_root / "skills" / "aops" / "SKILL.md",
            repo_root / "hooks" / "load_instructions.py",
            repo_root / "scripts" / "task_add.py",
            repo_root / "docs" / "AXIOMS.md",
        ]

        for file_path in normal_files:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            assert should_exclude(file_path, repo_root) is False


class TestGetVersion:
    """Test version detection."""

    @patch("subprocess.run")
    def test_gets_version_from_git_tag(self, mock_run):
        """Get version from git tag when available."""
        mock_run.return_value = Mock(returncode=0, stdout="v1.0.0\n")
        version = get_version()
        assert version == "v1.0.0"
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_fallback_to_date_version(self, mock_run):
        """Fall back to date-based version when no git tag."""
        mock_run.return_value = Mock(returncode=1, stdout="")
        version = get_version()
        # Should be format: vYYYY.MM.DD
        assert version.startswith("v")
        assert len(version.split(".")) == 3

    @patch("subprocess.run")
    def test_handles_subprocess_exception(self, mock_run):
        """Handle subprocess exceptions gracefully."""
        mock_run.side_effect = Exception("Git not found")
        version = get_version()
        # Should fall back to date-based version
        assert version.startswith("v")


class TestGetGitCommit:
    """Test git commit hash retrieval."""

    @patch("subprocess.run")
    def test_gets_commit_hash(self, mock_run):
        """Get short commit hash from git."""
        mock_run.return_value = Mock(returncode=0, stdout="abc1234\n")
        commit = get_git_commit()
        assert commit == "abc1234"

    @patch("subprocess.run")
    def test_returns_unknown_on_error(self, mock_run):
        """Return 'unknown' when git fails."""
        mock_run.side_effect = Exception("Git error")
        commit = get_git_commit()
        assert commit == "unknown"


class TestCreateManifest:
    """Test manifest creation."""

    def test_creates_valid_manifest(self, tmp_path):
        """Create manifest with correct structure and metadata."""
        files = [
            tmp_path / "README.md",
            tmp_path / "skills" / "aops" / "SKILL.md",
        ]
        for f in files:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.touch()

        manifest = create_manifest(files, tmp_path, "v1.0.0", "abc1234")

        assert manifest["name"] == "aops"
        assert manifest["version"] == "v1.0.0"
        assert manifest["commit"] == "abc1234"
        assert "created" in manifest
        assert "description" in manifest
        assert manifest["file_count"] == len(files)
        assert len(manifest["files"]) == len(files)
        assert "README.md" in manifest["files"]

    def test_manifest_has_iso_timestamp(self, tmp_path):
        """Manifest created timestamp is ISO format."""
        manifest = create_manifest([], tmp_path, "v1.0.0", "abc1234")
        # Should be parseable as ISO datetime
        datetime.fromisoformat(manifest["created"])


class TestCreateInstallGuide:
    """Test installation guide generation."""

    def test_creates_install_guide(self):
        """Create installation guide with version."""
        guide = create_install_guide("v1.0.0")

        assert "v1.0.0" in guide
        assert "# aOps Installation Guide" in guide
        assert "Quick Install" in guide
        assert "bash scripts/setup.sh" in guide
        assert "~/.claude/" in guide

    def test_includes_installation_steps(self):
        """Installation guide includes key steps."""
        guide = create_install_guide("v1.0.0")

        required_sections = [
            "Quick Install",
            "What Gets Installed",
            "Usage",
            "Updating",
            "Uninstallation",
            "Troubleshooting",
        ]
        for section in required_sections:
            assert section in guide

    def test_includes_axioms_reference(self):
        """Installation guide references AXIOMS.md."""
        guide = create_install_guide("v1.0.0")
        assert "docs/AXIOMS.md" in guide


class TestCreateArchive:
    """Test archive creation."""

    def test_creates_valid_tarball(self, tmp_path):
        """Create a valid gzipped tar archive."""
        # Setup test files
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        readme = repo_root / "README.md"
        readme.write_text("# Test")

        output_path = tmp_path / "test.tar.gz"

        # Create archive
        create_archive([readme], repo_root, output_path, "v1.0.0", "abc1234")

        # Verify archive exists and is valid
        assert output_path.exists()
        assert tarfile.is_tarfile(output_path)

    def test_archive_contains_files(self, tmp_path):
        """Archive contains all specified files."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        files = [
            repo_root / "README.md",
            repo_root / "CLAUDE.md",
        ]
        for f in files:
            f.write_text("content")

        output_path = tmp_path / "test.tar.gz"
        create_archive(files, repo_root, output_path, "v1.0.0", "abc1234")

        # Extract and verify
        with tarfile.open(output_path, "r:gz") as tar:
            members = tar.getnames()
            assert "aops-v1.0.0/README.md" in members
            assert "aops-v1.0.0/CLAUDE.md" in members

    def test_archive_contains_manifest(self, tmp_path):
        """Archive includes MANIFEST.json."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        readme = repo_root / "README.md"
        readme.write_text("# Test")

        output_path = tmp_path / "test.tar.gz"
        create_archive([readme], repo_root, output_path, "v1.0.0", "abc1234")

        with tarfile.open(output_path, "r:gz") as tar:
            members = tar.getnames()
            assert "aops-v1.0.0/MANIFEST.json" in members

            # Extract and validate manifest
            manifest_member = tar.getmember("aops-v1.0.0/MANIFEST.json")
            manifest_data = tar.extractfile(manifest_member).read()
            manifest = json.loads(manifest_data)
            assert manifest["version"] == "v1.0.0"
            assert manifest["commit"] == "abc1234"

    def test_archive_contains_install_guide(self, tmp_path):
        """Archive includes INSTALL.md."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        readme = repo_root / "README.md"
        readme.write_text("# Test")

        output_path = tmp_path / "test.tar.gz"
        create_archive([readme], repo_root, output_path, "v1.0.0", "abc1234")

        with tarfile.open(output_path, "r:gz") as tar:
            members = tar.getnames()
            assert "aops-v1.0.0/INSTALL.md" in members

    def test_handles_archive_creation_errors(self, tmp_path):
        """Raise exception with helpful message on archive errors."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        readme = repo_root / "README.md"
        readme.write_text("# Test")

        # Invalid output path (directory instead of file)
        output_path = tmp_path / "invalid_dir"
        output_path.mkdir()

        with pytest.raises((OSError, tarfile.TarError)):
            create_archive([readme], repo_root, output_path, "v1.0.0", "abc1234")


class TestIntegration:
    """Integration tests for full packaging workflow."""

    def test_packaging_creates_extractable_archive(self, tmp_path):
        """Full packaging workflow creates usable archive."""
        # Setup minimal repo structure
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create minimal structure
        (repo_root / "README.md").write_text("# aOps")
        (repo_root / "CLAUDE.md").write_text("Instructions")
        (repo_root / "skills").mkdir()
        (repo_root / "skills" / "aops").mkdir()
        (repo_root / "skills" / "aops" / "SKILL.md").write_text("Skill")
        (repo_root / "hooks").mkdir()
        (repo_root / "scripts").mkdir()

        # Get files and create archive
        files = get_files_to_package(repo_root)
        output_path = tmp_path / "aops-test.tar.gz"
        create_archive(files, repo_root, output_path, "v1.0.0", "abc1234")

        # Extract to verify
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()

        with tarfile.open(output_path, "r:gz") as tar:
            tar.extractall(extract_dir)

        # Verify structure
        extracted_root = extract_dir / "aops-v1.0.0"
        assert (extracted_root / "README.md").exists()
        assert (extracted_root / "CLAUDE.md").exists()
        assert (extracted_root / "MANIFEST.json").exists()
        assert (extracted_root / "INSTALL.md").exists()
        assert (extracted_root / "skills" / "aops" / "SKILL.md").exists()

    def test_excludes_development_files(self, tmp_path):
        """Packaged archive excludes development files."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Create both includable and excludable files
        (repo_root / "README.md").write_text("# aOps")
        (repo_root / "tests").mkdir()
        (repo_root / "tests" / "test_example.py").write_text("test")
        (repo_root / ".git").mkdir()
        (repo_root / ".git" / "config").write_text("git config")

        files = get_files_to_package(repo_root)

        # Should include README
        file_names = [f.name for f in files]
        assert "README.md" in file_names

        # Should exclude tests and .git
        file_paths = [str(f.relative_to(repo_root)) for f in files]
        assert not any("test" in p for p in file_paths)
        assert not any(".git" in p for p in file_paths)
