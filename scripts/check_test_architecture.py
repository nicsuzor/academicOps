#!/usr/bin/env python3
"""
Custom test architecture checker for academicOps.

Enforces architectural rules:
1. Only mock at project boundaries (external dependencies)
2. No mocking of internal project code
3. Tests should use real implementations for internal modules

Usage:
    uv run python scripts/check_test_architecture.py [test_directory]

Exit codes:
    0: All tests pass architectural rules
    1: Violations found
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import NamedTuple


class MockViolation(NamedTuple):
    """Represents a mocking violation."""

    file: str
    line: int
    target: str
    reason: str


class MockingChecker(ast.NodeVisitor):
    """AST visitor that detects mocking violations."""

    def __init__(self, filepath: Path, project_modules: set[str]):
        self.filepath = filepath
        self.project_modules = project_modules
        self.violations: list[MockViolation] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for mock.patch usage."""
        # Check for unittest.mock.patch calls
        if self._is_patch_call(node):
            target = self._extract_patch_target(node)
            if target and self._is_internal_module(target):
                self.violations.append(
                    MockViolation(
                        file=str(self.filepath),
                        line=node.lineno,
                        target=target,
                        reason="Mocking internal project code violates architecture",
                    )
                )

        self.generic_visit(node)

    def _is_patch_call(self, node: ast.Call) -> bool:
        """Check if this is a mock.patch call."""
        # Direct: mock.patch(...)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "patch"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "mock"
        ):
            return True

        # Decorator: @patch(...)
        # (handled by visit_FunctionDef checking decorators)

        # Direct import: patch(...)
        return bool(isinstance(node.func, ast.Name) and node.func.id == "patch")

    def _extract_patch_target(self, node: ast.Call) -> str | None:
        """Extract the target string from patch() call."""
        if node.args and isinstance(node.args[0], ast.Constant):
            value = node.args[0].value
            return value if isinstance(value, str) else None
        return None

    def _is_internal_module(self, target: str) -> bool:
        """Check if target is an internal project module."""
        # Extract root module from target
        root_module = target.split(".")[0]
        return root_module in self.project_modules

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check decorators for @patch usage."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and self._is_patch_call(decorator):
                target = self._extract_patch_target(decorator)
                if target and self._is_internal_module(target):
                    self.violations.append(
                        MockViolation(
                            file=str(self.filepath),
                            line=decorator.lineno,
                            target=target,
                            reason="Mocking internal project code violates architecture",
                        )
                    )

        self.generic_visit(node)


def check_file(filepath: Path, project_modules: set[str]) -> list[MockViolation]:
    """Check a single test file for mocking violations."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []

    checker = MockingChecker(filepath, project_modules)
    checker.visit(tree)
    return checker.violations


def discover_project_modules(test_dir: Path) -> set[str]:
    """
    Discover internal project modules.

    Assumes project structure:
        project/
            src/module_name/
            tests/

    Returns set of internal module names that shouldn't be mocked.
    """
    # Look for src/ directory siblings to tests/
    project_root = test_dir.parent
    src_dir = project_root / "src"

    modules = set()

    # If src/ exists, scan it
    if src_dir.exists():
        for item in src_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                modules.add(item.name)

    # Also check for top-level Python packages
    for item in project_root.iterdir():
        if (
            item.is_dir()
            and (item / "__init__.py").exists()
            and item.name not in {"tests", "test", ".venv", "venv"}
        ):
            modules.add(item.name)

    return modules


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check test architecture rules (no internal mocking)"
    )
    parser.add_argument(
        "test_dir",
        nargs="?",
        default="tests",
        help="Test directory to check (default: tests)",
    )
    parser.add_argument(
        "--project-modules",
        help="Comma-separated list of internal modules (auto-discovered if omitted)",
    )

    args = parser.parse_args()

    test_dir = Path(args.test_dir)
    if not test_dir.exists():
        print(f"Error: Test directory {test_dir} does not exist", file=sys.stderr)
        return 1

    # Discover or use provided project modules
    if args.project_modules:
        project_modules = set(args.project_modules.split(","))
    else:
        project_modules = discover_project_modules(test_dir)

    if not project_modules:
        print(
            "Warning: No internal modules discovered. Skipping check.", file=sys.stderr
        )
        return 0

    print(
        f"Checking for internal mocking of modules: {', '.join(sorted(project_modules))}"
    )

    # Scan all Python test files
    all_violations: list[MockViolation] = []
    test_files = list(test_dir.rglob("test_*.py")) + list(test_dir.rglob("*_test.py"))

    for filepath in test_files:
        violations = check_file(filepath, project_modules)
        all_violations.extend(violations)

    # Report results
    if all_violations:
        print(f"\n❌ Found {len(all_violations)} mocking violations:\n")
        for v in all_violations:
            print(f"  {v.file}:{v.line}")
            print(f"    Mocking internal module: {v.target}")
            print(f"    {v.reason}\n")

        print("🛠️  How to fix:")
        print(
            "  - Only mock external dependencies (APIs, databases, third-party libraries)"
        )
        print("  - Use real implementations for internal project code")
        print("  - Refactor to make boundaries explicit if needed")
        return 1
    print(f"✅ All {len(test_files)} test files follow architecture rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
