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
        """Scans for tasks in MERGE_READY status and attempts to merge them."""
        tasks = self.storage.list_tasks(status=TaskStatus.MERGE_READY)

        if not tasks:
            print("No tasks in MERGE_READY status.")
            return

        print(f"Found {len(tasks)} tasks awaiting merge.")

        for task in tasks:
            print(f"\nProcessing {task.id}: {task.title}")
            try:
                self.process_merge(task)
            except Exception as e:
                print(f"  ❌ Merge failed: {e}")
                self.handle_failure(task, str(e))

    def process_merge(self, task):
        repo_path = self.polecat_mgr.get_repo_path(task)

        if not repo_path.exists():
            raise FileNotFoundError(f"Repo not found at {repo_path}")

        # 0. Pre-flight checks
        if self._is_dirty(repo_path):
            raise RuntimeError(
                f"Repository has uncommitted changes. Run:\n"
                f"  cd {repo_path} && git stash"
            )

        # Set status to REVIEW for manual/agent intervention
        print(f"  Setting status to REVIEW for critic review...")
        task.status = TaskStatus.REVIEW
        self.storage.save_task(task)
        print("  ✅ Task moved to REVIEW queue.")

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
