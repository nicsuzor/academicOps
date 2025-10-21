#!/usr/bin/env python3
"""Fast, extensible code review system for enforcing coding standards.

This module provides a pluggable rule system for automated code review.
Rules are designed to be fast (<1s total) and provide actionable feedback.

Usage:
    # From PreToolUse hook
    from bot.scripts.code_review import review_staged_files
    violations = review_staged_files()

    # Standalone
    python3 .academicOps/scripts/code_review.py --git-staged
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Protocol


@dataclass
class Violation:
    """A code review violation found by a rule."""

    file: Path
    line: int
    rule: str
    message: str
    fix: str


class CodeReviewRule(Protocol):
    """Protocol for code review rules."""

    def check(self, file_path: Path, content: str) -> list[Violation]:
        """Check file content and return list of violations."""
        ...


class EnvironmentVariableRule:
    """Enforce config/fixture usage instead of direct environment variable access.

    This rule catches direct use of os.getenv(), os.environ[], and os.environ.get()
    in test files. Configuration should be loaded via pytest fixtures that read
    from testing.yaml, not directly from environment variables in test code.

    Allowed exceptions:
    - Non-test files (src/, config.py, etc)
    - conftest.py (where fixtures are defined)
    """

    patterns: ClassVar[list[str]] = [
        r"os\.getenv\(",
        r'os\.environ\["',
        r"os\.environ\['",
        r"os\.environ\.get\(",
    ]

    def check(self, file_path: Path, content: str) -> list[Violation]:
        """Check for direct environment variable access in test files."""
        # Only check test files
        path_str = str(file_path)
        if not ("test" in path_str and file_path.suffix == ".py"):
            return []

        # Allow in conftest.py (where fixtures are defined)
        if file_path.name == "conftest.py":
            return []

        violations = []
        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern in self.patterns:
                if re.search(pattern, line):
                    violations.append(
                        Violation(
                            file=file_path,
                            line=line_num,
                            rule="no-direct-env-vars",
                            message="Use testing config/fixtures instead of direct env var access",
                            fix="Create pytest fixture that loads from testing.yaml config",
                        )
                    )
                    break  # Only report once per line

        return violations


class MockUsageRule:
    """Enforce live fixtures instead of mocks for own codebase.

    This rule catches use of Mock() or MagicMock() for buttermilk classes.
    Within our codebase boundaries, we should use live code with test configuration,
    not mocks/fakes. Mocks are only acceptable for external libraries.

    Only applies to: projects/buttermilk/tests/**
    """

    # Buttermilk classes that should not be mocked
    buttermilk_classes: ClassVar[list[str]] = [
        "ZoteroSource",
        "ZoteroDownloadProcessor",
        "ChromaDBEmbeddings",
        "SemanticSplitter",
        # Add more as needed
    ]

    def check(self, file_path: Path, content: str) -> list[Violation]:
        """Check for mock usage on own code."""
        # Only check buttermilk tests
        path_str = str(file_path)
        if "projects/buttermilk/tests" not in path_str:
            return []

        violations = []

        # Check if mocking our own classes
        has_mock = "Mock(" in content or "MagicMock(" in content
        if not has_mock:
            return []

        # Check if any buttermilk classes are mentioned (being mocked)
        for class_name in self.buttermilk_classes:
            if class_name in content:
                # Find approximate line number
                for line_num, line in enumerate(content.split("\n"), 1):
                    if "Mock(" in line or "MagicMock(" in line:
                        violations.append(
                            Violation(
                                file=file_path,
                                line=line_num,
                                rule="no-mocks-for-own-code",
                                message=f"Use live fixtures for {class_name}, not mocks",
                                fix=f"Create pytest fixture that instantiates real {class_name} with test config",
                            )
                        )
                        break  # Only report once per file

        return violations


class TestFileLocationRule:
    """Enforce proper test file locations per academicOps axiom #5.

    Tests must be in project-specific tests/ directories, not /tmp.
    We build infrastructure for long-term replication, not throwaway scripts.

    Required structure:
    - projects/<project>/tests/test_*.py (project-specific tests)
    - bot/tests/test_*.py (framework tests)

    PROHIBITED:
    - /tmp/test_*.py (violates axiom #5: build for replication)
    - Any test file outside a tests/ directory
    """

    def check(self, file_path: Path, _content: str) -> list[Violation]:
        """Check test files are in proper locations."""
        path_str = str(file_path)

        # Only check test files (by name)
        if not ("test" in file_path.name.lower() and file_path.suffix == ".py"):
            return []

        # Check for /tmp violation
        if path_str.startswith("/tmp/"):
            return [
                Violation(
                    file=file_path,
                    line=1,
                    rule="no-tmp-tests",
                    message="/tmp test files violate academicOps axiom #5 (build for replication)",
                    fix="Move to projects/<project>/tests/test_<feature>.py and commit to git",
                )
            ]

        # Check for tests/ directory requirement
        if "/tests/" not in path_str:
            return [
                Violation(
                    file=file_path,
                    line=1,
                    rule="tests-in-tests-dir",
                    message="Test files must be in a tests/ directory",
                    fix="Move to projects/<project>/tests/ or bot/tests/",
                )
            ]

        return []


class CodeReviewer:
    """Main code review orchestrator that runs all rules."""

    def __init__(self):
        """Initialize with default rule set."""
        self.rules: list[CodeReviewRule] = [
            EnvironmentVariableRule(),
            MockUsageRule(),
            TestFileLocationRule(),
        ]

    def check_file(self, file_path: Path, content: str) -> list[Violation]:
        """Run all rules on a single file."""
        # Skip non-Python files
        if file_path.suffix != ".py":
            return []

        violations = []
        for rule in self.rules:
            violations.extend(rule.check(file_path, content))

        return violations

    def check_files(self, file_paths: list[Path]) -> list[Violation]:
        """Run all rules on multiple files."""
        all_violations = []
        for file_path in file_paths:
            try:
                if file_path.exists():
                    content = file_path.read_text()
                    violations = self.check_file(file_path, content)
                    all_violations.extend(violations)
            except Exception as e:
                # Log error but continue checking other files
                print(f"Warning: Could not check {file_path}: {e}", file=sys.stderr)

        return all_violations

    def format_violations(self, violations: list[Violation]) -> str:
        """Format violations for display."""
        if not violations:
            return ""

        lines = ["❌ Code Review Violations:", ""]

        for v in violations:
            lines.append(f"  {v.file}:{v.line} [{v.rule}]")
            lines.append(f"    ❌ {v.message}")
            lines.append(f"    ✅ Fix: {v.fix}")
            lines.append("")

        return "\n".join(lines)


def get_staged_files(cwd: str | None = None) -> list[Path]:
    """Get list of Python files staged for commit.

    Args:
        cwd: Working directory for git command (defaults to current directory)
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
        )

        files = result.stdout.strip().split("\n")
        # Filter for Python files and make absolute paths if cwd provided
        python_files = [f for f in files if f.endswith(".py") and f]

        if cwd:
            return [Path(cwd) / f for f in python_files]
        return [Path(f) for f in python_files]

    except subprocess.CalledProcessError:
        return []


def review_staged_files(cwd: str | None = None) -> list[Violation]:
    """Review all staged Python files (for git hooks).

    Args:
        cwd: Working directory where git command is run (for hook context)
    """
    reviewer = CodeReviewer()
    staged_files = get_staged_files(cwd)

    if not staged_files:
        return []

    return reviewer.check_files(staged_files)


def main():
    """CLI entry point for standalone usage."""
    parser = argparse.ArgumentParser(description="Run code review on files")
    parser.add_argument(
        "--git-staged", action="store_true", help="Review git staged files"
    )
    parser.add_argument("files", nargs="*", help="Specific files to review")
    args = parser.parse_args()

    reviewer = CodeReviewer()

    if args.git_staged:
        violations = review_staged_files()
    elif args.files:
        file_paths = [Path(f) for f in args.files]
        violations = reviewer.check_files(file_paths)
    else:
        print("Error: Specify --git-staged or file paths", file=sys.stderr)
        sys.exit(2)

    if violations:
        print(reviewer.format_violations(violations))
        sys.exit(1)

    print("✅ Code review passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
