#!/usr/bin/env python3
"""
Automated Test Harness for AcademicOps Framework.

This script orchestrates end-to-end framework tests by:
1. Optionally creating a test task OR pulling one from the stack.
2. Executing 'polecat run' in headless mode to spawn an agent (Gemini or Claude).
3. Monitoring execution and verifying the resulting transcript.
"""

import argparse
import logging
import re
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
    from lib.paths import get_sessions_dir
    from lib.task_model import TaskStatus, TaskType
    from lib.task_storage import TaskStorage
except ImportError as e:
    logger.error(f"Failed to import framework libs: {e}")
    logger.info("Tip: Try running with 'uv run scripts/automated_test_harness.py'")
    sys.exit(1)


class TestHarness:
    def __init__(self):
        self.storage = TaskStorage()
        self.task_id = None
        self.created_task = False

    def create_task(self, title: str, instructions: str) -> str:
        """Create a new test task."""
        logger.info(f"Creating test task: {title}")

        task = self.storage.create_task(
            title=f"TEST: {title}",
            type=TaskType.GOAL,
            status=TaskStatus.ACTIVE,
            project="aops",
            body=f"{instructions}\n\n<!-- automated-test-harness -->",
            assignee="bot",
        )
        self.storage.save_task(task)
        self.task_id = task.id
        self.created_task = True
        logger.info(f"Task created: {task.id}")
        return task.id

    def run_agent(self, agent_type: str = "gemini", timeout: int = 300) -> bool:
        """Run polecat in headless mode."""

        cmd = [
            "uv",
            "run",
            str(POLECAT_CLI),
            "run",
            "--no-auto-finish",  # Don't push/PR
        ]

        if agent_type == "gemini":
            cmd.append("--gemini")
        # Claude is default in polecat if --gemini is not present

        if self.task_id:
            logger.info(f"Starting polecat run ({agent_type}) for task {self.task_id}...")
            cmd.extend(["-t", self.task_id])
        else:
            logger.info(f"Starting polecat run ({agent_type}) (pulling from stack)...")

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
                        self._parse_output_for_id(out)
                    if err:
                        print(err, end="", file=sys.stderr)
                except subprocess.TimeoutExpired:
                    continue

            # Flush remaining output
            out, err = process.communicate()
            if out:
                print(out, end="")
                self._parse_output_for_id(out)
            if err:
                print(err, end="", file=sys.stderr)

            if process.returncode != 0:
                logger.error(f"Polecat failed with exit code {process.returncode}")
                return False

            logger.info("Agent execution completed successfully.")
            return True

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return False

    def _parse_output_for_id(self, output: str):
        """Parse polecat output to find the claimed Task ID."""
        if self.task_id:
            return

        # Look for "🎯 Task: Title (ID)"
        # Regex: 🎯 Task: .* \((.*)\)
        match = re.search(r"🎯 Task: .* \((.*)\)", output)
        if match:
            found_id = match.group(1)
            logger.info(f"Identified Task ID from output: {found_id}")
            self.task_id = found_id

    def verify_transcript(self, agent_type: str = "gemini", min_entries: int = 5) -> bool:
        """Verify that a transcript was generated and contains expected content."""
        logger.info(f"Verifying transcript generation for {agent_type}...")

        # Note: Both Gemini (via aops) and Claude (via polecat logic) currently depend on similar paths
        # but exact location might vary if configured differently.
        # We start with the known location.
        sessions_dir = get_sessions_dir() / "claude"
        today_str = datetime.now().strftime("%Y%m%d")

        candidates = list(sessions_dir.glob(f"{today_str}*-session-*.md"))

        if not candidates:
            logger.error(f"No transcripts found for today ({today_str}) in {sessions_dir}")
            return False

        latest = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        logger.info(f"Checking latest transcript: {latest.name}")

        content = latest.read_text(encoding="utf-8")

        if self.task_id and self.task_id in content:
            logger.info(f"Found task ID {self.task_id} in transcript.")
        elif "TEST:" in content:
            logger.info("Found task title 'TEST:' in transcript.")
        else:
            logger.warning("Transcript might not be for this task (Title/ID not explicitly found).")

        if len(content.splitlines()) < min_entries:
            logger.error("Transcript is too short.")
            return False

        logger.info("Transcript verification passed.")
        return True

    def cleanup(self):
        """Clean up the worktree (and task if we created it)."""
        if self.task_id:
            logger.info(f"Cleaning up worktree for {self.task_id}...")
            try:
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
    parser.add_argument("--create", help="Create a test task with these instructions")
    parser.add_argument("--task-id", help="Run specific Task ID")
    parser.add_argument("--keep", action="store_true", help="Keep execution artifacts")
    parser.add_argument(
        "--agent", choices=["gemini", "claude"], default="gemini", help="Agent to test"
    )
    args = parser.parse_args()

    harness = TestHarness()

    # Safety: If pulling from stack (real work) or using existing ID, default keep=True
    if not args.create:
        if not args.keep:
            logger.info("Running real/existing task: Defaulting to --keep (preserving worktree)")
            args.keep = True

    try:
        # 1. Setup
        if args.create:
            harness.create_task("Test Task", args.create)
        elif args.task_id:
            harness.task_id = args.task_id
            logger.info(f"Using specified task: {args.task_id}")
        else:
            logger.info("No task specified. Will pull from stack.")

        # 2. Run
        success = harness.run_agent(agent_type=args.agent)
        if not success:
            sys.exit(1)

        # 3. Verify
        # Wait for transcripts
        time.sleep(2)
        if not harness.verify_transcript(agent_type=args.agent):
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
