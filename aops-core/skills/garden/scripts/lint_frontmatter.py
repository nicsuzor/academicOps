#!/usr/bin/env python3
"""Lint markdown files for frontmatter problems.

Validates:
1. Proper frontmatter delimiters (--- on own line)
2. Valid YAML content
3. Required fields (id/task_id/permalink and title)

Usage:
    python lint_frontmatter.py <path> [--fix] [--recursive]
    python lint_frontmatter.py /path/to/file.md
    python lint_frontmatter.py /path/to/directory --recursive

Examples:
    python lint_frontmatter.py data/tasks/inbox/
    python lint_frontmatter.py data/tasks/ --recursive --fix
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yaml


class Severity(Enum):
    """Issue severity levels."""

    ERROR = "error"  # Must fix - file won't parse correctly
    WARNING = "warning"  # Should fix - non-standard format


@dataclass
class LintIssue:
    """A linting issue found in a file."""

    file: Path
    line: int
    severity: Severity
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.severity.value} [{self.code}] {self.message}"


def check_frontmatter_delimiters(content: str, path: Path) -> list[LintIssue]:
    """Check that frontmatter delimiters are properly formatted.

    The opening --- must be on its own line (start of file or after newline).
    The closing --- must also be on its own line.
    """
    issues: list[LintIssue] = []
    lines = content.split("\n")

    if not lines:
        issues.append(
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM001",
                message="Empty file",
            )
        )
        return issues

    # Check opening delimiter
    first_line = lines[0]
    if not first_line.startswith("---"):
        issues.append(
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM002",
                message="File must start with YAML frontmatter (---)",
            )
        )
        return issues

    # Check that opening --- is alone on its line
    if first_line != "---":
        issues.append(
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM003",
                message=f"Opening delimiter must be on its own line, found: '{first_line[:50]}...'",
            )
        )

    # Find closing delimiter
    closing_line = None
    for i, line in enumerate(lines[1:], start=2):
        if line == "---":
            closing_line = i
            break
        # Check for malformed closing delimiter
        if line.startswith("---") and line != "---":
            issues.append(
                LintIssue(
                    file=path,
                    line=i,
                    severity=Severity.WARNING,
                    code="FM004",
                    message=f"Possible malformed closing delimiter: '{line[:50]}'",
                )
            )

    if closing_line is None:
        issues.append(
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM005",
                message="Missing closing frontmatter delimiter (---)",
            )
        )

    return issues


def check_yaml_validity(content: str, path: Path) -> list[LintIssue]:
    """Check that frontmatter contains valid YAML."""
    issues: list[LintIssue] = []

    # Extract frontmatter content
    if not content.startswith("---"):
        return issues  # Already caught by delimiter check

    # Find the YAML content between delimiters
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        # Try to extract even with malformed delimiter
        lines = content.split("\n")
        yaml_lines = []
        in_frontmatter = False
        for i, line in enumerate(lines):
            if i == 0:
                if line == "---":
                    in_frontmatter = True
                elif line.startswith("---"):
                    # Malformed - extract what comes after ---
                    yaml_lines.append(line[3:])
                    in_frontmatter = True
                continue
            if line == "---":
                break
            if in_frontmatter:
                yaml_lines.append(line)
        yaml_content = "\n".join(yaml_lines)
    else:
        yaml_content = match.group(1)

    if not yaml_content.strip():
        issues.append(
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM006",
                message="Empty frontmatter",
            )
        )
        return issues

    try:
        data = yaml.safe_load(yaml_content)
        if data is None:
            issues.append(
                LintIssue(
                    file=path,
                    line=1,
                    severity=Severity.ERROR,
                    code="FM007",
                    message="Frontmatter parsed as null/empty",
                )
            )
    except yaml.YAMLError as e:
        # Extract line number from YAML error if available
        line = 1
        if hasattr(e, "problem_mark") and e.problem_mark:
            line = e.problem_mark.line + 2  # +2 for 1-indexed and --- line
        issues.append(
            LintIssue(
                file=path,
                line=line,
                severity=Severity.ERROR,
                code="FM008",
                message=f"Invalid YAML: {e}",
            )
        )

    return issues


def check_required_fields(content: str, path: Path) -> list[LintIssue]:
    """Check for required frontmatter fields."""
    issues: list[LintIssue] = []

    # Extract and parse frontmatter
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        # Try malformed extraction
        lines = content.split("\n")
        yaml_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                if line.startswith("---") and line != "---":
                    yaml_lines.append(line[3:])
                continue
            if line == "---":
                break
            yaml_lines.append(line)
        yaml_content = "\n".join(yaml_lines)
    else:
        yaml_content = match.group(1)

    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            return issues

        # Check for ID field (id, task_id, or permalink)
        has_id = any(k in data for k in ("id", "task_id", "permalink"))
        if not has_id:
            issues.append(
                LintIssue(
                    file=path,
                    line=1,
                    severity=Severity.WARNING,
                    code="FM009",
                    message="Missing identifier field (id, task_id, or permalink)",
                )
            )

        # Check for title
        if "title" not in data:
            issues.append(
                LintIssue(
                    file=path,
                    line=1,
                    severity=Severity.WARNING,
                    code="FM010",
                    message="Missing required field: title",
                )
            )

    except yaml.YAMLError:
        pass  # Already caught by validity check

    return issues


def lint_file(path: Path) -> list[LintIssue]:
    """Lint a single markdown file for frontmatter issues."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return [
            LintIssue(
                file=path,
                line=1,
                severity=Severity.ERROR,
                code="FM000",
                message=f"Cannot read file: {e}",
            )
        ]

    issues: list[LintIssue] = []
    issues.extend(check_frontmatter_delimiters(content, path))
    issues.extend(check_yaml_validity(content, path))
    issues.extend(check_required_fields(content, path))

    return issues


def fix_frontmatter_delimiter(content: str) -> str | None:
    """Attempt to fix malformed opening delimiter.

    Returns fixed content or None if cannot fix.
    """
    lines = content.split("\n")
    if not lines:
        return None

    first_line = lines[0]

    # Case: ---title: ... (no newline after ---)
    if first_line.startswith("---") and first_line != "---":
        # Insert newline after ---
        fixed_first = "---\n" + first_line[3:]
        return fixed_first + "\n" + "\n".join(lines[1:])

    return None


def lint_directory(
    path: Path, recursive: bool = False, fix: bool = False
) -> list[LintIssue]:
    """Lint all markdown files in a directory."""
    pattern = "**/*.md" if recursive else "*.md"
    all_issues: list[LintIssue] = []
    fixed_count = 0

    for md_file in path.glob(pattern):
        if md_file.is_file():
            issues = lint_file(md_file)

            # Attempt fixes if requested
            if fix and issues:
                content = md_file.read_text(encoding="utf-8")
                fixed_content = fix_frontmatter_delimiter(content)
                if fixed_content and fixed_content != content:
                    md_file.write_text(fixed_content, encoding="utf-8")
                    fixed_count += 1
                    # Re-lint after fix
                    issues = lint_file(md_file)

            all_issues.extend(issues)

    if fix and fixed_count > 0:
        print(f"Fixed {fixed_count} file(s)", file=sys.stderr)

    return all_issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint markdown files for frontmatter problems"
    )
    parser.add_argument("path", type=Path, help="File or directory to lint")
    parser.add_argument(
        "--recursive", "-r", action="store_true", help="Recursively lint directories"
    )
    parser.add_argument(
        "--fix", "-f", action="store_true", help="Attempt to fix simple issues"
    )
    parser.add_argument(
        "--errors-only",
        "-e",
        action="store_true",
        help="Only show errors, not warnings",
    )
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: {args.path} does not exist", file=sys.stderr)
        return 1

    if args.path.is_file():
        issues = lint_file(args.path)
        if args.fix:
            content = args.path.read_text(encoding="utf-8")
            fixed = fix_frontmatter_delimiter(content)
            if fixed and fixed != content:
                args.path.write_text(fixed, encoding="utf-8")
                print(f"Fixed: {args.path}", file=sys.stderr)
                issues = lint_file(args.path)
    else:
        issues = lint_directory(args.path, args.recursive, args.fix)

    # Filter by severity if requested
    if args.errors_only:
        issues = [i for i in issues if i.severity == Severity.ERROR]

    # Output results
    if args.json:
        import json

        output = [
            {
                "file": str(i.file),
                "line": i.line,
                "severity": i.severity.value,
                "code": i.code,
                "message": i.message,
            }
            for i in issues
        ]
        print(json.dumps(output, indent=2))
    else:
        for issue in issues:
            print(issue)

    # Summary
    error_count = sum(1 for i in issues if i.severity == Severity.ERROR)
    warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)

    if not args.json and issues:
        print(f"\nFound {error_count} error(s), {warning_count} warning(s)")

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
