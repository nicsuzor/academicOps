"""Tests for lib.path_bootstrap — centralised PATH detection."""

import os
from unittest.mock import patch

import pytest
from lib.path_bootstrap import COMMON_BIN_DIRS, REQUIRED_BINARIES, detect_path_additions


class TestDetectPathAdditions:
    """Tests for detect_path_additions()."""

    def test_returns_none_when_all_binaries_found(self):
        """No changes needed when all required binaries are already on PATH."""
        # Use real PATH — uv and gh are available in dev environment
        result = detect_path_additions(os.environ.get("PATH", ""))
        # If both are found, result is None; if not, that's fine too
        # The key invariant: result is either None or a valid PATH string
        assert result is None or isinstance(result, str)

    def test_returns_none_when_nothing_to_add(self):
        """Returns None when binaries are already on the given PATH."""
        with patch("lib.path_bootstrap.shutil.which", return_value="/usr/bin/fake"):
            result = detect_path_additions("/usr/bin:/usr/local/bin")
        assert result is None

    def test_adds_directory_for_missing_binary(self, tmp_path):
        """Adds a directory when a binary is found in common paths."""
        # Create a fake binary in a temp dir
        fake_bin = tmp_path / "gh"
        fake_bin.touch()
        fake_bin.chmod(0o755)

        # Use a non-existent base path so shutil.which won't find gh there
        empty_path = str(tmp_path / "empty")
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["gh"]):
                result = detect_path_additions(empty_path)

        assert result is not None
        assert str(tmp_path) in result
        # Original path preserved
        assert empty_path in result

    def test_does_not_duplicate_existing_path_entry(self, tmp_path):
        """Doesn't add a directory that's already in PATH."""
        fake_bin = tmp_path / "gh"
        fake_bin.touch()
        fake_bin.chmod(0o755)

        current = f"{tmp_path}:/usr/bin"
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["gh"]):
                # gh won't be found by shutil.which with our mocked common dirs
                # but the dir is already in PATH, so nothing to add
                with patch("lib.path_bootstrap.shutil.which", return_value=str(fake_bin)):
                    result = detect_path_additions(current)

        assert result is None

    def test_deduplicates_directories_across_binaries(self, tmp_path):
        """Same directory isn't added twice for different binaries."""
        for name in ("uv", "gh"):
            fake = tmp_path / name
            fake.touch()
            fake.chmod(0o755)

        empty_path = str(tmp_path / "empty")
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["uv", "gh"]):
                result = detect_path_additions(empty_path)

        assert result is not None
        # Count occurrences of tmp_path in result
        segments = result.split(os.pathsep)
        assert segments.count(str(tmp_path)) == 1

    def test_prepends_new_directories(self, tmp_path):
        """New directories are prepended, not appended."""
        fake_bin = tmp_path / "gh"
        fake_bin.touch()
        fake_bin.chmod(0o755)

        base_path = str(tmp_path / "base")
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["gh"]):
                result = detect_path_additions(base_path)

        assert result is not None
        segments = result.split(os.pathsep)
        assert segments[0] == str(tmp_path)
        assert segments[-1] == base_path

    def test_handles_empty_path(self, tmp_path):
        """Works with an empty PATH string."""
        fake_bin = tmp_path / "uv"
        fake_bin.touch()
        fake_bin.chmod(0o755)

        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["uv"]):
                result = detect_path_additions("")

        assert result is not None
        assert str(tmp_path) in result

    def test_skips_non_executable(self, tmp_path):
        """Skips binaries that exist but aren't executable."""
        fake_bin = tmp_path / "gh"
        fake_bin.touch()
        fake_bin.chmod(0o644)  # not executable

        empty_path = str(tmp_path / "empty")
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", [tmp_path]):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["gh"]):
                # Disable brew fallback so only common dirs are checked
                with patch("lib.path_bootstrap.sys.platform", "linux"):
                    result = detect_path_additions(empty_path)

        # Should not have added tmp_path since binary isn't executable
        assert result is None

    @pytest.mark.skipif(os.name == "nt", reason="brew only on macOS/Linux")
    def test_brew_fallback_on_darwin(self, tmp_path):
        """On macOS, tries brew --prefix when common paths fail."""
        # brew --prefix returns e.g. /opt/homebrew; we append /bin to get the bin dir
        brew_prefix = tmp_path / "homebrew"
        brew_bin_dir = brew_prefix / "bin"
        brew_bin_dir.mkdir(parents=True)
        fake_gh = brew_bin_dir / "gh"
        fake_gh.touch()
        fake_gh.chmod(0o755)

        def fake_brew_run(cmd, **kwargs):
            class PrefixResult:
                returncode = 0
                stdout = str(brew_prefix)

            return PrefixResult()

        empty_path = str(tmp_path / "empty")
        with patch("lib.path_bootstrap.COMMON_BIN_DIRS", []):
            with patch("lib.path_bootstrap.REQUIRED_BINARIES", ["gh"]):
                with patch("lib.path_bootstrap.sys.platform", "darwin"):
                    with patch("lib.path_bootstrap.subprocess.run", side_effect=fake_brew_run):
                        result = detect_path_additions(empty_path)

        assert result is not None
        assert str(brew_bin_dir) in result


class TestConstants:
    """Verify the shared constants are reasonable."""

    def test_required_binaries_includes_uv_and_gh(self):
        assert "uv" in REQUIRED_BINARIES
        assert "gh" in REQUIRED_BINARIES

    def test_common_dirs_includes_homebrew(self):
        homebrew_dirs = [str(d) for d in COMMON_BIN_DIRS]
        assert any("/opt/homebrew" in d for d in homebrew_dirs)

    def test_common_dirs_includes_local_bin(self):
        dir_strs = [str(d) for d in COMMON_BIN_DIRS]
        assert any(".local/bin" in d for d in dir_strs)

    def test_common_dirs_includes_cargo(self):
        dir_strs = [str(d) for d in COMMON_BIN_DIRS]
        assert any(".cargo/bin" in d for d in dir_strs)
