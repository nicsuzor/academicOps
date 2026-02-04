#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add aops-core and polecat to path for imports
SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "aops-core"))
sys.path.insert(0, str(REPO_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

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
        """Scans for tasks in MERGE_READY status and attempts to merge them.

        Uses MERGING status as a merge slot - only one task can be merging at a time.
        This serializes merges to prevent conflicts and ensure orderly integration.

        Also reconciles orphaned MERGING tasks (from manual merges or interrupted processes).
        """
        # First, reconcile any orphaned MERGING tasks
        self._reconcile_merging_tasks()

        # Check if another task is already merging (merge slot occupied)
        merging_tasks = self.storage.list_tasks(status=TaskStatus.MERGING)
        if merging_tasks:
            print(f"Merge slot occupied by {merging_tasks[0].id}. Waiting for it to complete.")
            return

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
            # Only process one task per scan (merge slot pattern)
            # Next task will be picked up on subsequent scan
            break

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

        # 3. Squash Merge (with auto-rebase on conflict)
        print(f"  Attempting squash merge of {branch_name}...")
        try:
            self._run_git(repo_path, ["merge", "--squash", branch_name])
        except subprocess.CalledProcessError:
            # Capture conflict details before abort
            conflict_files = self._get_conflict_files(repo_path)
            self._run_git(repo_path, ["merge", "--abort"])
            print(f"  Merge conflict detected in: {', '.join(conflict_files)}")
            print("  Attempting auto-rebase...")

            # Attempt auto-rebase before escalating
            rebase_result = self._attempt_rebase(repo_path, branch_name, target_branch)
            if rebase_result["success"]:
                print("  Rebase succeeded. Retrying merge...")
                try:
                    self._run_git(repo_path, ["merge", "--squash", branch_name])
                except subprocess.CalledProcessError:
                    # Capture conflict details before abort
                    conflict_files = self._get_conflict_files(repo_path)
                    self._run_git(repo_path, ["merge", "--abort"])
                    raise RuntimeError(
                        "Merge conflicts persist after rebase.\n"
                        f"Branch: {branch_name}\n"
                        f"Conflicting files: {', '.join(conflict_files)}\n"
                        "Manual resolution required."
                    )
            else:
                raise RuntimeError(rebase_result["error"])

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

    def _attempt_rebase(self, repo_path, branch_name, target_branch):
        """Attempt to rebase the polecat branch onto target before escalating merge conflicts.

        Returns:
            dict with keys:
            - success: bool
            - error: str (structured error message if failed)
        """
        try:
            # Checkout the polecat branch
            self._run_git(repo_path, ["checkout", branch_name])

            # Attempt rebase onto target
            self._run_git(repo_path, ["rebase", target_branch])

            # Push the rebased branch (force required after rebase)
            self._run_git(repo_path, ["push", "--force-with-lease", "origin", branch_name])

            # Return to target branch for merge retry
            self._run_git(repo_path, ["checkout", target_branch])

            return {"success": True, "error": None}

        except subprocess.CalledProcessError as e:
            # Get conflicting files for structured error
            conflicting_files = self._get_conflict_files(repo_path)

            # Abort the failed rebase
            self._run_git(repo_path, ["rebase", "--abort"], check=False)

            # Return to target branch
            self._run_git(repo_path, ["checkout", target_branch], check=False)

            # Build structured error message
            error_lines = [
                "Auto-rebase failed. Manual resolution required.",
                "",
                f"**Branch**: `{branch_name}`",
                f"**Target**: `{target_branch}`",
                "",
                "**Conflicting files**:",
            ]
            for f in conflicting_files:
                error_lines.append(f"- `{f}`")

            if e.stderr:
                error_lines.extend([
                    "",
                    "**Rebase error**:",
                    f"```\n{e.stderr.decode().strip()}\n```",
                ])

            error_lines.extend([
                "",
                "**Suggested resolution steps**:",
                f"1. `cd {repo_path}`",
                f"2. `git checkout {branch_name}`",
                f"3. `git rebase {target_branch}`",
                "4. Resolve conflicts in each file",
                "5. `git add <resolved-files>`",
                "6. `git rebase --continue`",
                f"7. `git push --force-with-lease origin {branch_name}`",
                "8. Re-run merge: `polecat merge <task-id>`",
            ])

            return {"success": False, "error": "\n".join(error_lines)}

    def _get_conflict_files(self, repo_path):
        """Get list of files with merge/rebase conflicts."""
        res = self._run_git(repo_path, ["diff", "--name-only", "--diff-filter=U"], check=False)
        if res.returncode == 0 and res.stdout:
            return res.stdout.decode().strip().split("\n")
        return ["(unable to determine conflicting files)"]

    def _reconcile_merging_tasks(self):
        """Reconcile tasks stuck in MERGING status.

        This handles cases where:
        1. Manual git merge was performed (bypassing refinery)
        2. Process was interrupted after merge but before status update
        3. Branch was deleted but task status wasn't updated

        For each MERGING task:
        - If branch doesn't exist → mark DONE (merge happened externally)
        - If branch exists and is merged → mark DONE + delete branch
        - If branch exists and not merged → leave as MERGING (needs investigation)
        """
        merging_tasks = self.storage.list_tasks(status=TaskStatus.MERGING)
        if not merging_tasks:
            return

        print(f"Reconciling {len(merging_tasks)} task(s) in MERGING status...")

        for task in merging_tasks:
            branch_name = f"polecat/{task.id}"
            try:
                repo_path = self.polecat_mgr.get_repo_path(task)
            except Exception:
                repo_path = REPO_ROOT

            # Fetch latest to ensure accurate branch state
            self._run_git(repo_path, ["fetch", "origin"], check=False)

            local_exists = self._branch_exists(repo_path, branch_name)
            remote_exists = self._branch_exists(repo_path, f"origin/{branch_name}")

            if not local_exists and not remote_exists:
                # Branch is gone - assume merge happened externally
                print(f"  {task.id}: Branch gone → marking DONE")
                task.status = TaskStatus.DONE
                task.body += f"\n\n## Reconciled ({datetime.now().strftime('%Y-%m-%d %H:%M')})\nBranch deleted externally. Marked done by reconciliation."
                self.storage.save_task(task)
                self.polecat_mgr.nuke_worktree(task.id, force=True)
                continue

            # Branch exists - check if it's merged (use whichever ref exists)
            check_ref = branch_name if local_exists else f"origin/{branch_name}"
            is_merged = self.polecat_mgr._is_branch_merged(repo_path, check_ref, target="main")

            if is_merged:
                # Branch is merged but cleanup didn't happen
                print(f"  {task.id}: Branch merged → cleaning up + marking DONE")
                self._run_git(repo_path, ["branch", "-D", branch_name], check=False)
                self._run_git(repo_path, ["push", "origin", "--delete", branch_name], check=False)
                task.status = TaskStatus.DONE
                task.body += f"\n\n## Reconciled ({datetime.now().strftime('%Y-%m-%d %H:%M')})\nBranch was merged but cleanup incomplete. Completed by reconciliation."
                self.storage.save_task(task)
                self.polecat_mgr.nuke_worktree(task.id, force=True)
            else:
                # Branch exists but not merged - something is wrong
                print(f"  {task.id}: Branch exists but NOT merged → leaving for investigation")
