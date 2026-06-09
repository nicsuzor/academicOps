#!/usr/bin/env python3
"""Tests for polecat's SSH→HTTPS GitHub remote normalization.

`_sync_working_repo` rewrites an SSH GitHub origin to HTTPS before any network
op so automation authenticates with the bot token over HTTPS rather than the SSH
agent (unreachable under cron; a 1Password prompt interactively). These tests
pin both halves of that behaviour:

  * `_ssh_github_to_https` — the pure string transform, now the single
    authoritative converter living in ``polecat.manager`` — across every SSH form
    git accepts, every no-op case (already-HTTPS, non-GitHub, git://), and the
    lookalike-host attack (`github.com.evil.com`).
  * `_to_https_url` — the best-effort wrapper the manager mirror/worktree call
    sites use, which must return a usable remote URL in EVERY case (HTTPS for an
    SSH GitHub URL, the original string otherwise) and now shares the
    comprehensive SSH-form coverage of the pure transform.
  * `_normalize_origin_to_https` — the in-place git-config rewrite — against a
    real on-disk repo, confirming it actually mutates the stored remote, is
    idempotent, leaves non-SSH/non-GitHub remotes untouched, no-ops cleanly
    when there is no origin at all, and logs at DEBUG when ``set-url`` fails.

Both call sites (the cli origin-normaliser and the manager mirror/worktree
paths) route through the one converter in ``polecat.manager`` — this module
pins that single source of truth so a future divergence breaks a test.
"""

import logging
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

# The pure transform is authoritative in polecat.manager; cli imports it from
# there. Import from both to assert they are the *same* object (no duplicate).
import cli  # noqa: E402
from cli import _normalize_origin_to_https  # noqa: E402

from polecat.manager import _ssh_github_to_https, _to_https_url  # noqa: E402

_HTTPS = "https://github.com/nicsuzor/academicOps.git"


def test_single_source_of_truth_no_duplicate_converter():
    """The cli call site must reuse the manager converter, not redefine one."""
    assert cli._ssh_github_to_https is _ssh_github_to_https


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
# Best-effort wrapper: _to_https_url (the manager mirror/worktree call sites)  #
#                                                                              #
# Unlike the pure transform, this MUST return a usable remote URL in every     #
# case — it is handed straight to ``git`` as a remote. It now shares the       #
# comprehensive SSH-form coverage, closing the gap on the mirror/worktree      #
# paths that previously only handled ``git@github.com:owner/repo.git``.        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url",
    [
        "git@github.com:nicsuzor/academicOps.git",
        "github.com:nicsuzor/academicOps.git",
        "ssh://git@github.com/nicsuzor/academicOps.git",
        "ssh://github.com/nicsuzor/academicOps.git",
        "ssh://git@github.com:22/nicsuzor/academicOps.git",
        "git+ssh://git@github.com/nicsuzor/academicOps.git",
        "git@GitHub.com:nicsuzor/academicOps.git",
        "ssh://git@GITHUB.COM/nicsuzor/academicOps.git",
        "git@github.com:/nicsuzor/academicOps.git",
    ],
)
def test_to_https_url_rewrites_every_ssh_form(url):
    # The manager call sites now gain the full SSH-form coverage, not just the
    # narrow git@github.com: case the old _to_https_url handled.
    assert _to_https_url(url) == _HTTPS


@pytest.mark.parametrize(
    "url",
    [
        # Already HTTPS / non-SSH / non-GitHub — returned UNCHANGED (usable URL),
        # never None: these strings are fed straight to git as a remote.
        "https://github.com/nicsuzor/academicOps.git",
        "https://github.com:443/nicsuzor/academicOps.git",
        "git://github.com/nicsuzor/academicOps.git",
        "git@gitlab.com:foo/bar.git",
        "ssh://git@bitbucket.org/foo/bar.git",
        "git@github.com.evil.com:foo/bar.git",
        "git@notgithub.com:foo/bar.git",
    ],
)
def test_to_https_url_passes_through_non_ssh_github_unchanged(url):
    assert _to_https_url(url) == url


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


def test_failed_set_url_is_logged_at_debug(repo, monkeypatch, caplog):
    """A failed ``git remote set-url`` must surface at DEBUG, not vanish — so a
    later fetch failure is not mis-attributed to the network when the remote was
    never actually normalised.
    """
    _git(["remote", "add", "origin", "git@github.com:nicsuzor/academicOps.git"], repo)

    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        # Let the read (`git config --get`) through; force the set-url to fail.
        if args[:3] == ["git", "remote", "set-url"]:
            return subprocess.CompletedProcess(
                args, returncode=1, stdout="", stderr="boom: set-url refused"
            )
        return real_run(args, *a, **kw)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    with caplog.at_level(logging.DEBUG, logger=cli._log.name):
        _normalize_origin_to_https(repo)

    assert any(
        "set-url" in rec.getMessage() and rec.levelno == logging.DEBUG for rec in caplog.records
    ), f"expected a DEBUG log mentioning set-url; got {[r.getMessage() for r in caplog.records]}"
