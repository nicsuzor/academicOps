#!/usr/bin/env python3
import sys
import os
import fcntl
import subprocess
import shutil
from pathlib import Path

# Add aops-core to path for lib imports
# Assumes this script will be running from ~/src/academicOps/polecat/manager.py
# after being moved
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

# These imports will fail here but work when moved to academicOps
try:
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
except ImportError:
    # Fallback for when running in gastown context (for linting/verification if needed)
    pass

class PolecatManager:
    def __init__(self):
        self.repo_root = REPO_ROOT
        self.storage = TaskStorage()
        self.polecats_dir = self.repo_root / "polecats"
        self.polecats_dir.mkdir(exist_ok=True)

    def claim_next_task(self, caller: str, project: str = None):
        """Finds and claims the highest priority ready task."""
        tasks = self.storage.get_ready_tasks(project=project)
        
        if not tasks:
            return None

        # Try to claim tasks in priority order
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
                        continue  # Locked by another process

                    try:
                        # Re-load task to ensure it's still valid/unclaimed
                        fresh_task = self.storage.get_task(task.id)
                        if fresh_task is None:
                            continue

                        if fresh_task.status != TaskStatus.ACTIVE:
                            continue
                        if fresh_task.assignee and fresh_task.assignee != caller:
                            continue

                        # Claim it
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
        """Creates a git worktree for the task."""
        worktree_path = self.polecats_dir / task.id
        branch_name = f"polecat/{task.id}"

        # If worktree already exists, return it
        if worktree_path.exists():
            return worktree_path

        print(f"Creating worktree at {worktree_path} for task {task.id}...")

        # Create branch and worktree
        # git worktree add -b <branch> <path> <start-point>
        # We assume starting from main
        cmd = [
            "git", "worktree", "add",
            "-b", branch_name,
            str(worktree_path),
            "main"
        ]

        try:
            subprocess.run(cmd, cwd=self.repo_root, check=True)
        except subprocess.CalledProcessError as e:
            # Maybe branch already exists? Try without -b
            # Or handle detached head if main is checked out? 
            # Git worktrees require distinct branches usually.
            # If branch exists, we might need to use it.
            print(f"Worktree creation failed: {e}. Attempting recovery...", file=sys.stderr)
            
            # Check if branch exists
            if self._branch_exists(branch_name):
                 cmd = ["git", "worktree", "add", str(worktree_path), branch_name]
                 subprocess.run(cmd, cwd=self.repo_root, check=True)
            else:
                 raise e

        return worktree_path

    def _branch_exists(self, branch_name):
        res = subprocess.run(
            ["git", "rev-parse", "--verify", branch_name], 
            cwd=self.repo_root, 
            capture_output=True
        )
        return res.returncode == 0

    def nuke_worktree(self, task_id):
        """Removes the worktree and deletes the branch."""
        worktree_path = self.polecats_dir / task_id
        branch_name = f"polecat/{task_id}"

        if worktree_path.exists():
            print(f"Removing worktree {worktree_path}...")
            # git worktree remove --force <path>
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=self.repo_root,
                check=False 
            )
            # Just in case git leaves folders
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
        
        if self._branch_exists(branch_name):
            print(f"Deleting branch {branch_name}...")
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.repo_root,
                check=False
            )
