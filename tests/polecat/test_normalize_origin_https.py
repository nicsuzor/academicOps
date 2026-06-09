#!/usr/bin/env python3
"""Tests for polecat's SSH→HTTPS GitHub remote normalization.

`_sync_working_repo` rewrites an SSH GitHub origin to HTTPS before any network
op so automation authenticates with the bot token over HTTPS rather than the SSH
agent (unreachable under cron; a 1Password prompt interactively). These tests
pin both halves of that behaviour:

  * `_ssh_github_to_https` — the pure string transform — across every SSH form
    git accepts, every no-op case (already-HTTPS, non-GitHub, git://), and the
    lookalike-host attack (`github.com.evil.com`).
  * `_normalize_origin_to_https` — the in-place git-config rewrite — against a
    real on-disk repo, confirming it actually mutates the stored remote, is
    idempotent, leaves non-SSH/non-GitHub remotes untouched, and no-ops cleanly
    when there is no origin at all.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from cli import (  # noqa: E402
    _normalize_origin_to_https,
    _ssh_github_to_https,
)

_HTTPS = "https://github.com/nicsuzor/academicOps.git"


# --------------------------------------------------------------------------- #
# Pure transform: _ssh_github_to_https                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url",
    [
        # SCP-like, the common clone form.
        "git@github.com:nicsuzor/academicOps.git",
        # SCP-like without an explicit user (git accepts this).
        "github.com:nicsuzor/academicOps.git",
        # Full ssh:// URL.
        "ssh://git@github.com/nicsuzor/academicOps.git",
        # ssh:// URL without user.
        "ssh://github.com/nicsuzor/academicOps.git",
        # ssh:// URL with an explicit port — must drop the port.
        "ssh://git@github.com:22/nicsuzor/academicOps.git",
        # git+ssh:// scheme (gemini review asked for this form).
        "git+ssh://git@github.com/nicsuzor/academicOps.git",
        # Case-insensitive host.
        "git@GitHub.com:nicsuzor/academicOps.git",
        "ssh://git@GITHUB.COM/nicsuzor/academicOps.git",
    ],
)
def test_ssh_forms_rewrite_to_https(url):
    assert _ssh_github_to_https(url) == _HTTPS


def test_leading_slash_in_scp_path_is_stripped():
    # A misformatted SCP remote with a leading slash must not yield a double
    # slash after the host (the gemini review's double-slash concern).
    assert _ssh_github_to_https("git@github.com:/nicsuzor/academicOps.git") == _HTTPS


@pytest.mark.parametrize(
    "url",
    [
        # Already HTTPS — nothing to do.
        "https://github.com/nicsuzor/academicOps.git",
        # HTTPS with an explicit port must NOT be mistaken for an SCP path.
        "https://github.com:443/nicsuzor/academicOps.git",
        # git:// protocol is not SSH and carries no token.
        "git://github.com/nicsuzor/academicOps.git",
        # Non-GitHub hosts are out of scope.
        "git@gitlab.com:foo/bar.git",
        "ssh://git@bitbucket.org/foo/bar.git",
        # Lookalike host — must NOT be normalised (would hijack the remote).
        "git@github.com.evil.com:foo/bar.git",
        "ssh://git@github.com.evil.com/foo/bar.git",
        # A host that merely contains "github.com" as a substring elsewhere.
        "git@notgithub.com:foo/bar.git",
        # Empty / junk.
        "",
        "not a url at all",
        # GitHub host but empty path — nothing meaningful to rewrite.
        "git@github.com:",
        "ssh://git@github.com/",
    ],
)
def test_non_ssh_github_returns_none(url):
    assert _ssh_github_to_https(url) is None


def test_transform_is_idempotent_on_its_own_output():
    once = _ssh_github_to_https("git@github.com:nicsuzor/academicOps.git")
    assert once == _HTTPS
    # Feeding the HTTPS result back in is a no-op (returns None → "leave it").
    assert _ssh_github_to_https(once) is None


# --------------------------------------------------------------------------- #
# In-place rewrite: _normalize_origin_to_https against a real repo            #
# --------------------------------------------------------------------------- #


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


def _origin_url(repo: Path) -> str:
    return _git(["config", "--get", "remote.origin.url"], repo).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    _git(["init", "-q"], r)
    return r


def test_rewrites_ssh_origin_in_place(repo):
    _git(["remote", "add", "origin", "git@github.com:nicsuzor/academicOps.git"], repo)
    _normalize_origin_to_https(repo)
    assert _origin_url(repo) == _HTTPS


def test_rewrites_git_plus_ssh_origin_in_place(repo):
    _git(
        ["remote", "add", "origin", "git+ssh://git@github.com/nicsuzor/academicOps.git"],
        repo,
    )
    _normalize_origin_to_https(repo)
    assert _origin_url(repo) == _HTTPS


def test_idempotent_against_already_https(repo):
    _git(["remote", "add", "origin", _HTTPS], repo)
    _normalize_origin_to_https(repo)
    assert _origin_url(repo) == _HTTPS
    # Second call must not corrupt the remote.
    _normalize_origin_to_https(repo)
    assert _origin_url(repo) == _HTTPS


def test_leaves_non_github_remote_untouched(repo):
    url = "git@gitlab.com:foo/bar.git"
    _git(["remote", "add", "origin", url], repo)
    _normalize_origin_to_https(repo)
    assert _origin_url(repo) == url


def test_no_origin_is_a_clean_noop(repo):
    # No origin configured: must not raise and must not invent a remote.
    _normalize_origin_to_https(repo)
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0  # still no origin


def test_reads_raw_url_not_insteadof_rewrite(repo):
    """The normaliser must read the RAW stored URL, so an `insteadOf` rule that
    maps SSH→something-else at read time cannot mask the real stored value.

    We store an SSH origin and add an unrelated insteadOf rule; `git remote
    get-url` would surface the rewritten value, but the normaliser uses
    `git config --get`, sees the true SSH URL, and rewrites it to HTTPS.
    """
    _git(["remote", "add", "origin", "git@github.com:nicsuzor/academicOps.git"], repo)
    # An insteadOf that rewrites a DIFFERENT prefix at resolution time.
    _git(
        ["config", "url.https://example.invalid/.insteadOf", "git@github.com:nicsuzor/"],
        repo,
    )
    _normalize_origin_to_https(repo)
    # The stored value is normalised to HTTPS regardless of the insteadOf rule.
    assert _origin_url(repo) == _HTTPS
