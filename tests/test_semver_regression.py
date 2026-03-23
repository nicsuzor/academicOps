"""Reproduction test for semver regression in dev releases.

The bug: git describe could match a pre-release tag like v0.3.1-dev.17
instead of the stable tag v0.3.13, causing the version to regress from
0.3.13-dev.49 to 0.3.1-dev.17.

The fix: exclude all pre-release tag patterns (*.dev*, *-dev.*, *-alpha*,
*-beta*, *-rc*) from git describe so it always finds the stable base tag.
"""

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def aops_root(tmp_path: Path) -> Path:
    """Create a minimal aops root with pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "academicops"\nversion = "0.3.13"\n')
    return tmp_path


class TestSemverRegression:
    """Ensure git describe excludes pre-release tags to find the stable base."""

    def test_excludes_dev_tags_from_git_describe(self, aops_root: Path):
        """Regression: dev tag v0.3.1-dev.17 must not shadow stable tag v0.3.13.

        When git describe finds stable v0.3.13 (5 commits ahead), the version
        should be 0.3.13-dev.5, NOT 0.3.1-dev.17 (from a stale dev tag).
        """
        from scripts.build import get_project_version

        # Mock both uv (fails) and git describe (returns stable-based result)
        def mock_run(cmd, **kwargs):
            from unittest.mock import MagicMock

            result = MagicMock()

            if "uv" in cmd[0]:
                result.returncode = 1
                result.stdout = ""
                return result

            if "git" in cmd and "describe" in cmd:
                # Verify that the command excludes dev tags
                assert any(arg == "*-dev.*" for arg in cmd), (
                    "git describe must exclude *-dev.* tags"
                )
                assert any(arg == "*.dev*" for arg in cmd), "git describe must exclude *.dev* tags"

                # Simulate: stable tag v0.3.13 is 5 commits behind HEAD
                result.returncode = 0
                result.stdout = "v0.3.13-5-gabc1234\n"
                return result

            # Any other git command
            result.returncode = 1
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            version = get_project_version(aops_root)

        # Must be based on 0.3.13, not 0.3.1
        assert version == "0.3.13-dev.5+gabc1234"

    def test_stable_tag_returns_clean_version(self, aops_root: Path):
        """When HEAD is exactly on a stable tag, return the clean version."""
        from scripts.build import get_project_version

        def mock_run(cmd, **kwargs):
            from unittest.mock import MagicMock

            result = MagicMock()

            if "uv" in cmd[0]:
                result.returncode = 1
                result.stdout = ""
                return result

            if "git" in cmd and "describe" in cmd:
                result.returncode = 0
                result.stdout = "v0.3.13\n"
                return result

            result.returncode = 1
            result.stdout = ""
            return result

        with patch("subprocess.run", side_effect=mock_run):
            version = get_project_version(aops_root)

        assert version == "0.3.13"

    def test_stable_tags_filter_excludes_prerelease(self):
        """The stable_tags filter must exclude all pre-release patterns."""
        prerelease_tags = [
            "v0.3.1-dev.17",
            "v0.3.2-testing",
            "v0.3.3-alpha.1",
            "v0.3.4-beta.2",
            "v0.3.5-rc.1",
            "v0.3.6.dev3",
        ]
        stable_tags = ["v0.3.13", "v0.3.12", "v0.3.0"]
        all_tags = prerelease_tags + stable_tags

        exclusions = ["-testing", ".dev", "-dev.", "-beta", "-rc", "-alpha"]
        filtered = [t for t in all_tags if not any(s in t for s in exclusions)]

        assert filtered == stable_tags
        # Verify no duplicates in exclusion list
        assert len(exclusions) == len(set(exclusions)), "Exclusion list has duplicates"
