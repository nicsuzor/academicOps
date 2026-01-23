#!/usr/bin/env python3
"""Migrate task IDs from legacy format to v2 format.

Migrates task IDs and updates all references:
- Old format: YYYYMMDD-slug or simple-slug
- New format: project-hash8 (e.g., aops-a1b2c3d4)

Updates:
- Task frontmatter (id field)
- File paths (renames files)
- Parent references
- Dependency references (depends_on)
- Wikilinks in task bodies

Usage:
    # Dry run (preview changes)
    uv run python aops-core/scripts/migrate_task_ids.py --dry-run

    # Execute migration
    uv run python aops-core/scripts/migrate_task_ids.py

    # Migrate specific project only
    uv run python aops-core/scripts/migrate_task_ids.py --project aops
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# Add lib to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.task_model import Task, TaskType
from lib.task_storage import TaskStorage
from lib.paths import get_data_root


def is_legacy_id(task_id: str) -> bool:
    """Check if task ID is in legacy format.

    Legacy formats:
    - YYYYMMDD-slug (date-based)
    - simple-slug (no project prefix)

    New format:
    - project-hash8 (e.g., aops-a1b2c3d4)

    Args:
        task_id: Task ID to check

    Returns:
        True if legacy format, False if already v2
    """
    # Check for date-based format (YYYYMMDD-...)
    if re.match(r'^\d{8}-', task_id):
        return True

    # Check if it's already project-hash8 format
    # New format has 8-char hex hash after project prefix
    if re.match(r'^[a-z]+-[0-9a-f]{8}$', task_id):
        return False

    # Everything else is legacy (simple slugs, etc.)
    return True


def generate_new_id(project: str | None) -> str:
    """Generate new v2 format task ID.

    Args:
        project: Project slug (None -> 'ns')

    Returns:
        New ID in format project-hash8
    """
    prefix = project if project else "ns"
    hash_part = uuid.uuid4().hex[:8]
    return f"{prefix}-{hash_part}"


def update_wikilinks(text: str, id_mapping: Dict[str, str]) -> str:
    """Update wikilinks in text using ID mapping.

    Replaces [[old-id]] with [[new-id]] for all mapped IDs.

    Args:
        text: Text containing wikilinks
        id_mapping: Dictionary of old_id -> new_id

    Returns:
        Updated text with new IDs in wikilinks
    """
    for old_id, new_id in id_mapping.items():
        # Match [[old-id]] or [[old-id|display text]]
        pattern = rf'\[\[{re.escape(old_id)}(\|[^\]]+)?\]\]'
        replacement = rf'[[{new_id}\1]]'
        text = re.sub(pattern, replacement, text)

    return text


def create_backup(data_root: Path) -> Path:
    """Create timestamped backup of task directories.

    Args:
        data_root: Root data directory

    Returns:
        Path to backup directory
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = data_root / "backups" / f"tasks-migration-{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    return backup_dir


def migrate_tasks(
    project: str | None = None,
    dry_run: bool = True,
    limit: int | None = None,
) -> Tuple[int, int, Dict[str, str]]:
    """Migrate tasks from legacy IDs to v2 format.

    Args:
        project: Only migrate tasks for this project (None = all)
        dry_run: If True, only preview changes without modifying files
        limit: Maximum number of tasks to migrate (None = all)

    Returns:
        Tuple of (migrated_count, total_count, id_mapping)
    """
    storage = TaskStorage(data_root=get_data_root())

    # Phase 1: Scan all tasks and build ID mapping
    print("=" * 60)
    print("PHASE 1: Scanning tasks and generating new IDs")
    print("=" * 60)

    id_mapping: Dict[str, str] = {}
    tasks_to_migrate: List[Tuple[Task, Path]] = []
    total_count = 0

    for task, task_path in storage._iter_all_tasks_with_paths():
        total_count += 1

        # Filter by project if specified
        if project is not None and task.project != project:
            continue

        # Check if needs migration
        if is_legacy_id(task.id):
            # Check limit before adding more tasks
            if limit is not None and len(tasks_to_migrate) >= limit:
                continue

            old_id = task.id
            new_id = generate_new_id(task.project)
            id_mapping[old_id] = new_id
            tasks_to_migrate.append((task, task_path))

            status = "[DRY RUN]" if dry_run else "[MIGRATE]"
            print(f"{status} {old_id} -> {new_id}")
            print(f"         Title: {task.title}")
            print(f"         Project: {task.project or '(none)'}")
            print(f"         Path: {task_path}")
            print()

    migrated_count = len(tasks_to_migrate)

    print(f"\nFound {migrated_count} tasks to migrate (out of {total_count} total)")
    print(f"ID mapping entries: {len(id_mapping)}")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 60)
        return migrated_count, total_count, id_mapping

    # Phase 2: Update all task references
    print("\n" + "=" * 60)
    print("PHASE 2: Updating references in all tasks")
    print("=" * 60)

    reference_updates = 0
    for task, _task_path in storage._iter_all_tasks_with_paths():
        updated = False

        # Update parent reference
        if task.parent and task.parent in id_mapping:
            old_parent = task.parent
            task.parent = id_mapping[old_parent]
            print(f"Updated parent: {task.id}")
            print(f"  {old_parent} -> {task.parent}")
            updated = True

        # Update dependencies
        if task.depends_on:
            old_deps = task.depends_on.copy()
            task.depends_on = [
                id_mapping.get(dep, dep) for dep in task.depends_on
            ]
            if old_deps != task.depends_on:
                print(f"Updated depends_on: {task.id}")
                print(f"  Old: {old_deps}")
                print(f"  New: {task.depends_on}")
                updated = True

        # Update wikilinks in body
        old_body = task.body
        task.body = update_wikilinks(task.body, id_mapping)
        if old_body != task.body:
            print(f"Updated wikilinks in body: {task.id}")
            updated = True

        if updated:
            reference_updates += 1
            # Save task (will write to existing path first)
            storage.save_task(task)

    print(f"\nUpdated references in {reference_updates} tasks")

    # Phase 3: Migrate task IDs and rename files
    print("\n" + "=" * 60)
    print("PHASE 3: Migrating task IDs and renaming files")
    print("=" * 60)

    for task, old_path in tasks_to_migrate:
        old_id = task.id
        new_id = id_mapping[old_id]

        # Update task ID
        task.id = new_id

        # Get new path
        new_path = storage._get_task_path(task)

        print(f"Migrating: {old_id} -> {new_id}")
        print(f"  Old path: {old_path}")
        print(f"  New path: {new_path}")

        # Save task with new ID (creates new file)
        storage.save_task(task)

        # Delete old file if it's different from new file
        if old_path != new_path and old_path.exists():
            old_path.unlink()
            print(f"  Deleted old file: {old_path}")

        print()

    print("=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"Migrated: {migrated_count} tasks")
    print(f"Updated references in: {reference_updates} tasks")
    print(f"Total tasks: {total_count}")

    # Save ID mapping for reference
    mapping_file = get_data_root() / "tasks" / "id_mapping.json"
    mapping_file.parent.mkdir(parents=True, exist_ok=True)
    with open(mapping_file, 'w') as f:
        json.dump(id_mapping, f, indent=2)
    print(f"\nID mapping saved to: {mapping_file}")

    return migrated_count, total_count, id_mapping


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate task IDs from legacy format to v2 format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Only migrate tasks for specific project",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of tasks to migrate (for testing)",
    )

    args = parser.parse_args()

    print("Task ID Migration Script")
    print("=" * 60)
    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
    else:
        print("MODE: LIVE MIGRATION")
    if args.project:
        print(f"PROJECT: {args.project}")
    else:
        print("PROJECT: ALL")
    print()

    try:
        migrated, total, mapping = migrate_tasks(
            project=args.project,
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print("\nTo execute migration, run:")
            if args.project:
                print(f"  uv run python aops-core/scripts/migrate_task_ids.py --project {args.project}")
            else:
                print("  uv run python aops-core/scripts/migrate_task_ids.py")

        return 0

    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
