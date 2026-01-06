"""E2E demo tests for PreToolUse criteria_gate hook.

Run with: uv run pytest tests/integration/test_criteria_gate_e2e.py -k demo -v -s -n 0

These tests print FULL UNTRUNCATED output for human validation (H37a).
Tests use REAL framework scenarios (H37b), not contrived examples.

Tests verify the hook blocks Edit/Write/Bash operations until
the criteria gate has been passed (gate file exists).

NOTE: These tests use default permission mode (not bypassPermissions) because
bypassPermissions appears to also bypass PreToolUse hooks.
"""

import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.integration.conftest import extract_response_text


@pytest.fixture
def claude_test(claude_headless):
    """Fixture providing claude_headless with default test settings.

    Uses longer timeout and NO bypassPermissions (so hooks run).
    """

    def _run(prompt: str, cwd: Path | None = None):
        return claude_headless(
            prompt=prompt,
            model="haiku",
            timeout_seconds=180,
            # Don't use bypassPermissions - we need hooks to run
            cwd=cwd,
        )

    return _run


@pytest.fixture
def temp_repo():
    """Fixture providing a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir)
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        (repo_dir / "test.txt").write_text("test")
        subprocess.run(
            ["git", "add", "."], cwd=repo_dir, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo_dir,
            capture_output=True,
            check=True,
        )
        yield repo_dir


def print_demo_header(title: str) -> None:
    """Print a demo section header."""
    print("\n" + "=" * 80)
    print(f"CRITERIA GATE DEMO - {title}")
    print("=" * 80)


def print_validation_results(checks: dict[str, bool]) -> bool:
    """Print validation results and return whether all passed."""
    print("\n--- STRUCTURAL VALIDATION ---")
    all_passed = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")
        if not passed:
            all_passed = False
    print("=" * 80)
    return all_passed


@pytest.mark.demo
@pytest.mark.slow
@pytest.mark.integration
class TestCriteriaGateDemo:
    """Demo tests showing criteria gate blocking behavior.

    Run with: uv run pytest tests/integration/test_criteria_gate_e2e.py -k demo -v -s -n 0

    These tests print FULL UNTRUNCATED output for human validation (H37a).
    Uses REAL framework scenarios (H37b).
    """

    def test_demo_blocks_edit_without_gate(self, claude_test) -> None:
        """Demo: Edit tool blocked without criteria gate.

        REAL SCENARIO: Agent tries to edit a framework file without
        first defining acceptance criteria. Gate should block.

        Per H37a: Shows FULL response for human validation.
        Per H37b: Uses real framework editing scenario.
        """
        print_demo_header("EDIT BLOCKED WITHOUT GATE (H37a/H37b)")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file simulating a framework component
            target_file = Path(tmpdir) / "CLAUDE.md"
            target_file.write_text(
                "# Component Instructions\n\nOriginal content here.\n"
            )

            # REAL framework prompt - editing component instructions
            prompt = (
                f"Edit the file at {target_file} to add a new section "
                "'## Testing Requirements' with content about running pytest."
            )

            print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
            print(f"\nTarget file: {target_file}")
            print(f"Original content:\n{target_file.read_text()}")
            print("\nExecuting headless session...")

            result = claude_test(prompt=prompt, cwd=Path(tmpdir))

            print(f"\nExecution success: {result['success']}")

            if not result["success"]:
                print(f"Error: {result.get('error')}")

            # Show FULL response - no truncation (H37a)
            print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
            try:
                response = extract_response_text(result)
                print(response)
            except (ValueError, TypeError) as e:
                print(f"Could not extract response: {e}")
                response = ""
            print("\n--- END RESPONSE ---\n")

            # Show file state after attempt
            final_content = target_file.read_text()
            print(f"File content AFTER attempt:\n{final_content}")

            # Structural validation with visible checks
            response_lower = response.lower()
            checks = {
                "Execution completed": result["success"],
                "File unchanged (edit blocked)": "Original content" in final_content,
                "Response mentions 'blocked' or 'criteria'": (
                    "blocked" in response_lower or "criteria" in response_lower
                ),
                "Response mentions workflow requirements": any(
                    term in response_lower
                    for term in ["acceptance", "todowrite", "checkpoint", "gate"]
                ),
            }

            all_passed = print_validation_results(checks)
            assert all_passed, "Gate did not block edit as expected - see output above"

    def test_demo_blocks_write_without_gate(self, claude_test) -> None:
        """Demo: Write tool blocked without criteria gate.

        REAL SCENARIO: Agent tries to create a new test file without
        first defining acceptance criteria. Gate should block.

        Per H37a: Shows FULL response for human validation.
        Per H37b: Uses real test file creation scenario.
        """
        print_demo_header("WRITE BLOCKED WITHOUT GATE (H37a/H37b)")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "test_new_feature.py"

            # REAL framework prompt - creating a test file
            prompt = (
                f"Create a new pytest test file at {target_file} with a test "
                "function test_feature_works() that asserts True."
            )

            print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
            print(f"\nTarget file: {target_file}")
            print(f"File exists before: {target_file.exists()}")
            print("\nExecuting headless session...")

            result = claude_test(prompt=prompt, cwd=Path(tmpdir))

            print(f"\nExecution success: {result['success']}")

            if not result["success"]:
                print(f"Error: {result.get('error')}")

            # Show FULL response - no truncation (H37a)
            print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
            try:
                response = extract_response_text(result)
                print(response)
            except (ValueError, TypeError) as e:
                print(f"Could not extract response: {e}")
                response = ""
            print("\n--- END RESPONSE ---\n")

            # Show file state after attempt
            file_exists = target_file.exists()
            print(f"File exists AFTER attempt: {file_exists}")
            if file_exists:
                print(f"File content:\n{target_file.read_text()}")

            # Structural validation with visible checks
            response_lower = response.lower()
            checks = {
                "Execution completed": result["success"],
                "File NOT created (write blocked)": not file_exists,
                "Response mentions 'blocked' or 'criteria'": (
                    "blocked" in response_lower or "criteria" in response_lower
                ),
                "Response mentions workflow requirements": any(
                    term in response_lower
                    for term in ["acceptance", "todowrite", "checkpoint", "gate"]
                ),
            }

            all_passed = print_validation_results(checks)
            assert all_passed, "Gate did not block write as expected - see output above"

    def test_demo_blocks_destructive_bash_without_gate(
        self, claude_test, temp_repo
    ) -> None:
        """Demo: Destructive Bash commands blocked without criteria gate.

        REAL SCENARIO: Agent tries to run rm command without
        first defining acceptance criteria. Gate should block.

        Per H37a: Shows FULL response for human validation.
        Per H37b: Uses real file deletion scenario.
        """
        print_demo_header("DESTRUCTIVE BASH BLOCKED WITHOUT GATE (H37a/H37b)")

        # Create a file to potentially delete
        target_file = temp_repo / "important_data.json"
        target_file.write_text('{"important": "data"}')

        # REAL framework prompt - attempting file deletion
        prompt = f"Run this bash command to clean up: rm {target_file}"

        print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
        print(f"\nTarget file: {target_file}")
        print(f"File exists before: {target_file.exists()}")
        print(f"File content: {target_file.read_text()}")
        print("\nExecuting headless session...")

        result = claude_test(prompt=prompt, cwd=temp_repo)

        print(f"\nExecution success: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        # Show FULL response - no truncation (H37a)
        print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
        try:
            response = extract_response_text(result)
            print(response)
        except (ValueError, TypeError) as e:
            print(f"Could not extract response: {e}")
            response = ""
        print("\n--- END RESPONSE ---\n")

        # Show file state after attempt
        file_exists = target_file.exists()
        print(f"File exists AFTER attempt: {file_exists}")

        # Structural validation with visible checks
        response_lower = response.lower()
        checks = {
            "Execution completed": result["success"],
            "File still exists (rm blocked)": file_exists,
            "Response mentions 'blocked' or 'criteria'": (
                "blocked" in response_lower or "criteria" in response_lower
            ),
        }

        all_passed = print_validation_results(checks)
        assert all_passed, "Gate did not block rm as expected - see output above"

    def test_demo_allows_readonly_bash_without_gate(
        self, claude_test, temp_repo
    ) -> None:
        """Demo: Read-only Bash commands allowed without criteria gate.

        REAL SCENARIO: Agent runs git status to check repository state.
        This is in the allowlist and should NOT be blocked.

        Per H37a: Shows FULL response for human validation.
        Per H37b: Uses real git workflow scenario.
        """
        print_demo_header("READ-ONLY BASH ALLOWED WITHOUT GATE (H37a/H37b)")

        # REAL framework prompt - checking git status (common workflow)
        prompt = "Run 'git status' to check the repository state and tell me what you see."

        print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
        print(f"\nRepository: {temp_repo}")
        print("\nExecuting headless session...")

        result = claude_test(prompt=prompt, cwd=temp_repo)

        print(f"\nExecution success: {result['success']}")

        if not result["success"]:
            print(f"Error: {result.get('error')}")

        # Show FULL response - no truncation (H37a)
        print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
        try:
            response = extract_response_text(result)
            print(response)
        except (ValueError, TypeError) as e:
            print(f"Could not extract response: {e}")
            response = ""
        print("\n--- END RESPONSE ---\n")

        # Structural validation with visible checks
        response_lower = response.lower()
        checks = {
            "Execution completed": result["success"],
            "Response contains git output": any(
                term in response_lower
                for term in ["branch", "commit", "nothing to commit", "clean", "main", "master"]
            ),
            "Response NOT blocked": "blocked" not in response_lower,
            "No criteria gate mention": "criteria gate" not in response_lower,
        }

        all_passed = print_validation_results(checks)
        assert all_passed, "Git status was unexpectedly blocked - see output above"

    def test_demo_allows_ls_without_gate(self, claude_test) -> None:
        """Demo: ls command allowed without criteria gate.

        REAL SCENARIO: Agent lists directory contents for exploration.
        This is in the allowlist and should NOT be blocked.

        Per H37a: Shows FULL response for human validation.
        Per H37b: Uses real directory exploration scenario.
        """
        print_demo_header("LS COMMAND ALLOWED WITHOUT GATE (H37a/H37b)")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files simulating a project structure
            (Path(tmpdir) / "CLAUDE.md").write_text("# Instructions")
            (Path(tmpdir) / "pyproject.toml").write_text("[project]")
            (Path(tmpdir) / "src").mkdir()
            (Path(tmpdir) / "tests").mkdir()

            # REAL framework prompt - exploring project structure
            prompt = "Run 'ls -la' to see what files are in this directory."

            print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
            print(f"\nDirectory: {tmpdir}")
            print("\nExecuting headless session...")

            result = claude_test(prompt=prompt, cwd=Path(tmpdir))

            print(f"\nExecution success: {result['success']}")

            if not result["success"]:
                print(f"Error: {result.get('error')}")

            # Show FULL response - no truncation (H37a)
            print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
            try:
                response = extract_response_text(result)
                print(response)
            except (ValueError, TypeError) as e:
                print(f"Could not extract response: {e}")
                response = ""
            print("\n--- END RESPONSE ---\n")

            # Structural validation with visible checks
            response_lower = response.lower()
            checks = {
                "Execution completed": result["success"],
                "Response contains file listing": any(
                    term in response_lower
                    for term in ["claude.md", "pyproject", "src", "tests", "total"]
                ),
                "Response NOT blocked": "blocked" not in response_lower,
                "No criteria gate mention": "criteria gate" not in response_lower,
            }

            all_passed = print_validation_results(checks)
            assert all_passed, "ls was unexpectedly blocked - see output above"

    def test_demo_gate_message_content(self, claude_test) -> None:
        """Demo: Gate block message includes helpful instructions.

        REAL SCENARIO: When gate blocks, the message should tell the agent
        what steps are needed to proceed (acceptance criteria workflow).

        Per H37a: Shows FULL block message for human validation.
        Per H37b: Validates the workflow instructions are present.
        """
        print_demo_header("GATE BLOCK MESSAGE CONTENT (H37a/H37b)")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "new_hook.py"

            # REAL framework prompt - creating a hook file
            prompt = (
                f"Create a new PreToolUse hook at {target_file} that blocks "
                "all Write operations to the /etc directory."
            )

            print(f"\nPrompt (REAL FRAMEWORK TASK):\n{prompt}")
            print(f"\nTarget file: {target_file}")
            print("\nExecuting headless session...")

            result = claude_test(prompt=prompt, cwd=Path(tmpdir))

            print(f"\nExecution success: {result['success']}")

            if not result["success"]:
                print(f"Error: {result.get('error')}")

            # Show FULL response - no truncation (H37a)
            print("\n--- FULL CLAUDE RESPONSE (NO TRUNCATION) ---\n")
            try:
                response = extract_response_text(result)
                print(response)
            except (ValueError, TypeError) as e:
                print(f"Could not extract response: {e}")
                response = ""
            print("\n--- END RESPONSE ---\n")

            # Structural validation - check block message content
            response_lower = response.lower()
            checks = {
                "Execution completed": result["success"],
                "Response mentions blocking": (
                    "blocked" in response_lower or "cannot" in response_lower
                ),
                "Mentions acceptance criteria": "acceptance" in response_lower or "criteria" in response_lower,
                "Mentions TodoWrite or checkpoint": (
                    "todowrite" in response_lower or "checkpoint" in response_lower
                ),
                "Mentions gate or workflow": (
                    "gate" in response_lower or "workflow" in response_lower or "/do" in response_lower
                ),
            }

            all_passed = print_validation_results(checks)
            # Note: This test validates message quality, not blocking behavior
            # It's OK if not all message elements are present, but we should see most
            passed_count = sum(1 for v in checks.values() if v)
            assert passed_count >= 3, (
                f"Block message missing key elements ({passed_count}/5 checks passed) - "
                "see output above"
            )
