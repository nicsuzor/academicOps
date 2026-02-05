#!/usr/bin/env python3
"""Pre-commit hook: Block silent fallback patterns in hook code.

Enforces P#8 (Fail-Fast Code): No defaults, no fallbacks, no workarounds, no silent failures.

Detects:
1. .get(..., "") or .get(..., '') - empty string fallback
2. .get(..., []) - empty list fallback
3. .get(..., {}) - empty dict fallback
4. `or ""` / `or ''` / `or []` / `or {}` - fallback chains

These patterns mask missing data instead of failing fast. Required values should raise
exceptions when missing, not silently return empty values.

Usage:
    python check_no_fallbacks.py [files...]

    If no files specified, scans $AOPS/aops-core/hooks/*.py

Exit codes:
    0: No fallback patterns found
    1: Fallback patterns detected (blocks commit)
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path


class FallbackDetector(ast.NodeVisitor):
    """AST visitor that detects silent fallback patterns."""

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.violations: list[dict] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Detect .get(..., empty_value) patterns."""
        # Check for method calls like x.get(key, default)
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) >= 2
        ):
            default_arg = node.args[1]
            if self._is_empty_fallback(default_arg):
                self.violations.append(
                    {
                        "file": str(self.filepath),
                        "line": node.lineno,
                        "col": node.col_offset,
                        "pattern": f".get(..., {ast.unparse(default_arg)})",
                        "message": "Silent fallback to empty value. Raise exception if value required.",
                    }
                )
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Detect `x or ""` fallback chains."""
        if isinstance(node.op, ast.Or):
            # Check the last value in the `or` chain
            last_value = node.values[-1]
            if self._is_empty_fallback(last_value):
                self.violations.append(
                    {
                        "file": str(self.filepath),
                        "line": node.lineno,
                        "col": node.col_offset,
                        "pattern": f"... or {ast.unparse(last_value)}",
                        "message": "Silent fallback chain. Raise exception if value required.",
                    }
                )
        self.generic_visit(node)

    def _is_empty_fallback(self, node: ast.expr) -> bool:
        """Check if node represents an empty fallback value."""
        # Empty string: "" or ''
        if isinstance(node, ast.Constant) and node.value == "":
            return True
        # Empty list: []
        if isinstance(node, ast.List) and len(node.elts) == 0:
            return True
        # Empty dict: {}
        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return True
        return False


def check_file(filepath: Path) -> list[dict]:
    """Check a single Python file for fallback patterns."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {filepath}: {e}", file=sys.stderr)
        return []

    detector = FallbackDetector(filepath)
    detector.visit(tree)
    return detector.violations


def main() -> int:
    """Main entry point."""
    # Get files to check
    if len(sys.argv) > 1:
        files = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    else:
        # Default: scan hooks directory
        aops_root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()
        hooks_dir = aops_root / "aops-core" / "hooks"
        if hooks_dir.is_dir():
            files = list(hooks_dir.glob("*.py"))
        else:
            print(f"Warning: Hooks directory not found: {hooks_dir}", file=sys.stderr)
            files = []

    all_violations: list[dict] = []
    for filepath in files:
        if filepath.is_file():
            violations = check_file(filepath)
            all_violations.extend(violations)

    if all_violations:
        print(f"ERROR: {len(all_violations)} silent fallback pattern(s) detected:")
        print()
        for v in all_violations:
            print(f"  {v['file']}:{v['line']}:{v['col']}")
            print(f"    Pattern: {v['pattern']}")
            print(f"    Fix: {v['message']}")
            print()
        print("P#8 (Fail-Fast Code): No defaults, no fallbacks, no silent failures.")
        print(
            "If the value is optional, use explicit None checks with clear semantics."
        )
        return 1

    print(f"OK: No silent fallback patterns in {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
