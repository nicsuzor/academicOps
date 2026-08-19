"""Unit tests for scripts/check_no_new_orphan_md.py (R5.6 enforcement).

Tests the path-classification logic directly and exercises git index diffing.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_no_new_orphan_md.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_no_new_orphan_md", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


# ----- allowlist classification -------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        # plugin content
        "plugins/ida/README.md",
        "plugins/ida/agents/ida.md",
        "plugins/ida/skills/strategize/SKILL.md",
        "plugins/pkb/workflows/process/feature-dev.md",
        "plugins/orchestrate/hooks/messages/honesty.md",
        "plugins/tools/skills/analyst/SKILL.md",
        # disabled plugins during development
        "plugins.disabled/specs/learning-log-skill.md",
        "plugins.disabled/workflows/base-commit.md",
        # specs / tests / templates
        "specs/ARCHITECTURE.md",
        "specs/enforcement/task-contract.md",
        "specs/sub/dir/deep.md",
        "tests/fixtures/sample.md",
        "tests/transcripts/fixtures/README.md",
        "templates/github-agent/worker.agent.md",
        "templates/plugin/README.md",
        # project-local rules + GitHub + Claude
        ".agents/AGENTS.md",
        ".agents/rules/HEURISTICS.md",
        ".github/copilot-instructions.md",
        ".claude/CLAUDE.md",
        # repo-root permitted basenames
        "README.md",
        "CHANGELOG.md",
        "GEMINI.md",
        "INSTALL.md",
        "CONTRIBUTING.md",
        "CLAUDE.md",
        "AGENTS.md",
        "RULES.md",
    ],
)
def test_allowed_paths(mod, path):
    assert mod.is_allowed(path), f"expected allowed: {path}"


@pytest.mark.parametrize(
    "path",
    [
        # unreviewed explainer / doc adds
        "docs/GEMINI-POLECAT-CAPABILITY-MATRIX.md",
        "docs/SOMETHING-NEW.md",
        # repo-root explainer / summary / capability docs
        "EXPLAINER.md",
        "SUMMARY.md",
        "CAPABILITY-MATRIX.md",
        # adds inside lib or scripts (Python homes)
        "lib/notes.md",
        "scripts/notes.md",
        "scripts/MIGRATION.md",
        # arbitrary new top-level dir
        "notes/findings.md",
        "scratch/idea.md",
    ],
)
def test_blocked_paths(mod, path):
    assert not mod.is_allowed(path), f"expected blocked: {path}"


def test_allowed_root_basenames_only_at_root(mod):
    """README.md at root is allowed; README.md elsewhere goes through recognized
    directory patterns (plugins/, specs/, etc). A path outside canonical dirs is blocked."""
    assert mod.is_allowed("README.md")
    assert mod.is_allowed("plugins/ida/README.md")
    assert not mod.is_allowed("notes/README.md")
    assert not mod.is_allowed("lib/README.md")


# ----- end-to-end: real git index -----------------------------------------------


@pytest.fixture
def git_repo(tmp_path):
    """Initialise a tiny repo with one committed file."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init", "--no-verify"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def _run_script(cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_passes_when_only_modifying_existing(git_repo):
    (git_repo / "README.md").write_text("# t (edited)\n")
    subprocess.run(["git", "add", "README.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 0, r.stderr


def test_passes_for_canonical_add(git_repo):
    target = git_repo / "specs" / "new-spec.md"
    target.parent.mkdir(parents=True)
    target.write_text("# spec\n")
    subprocess.run(["git", "add", "specs/new-spec.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 0, r.stderr


def test_blocks_orphan_docs_add(git_repo):
    target = git_repo / "docs" / "CAPABILITY-MATRIX.md"
    target.parent.mkdir(parents=True)
    target.write_text("# matrix\n")
    subprocess.run(
        ["git", "add", "docs/CAPABILITY-MATRIX.md"],
        cwd=git_repo,
        check=True,
    )
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "docs/CAPABILITY-MATRIX.md" in r.stderr
    assert "R5.6" in r.stderr


def test_blocks_repo_root_explainer(git_repo):
    (git_repo / "EXPLAINER.md").write_text("# notes\n")
    subprocess.run(["git", "add", "EXPLAINER.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "EXPLAINER.md" in r.stderr


def test_rename_does_not_trigger(git_repo):
    """Pure renames are status=R, not A — must not fire."""
    src = git_repo / "specs"
    src.mkdir()
    (src / "old-spec.md").write_text("# old\n")
    subprocess.run(["git", "add", "specs/old-spec.md"], cwd=git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "spec", "--no-verify"],
        cwd=git_repo,
        check=True,
    )
    # Now rename. Use git mv so the index sees a rename.
    subprocess.run(
        ["git", "mv", "specs/old-spec.md", "specs/new-spec.md"],
        cwd=git_repo,
        check=True,
    )
    r = _run_script(git_repo)
    # diff-filter=A in the script excludes renames (status=R), so this is OK.
    assert r.returncode == 0, r.stderr


def test_no_md_changes_passes(git_repo):
    (git_repo / "code.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "code.py"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 0, r.stderr


def test_mixed_add_with_one_blocked(git_repo):
    """If multiple .md files are staged, all blocked ones must surface."""
    (git_repo / "specs").mkdir()
    (git_repo / "specs" / "ok.md").write_text("# ok\n")
    (git_repo / "BAD.md").write_text("# bad\n")
    subprocess.run(["git", "add", "specs/ok.md", "BAD.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "BAD.md" in r.stderr
    assert "specs/ok.md" not in r.stderr
