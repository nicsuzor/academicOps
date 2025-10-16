#!/usr/bin/env python3
"""
Check for orphaned instruction and documentation files.

Analyzes markdown files to find documentation that is never referenced in any
loading path. Useful for maintaining the instruction system and preventing
documentation drift.

Exit codes:
    0 - No orphans found (or only non-critical orphans)
    1 - Critical orphans found (files in critical paths not referenced)
    2 - Script error
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

# Critical paths where orphans should cause CI failure
CRITICAL_PATHS = [
    "agents/",
    "docs/INSTRUCTIONS.md",
    "docs/INDEX.md",
    "docs/modes.md",
    "docs/error-",
    "docs/AUTO-EXTRACTION.md",
    "docs/PATH-RESOLUTION.md",
]

# Paths to exclude from analysis
EXCLUDE_PATTERNS = [
    "papers/",
    "vendor/",
    "node_modules/",
    ".venv/",
    "dbt_packages/",
    "archive/",
    "lib/",
    ".pytest_cache/",
    "bower_components/",
]


def should_exclude(path: Path, exclude_patterns: list[str]) -> bool:
    """Check if path should be excluded from analysis."""
    path_str = str(path)
    return any(excl in path_str for excl in exclude_patterns)


def extract_references(content: str) -> set[str]:
    """Extract markdown file references from content."""
    refs = set()

    # Extract markdown link targets
    for match in re.finditer(r"\[([^\]]+)\]\(([^)]+\.md)\)", content):
        refs.add(match.group(2))

    # Extract backtick references
    for match in re.finditer(r"`([^`]*\.md)`", content):
        refs.add(match.group(1))

    # Extract "Read X" style references
    for match in re.finditer(
        r"(?:Read|See|Consult|refer to|Check for|Look for)\s+([^\s,]+\.md)",
        content,
        re.IGNORECASE,
    ):
        refs.add(match.group(1))

    return refs


def find_markdown_files(root: Path, exclude_patterns: list[str]) -> list[Path]:
    """Find all relevant markdown files."""
    files = []
    for pattern in [
        "**/docs/**/*.md",
        "**/{CLAUDE,INSTRUCTIONS,README}.md",
        "**/agents/*.md",
    ]:
        for p in root.glob(pattern):
            if p.is_file() and not should_exclude(p, exclude_patterns):
                files.append(p)
    return files


def analyze_references(
    root: Path, exclude_patterns: list[str]
) -> tuple[dict[str, set[str]], set[str]]:
    """
    Analyze file references.

    Returns:
        Tuple of (references dict, all referenced files set)
    """
    md_files = find_markdown_files(root, exclude_patterns)
    references = defaultdict(set)

    for md_file in md_files:
        try:
            content = md_file.read_text()
            refs = extract_references(content)
            if refs:
                rel_path = str(md_file.relative_to(root))
                references[rel_path] = refs
        except Exception as e:
            print(f"Warning: Error reading {md_file}: {e}", file=sys.stderr)

    # Collect all referenced files
    all_referenced = set()
    for refs in references.values():
        all_referenced.update(refs)

    return references, all_referenced


def find_orphans(root: Path, exclude_patterns: list[str]) -> dict[str, list[str]]:
    """
    Find orphaned markdown files.

    Returns:
        Dict with 'critical' and 'non_critical' lists of orphaned files
    """
    references, all_referenced = analyze_references(root, exclude_patterns)

    # Get all markdown files
    all_files = {
        str(p.relative_to(root)) for p in find_markdown_files(root, exclude_patterns)
    }

    # Files that are never referenced
    never_referenced = all_files - all_referenced - set(references.keys())

    # Filter to documentation/instruction files
    orphans = {
        f
        for f in never_referenced
        if any(
            pattern in f
            for pattern in ["docs/", "INSTRUCTIONS", "CLAUDE", "agents/", "README"]
        )
    }

    # Categorize orphans
    critical = []
    non_critical = []

    for orphan in sorted(orphans):
        is_critical = any(pattern in orphan for pattern in CRITICAL_PATHS)
        if is_critical:
            critical.append(orphan)
        else:
            non_critical.append(orphan)

    return {"critical": critical, "non_critical": non_critical}


def main():
    """Main entry point."""
    # Determine root directory
    script_dir = Path(__file__).parent
    root = script_dir.parent  # Assumes script is in bot/scripts/

    # Check if we're in the bot submodule or parent repo
    if (root / ".git").exists() and (root / "agents").exists():
        # We're in the bot submodule
        analysis_root = root
        context = "academicOps (bot)"
    elif (root.parent / "bot").exists():
        # We're in parent repo, check bot submodule
        analysis_root = root.parent / "bot"
        context = "academicOps (from parent)"
    else:
        # Try current directory
        analysis_root = Path.cwd()
        context = "current directory"

    print(f"Analyzing instruction files in: {context}")
    print(f"Root: {analysis_root}")
    print()

    orphans = find_orphans(analysis_root, EXCLUDE_PATTERNS)

    # Report findings
    exit_code = 0

    if orphans["critical"]:
        print("❌ CRITICAL ORPHANED FILES FOUND:")
        print("=" * 80)
        print("These files are in critical paths but not referenced anywhere:")
        print()
        for orphan in orphans["critical"]:
            print(f"  - {orphan}")
        print()
        print("Critical files should be referenced in the loading hierarchy.")
        print("Add references from parent files or move to non-critical locations.")
        exit_code = 1

    if orphans["non_critical"]:
        print("⚠️  Non-critical orphaned files:")
        print("=" * 80)
        for orphan in orphans["non_critical"]:
            print(f"  - {orphan}")
        print()
        print("These files may be user-facing documentation or reference material.")
        print("Consider linking them or moving to an archive/ folder.")

    if not orphans["critical"] and not orphans["non_critical"]:
        print("✅ No orphaned instruction files found.")
        print("All documentation appears to be properly linked.")

    print()
    print(f"Exit code: {exit_code}")
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(2)
