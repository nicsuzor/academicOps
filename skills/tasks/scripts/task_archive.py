#!/usr/bin/env python3
"""Archive/unarchive tasks using shared task operations library.

Usage:
    uv run python bots/skills/tasks/scripts/task_archive.py <task_filename> [task_filename2 ...] [options]

Examples:
    uv run python scripts/task_archive.py "20251110-abc123.md"
    uv run python scripts/task_archive.py task1.md task2.md task3.md
    uv run python scripts/task_archive.py "20251110-abc123" --unarchive

Options:
    --unarchive     Move task back to inbox (unarchive)
    --data-dir=PATH Use custom data directory
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from bots.skills.tasks import task_ops


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Archive or unarchive tasks (supports batch operations)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "filenames",
        nargs="+",
        help="Task filename(s) or identifiers (with or without .md extension, or index if you've run task_view.py)",
    )
    parser.add_argument(
        "--unarchive",
        action="store_true",
        help="Move task back to inbox (unarchive)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory path (default: $ACA/data or ./data)",
    )

    args = parser.parse_args()

    # Initialize data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        ACA = os.environ.get("ACA")
        data_dir = Path(ACA) / "data" if ACA else Path().cwd() / "data"

    # Process each file
    results = []
    success_count = 0
    failure_count = 0

    for identifier in args.filenames:
        # Archive or unarchive using shared library
        try:
            if args.unarchive:
                result = task_ops.unarchive_task(identifier, data_dir)
            else:
                # Try to resolve identifier (supports index-based)
                try:
                    filename = task_ops.resolve_identifier(identifier, data_dir)
                    result = task_ops.archive_task(filename, data_dir)
                except ValueError:
                    # Not an index, use as-is
                    result = task_ops.archive_task(identifier, data_dir)

            results.append((identifier, result))
            if result["success"]:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            results.append((identifier, {
                "success": False,
                "message": f"Unexpected error: {e}"
            }))
            failure_count += 1

    # Report results
    for identifier, result in results:
        if result["success"]:
            print(f"✓ {result['message']}")
            if "from" in result and "to" in result:
                print(f"  {result['from']} → {result['to']}")
        else:
            print(f"✗ {result['message']}", file=sys.stderr)

    # Summary if multiple files
    if len(results) > 1:
        print(
            f"\nProcessed {len(results)} tasks: {success_count} succeeded, {failure_count} failed"
        )

    # Exit with failure if any failed
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
