#!/usr/bin/env python3
"""
Pre-commit linter to detect potential reinvented wheels.

Flags code that appears to reimplement functionality available in standard libraries.
Follows Axiom #11: Use Standard Tools - reduces maintenance burden, leverages community.

Usage:
    uv run python scripts/check_solved_problems.py [files...]

    # Check all Python files
    uv run python scripts/check_solved_problems.py $(git diff --name-only --cached '*.py')

Exit codes:
    0: No issues found
    1: Suspicious patterns detected (requires manual review)
    2: Script error

Examples of solved problems this detects:
    - Custom regex-based secrets detection → detect-secrets library
    - Custom CLI argument parsing wrappers → Click, Typer
    - Custom data validation classes → Pydantic
    - Custom HTTP client implementations → httpx
    - Custom configuration loaders → Pydantic Settings
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from re import Pattern


@dataclass
class SolvedProblem:
    """Pattern for detecting reinvented wheels."""

    name: str
    description: str
    pattern: Pattern[str]
    recommended_library: str
    min_lines: int = (
        30  # Minimum file lines to trigger (avoid false positives on small code)
    )


# Patterns for common solved problems
SOLVED_PROBLEMS = [
    SolvedProblem(
        name="secrets_detection",
        description="Custom secrets/credentials detection with regex patterns",
        pattern=re.compile(
            r"(class\s+\w*Sanitiz\w*|class\s+\w*Secret\w*Detect\w*).*?re\.compile.*?(api[_-]?key|password|token|credential)",
            re.DOTALL | re.IGNORECASE,
        ),
        recommended_library="detect-secrets (Yelp, 3k+ stars)",
        min_lines=50,
    ),
    SolvedProblem(
        name="data_validation",
        description="Custom data validation classes without Pydantic",
        pattern=re.compile(
            r"class\s+\w*(Config|Settings|Validator)\w*.*?def\s+validate.*?raise\s+(ValueError|ValidationError)",
            re.DOTALL,
        ),
        recommended_library="Pydantic (validation + settings)",
        min_lines=40,
    ),
    SolvedProblem(
        name="cli_parsing",
        description="Custom argparse wrapper or CLI framework",
        pattern=re.compile(
            r"class\s+\w*(CLI|Command|Parser)\w*.*?argparse\.ArgumentParser",
            re.DOTALL,
        ),
        recommended_library="Click or Typer (modern CLI frameworks)",
        min_lines=50,
    ),
    SolvedProblem(
        name="http_client",
        description="Custom HTTP client or request handling",
        pattern=re.compile(
            r"class\s+\w*(HTTP|API|Request)Client\w*.*?(urllib|http\.client)",
            re.DOTALL,
        ),
        recommended_library="httpx (modern async HTTP client)",
        min_lines=40,
    ),
    SolvedProblem(
        name="config_loader",
        description="Custom configuration loading without Pydantic Settings",
        pattern=re.compile(
            r"class\s+\w*Config\w*Loader\w*.*?(yaml\.load|json\.load).*?os\.environ",
            re.DOTALL,
        ),
        recommended_library="Pydantic Settings (config + env vars + validation)",
        min_lines=30,
    ),
]


def count_lines(file_path: Path) -> int:
    """Count non-empty lines in file."""
    try:
        return sum(1 for line in file_path.read_text().splitlines() if line.strip())
    except Exception:
        return 0


def check_file(file_path: Path) -> list[tuple[SolvedProblem, str]]:
    """
    Check file for reinvented wheel patterns.

    Args:
        file_path: Python file to check

    Returns:
        List of (pattern, matched_code_snippet) tuples for detected issues
    """
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []

    line_count = count_lines(file_path)
    issues = []

    for problem in SOLVED_PROBLEMS:
        # Skip if file too small (likely not reinventing wheels)
        if line_count < problem.min_lines:
            continue

        match = problem.pattern.search(content)
        if match:
            # Extract snippet (up to 100 chars for readability)
            snippet = match.group(0)[:100]
            if len(match.group(0)) > 100:
                snippet += "..."

            issues.append((problem, snippet))

    return issues


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Detect potential reinvented wheels in Python code",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="Python files to check (if none, checks all staged .py files)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 on any detection)",
    )

    args = parser.parse_args()

    # Determine files to check
    files_to_check: list[Path] = []
    if args.files:
        files_to_check = [Path(f) for f in args.files if Path(f).suffix == ".py"]
    else:
        # Check staged Python files
        import subprocess

        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", "*.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            files_to_check = [
                Path(f.strip()) for f in result.stdout.splitlines() if f.strip()
            ]

    if not files_to_check:
        print("No Python files to check", file=sys.stderr)
        return 0

    # Check each file
    all_issues: dict[Path, list[tuple[SolvedProblem, str]]] = {}
    for file_path in files_to_check:
        issues = check_file(file_path)
        if issues:
            all_issues[file_path] = issues

    # Report findings
    if not all_issues:
        print("✅ No reinvented wheels detected")
        return 0

    # Found potential issues
    print("\n⚠️  POTENTIAL REINVENTED WHEELS DETECTED\n")
    print(
        "The following files may be reimplementing functionality available in standard libraries."
    )
    print("This violates Axiom #11: Use Standard Tools\n")

    for file_path, issues in all_issues.items():
        print(f"📁 {file_path} ({count_lines(file_path)} lines)")
        for problem, snippet in issues:
            print(f"  ❌ {problem.name}: {problem.description}")
            print(f"     Recommended: {problem.recommended_library}")
            print(f"     Matched: {snippet}")
            print()

    print("\n💡 RECOMMENDED ACTION:")
    print("1. Search PyPI for existing libraries that solve this problem")
    print("2. If library exists: Refactor to use it instead of custom implementation")
    print("3. If custom code justified: Document rationale in code comments")
    print("\nSee: bots/agents/_CORE.md Axiom #11 - Use Standard Tools\n")

    # Exit code
    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
