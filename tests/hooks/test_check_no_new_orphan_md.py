"""Unit tests for scripts/check_no_new_orphan_md.py (R5.6 enforcement).

We test the path-classification logic directly. The git-diff side is exercised
by the integration test which spins up a real ephemeral repo and runs the
script under pre-commit.
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
        # framework top-level
        "aops-core/AXIOMS.md",
        "aops-core/RULES.md",
        "aops-core/HEURISTICS.md",
        "aops-core/CONSTRAINTS.md",
        "aops-core/SCRIPTS.md",
        # skill / agent / workflow / command / hook content
        "aops-core/skills/remember/SKILL.md",
        "aops-core/skills/remember/references/TAXONOMY.md",
        "aops-core/agents/rbg.md",
        "aops-core/workflows/decompose.md",
        "aops-core/commands/learn.md",
        "aops-core/hooks/templates/enforcer-context.md",
        "aops-core/policies/some-policy.md",
        "aops-core/.claude-plugin/some.md",
        # tests / templates
        "tests/fixtures/sample.md",
        "tests/hooks/fixture.md",
        "templates/github-agent/worker.agent.md",
        # project-local rules + GitHub
        ".agents/AGENTS.md",
        ".agents/rules/HEURISTICS.md",
        ".github/copilot-instructions.md",
        # repo-root permitted basenames
        "README.md",
        "CHANGELOG.md",
        "GEMINI.md",
        "INSTALL.md",
    ],
)
def test_allowed_paths(mod, path):
    assert mod.is_allowed(path), f"expected allowed: {path}"


@pytest.mark.parametrize(
    "path",
    [
        # the actual PR #787 case
        "aops-core/docs/GEMINI-POLECAT-CAPABILITY-MATRIX.md",
        # other aops-core/docs adds
        "aops-core/docs/SOMETHING-NEW.md",
        # repo-root explainer / summary / capability docs
        "EXPLAINER.md",
        "SUMMARY.md",
        "CAPABILITY-MATRIX.md",
        # adds inside aops-core/lib or aops-core/scripts (Python homes)
        "aops-core/lib/notes.md",
        "aops-core/scripts/notes.md",
        # subdirectory README still permitted (it's a README) but a non-README
        # alongside it is not
        "aops-core/lib/MIGRATION.md",
        # arbitrary new top-level dir
        "notes/findings.md",
        "scratch/idea.md",
        # specs/ is no longer a canonical location — specs live in the brain PKB
        "specs/new-design.md",
        "specs/sub/dir/deep.md",
    ],
)
def test_blocked_paths(mod, path):
    assert not mod.is_allowed(path), f"expected blocked: {path}"


def test_allowed_root_basenames_only_at_root(mod):
    """README.md at root is allowed; README.md elsewhere goes through the
    .github / aops-core/skills / etc patterns. A bogus path that happens to
    end in README.md without a matching directory pattern is still blocked."""
    assert mod.is_allowed("README.md")
    # nested README under a recognised dir hits the dir pattern (aops-core/skills)
    assert mod.is_allowed("aops-core/skills/foo/README.md")
    # a README under a *non*-recognised dir is blocked — there is no
    # generic **/README.md allowlist (would be a hole)
    assert not mod.is_allowed("notes/README.md")


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
    target = git_repo / "tests" / "fixtures" / "new-fixture.md"
    target.parent.mkdir(parents=True)
    target.write_text("# fixture\n")
    subprocess.run(["git", "add", "tests/fixtures/new-fixture.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 0, r.stderr


def test_blocks_aops_core_docs_add(git_repo):
    """The PR #787 failure mode."""
    target = git_repo / "aops-core" / "docs" / "CAPABILITY-MATRIX.md"
    target.parent.mkdir(parents=True)
    target.write_text("# matrix\n")
    subprocess.run(
        ["git", "add", "aops-core/docs/CAPABILITY-MATRIX.md"],
        cwd=git_repo,
        check=True,
    )
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "aops-core/docs/CAPABILITY-MATRIX.md" in r.stderr
    assert "R5.6" in r.stderr


def test_blocks_repo_root_explainer(git_repo):
    (git_repo / "EXPLAINER.md").write_text("# notes\n")
    subprocess.run(["git", "add", "EXPLAINER.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "EXPLAINER.md" in r.stderr


def test_rename_does_not_trigger(git_repo):
    """Pure renames are status=R, not A — must not fire."""
    src = git_repo / "tests" / "fixtures"
    src.mkdir(parents=True)
    (src / "old.md").write_text("# old\n")
    subprocess.run(["git", "add", "tests/fixtures/old.md"], cwd=git_repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fixture", "--no-verify"],
        cwd=git_repo,
        check=True,
    )
    # Now rename. Use git mv so the index sees a rename.
    subprocess.run(
        ["git", "mv", "tests/fixtures/old.md", "tests/fixtures/new.md"],
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
    (git_repo / "tests" / "fixtures").mkdir(parents=True)
    (git_repo / "tests" / "fixtures" / "ok.md").write_text("# ok\n")
    (git_repo / "BAD.md").write_text("# bad\n")
    subprocess.run(["git", "add", "tests/fixtures/ok.md", "BAD.md"], cwd=git_repo, check=True)
    r = _run_script(git_repo)
    assert r.returncode == 1
    assert "BAD.md" in r.stderr
    assert "tests/fixtures/ok.md" not in r.stderr
