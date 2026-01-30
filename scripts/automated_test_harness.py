#!/usr/bin/env python3
"""
Automated Test Harness for AcademicOps Framework.

This script orchestrates end-to-end framework tests by:
1. Creating a test task via TaskManager.
2. Executing 'polecat run' in headless mode to spawn an agent.
3. Monitoring execution and verifying the resulting transcript.
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("harness")

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_ROOT = SCRIPT_DIR.parent
AOPS_CORE = AOPS_ROOT / "aops-core"
POLECAT_CLI = AOPS_ROOT / "polecat" / "cli.py"

# Add aops-core to path
sys.path.insert(0, str(AOPS_CORE))

try:
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
    from lib.paths import get_sessions_dir
except ImportError as e:
    logger.error(f"Failed to import framework libs: {e}")
    # We might be running in a bare python env. Verify dependencies.
    logger.info("Tip: Try running with 'uv run scripts/automated_test_harness.py'")
    sys.exit(1)


class TestHarness:
    def __init__(self, target_project="current_project"):
        self.storage = TaskStorage()
        self.project = target_project
        self.task_id = None
        self.worktree_path = None

    def create_task(self, title: str, instructions: str) -> str:
        """Create a new test task."""
        logger.info(f"Creating test task: {title}")

        task = self.storage.create_task(
            title=f"TEST: {title}",
            type=TaskType.TASK,
            status=TaskStatus.ACTIVE,
            project="aops",
            body=f"{instructions}\n\n<!-- automated-test-harness -->",
            assignee="bot",
        )
        self.storage.save_task(task)
        self.task_id = task.id
        logger.info(f"Task created: {task.id}")
        return task.id

    def run_agent(self, timeout: int = 300) -> bool:
        """Run polecat in headless mode."""
        if not self.task_id:
            raise ValueError("No task created")

        logger.info(f"Starting polecat run for task {self.task_id}...")

        # Invoke via via uv run to ensure environment matches user alias
        cmd = [
            "uv",
            "run",
            str(POLECAT_CLI),
            "run",
            "-t",
            self.task_id,
            "--gemini",  # Use Gemini
            "--no-auto-finish",  # Don't push/PR
        ]

        try:
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=AOPS_ROOT,
            )

            stdout_lines = []
            stderr_lines = []

            while True:
                if process.poll() is not None:
                    break

                if time.time() - start_time > timeout:
                    process.terminate()
                    logger.error("Agent timed out!")
                    return False

                try:
                    out, err = process.communicate(timeout=1)
                    if out:
                        print(out, end="")
                        stdout_lines.append(out)
                    if err:
                        print(err, end="", file=sys.stderr)
                        stderr_lines.append(err)
                except subprocess.TimeoutExpired:
                    continue

            if process.returncode != 0:
                logger.error(f"Polecat failed with exit code {process.returncode}")
                return False

            logger.info("Agent execution completed successfully.")
            return True

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return False

    def verify_transcript(self, min_entries: int = 5) -> bool:
        """Verify that a transcript was generated and contains expected content."""
        logger.info("Verifying transcript generation...")

        # Transcript generation matches based on session ID.
        sessions_dir = get_sessions_dir() / "claude"

        # Find files matching the date
        today_str = datetime.now().strftime("%Y%m%d")

        # Match pattern: YYYYMMDD-HH-* or just YYYYMMDD-*
        candidates = list(sessions_dir.glob(f"{today_str}*-session-*.md"))

        if not candidates:
            logger.error(
                f"No transcripts found for today ({today_str}) in {sessions_dir}"
            )
            return False

        # Sort by mtime
        latest = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        logger.info(f"Checking latest transcript: {latest.name}")

        content = latest.read_text(encoding="utf-8")

        if "TEST:" in content:
            logger.info("Found task title 'TEST:' in transcript.")
        elif self.task_id and self.task_id in content:
            logger.info(f"Found task ID {self.task_id} in transcript.")
        else:
            logger.warning(
                "Transcript might not be for this task (Title/ID not explictly found)."
            )

        if len(content.splitlines()) < min_entries:
            logger.error("Transcript is too short.")
            return False

        logger.info("Transcript verification passed.")
        return True

    def cleanup(self):
        """Clean up the test task and worktree."""
        if self.task_id:
            logger.info(f"Cleaning up task {self.task_id}...")
            try:
                # Use subproccess with same python executable
                subprocess.run(
                    [sys.executable, str(POLECAT_CLI), "nuke", self.task_id, "-f"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                logger.warning(f"Failed to nuke worktree: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run automated framework testing.")
    parser.add_argument(
        "--task",
        help="Custom task instructions",
        default="Say hello and list files in current directory.",
    )
    parser.add_argument(
        "--keep", action="store_true", help="Keep execution artifacts (don't cleanup)"
    )
    args = parser.parse_args()

    harness = TestHarness()

    try:
        # 1. Setup
        task_id = harness.create_task("Review Local Files", args.task)

        # 2. Run
        success = harness.run_agent()
        if not success:
            sys.exit(1)

        # 3. Verify
        time.sleep(2)
        if not harness.verify_transcript():
            sys.exit(1)

        logger.info("✅ Test Passed!")

    except KeyboardInterrupt:
        logger.info("Interrupted.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test Loop Failed: {e}")
        sys.exit(1)
    finally:
        if not args.keep:
            harness.cleanup()


if __name__ == "__main__":
    main()
