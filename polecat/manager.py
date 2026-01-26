#!/usr/bin/env python3
import sys
import os
import fcntl
import subprocess
import shutil
from pathlib import Path

# Add aops-core to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports will fail here but work when moved to academicOps
try:
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
except ImportError:
    pass

class PolecatManager:
    def __init__(self):
        # Global location for all active agents
        self.polecats_dir = Path.home() / "polecats"
        self.polecats_dir.mkdir(exist_ok=True)
        
        # We still need access to the task DB
        self.storage = TaskStorage()

    def get_repo_path(self, task) -> Path:
        """Determines which git repo to spawn the worktree from.
        
        TODO: Add your project mapping logic here.
        """
        if task.project == "buttermilk":
             return Path.home() / "src/buttermilk"
        if task.project == "writing":
             return Path.home() / "writing"
             
        # Default fallback
        return REPO_ROOT

    def claim_next_task(self, caller: str, project: str = None):
        """Finds and claims the highest priority ready task."""
        tasks = self.storage.get_ready_tasks(project=project)
        
        if not tasks:
            return None

        for task in tasks:
            task_path = self.storage._find_task_path(task.id)
            if task_path is None:
                continue

            lock_path = task_path.with_suffix(".lock")

            try:
                with open(lock_path, "w") as lock_file:
                    try:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue 

                    try:
                        fresh_task = self.storage.get_task(task.id)
                        if fresh_task is None or fresh_task.status != TaskStatus.ACTIVE:
                            continue
                        if fresh_task.assignee and fresh_task.assignee != caller:
                            continue

                        fresh_task.status = TaskStatus.IN_PROGRESS
                        fresh_task.assignee = caller
                        self.storage.save_task(fresh_task)
                        return fresh_task

                    finally:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

            except Exception as e:
                print(f"Warning: Failed to claim {task.id}: {e}", file=sys.stderr)
                continue
            finally:
                try:
                    lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
        
        return None

    def setup_worktree(self, task):
        """Creates a git worktree in ~/polecats linked to the project repo."""
        repo_path = self.get_repo_path(task)
        if not repo_path.exists():
            raise FileNotFoundError(f"Project repository not found at {repo_path}")

        worktree_path = self.polecats_dir / task.id
        branch_name = f"polecat/{task.id}"

        if worktree_path.exists():
            return worktree_path

        print(f"Creating worktree at {worktree_path} from repo {repo_path}...")

        # We must run git commands from the PARENT repo
        cmd = [
            "git", "worktree", "add",
            "-b", branch_name,
            str(worktree_path),
            "main"
        ]

        try:
            subprocess.run(cmd, cwd=repo_path, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Worktree creation failed: {e}. Attempting recovery...", file=sys.stderr)
            if self._branch_exists(repo_path, branch_name):
                 cmd = ["git", "worktree", "add", str(worktree_path), branch_name]
                 subprocess.run(cmd, cwd=repo_path, check=True)
            else:
                 raise e

        return worktree_path

    def _branch_exists(self, repo_path, branch_name):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name],
            cwd=repo_path,
            capture_output=True
        )
        return res.returncode == 0

    def _is_branch_merged(self, repo_path: Path, branch_name: str, target: str = "main") -> bool:
        """Check if branch has been merged into target branch."""
        # Check if any commits in branch are NOT in target
        result = subprocess.run(
            ["git", "log", "--oneline", f"{target}..{branch_name}"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        # If output is empty, branch is fully merged
        return result.returncode == 0 and not result.stdout.strip()

    def nuke_worktree(self, task_id, force=False):
        """Removes the worktree and deletes the branch.

        Args:
            task_id: The task ID whose worktree should be removed
            force: If True, skip merge verification check

        Raises:
            RuntimeError: If branch has unmerged commits and force=False
        """
        # We need the task to know which repo it came from, but if we don't have it
        # (e.g. CLI just passed an ID), we might have to guess or search.
        # For simplicity, let's look up the task.
        task = self.storage.get_task(task_id)
        if task:
            repo_path = self.get_repo_path(task)
        else:
            # Fallback: assume academicOps if task deleted
            repo_path = REPO_ROOT

        worktree_path = self.polecats_dir / task_id
        branch_name = f"polecat/{task_id}"

        # Safety check: verify branch is merged before deletion
        if not force and self._branch_exists(repo_path, branch_name):
            if not self._is_branch_merged(repo_path, branch_name):
                raise RuntimeError(
                    f"Branch {branch_name} has unmerged commits. "
                    f"Use --force to delete anyway, or merge first with 'polecat merge'."
                )

        if worktree_path.exists():
            print(f"Removing worktree {worktree_path}...")
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=repo_path,
                check=False 
            )
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
        
        if self._branch_exists(repo_path, branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=repo_path,
                check=False
            )
