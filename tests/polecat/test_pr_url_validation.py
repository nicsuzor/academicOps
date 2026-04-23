#!/usr/bin/env python3
"""Tests for PR URL validation — A3/A8 integrity gate.

Motivation: task-0e4d20a8. On 2026-04-18 a crew worker released a task with
a fabricated pr_url (``https://github.com/academic-ops/academicOps/commit/...``)
pointing at an org that does not exist. The release still succeeded because
neither format nor liveness were checked. This gate is the reason that can
no longer happen silently.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from validation import (  # noqa: E402
    PRURLValidationError,
    validate_pr_url_format,
    verify_pr_url_live,
)

# ---------------------------------------------------------------------------
# Format validation
# ---------------------------------------------------------------------------


class TestValidFormat:
    def test_pull_url(self):
        m = validate_pr_url_format("https://github.com/nicsuzor/academicOps/pull/649")
        assert m.group("org") == "nicsuzor"
        assert m.group("repo") == "academicOps"
        assert m.group("pr") == "649"

    def test_issue_url(self):
        m = validate_pr_url_format("https://github.com/nicsuzor/academicOps/issues/42")
        assert m.group("issue") == "42"

    def test_commit_url(self):
        m = validate_pr_url_format("https://github.com/nicsuzor/academicOps/commit/9841e951abcdef0")
        assert m.group("sha") == "9841e951abcdef0"

    def test_trailing_slash_accepted(self):
        m = validate_pr_url_format("https://github.com/a/b/pull/1/")
        assert m.group("pr") == "1"

    def test_dot_in_repo_name(self):
        m = validate_pr_url_format("https://github.com/foo/my.repo/pull/1")
        assert m.group("repo") == "my.repo"

    def test_repo_starting_with_dot(self):
        m = validate_pr_url_format("https://github.com/foo/.github/pull/1")
        assert m.group("repo") == ".github"

    def test_repo_starting_with_underscore(self):
        m = validate_pr_url_format("https://github.com/foo/_templates/pull/1")
        assert m.group("repo") == "_templates"

    def test_commit_sha_uppercase(self):
        m = validate_pr_url_format("https://github.com/a/b/commit/9841E951ABCDEF0")
        assert m.group("sha") == "9841E951ABCDEF0"


class TestInvalidFormat:
    @pytest.mark.parametrize(
        "url",
        [
            "",
            "not a url",
            "http://github.com/a/b/pull/1",  # plain http
            "https://github.com/a/b/wiki/Home",  # wrong path component
            "https://gitlab.com/a/b/pull/1",  # wrong host
            "https://github.com/academic-ops/academicOps/commit/",  # no sha
            "https://github.com/a/b/pull/abc",  # non-numeric PR number
            "https://github.com/a/b/commit/xyz",  # non-hex sha
            None,  # not a string
            123,  # not a string
        ],
    )
    def test_rejected(self, url):
        with pytest.raises(PRURLValidationError):
            validate_pr_url_format(url)  # type: ignore[arg-type]

    def test_incident_url_has_valid_shape(self):
        """The fabricated URL from the cheryl 2026-04-18 incident passes format
        validation — that is expected. Format alone cannot catch fabrication;
        only the live check can. This test exists to pin that behaviour so
        future reviewers don't remove the live check thinking format is enough.
        """
        # Format check passes...
        validate_pr_url_format("https://github.com/academic-ops/academicOps/commit/9841e951")


# ---------------------------------------------------------------------------
# Live verification
# ---------------------------------------------------------------------------


class TestLiveVerify:
    def test_skip_via_env(self, monkeypatch):
        monkeypatch.setenv("POLECAT_SKIP_PR_URL_CHECK", "1")
        # Would fail live check, but env skip short-circuits.
        verify_pr_url_live("https://github.com/does-not-exist-abc/xyz/pull/1")

    def test_expected_org_mismatch(self, monkeypatch):
        monkeypatch.setenv("POLECAT_SKIP_PR_URL_CHECK", "1")
        with pytest.raises(PRURLValidationError, match="org is"):
            verify_pr_url_live(
                "https://github.com/academic-ops/academicOps/pull/1",
                expected_org="nicsuzor",
            )

    def test_expected_org_match_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("POLECAT_SKIP_PR_URL_CHECK", "1")
        verify_pr_url_live(
            "https://github.com/NicSuzor/academicOps/pull/1",
            expected_org="nicsuzor",
        )

    def test_gh_not_installed_warns_but_passes(self, monkeypatch, capsys):
        """If gh is unavailable we can't verify — fail open with a visible
        warning. Don't silently accept without flagging the gap.
        """
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with patch("validation.shutil.which", return_value=None):
            verify_pr_url_live("https://github.com/a/b/pull/1")
        err = capsys.readouterr().err
        assert "gh not installed" in err

    def test_gh_resolves_pr(self, monkeypatch):
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with (
            patch("validation.shutil.which", return_value="/usr/bin/gh"),
            patch("validation.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"state":"OPEN"}'
            mock_run.return_value.stderr = ""
            verify_pr_url_live("https://github.com/nicsuzor/academicOps/pull/649")
            # Asserts we called gh pr view with the URL
            args = mock_run.call_args[0][0]
            assert args[:3] == ["gh", "pr", "view"]
            assert "https://github.com/nicsuzor/academicOps/pull/649" in args

    def test_gh_fails_raises(self, monkeypatch):
        """The incident case: fabricated org. gh returns non-zero → raise."""
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with (
            patch("validation.shutil.which", return_value="/usr/bin/gh"),
            patch("validation.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = (
                "GraphQL: Could not resolve to a Repository with "
                "the name 'academic-ops/academicOps'."
            )
            with pytest.raises(PRURLValidationError, match="gh could not resolve"):
                verify_pr_url_live("https://github.com/academic-ops/academicOps/pull/1")

    def test_commit_url_uses_gh_api(self, monkeypatch):
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with (
            patch("validation.shutil.which", return_value="/usr/bin/gh"),
            patch("validation.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "{}"
            mock_run.return_value.stderr = ""
            verify_pr_url_live("https://github.com/nicsuzor/academicOps/commit/9841e951abcdef0")
            args = mock_run.call_args[0][0]
            assert args[:2] == ["gh", "api"]
            assert "/repos/nicsuzor/academicOps/commits/9841e951abcdef0" in args

    def test_timeout_raises(self, monkeypatch):
        import subprocess as _sub

        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with (
            patch("validation.shutil.which", return_value="/usr/bin/gh"),
            patch(
                "validation.subprocess.run",
                side_effect=_sub.TimeoutExpired(cmd="gh", timeout=15),
            ),
        ):
            with pytest.raises(PRURLValidationError, match="timed out"):
                verify_pr_url_live("https://github.com/a/b/pull/1")
