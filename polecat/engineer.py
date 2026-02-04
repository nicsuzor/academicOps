#!/usr/bin/env python3
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add aops-core to path
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

from observability import metrics

try:
    from lib.task_model import TaskStatus
    from lib.task_storage import TaskStorage
    from manager import PolecatManager
except ImportError as e:
    # These imports may fail when running outside academicOps context
    # but are required for actual operation
    raise ImportError(f"Required task management modules not found: {e}") from e

class Engineer:
    def __init__(self):
        self.storage = TaskStorage()
        self.polecat_mgr = PolecatManager()

    def scan_and_merge(self):
        """Scans for tasks in MERGE_READY status and attempts to merge them.

        Uses MERGING status as a merge slot - only one task can be merging at a time.
        This serializes merges to prevent conflicts and ensure orderly integration.
        """
        # Check if another task is already merging (merge slot occupied)
        merging_tasks = self.storage.list_tasks(status=TaskStatus.MERGING)
        if merging_tasks:
            print(f"Merge slot occupied by {merging_tasks[0].id}. Waiting for it to complete.")
            metrics.record_queue_depth("merging", count=len(merging_tasks))
            return

        tasks = self.storage.list_tasks(status=TaskStatus.MERGE_READY)

        # Record merge queue depth
        metrics.record_queue_depth("merge_ready", count=len(tasks))

        if not tasks:
            print("No tasks in MERGE_READY status.")
            return

        print(f"Found {len(tasks)} tasks awaiting merge.")

        for task in tasks:
            print(f"\nProcessing {task.id}: {task.title}")
            start_time = time.perf_counter()
            try:
                self.process_merge(task)
                duration_ms = (time.perf_counter() - start_time) * 1000
                metrics.record_merge_attempt(
                    task_id=task.id,
                    success=True,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                print(f"  ❌ Merge failed: {e}")
                failure_reason = self._categorize_merge_failure(str(e))
                metrics.record_merge_attempt(
                    task_id=task.id,
                    success=False,
                    duration_ms=duration_ms,
                    failure_reason=failure_reason,
                )
                self.handle_failure(task, str(e))
            # Only process one task per scan (merge slot pattern)
            # Next task will be picked up on subsequent scan
            break

    def _categorize_merge_failure(self, error_message: str) -> str:
        """Categorize merge failure reason from error message."""
        error_lower = error_message.lower()
        if "conflict" in error_lower:
            return "conflicts"
        if "test" in error_lower:
            return "tests_failed"
        if "uncommitted" in error_lower:
            return "dirty_worktree"
        if "dirty" in error_lower:
            return "dirty_worktree"
        return "other"

    def process_merge(self, task):
        """Process a single task merge.

        Status transitions:
        - merge_ready → merging (claim merge slot)
        - merging → done (on success)
        - merging → review (on failure, via handle_failure)
        """
        # Claim merge slot by transitioning to MERGING
        print(f"  Claiming merge slot...")
        task.status = TaskStatus.MERGING
        self.storage.save_task(task)

        repo_path = self.polecat_mgr.get_repo_path(task)
        branch_name = f"polecat/{task.id}"
        target_branch = "main"

        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found at {repo_path}")

        # 0. Pre-flight checks
        if self._is_dirty(repo_path):
            raise RuntimeError(
                f"Repository has uncommitted changes. Run:\n"
                f"  cd {repo_path} && git stash"
            )

        # 1. Fetch & Verify
        print(f"  Fetching in {repo_path}...")
        self._run_git(repo_path, ["fetch", "origin"])

        unpushed = self._get_unpushed_count(repo_path, target_branch)
        if unpushed > 0:
            raise RuntimeError(
                f"Main branch has {unpushed} unpushed commits. Run:\n"
                f"  cd {repo_path} && git push origin {target_branch}"
            )

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
        if not (repo_path / "pyproject.toml").exists():
            raise RuntimeError(
                f"No test configuration found. Expected pyproject.toml at {repo_path}. "
                f"Merge verification requires a test suite."
            )
        test_cmd = ["uv", "run", "pytest"]
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
        """Kickback workflow: Set status to review for human intervention."""
        print("  ↪ Kickback: Setting status to REVIEW.")

        task.status = TaskStatus.REVIEW

        # Append report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        report = f"\n\n## 🏭 Refinery Report ({timestamp})\n"
        report += f"**❌ Merge Failed**\n\n"
        report += f"```\n{error_msg}\n```\n"
        report += "Status set to `review` for manual intervention."

        task.body += report
        self.storage.save_task(task)

    def _run_git(self, cwd, args, check=True):
        cmd = ["git"] + args
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True)

    def _branch_exists(self, cwd, branch):
        res = self._run_git(cwd, ["rev-parse", "--verify", branch], check=False)
        return res.returncode == 0

    def _is_dirty(self, cwd):
        """Check if working directory has uncommitted changes."""
        res = self._run_git(cwd, ["status", "--porcelain"], check=False)
        return bool(res.stdout.decode().strip())

    def _get_unpushed_count(self, cwd, branch="main"):
        """Count commits ahead of origin."""
        res = self._run_git(cwd, ["rev-list", "--count", f"origin/{branch}..{branch}"], check=False)
        if res.returncode == 0:
            return int(res.stdout.decode().strip())
        return 0
