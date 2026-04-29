import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parents[2].resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from manager import PolecatManager  # noqa: E402

from tests.polecat.conftest import write_polecat_test_config  # noqa: E402


def setup_git_repo(path: Path):
    subprocess.run(["git", "init", "--bare", str(path)], check=True)
    # Create a working copy to add initial content
    work_path = path.parent / (path.name + "_work")
    subprocess.run(["git", "clone", str(path), str(work_path)], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=work_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=work_path, check=True)

    (work_path / "README.md").write_text("initial")
    subprocess.run(["git", "add", "README.md"], cwd=work_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=work_path, check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work_path, check=True)

    return work_path


def test_sync_resolves_staleness_with_checked_out_branch(tmp_path):
    # 1. Setup remote repo
    remote_path = tmp_path / "remote.git"
    work_path = setup_git_repo(remote_path)

    # 2. Setup polecat manager and mirror
    home_dir = tmp_path / "polecat_home"
    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home_dir,
        project_paths={"testproj": work_path},
        crew_names=["worker"],
    )

    aca_data = tmp_path / "aca_data"
    aca_data.mkdir(exist_ok=True)

    with patch.dict("os.environ", {"ACA_DATA": str(aca_data), "AOPS_SESSIONS": str(sessions_dir)}):
        manager = PolecatManager(home_dir=home_dir)
        manager.ensure_repo_mirror("testproj")

        mirror_path = manager.repos_dir / "testproj.git"

        # 3. Create a worktree on 'main' in the mirror
        wt_path = tmp_path / "wt_main"
        subprocess.run(
            ["git", "worktree", "add", str(wt_path), "main"], cwd=mirror_path, check=True
        )

        # Verify it's checked out
        exclude = manager._worktree_exclude_refspecs(mirror_path)
        assert "^refs/heads/main" in exclude

        # 4. Add a new commit to remote
        (work_path / "file.txt").write_text("new stuff")
        subprocess.run(["git", "add", "file.txt"], cwd=work_path, check=True)
        subprocess.run(["git", "commit", "-m", "new stuff"], cwd=work_path, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work_path, check=True)
        remote_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=work_path, capture_output=True, text=True
        ).stdout.strip()

        # 5. Run sync
        success = manager.safe_sync_mirror("testproj")
        assert success is True

        # 6. Verify mirror is now at remote_sha
        mirror_sha = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"], cwd=mirror_path, capture_output=True, text=True
        ).stdout.strip()
        assert mirror_sha == remote_sha

        # 7. Verify freshness check reports OK
        is_fresh, message = manager.check_mirror_freshness("testproj")
        assert is_fresh is True
        assert "up-to-date" in message


def test_sync_updates_other_branches_when_one_is_checked_out(tmp_path):
    # 1. Setup remote repo
    remote_path = tmp_path / "remote.git"
    work_path = setup_git_repo(remote_path)

    # Create another branch
    subprocess.run(["git", "checkout", "-b", "other"], cwd=work_path, check=True)
    (work_path / "other.txt").write_text("other")
    subprocess.run(["git", "add", "other.txt"], cwd=work_path, check=True)
    subprocess.run(["git", "commit", "-m", "other branch"], cwd=work_path, check=True)
    subprocess.run(["git", "push", "origin", "other"], cwd=work_path, check=True)

    # 2. Setup polecat manager and mirror
    home_dir = tmp_path / "polecat_home"
    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home_dir,
        project_paths={"testproj": work_path},
        crew_names=["worker"],
    )

    aca_data = tmp_path / "aca_data"
    aca_data.mkdir(exist_ok=True)

    with patch.dict("os.environ", {"ACA_DATA": str(aca_data), "AOPS_SESSIONS": str(sessions_dir)}):
        manager = PolecatManager(home_dir=home_dir)
        manager.ensure_repo_mirror("testproj")
        mirror_path = manager.repos_dir / "testproj.git"

        # 3. Create a worktree on 'other' in the mirror
        wt_path = tmp_path / "wt_other"
        subprocess.run(
            ["git", "worktree", "add", str(wt_path), "other"], cwd=mirror_path, check=True
        )

        # 4. Add a new commit to 'main' on remote
        subprocess.run(["git", "checkout", "main"], cwd=work_path, check=True)
        (work_path / "main_new.txt").write_text("main new")
        subprocess.run(["git", "add", "main_new.txt"], cwd=work_path, check=True)
        subprocess.run(["git", "commit", "-m", "main new"], cwd=work_path, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=work_path, check=True)
        main_remote_sha = subprocess.run(
            ["git", "rev-parse", "main"], cwd=work_path, capture_output=True, text=True
        ).stdout.strip()

        # 5. Run sync
        success = manager.safe_sync_mirror("testproj")
        assert success is True

        # 6. Verify 'main' is updated even though 'other' was checked out
        # (This failed before because the bulk fetch skipped main)
        mirror_main_sha = subprocess.run(
            ["git", "rev-parse", "refs/heads/main"], cwd=mirror_path, capture_output=True, text=True
        ).stdout.strip()
        assert mirror_main_sha == main_remote_sha


def test_sync_fails_loudly_when_remains_stale(tmp_path, capsys):
    # 1. Setup remote repo
    remote_path = tmp_path / "remote.git"
    work_path = setup_git_repo(remote_path)

    # 2. Setup polecat manager and mirror
    home_dir = tmp_path / "polecat_home"
    sessions_dir = write_polecat_test_config(
        tmp_path,
        home_dir=home_dir,
        project_paths={"testproj": work_path},
        crew_names=["worker"],
    )

    aca_data = tmp_path / "aca_data"
    aca_data.mkdir(exist_ok=True)

    with patch.dict("os.environ", {"ACA_DATA": str(aca_data), "AOPS_SESSIONS": str(sessions_dir)}):
        manager = PolecatManager(home_dir=home_dir)
        manager.ensure_repo_mirror("testproj")

        # 3. Add a new commit to remote
        (work_path / "file.txt").write_text("new stuff")
        subprocess.run(["git", "add", "file.txt"], cwd=work_path, check=True)
        subprocess.run(["git", "commit", "-m", "new stuff"], cwd=work_path, check=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=work_path, check=True)

        # 4. Mock git fetch to be a NO-OP so it remains stale
        # We need to use real subprocess for almost everything except the actual fetch
        real_run = subprocess.run

        def mocked_run(cmd, **kwargs):
            if cmd[0] == "git" and cmd[1] == "fetch":
                return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
            return real_run(cmd, **kwargs)

        with patch("subprocess.run", side_effect=mocked_run):
            success = manager.safe_sync_mirror("testproj")

            assert success is False
            captured = capsys.readouterr()
            assert "Mirror remains stale after sync" in captured.err
            assert "stale vs origin" in captured.err
