#!/usr/bin/env python3
"""One-time migration script: Add category field to markdown frontmatter.

This script adds the `category` field to files that are missing it,
based on the directory mapping in specs/file-taxonomy.md.

Usage:
    uv run python scripts/migrate_file_taxonomy.py --dry-run  # Preview changes
    uv run python scripts/migrate_file_taxonomy.py            # Apply changes
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

# Import category rules from the validation script
from check_file_taxonomy import (
    CATEGORY_RULES,
    SKIP_PATTERNS,
    get_expected_category,
    parse_frontmatter,
    should_skip,
)


def add_category_to_frontmatter(content: str, category: str) -> str:
    """Add category field to existing frontmatter."""
    # Find the frontmatter block
    match = re.match(r"^(---\n)(.*?)(\n---)", content, re.DOTALL)
    if not match:
        return content

    start, fm_content, end = match.groups()

    # Parse existing frontmatter
    try:
        fm = yaml.safe_load(fm_content)
        if fm is None:
            fm = {}
    except yaml.YAMLError:
        return content

    # Skip if category already exists
    if "category" in fm:
        return content

    # Add category after 'type' field if it exists, otherwise after 'description' or 'name'
    lines = fm_content.split("\n")
    new_lines = []
    inserted = False

    for line in lines:
        new_lines.append(line)
        # Insert after type, description, or name field
        if not inserted and re.match(r"^(type|description|name):", line):
            # Check if next line is not already category
            new_lines.append(f"category: {category}")
            inserted = True

    # If we didn't find a good insertion point, add at the end
    if not inserted:
        new_lines.append(f"category: {category}")

    new_fm_content = "\n".join(new_lines)

    # Reconstruct the file
    rest = content[match.end() :]
    return f"{start}{new_fm_content}{end}{rest}"


def create_frontmatter(category: str, name: str, title: str) -> str:
    """Create new frontmatter for files that don't have any."""
    return f"""---
name: {name}
title: {title}
category: {category}
---

"""


def migrate_file(
    root: Path, file_path: Path, dry_run: bool = False
) -> tuple[bool, str]:
    """Migrate a single file. Returns (changed, message)."""
    relative = file_path.relative_to(root)
    relative_str = str(relative)

    # Skip non-markdown and excluded files
    if not file_path.suffix == ".md":
        return False, "not markdown"
    if should_skip(relative_str):
        return False, "skipped by pattern"

    # Determine expected category
    expected = get_expected_category(relative_str)
    if expected is None:
        return False, "no category rule"

    # Read file
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"read error: {e}"

    # Check if has frontmatter
    fm = parse_frontmatter(content)

    if fm is None:
        # No frontmatter - need to add it
        name = file_path.stem.lower().replace(" ", "-")
        title = file_path.stem.replace("-", " ").replace("_", " ").title()
        new_frontmatter = create_frontmatter(expected, name, title)
        new_content = new_frontmatter + content

        if dry_run:
            return True, f"would add frontmatter with category: {expected}"

        file_path.write_text(new_content, encoding="utf-8")
        return True, f"added frontmatter with category: {expected}"

    if "category" in fm:
        # Already has category
        if fm["category"] == expected:
            return False, "already correct"
        else:
            return False, f"has wrong category: {fm['category']} (expected {expected})"

    # Has frontmatter but no category - add it
    new_content = add_category_to_frontmatter(content, expected)

    if new_content == content:
        return False, "no change (add failed)"

    if dry_run:
        return True, f"would add category: {expected}"

    file_path.write_text(new_content, encoding="utf-8")
    return True, f"added category: {expected}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate files to add category field")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    parser.add_argument(
        "--directory", type=str, help="Only migrate files in this directory"
    )
    args = parser.parse_args()

    root = Path(os.environ.get("AOPS", Path(__file__).parent.parent)).resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    # Find files
    if args.directory:
        target = root / args.directory
        if not target.is_dir():
            print(f"Error: Directory does not exist: {target}", file=sys.stderr)
            return 1
        files = list(target.rglob("*.md"))
    else:
        files = list(root.rglob("*.md"))

    changed = 0
    skipped = 0
    errors = 0

    mode = "DRY RUN" if args.dry_run else "MIGRATING"
    print(f"{mode}: Processing {len(files)} files...\n")

    for file_path in sorted(files):
        was_changed, message = migrate_file(root, file_path, args.dry_run)
        relative = file_path.relative_to(root)

        if was_changed:
            print(f"  [CHANGE] {relative}: {message}")
            changed += 1
        elif "error" in message.lower():
            print(f"  [ERROR] {relative}: {message}")
            errors += 1
        else:
            skipped += 1

    print(f"\nSummary: {changed} changed, {skipped} skipped, {errors} errors")

    if args.dry_run and changed > 0:
        print("\nRun without --dry-run to apply changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
