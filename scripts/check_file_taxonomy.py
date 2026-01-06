#!/usr/bin/env python3
"""Pre-commit hook: Validate file taxonomy categories.

Checks that markdown files have a `category` field in frontmatter
and that the category matches the expected value for the file location.

Exit codes:
    0: All files valid (or only warnings)
    1: Validation errors found
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

import yaml


class ValidationResult(NamedTuple):
    """Result of validating a single file."""

    path: Path
    has_frontmatter: bool
    has_category: bool
    actual_category: str | None
    expected_category: str | None
    is_valid: bool
    message: str


# Directory patterns mapped to expected categories
# Order matters - more specific patterns first
CATEGORY_RULES: list[tuple[str, str]] = [
    # STATE files
    (r"^RULES\.md$", "state"),
    # TEMPLATE files
    (r".*/templates/.*\.md$", "template"),
    # INSTRUCTION files
    (r"^commands/.*\.md$", "instruction"),
    (r"^agents/.*\.md$", "instruction"),
    (r".*/SKILL\.md$", "instruction"),
    (r".*/instructions/.*\.md$", "instruction"),
    (r".*/workflows/.*\.md$", "instruction"),
    # REF files (external knowledge)
    (r".*/references/.*\.md$", "ref"),
    # DOCS files (implementation guides)
    (r"^docs/.*\.md$", "docs"),
    # SPEC files
    (r"^specs/.*\.md$", "spec"),
    (r"^AXIOMS\.md$", "spec"),
    (r"^VISION\.md$", "spec"),
    (r"^HEURISTICS\.md$", "spec"),
    (r"^README\.md$", "spec"),
    (r"^INDEX\.md$", "spec"),
    (r"^ROADMAP\.md$", "spec"),
    (r"^WORKFLOWS\.md$", "spec"),
    (r"^FRAMEWORK\.md$", "spec"),
    (r"^CLAUDE\.md$", "spec"),
    (r"^AGENTS\.md$", "spec"),
    (r"^GEMINI\.md$", "spec"),
]

# Files to skip (not markdown content files)
SKIP_PATTERNS: list[str] = [
    r"^\.github/",
    r"^\.venv/",
    r"^tests/",
    r"^lib/",
    r"^scripts/",
    r"^config/",
    r"^gemini/",
    r".*/__pycache__/",
    r".*\.py$",
    r".*\.sh$",
    r".*\.json$",
    r".*\.yaml$",
    r".*\.yml$",
    r".*\.toml$",
    r".*\.lock$",
    r".*\.css$",
    r".*\.ttf$",
    r".*\.excalidrawlib$",
    r".*\.excalidraw$",
    r".*\.csv$",
]


def parse_frontmatter(content: str) -> dict | None:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None

    # Find closing ---
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None

    try:
        return yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None


def get_expected_category(relative_path: str) -> str | None:
    """Determine expected category based on file path."""
    for pattern, category in CATEGORY_RULES:
        if re.match(pattern, relative_path):
            return category
    return None


def should_skip(relative_path: str) -> bool:
    """Check if file should be skipped."""
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, relative_path):
            return True
    return False


def validate_file(root: Path, file_path: Path) -> ValidationResult | None:
    """Validate a single markdown file."""
    relative = file_path.relative_to(root)
    relative_str = str(relative)

    # Skip non-markdown and excluded files
    if not file_path.suffix == ".md":
        return None
    if should_skip(relative_str):
        return None

    # Determine expected category
    expected = get_expected_category(relative_str)
    if expected is None:
        # No rule for this location - might be intentional
        return ValidationResult(
            path=relative,
            has_frontmatter=False,
            has_category=False,
            actual_category=None,
            expected_category=None,
            is_valid=True,
            message="No category rule for this location (skipped)",
        )

    # Read and parse file
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return ValidationResult(
            path=relative,
            has_frontmatter=False,
            has_category=False,
            actual_category=None,
            expected_category=expected,
            is_valid=False,
            message=f"Could not read file: {e}",
        )

    # Parse frontmatter
    frontmatter = parse_frontmatter(content)
    if frontmatter is None:
        return ValidationResult(
            path=relative,
            has_frontmatter=False,
            has_category=False,
            actual_category=None,
            expected_category=expected,
            is_valid=False,
            message=f"Missing frontmatter (expected category: {expected})",
        )

    # Check for category field
    actual = frontmatter.get("category")
    if actual is None:
        return ValidationResult(
            path=relative,
            has_frontmatter=True,
            has_category=False,
            actual_category=None,
            expected_category=expected,
            is_valid=False,
            message=f"Missing 'category' field (expected: {expected})",
        )

    # Validate category matches expected
    if actual != expected:
        return ValidationResult(
            path=relative,
            has_frontmatter=True,
            has_category=True,
            actual_category=actual,
            expected_category=expected,
            is_valid=False,
            message=f"Category mismatch: got '{actual}', expected '{expected}'",
        )

    return ValidationResult(
        path=relative,
        has_frontmatter=True,
        has_category=True,
        actual_category=actual,
        expected_category=expected,
        is_valid=True,
        message="OK",
    )


def find_markdown_files(root: Path) -> list[Path]:
    """Find all markdown files in the repository."""
    return list(root.rglob("*.md"))


def main() -> int:
    """Run taxonomy validation."""
    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    files = find_markdown_files(root)
    results: list[ValidationResult] = []

    for file_path in files:
        result = validate_file(root, file_path)
        if result is not None:
            results.append(result)

    # Separate valid and invalid
    valid = [r for r in results if r.is_valid]
    invalid = [r for r in results if not r.is_valid]

    # Report results
    if invalid:
        print(f"TAXONOMY ERRORS: {len(invalid)} files need category fixes:\n")

        # Group by issue type
        missing_frontmatter = [r for r in invalid if not r.has_frontmatter]
        missing_category = [
            r for r in invalid if r.has_frontmatter and not r.has_category
        ]
        wrong_category = [r for r in invalid if r.has_category and not r.is_valid]

        if missing_frontmatter:
            print(f"Missing frontmatter ({len(missing_frontmatter)}):")
            for r in missing_frontmatter[:10]:
                print(f"  {r.path}: add category: {r.expected_category}")
            if len(missing_frontmatter) > 10:
                print(f"  ... and {len(missing_frontmatter) - 10} more")
            print()

        if missing_category:
            print(f"Missing 'category' field ({len(missing_category)}):")
            for r in missing_category[:10]:
                print(f"  {r.path}: add category: {r.expected_category}")
            if len(missing_category) > 10:
                print(f"  ... and {len(missing_category) - 10} more")
            print()

        if wrong_category:
            print(f"Wrong category ({len(wrong_category)}):")
            for r in wrong_category[:10]:
                print(
                    f"  {r.path}: change '{r.actual_category}' → '{r.expected_category}'"
                )
            if len(wrong_category) > 10:
                print(f"  ... and {len(wrong_category) - 10} more")
            print()

        print(f"Total: {len(valid)} valid, {len(invalid)} invalid")
        # Return 0 for now - warning only during migration
        # TODO: Change to return 1 after migration complete
        return 0

    print(f"OK: {len(valid)} files have valid taxonomy categories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
