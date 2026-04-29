#!/usr/bin/env python3
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

from tests.polecat.conftest import write_polecat_test_config  # noqa: E402


@dataclass
class Task:
    id: str
    title: str = ""
    project: str | None = "test"


def _git(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture()
def bare_origin(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    _git(["init", "--bare", "-b", "main", str(origin)], cwd=tmp_path)

    seed = tmp_path / "seed"
    seed.mkdir()
    _git(["init", "-b", "main", str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)
    (seed / "README.md").write_text("seed\n")
    (seed / ".gitignore").write_text(".claude/\n.gemini/\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "init"], cwd=seed)
    _git(["remote", "add", "origin", str(origin)], cwd=seed)
    _git(["push", "-u", "origin", "main"], cwd=seed)
    return origin


@pytest.fixture()
def local_mirror(tmp_path: Path, bare_origin: Path) -> Path:
    mirror = tmp_path / "mirror.git"
    _git(["clone", "--mirror", str(bare_origin), str(mirror)], cwd=tmp_path)
    return mirror


@pytest.fixture()
def aca_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    data_dir = tmp_path / "aca_data"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


@pytest.fixture()
def polecat_home(tmp_path: Path, local_mirror: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "polecat_home"
    home.mkdir()
    # Polecat expects repos in home/.repos/project.git
    repos_dir = home / ".repos"
    repos_dir.mkdir()
    shutil.copytree(local_mirror, repos_dir / "test.git")

    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home,
        project_paths={"test": local_mirror},
    )
    monkeypatch.setenv("AOPS_SESSIONS", str(sessions_dir))
    return home


@pytest.fixture()
def manager(polecat_home: Path, aca_data: Path) -> PolecatManager:
    # Need to mock safe_sync_mirror to not actually try to hit GitHub if it's not needed,
    # but our fixtures use local paths so it might just work.
    return PolecatManager(home_dir=polecat_home)


def test_auto_rebase_silent(bare_origin: Path, manager: PolecatManager, tmp_path: Path):
    # 1. Advance origin by 3 commits
    seed = tmp_path / "seed_update"
    _git(["clone", str(bare_origin), str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)
    for i in range(3):
        (seed / f"file_{i}.txt").write_text(f"content {i}")
        _git(["add", "."], cwd=seed)
        _git(["commit", "-m", f"commit {i}"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    # 2. Sync mirror
    manager.safe_sync_mirror("test")

    # 3. Create worktree
    task = Task(id="task-silent")
    worktree_path = manager._do_setup_worktree(task)

    # 4. Verify it was rebased
    result = _git(["log", "--oneline"], cwd=worktree_path)
    assert "commit 0" in result.stdout
    assert "commit 1" in result.stdout
    assert "commit 2" in result.stdout


def test_auto_rebase_logged(bare_origin: Path, manager: PolecatManager, tmp_path: Path, capsys):
    # 1. Create the worktree at current state (origin has only the seed commit)
    task = Task(id="task-logged")
    manager._do_setup_worktree(task)

    # 2. Advance origin/main by 6 commits (> threshold of 5)
    seed = tmp_path / "seed_update_logged"
    _git(["clone", str(bare_origin), str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)
    for i in range(6):
        (seed / f"logged_{i}.txt").write_text(f"content {i}")
        _git(["add", "."], cwd=seed)
        _git(["commit", "-m", f"commit {i}"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    # 3. Re-run setup on the EXISTING worktree — triggers _verify_worktree_setup
    #    which sees 6 commits behind and emits the verbose rebase log to stderr.
    capsys.readouterr()  # Clear prior output
    worktree_path = manager._do_setup_worktree(task)

    # 4. Verify logged rebase happened (messages go to sys.stderr)
    captured = capsys.readouterr()
    assert "Attempting auto-rebase" in captured.err
    assert "Rebase successful" in captured.err

    result = _git(["log", "--oneline"], cwd=worktree_path)
    assert "commit 5" in result.stdout


def test_auto_rebase_conflicts(bare_origin: Path, manager: PolecatManager, tmp_path: Path):
    # 1. Start with origin main at Commit A
    seed = tmp_path / "seed_conflict"
    _git(["clone", str(bare_origin), str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)

    # 2. Create feature branch from Commit A
    _git(["checkout", "-b", "polecat/task-conflict"], cwd=seed)
    (seed / "README.md").write_text("feature change\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "feature commit"], cwd=seed)
    _git(["push", "origin", "polecat/task-conflict"], cwd=seed)

    # 3. Advance origin/main with a conflicting change (Commit B)
    _git(["checkout", "main"], cwd=seed)
    (seed / "README.md").write_text("origin change\n")
    _git(["add", "."], cwd=seed)
    _git(["commit", "-m", "origin commit"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    manager.safe_sync_mirror("test")

    task = Task(id="task-conflict")

    # 4. _do_setup_worktree should raise RuntimeError due to rebase conflict
    with pytest.raises(RuntimeError) as excinfo:
        manager._do_setup_worktree(task)

    assert "could not be cleanly rebased" in str(excinfo.value)


def test_auto_rebase_dirty(bare_origin: Path, manager: PolecatManager, tmp_path: Path):
    # 1. Advance origin
    seed = tmp_path / "seed_dirty"
    _git(["clone", str(bare_origin), str(seed)], cwd=tmp_path)
    _git(["config", "user.email", "test@test.example"], cwd=seed)
    _git(["config", "user.name", "Test User"], cwd=seed)
    for i in range(6):
        (seed / f"dirty_{i}.txt").write_text(f"content {i}")
        _git(["add", "."], cwd=seed)
        _git(["commit", "-m", f"commit {i}"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    manager.safe_sync_mirror("test")

    task = Task(id="task-dirty")

    # 2. First creation (fresh) - will rebase
    worktree_path = manager._do_setup_worktree(task)

    # 3. Make it dirty
    (worktree_path / "dirty.txt").write_text("dirty")

    # 4. Advance origin again
    for i in range(6, 12):
        (seed / f"dirty_{i}.txt").write_text(f"content {i}")
        _git(["add", "."], cwd=seed)
        _git(["commit", "-m", f"commit {i}"], cwd=seed)
    _git(["push", "origin", "main"], cwd=seed)

    manager.safe_sync_mirror("test")

    # 5. Re-run setup - should raise RuntimeError because dirty and > threshold
    with pytest.raises(RuntimeError) as excinfo:
        # We need to ensure _do_setup_worktree is called for the existing worktree
        manager._do_setup_worktree(task)

    assert "has uncommitted changes" in str(excinfo.value)
