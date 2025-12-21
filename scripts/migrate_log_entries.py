#!/usr/bin/env python3
"""Migrate LOG.md entries to thematic learning files.

Parses LOG.md entries and appends them to appropriate thematic files based on
pattern tags in each entry.

Usage:
    uv run python scripts/migrate_log_entries.py
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


# Tag to file mapping
TAG_MAPPINGS: dict[str, str] = {
    # verification-skip.md (agents claiming success without verification)
    "verify-first": "verification-skip.md",
    "overconfidence": "verification-skip.md",
    "validation": "verification-skip.md",
    "incomplete-task": "verification-skip.md",
    "axiom-violation": "verification-skip.md",
    "confirmation-bias": "verification-skip.md",
    "security-theater": "verification-skip.md",
    # instruction-ignore.md (agents ignoring explicit instructions)
    "instruction-following": "instruction-ignore.md",
    "scope": "instruction-ignore.md",
    "literal": "instruction-ignore.md",
    "user-request": "instruction-ignore.md",
    "accommodations": "instruction-ignore.md",
    "request-interpretation": "instruction-ignore.md",
    # validation-bypass.md (git/validation rule violations)
    "git-safety": "validation-bypass.md",
    "no-verify": "validation-bypass.md",
    "validation-bypass": "validation-bypass.md",
    "pre-commit": "validation-bypass.md",
    "reset-hard": "validation-bypass.md",
    "pre-commit-hooks": "validation-bypass.md",
    # skill-bypass.md (agents bypassing skills, using wrong tools)
    "skill-invocation": "skill-bypass.md",
    "tool-usage": "skill-bypass.md",
    "mcp": "skill-bypass.md",
    "memory-integration": "skill-bypass.md",
    "skill-context": "skill-bypass.md",
    "skill-creation": "skill-bypass.md",
    "skill-discovery": "skill-bypass.md",
    "skill-overlap": "skill-bypass.md",
    "proactive-enforcement": "skill-bypass.md",
    "memory": "skill-bypass.md",
    "memory-skill": "skill-bypass.md",
    "memory-validation": "skill-bypass.md",
    "cross-skill-knowledge": "skill-bypass.md",
    # test-and-tdd.md
    "tdd": "test-and-tdd.md",
    "testing": "test-and-tdd.md",
    "test-contract": "test-and-tdd.md",
    "fake-data": "test-and-tdd.md",
    "dogfooding": "test-and-tdd.md",
    "test-design": "test-and-tdd.md",
    "tdd-philosophy": "test-and-tdd.md",
    "tdd-workflow": "test-and-tdd.md",
    "test-hygiene": "test-and-tdd.md",
    "test-location": "test-and-tdd.md",
    "e2e-testing": "test-and-tdd.md",
    # technical-successes.md (called technical-wins in spec)
    "success": "technical-successes.md",
    "tdd-win": "technical-successes.md",
    "workflow-success": "technical-successes.md",
}

# Default file for entries with no clear match
DEFAULT_FILE = "verification-skip.md"


@dataclass
class LogEntry:
    """Represents a parsed LOG.md entry."""

    title: str
    raw_content: str
    tags: list[str]
    is_success: bool


def get_aca_data_path() -> Path:
    """Get ACA_DATA path from environment.

    Returns:
        Path to ACA_DATA directory

    Raises:
        ValueError: If ACA_DATA environment variable is not set
    """
    aca_data = os.environ.get("ACA_DATA")
    if not aca_data:
        raise ValueError("ACA_DATA environment variable is not set")
    return Path(aca_data)


def parse_entries(log_content: str) -> list[LogEntry]:
    """Parse LOG.md content into individual entries.

    Args:
        log_content: Full content of LOG.md file

    Returns:
        List of parsed LogEntry objects
    """
    entries: list[LogEntry] = []

    # Split on ## at start of line (but not the header or Context section)
    # Skip the frontmatter and introductory sections
    entry_pattern = re.compile(r"^## (?!Context\b|Learning Patterns Log)", re.MULTILINE)
    parts = entry_pattern.split(log_content)

    # First part is the header/intro, skip it
    if len(parts) > 1:
        # Find where entries start
        entry_starts = list(entry_pattern.finditer(log_content))

        for i, match in enumerate(entry_starts):
            start = match.start()
            end = entry_starts[i + 1].start() if i + 1 < len(entry_starts) else len(log_content)
            entry_content = log_content[start:end].strip()

            if entry_content:
                entry = parse_single_entry(entry_content)
                if entry:
                    entries.append(entry)

    return entries


def parse_single_entry(entry_content: str) -> LogEntry | None:
    """Parse a single entry's content.

    Args:
        entry_content: Content of a single entry starting with ##

    Returns:
        Parsed LogEntry or None if invalid
    """
    lines = entry_content.split("\n")
    if not lines:
        return None

    # Extract title from first line (## Category: Title)
    title_line = lines[0].strip()
    if not title_line.startswith("## "):
        return None

    full_title = title_line[3:].strip()  # Remove "## "

    # Extract tags from **Pattern**: line
    tags: list[str] = []
    pattern_match = re.search(r"\*\*Pattern\*\*:\s*([^\n]+)", entry_content)
    if pattern_match:
        pattern_line = pattern_match.group(1)
        # Extract hashtags
        tags = re.findall(r"#([a-zA-Z0-9_-]+)", pattern_line)

    # Check if it's a success entry
    is_success = "✅ Success" in entry_content or any(
        tag in ["success", "tdd-win", "workflow-success"] for tag in tags
    )

    # Also check Type field for success indicators
    type_match = re.search(r"\*\*Type\*\*:\s*([^\|]+)", entry_content)
    if type_match:
        type_text = type_match.group(1).strip()
        if "✅" in type_text or "Success" in type_text:
            is_success = True

    return LogEntry(
        title=full_title,
        raw_content=entry_content,
        tags=tags,
        is_success=is_success,
    )


def strip_category_prefix(title: str) -> str:
    """Strip the category prefix from a title.

    Args:
        title: Full title like "Behavioral Pattern: Agent Did X"

    Returns:
        Title without category prefix, e.g., "Agent Did X"
    """
    # Known category prefixes
    prefixes = [
        "Meta-Framework:",
        "Component-Level:",
        "Behavioral Pattern:",
    ]
    for prefix in prefixes:
        if title.startswith(prefix):
            return title[len(prefix) :].strip()
    return title


def determine_target_file(entry: LogEntry) -> str:
    """Determine which thematic file an entry belongs to.

    Args:
        entry: Parsed log entry

    Returns:
        Filename for the target thematic file
    """
    # Success entries go to technical-successes.md
    if entry.is_success:
        return "technical-successes.md"

    # Check tags against mapping
    for tag in entry.tags:
        tag_lower = tag.lower()
        if tag_lower in TAG_MAPPINGS:
            return TAG_MAPPINGS[tag_lower]

    # Default
    return DEFAULT_FILE


def format_entry_for_append(entry: LogEntry) -> str:
    """Format entry for appending to thematic file.

    Args:
        entry: Parsed log entry

    Returns:
        Formatted entry string to append
    """
    # Get the stripped title
    stripped_title = strip_category_prefix(entry.title)

    # Replace the title in the content
    lines = entry.raw_content.split("\n")
    if lines and lines[0].startswith("## "):
        lines[0] = f"## {stripped_title}"

    # Ensure proper spacing
    formatted = "\n".join(lines)

    # Remove trailing separators (---) but ensure clean ending
    formatted = formatted.rstrip()
    if formatted.endswith("---"):
        formatted = formatted[:-3].rstrip()

    return formatted + "\n\n---\n"


def append_to_file(file_path: Path, entries: Sequence[LogEntry]) -> int:
    """Append entries to a thematic file.

    Args:
        file_path: Path to the thematic file
        entries: List of entries to append

    Returns:
        Number of entries appended

    Raises:
        FileNotFoundError: If target file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Target file does not exist: {file_path}")

    content = file_path.read_text()

    # Find insertion point - before ## Relations section if present
    # Otherwise append at end
    relations_match = re.search(r"^## Relations\s*$", content, re.MULTILINE)

    formatted_entries = "\n".join(format_entry_for_append(e) for e in entries)

    if relations_match:
        # Insert before Relations section
        insert_pos = relations_match.start()
        # Ensure proper spacing
        new_content = (
            content[:insert_pos].rstrip() + "\n\n" + formatted_entries + "\n" + content[insert_pos:]
        )
    else:
        # Append at end
        new_content = content.rstrip() + "\n\n" + formatted_entries

    file_path.write_text(new_content)
    return len(entries)


def migrate_log_entries() -> dict[str, int]:
    """Main migration function.

    Returns:
        Dictionary mapping filenames to entry counts

    Raises:
        ValueError: If ACA_DATA not set
        FileNotFoundError: If LOG.md or target files don't exist
    """
    aca_data = get_aca_data_path()

    log_path = aca_data / "projects/aops/experiments/LOG.md"
    learning_dir = aca_data / "projects/aops/learning"

    if not log_path.exists():
        raise FileNotFoundError(f"LOG.md not found: {log_path}")

    if not learning_dir.exists():
        raise FileNotFoundError(f"Learning directory not found: {learning_dir}")

    # Parse entries
    log_content = log_path.read_text()
    entries = parse_entries(log_content)

    if not entries:
        print("No entries found in LOG.md")
        return {}

    # Group entries by target file
    entries_by_file: dict[str, list[LogEntry]] = {}
    for entry in entries:
        target = determine_target_file(entry)
        if target not in entries_by_file:
            entries_by_file[target] = []
        entries_by_file[target].append(entry)

    # Append entries to each file
    results: dict[str, int] = {}
    for filename, file_entries in entries_by_file.items():
        file_path = learning_dir / filename
        try:
            count = append_to_file(file_path, file_entries)
            results[filename] = count
            print(f"  {filename}: {count} entries")
        except FileNotFoundError as e:
            print(f"  WARNING: {e}")
            results[filename] = 0

    return results


def print_summary(results: dict[str, int]) -> None:
    """Print migration summary.

    Args:
        results: Dictionary mapping filenames to entry counts
    """
    total = sum(results.values())
    print("\n" + "=" * 50)
    print("MIGRATION SUMMARY")
    print("=" * 50)
    print(f"Total entries migrated: {total}")
    print("\nBreakdown by file:")
    for filename, count in sorted(results.items()):
        print(f"  {filename}: {count}")


def main() -> None:
    """Entry point for migration script."""
    print("Migrating LOG.md entries to thematic learning files...")
    print("=" * 50)
    print()

    try:
        results = migrate_log_entries()
        print_summary(results)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
