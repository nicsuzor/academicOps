"""Tests for scripts/ci/reviewer-authz.sh — the shared write-class-or-allowlisted
authorization predicate (specs/workflows/pr-pipeline.md §5.1).

This is the single source of truth `admit-on-review.sh`,
`find-conflicting-admitted-prs.sh`, and `admit-on-review.yml`'s
`authorize-changes` job all source instead of reimplementing independently.
Exercised here in isolation via `bash -c`, with inputs passed as env vars (not
string-interpolated) to avoid quoting hazards.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LIB = REPO_ROOT / "scripts" / "ci" / "reviewer-authz.sh"


def _run(script: str, env: dict) -> str:
    full_env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), **env}
    proc = subprocess.run(
        ["bash", "-c", script],
        env=full_env,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def is_authorized(login: str, permission: str, allowlist: str) -> bool:
    """Call is_authorized_reviewer directly with an explicit allowlist arg."""
    out = _run(
        'source "$LIB_PATH"; '
        'is_authorized_reviewer "$LOGIN" "$PERM" "$ALLOW" && echo yes || echo no',
        {"LIB_PATH": str(LIB), "LOGIN": login, "PERM": permission, "ALLOW": allowlist},
    )
    return out == "yes"


# ── Permission-based authorization ───────────────────────────────────────────


def test_write_permission_authorized():
    assert is_authorized("someone", "write", "")


def test_admin_permission_authorized():
    assert is_authorized("someone", "admin", "")


def test_maintain_permission_authorized():
    assert is_authorized("someone", "maintain", "")


def test_triage_permission_not_authorized():
    assert not is_authorized("someone", "triage", "")


def test_read_permission_not_authorized():
    assert not is_authorized("someone", "read", "")


def test_none_permission_not_authorized():
    assert not is_authorized("someone", "none", "")


def test_empty_permission_not_authorized():
    assert not is_authorized("someone", "", "")


# ── Allowlist-based authorization ────────────────────────────────────────────


def test_allowlist_authorizes_without_permission():
    assert is_authorized("nicsuzor", "none", "nicsuzor")


def test_allowlist_is_per_login_not_substring():
    assert not is_authorized("nicsuzor2", "none", "nicsuzor")
    assert not is_authorized("evil-nicsuzor", "none", "nicsuzor")


def test_multi_entry_allowlist():
    assert is_authorized("bob", "none", "alice bob carol")
    assert not is_authorized("dave", "none", "alice bob carol")


def test_empty_allowlist_no_bypass():
    assert not is_authorized("anyone", "none", "")


def test_write_permission_authorized_even_with_unrelated_allowlist():
    assert is_authorized("someone", "write", "somebody-else")


# ── ADMIT_ALLOWLIST default (source-time side effect) ───────────────────────
#
# Sourcing the lib sets `ADMIT_ALLOWLIST` to "nicsuzor" ONLY if the caller
# hasn't already set it — this is what collapses the 3 independently-hardcoded
# "nicsuzor" literals (2 workflow env blocks + 1 script default) into one.


def test_default_allowlist_is_nicsuzor_when_unset():
    out = _run(
        'source "$LIB_PATH"; '
        'is_authorized_reviewer "nicsuzor" "none" "$ADMIT_ALLOWLIST" && echo yes || echo no',
        {"LIB_PATH": str(LIB)},
    )
    assert out == "yes"


def test_default_allowlist_does_not_admit_unrelated_login():
    out = _run(
        'source "$LIB_PATH"; '
        'is_authorized_reviewer "someone-else" "none" "$ADMIT_ALLOWLIST" && echo yes || echo no',
        {"LIB_PATH": str(LIB)},
    )
    assert out == "no"


def test_explicit_admit_allowlist_env_overrides_default():
    out = _run(
        'source "$LIB_PATH"; '
        'is_authorized_reviewer "custom-user" "none" "$ADMIT_ALLOWLIST" && echo yes || echo no',
        {"LIB_PATH": str(LIB), "ADMIT_ALLOWLIST": "custom-user"},
    )
    assert out == "yes"


def test_explicit_admit_allowlist_env_excludes_default_login():
    # An explicit override REPLACES the default rather than extending it —
    # "nicsuzor" is no longer authorized once ADMIT_ALLOWLIST is overridden.
    out = _run(
        'source "$LIB_PATH"; '
        'is_authorized_reviewer "nicsuzor" "none" "$ADMIT_ALLOWLIST" && echo yes || echo no',
        {"LIB_PATH": str(LIB), "ADMIT_ALLOWLIST": "custom-user"},
    )
    assert out == "no"
