#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add aops-core to path
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

try:
    from lib.task_model import TaskStatus
    from lib.task_storage import TaskStorage
    from manager import PolecatManager
except ImportError:
    pass

class Engineer:
    def __init__(self):
        self.storage = TaskStorage()
        self.polecat_mgr = PolecatManager()

    def scan_and_merge(self):
        """Scans for tasks in REVIEW status and attempts to merge them."""
        # Only process tasks assigned to 'refinery' (the automated bot) or unassigned
        # Tasks assigned to 'engineer' are waiting for human/LLM intervention
        tasks = self.storage.list_tasks(status=TaskStatus.REVIEW)
        
        if not tasks:
            print("No tasks in REVIEW status.")
            return

        to_process = [t for t in tasks if t.assignee in (None, "refinery", "")]
        print(f"Found {len(to_process)} tasks awaiting merge (skipping {len(tasks)-len(to_process)} assigned to engineer).")

        for task in to_process:
            print(f"\nProcessing {task.id}: {task.title}")
            try:
                self.process_merge(task)
            except Exception as e:
                print(f"  ❌ Merge failed: {e}")
                self.handle_failure(task, str(e))

    def process_merge(self, task):
        repo_path = self.polecat_mgr.get_repo_path(task)
        branch_name = f"polecat/{task.id}"
        target_branch = "main"

        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found at {repo_path}")

        # 1. Fetch & Verify
        print(f"  Fetching in {repo_path}...")
        self._run_git(repo_path, ["fetch", "origin"])

        remote_branch = f"origin/{branch_name}"
        if not self._branch_exists(repo_path, remote_branch) and not self._branch_exists(repo_path, branch_name):
             raise ValueError(f"Branch {branch_name} not found locally or on origin")

        # 2. Checkout Target
        print(f"  Updating {target_branch}...")
        self._run_git(repo_path, ["checkout", target_branch])
        self._run_git(repo_path, ["pull", "origin", target_branch])

        # 3. Squash Merge (Dry Run)
        print(f"  Attempting squash merge of {branch_name}...")
        try:
            self._run_git(repo_path, ["merge", "--squash", branch_name])
        except subprocess.CalledProcessError:
            self._run_git(repo_path, ["merge", "--abort"])
            raise RuntimeError("Merge conflicts detected")

        # 4. Run Tests
        test_cmd = ["uv", "run", "pytest"] if (repo_path / "pyproject.toml").exists() else ["echo", "No tests configured"]
        print(f"  Running tests: {' '.join(test_cmd)}")
        try:
            # Capture output to log on failure
            subprocess.run(test_cmd, cwd=repo_path, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            self._run_git(repo_path, ["reset", "--hard", "HEAD"])
            # Include stdout/stderr in error message
            raise RuntimeError(f"Tests failed:\n{e.stdout.decode()}\n{e.stderr.decode()}")

        # 5. Commit & Push
        print("  Committing and Pushing...")
        commit_msg = f"Merge {branch_name}: {task.title} ({task.id})"
        self._run_git(repo_path, ["commit", "-m", commit_msg])
        self._run_git(repo_path, ["push", "origin", target_branch])

        # 6. Cleanup Branches
        print("  Cleaning up branch...")
        self._run_git(repo_path, ["branch", "-D", branch_name], check=False)
        self._run_git(repo_path, ["push", "origin", "--delete", branch_name], check=False)

        # 7. Update Task (Success)
        print("  Marking task as DONE...")
        task.status = TaskStatus.DONE
        self.storage.save_task(task)
        
        # 8. Nuke Worktree
        self.polecat_mgr.nuke_worktree(task.id)
        print("  ✅ Merge Complete.")

    def handle_failure(self, task, error_msg):
        """Kickback workflow: Assign to 'engineer' for manual review."""
        print("  ↪ Kickback: Assigning to 'engineer' for review.")
        
        task.status = TaskStatus.REVIEW
        task.assignee = "engineer"
        
        # Append report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = f"\n\n## 🏭 Refinery Report ({timestamp})\n"
        report += f"**❌ Merge Failed**\n\n"
        report += f"```\n{error_msg}\n```\n"
        report += "Assigned to `engineer` for manual intervention."
        
        task.body += report
        self.storage.save_task(task)

    def _run_git(self, cwd, args, check=True):
        cmd = ["git"] + args
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True)

    def _branch_exists(self, cwd, branch):
        res = self._run_git(cwd, ["rev-parse", "--verify", branch], check=False)
        return res.returncode == 0
