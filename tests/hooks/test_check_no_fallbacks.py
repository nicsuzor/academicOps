"""Regression tests for scripts/check_no_fallbacks.py (P#8 / halt-on-failure).

Background (#1585): the detector (PR #931) was sound, but the pre-commit
`files:` glob scoped the hook to only 3 paths — a fallback authored anywhere
else (e.g. aops-core/lib/, polecat/) passed pre-commit silently. This widens
the glob to ALL first-party Python/shell and pins three behaviours:

1. The hook *fires* on a new env-var literal default planted in an
   aops-core/lib or polecat path (AC1) — behaviour, not a file-list.
2. The bare-run scope (`_default_targets` via `_in_scope`) and the pre-commit
   `files:`/`exclude:` glob AGREE on representative paths (AC2) — the glob is
   loaded from the real .pre-commit-config.yaml, not hard-coded.
3. Genuinely-optional values stay annotatable with `# allow-fallback:` (AC3).

Plus the baseline mechanism that lets the widening land before the P0
content-sweep (aops-682e75a5): pre-existing sites are grandfathered, but NEW
fallbacks in those same files still fail.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_no_fallbacks.py"
CONFIG = REPO_ROOT / ".pre-commit-config.yaml"


def _load_script():
    spec = importlib.util.spec_from_file_location("check_no_fallbacks", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_script()


def _run_on(*paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------
# AC1 — the hook fires on a planted violation outside the old 3-path glob.
# These assert BEHAVIOUR (run the detector on the file) on the *kind* of path
# that used to escape, not a hard-coded list.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("subdir", ["aops-core/lib", "aops-core/lib/gates", "polecat", "scripts"])
def test_detector_fires_on_planted_env_literal(tmp_path, subdir):
    target = tmp_path / subdir / "planted.py"
    target.parent.mkdir(parents=True)
    target.write_text('import os\nx = os.getenv("REQUIRED_X", "literal-default")\n')
    r = _run_on(target)
    assert r.returncode == 1, f"expected the hook to fire on {subdir}: {r.stdout}\n{r.stderr}"
    assert "planted.py" in r.stdout
    assert "os.getenv" in r.stdout


# --------------------------------------------------------------------------
# AC3 — genuinely-optional values stay annotatable.
# --------------------------------------------------------------------------


def test_allow_fallback_annotation_suppresses(tmp_path):
    target = tmp_path / "aops-core" / "lib" / "opt.py"
    target.parent.mkdir(parents=True)
    target.write_text(
        "import os\n"
        'x = os.getenv("OPT_X", "default")  # allow-fallback: genuinely optional feature flag\n'
    )
    r = _run_on(target)
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------------------
# AC2 — bare-run scope (`_in_scope`) and the pre-commit glob AGREE.
# The glob is read from the real config (SSoT), not asserted as a literal
# string, so the test checks the *scope decision* on representative paths.
# --------------------------------------------------------------------------


def _precommit_scope():
    """Return a predicate replicating pre-commit's include/exclude decision for
    the check-no-fallbacks hook, loaded from .pre-commit-config.yaml."""
    cfg = yaml.safe_load(CONFIG.read_text())
    hook = next(
        h for repo in cfg["repos"] for h in repo.get("hooks", []) if h["id"] == "check-no-fallbacks"
    )
    files_re = re.compile(hook["files"])
    exclude_re = re.compile(hook["exclude"]) if hook.get("exclude") else None

    def matches(path: str) -> bool:
        if not files_re.search(path):
            return False
        if exclude_re and exclude_re.search(path):
            return False
        return True

    return matches


# (path, expected-in-scope)
_REPRESENTATIVE_PATHS = [
    ("aops-core/hooks/router.py", True),
    ("aops-core/lib/gates/gate_config.py", True),
    ("polecat/manager.py", True),
    ("scripts/build.py", True),
    ("aops-tools/foo.py", True),
    ("aops-core/hooks/router.sh", True),
    ("scripts/repo-sync-cron.sh", True),
    ("aops-core/agent-env-map.conf", True),
    # out of scope
    ("tests/hooks/test_check_no_fallbacks.py", False),
    ("README.md", False),
    ("aops-core/lib/notes.md", False),
    ("aops-core/.venv/lib/x.py", False),
    ("scripts/dist/bundle.py", False),
    ("polecat/__pycache__/manager.py", False),
    (".claude/worktrees/wt/aops-core/lib/x.py", False),
    ("aops-tools/agent-env-map.conf", False),  # only the canonical aops-core copy
]


@pytest.mark.parametrize("path,expected", _REPRESENTATIVE_PATHS)
def test_precommit_glob_matches_expected_scope(path, expected):
    matches = _precommit_scope()
    assert matches(path) is expected, f"pre-commit glob scope wrong for {path}"


@pytest.mark.parametrize("path,expected", _REPRESENTATIVE_PATHS)
def test_in_scope_matches_expected_scope(mod, path, expected):
    assert mod._in_scope(path) is expected, f"_in_scope wrong for {path}"


@pytest.mark.parametrize("path,_expected", _REPRESENTATIVE_PATHS)
def test_bare_run_and_precommit_scope_agree(mod, path, _expected):
    """The lock-step guarantee: the bare-run predicate and the pre-commit glob
    must make the SAME include/exclude decision for every representative path.
    This is the test that catches silent drift between the two definitions."""
    matches = _precommit_scope()
    assert mod._in_scope(path) == matches(path), f"scope drift on {path}"


# --------------------------------------------------------------------------
# Baseline — grandfather pre-existing sites, but still catch NEW ones.
# --------------------------------------------------------------------------


def test_baseline_grandfathers_existing_but_catches_new(mod):
    baseline = {"aops-core/lib/x.py": {"os.getenv(..., 'a')": 1}}
    grandfathered = {
        "file": "aops-core/lib/x.py",
        "pattern": "os.getenv(..., 'a')",
        "line": 1,
        "col": 0,
        "message": "",
    }
    new_distinct = {
        "file": "aops-core/lib/x.py",
        "pattern": "os.getenv(..., 'b')",
        "line": 2,
        "col": 0,
        "message": "",
    }
    # The grandfathered one alone survives baseline filtering -> nothing blocks.
    assert mod._apply_baseline([dict(grandfathered)], baseline) == []
    # A new, distinct fallback in the SAME baselined file still blocks.
    survivors = mod._apply_baseline([dict(grandfathered), dict(new_distinct)], baseline)
    assert [v["pattern"] for v in survivors] == ["os.getenv(..., 'b')"]
    # A DUPLICATE of the grandfathered pattern beyond the allowed count blocks.
    dup_survivors = mod._apply_baseline([dict(grandfathered), dict(grandfathered)], baseline)
    assert len(dup_survivors) == 1


def test_real_baseline_is_consistent_with_current_scan(mod):
    """The committed baseline must not under-count the current scan, or a fresh
    checkout would block on pre-existing sites. (It MAY over-count: the sweep
    removes sites faster than the baseline shrinks — that is fine, fewer
    violations than grandfathered still passes.)"""
    baseline = mod._load_baseline()
    # Run the real bare scan; with the committed baseline applied it must be clean.
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert r.returncode == 0, (
        f"bare run not clean against committed baseline:\n{r.stdout}\n{r.stderr}"
    )
    assert isinstance(baseline, dict)
