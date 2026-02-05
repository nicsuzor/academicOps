#!/usr/bin/env python3
"""Task Sync: Update task files when session accomplishments are matched.

This module syncs completed work from session insights to task files:
1. Takes matched task_id from session insights
2. Loads task file from storage
3. Finds related checklist items in body
4. Marks items as [x] with completion date
5. Appends Progress section with session reference
6. Preserves existing content (no deletions)

Usage:
    from lib.task_sync import TaskSyncService

    service = TaskSyncService()
    results = service.sync_accomplishments_to_tasks(insights)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from lib.task_storage import TaskStorage
from lib.task_model import Task


@dataclass
class SyncResult:
    """Result of syncing an accomplishment to a task."""

    task_id: str
    task_title: str
    checklist_items_marked: list[str]
    progress_entry_added: bool
    success: bool
    error: str | None = None


@dataclass
class TaskSyncReport:
    """Summary report of task sync operation."""

    session_id: str
    session_date: str
    tasks_updated: int
    tasks_failed: int
    results: list[SyncResult]


class TaskSyncService:
    """Service for syncing session accomplishments to task files."""

    def __init__(self, storage: TaskStorage | None = None):
        """Initialize task sync service.

        Args:
            storage: TaskStorage instance. Creates new one if not provided.
        """
        self.storage = storage or TaskStorage()

    def sync_accomplishments_to_tasks(
        self,
        insights: dict[str, Any],
    ) -> TaskSyncReport:
        """Sync accomplishments from session insights to task files.

        Args:
            insights: Session insights dictionary with:
                - session_id: Session identifier
                - date: Session date (ISO format)
                - accomplishments: List of accomplishment strings or dicts

        Returns:
            TaskSyncReport with sync results
        """
        session_id = insights.get("session_id", "unknown")
        session_date = insights.get("date", "")
        if isinstance(session_date, datetime):
            session_date = session_date.strftime("%Y-%m-%d")
        elif session_date and "T" in session_date:
            session_date = session_date.split("T")[0]

        accomplishments = insights.get("accomplishments", [])
        results: list[SyncResult] = []

        for accomplishment in accomplishments:
            result = self._sync_single_accomplishment(
                accomplishment,
                session_id,
                session_date,
            )
            if result:
                results.append(result)

        tasks_updated = sum(1 for r in results if r.success)
        tasks_failed = sum(1 for r in results if not r.success)

        return TaskSyncReport(
            session_id=session_id,
            session_date=session_date,
            tasks_updated=tasks_updated,
            tasks_failed=tasks_failed,
            results=results,
        )

    def _sync_single_accomplishment(
        self,
        accomplishment: str | dict[str, Any],
        session_id: str,
        session_date: str,
    ) -> SyncResult | None:
        """Sync a single accomplishment to its matched task.

        Args:
            accomplishment: Accomplishment string or dict with task_id
            session_id: Session identifier for progress entry
            session_date: Session date for progress entry

        Returns:
            SyncResult if task_id was found, None otherwise
        """
        # Extract task_id from accomplishment
        task_id = self._extract_task_id(accomplishment)
        if not task_id:
            return None

        # Extract accomplishment text
        if isinstance(accomplishment, dict):
            text = accomplishment.get("text", accomplishment.get("description", ""))
        else:
            text = str(accomplishment)

        # Load task
        try:
            task = self.storage.get_task(task_id)
            if task is None:
                return SyncResult(
                    task_id=task_id,
                    task_title="",
                    checklist_items_marked=[],
                    progress_entry_added=False,
                    success=False,
                    error=f"Task not found: {task_id}",
                )
        except Exception as e:
            return SyncResult(
                task_id=task_id,
                task_title="",
                checklist_items_marked=[],
                progress_entry_added=False,
                success=False,
                error=f"Failed to load task: {e}",
            )

        # Update task
        try:
            marked_items = self._mark_checklist_items(task, text)
            progress_added = self._add_progress_entry(
                task, text, session_id, session_date
            )

            # Save task
            self.storage.save_task(task)

            return SyncResult(
                task_id=task_id,
                task_title=task.title,
                checklist_items_marked=marked_items,
                progress_entry_added=progress_added,
                success=True,
            )

        except Exception as e:
            return SyncResult(
                task_id=task_id,
                task_title=task.title if task else "",
                checklist_items_marked=[],
                progress_entry_added=False,
                success=False,
                error=f"Failed to update task: {e}",
            )

    def _extract_task_id(self, accomplishment: str | dict[str, Any]) -> str | None:
        """Extract task ID from accomplishment.

        Looks for:
        1. Explicit task_id field in dict
        2. Wikilink reference [[task-id]]
        3. Task ID pattern in text (project-8chars)

        Args:
            accomplishment: Accomplishment string or dict

        Returns:
            Task ID if found, None otherwise
        """
        # Dict with explicit task_id
        if isinstance(accomplishment, dict):
            task_id = accomplishment.get("task_id")
            if task_id:
                return task_id
            text = accomplishment.get("text", accomplishment.get("description", ""))
        else:
            text = str(accomplishment)

        # Look for wikilink [[task-id]]
        wikilink_match = re.search(r"\[\[([a-z]+-[a-f0-9]{8})\]\]", text.lower())
        if wikilink_match:
            return wikilink_match.group(1)

        # Look for task ID pattern (project-8hexchars)
        # Match patterns like aops-a1b2c3d4, framework-12345678, ns-abcdef12
        task_id_match = re.search(r"\b([a-z]+-[a-f0-9]{8})\b", text.lower())
        if task_id_match:
            return task_id_match.group(1)

        return None

    def _mark_checklist_items(self, task: Task, accomplishment_text: str) -> list[str]:
        """Mark matching checklist items as complete in task body.

        Uses fuzzy matching to find checklist items that match the accomplishment.

        Args:
            task: Task to update
            accomplishment_text: Accomplishment text to match

        Returns:
            List of marked item texts
        """
        if not task.body:
            return []

        marked_items: list[str] = []
        lines = task.body.split("\n")
        updated_lines: list[str] = []

        # Normalize accomplishment text for matching
        accomplishment_normalized = self._normalize_for_matching(accomplishment_text)
        accomplishment_words = set(accomplishment_normalized.split())

        for line in lines:
            # Check if line is an incomplete checklist item
            match = re.match(r"^(\s*)-\s*\[ \]\s*(.+)$", line)
            if match:
                indent = match.group(1)
                item_text = match.group(2)

                # Check for match
                if self._items_match(
                    item_text, accomplishment_text, accomplishment_words
                ):
                    # Mark as complete
                    updated_lines.append(f"{indent}- [x] {item_text}")
                    marked_items.append(item_text)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        task.body = "\n".join(updated_lines)
        return marked_items

    def _normalize_for_matching(self, text: str) -> str:
        """Normalize text for fuzzy matching.

        Args:
            text: Text to normalize

        Returns:
            Lowercase, alphanumeric-only text
        """
        # Remove wikilinks but keep content
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        # Remove special characters
        text = re.sub(r"[^\w\s]", " ", text.lower())
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _items_match(
        self,
        item_text: str,
        accomplishment_text: str,
        accomplishment_words: set[str],
    ) -> bool:
        """Check if a checklist item matches an accomplishment.

        Uses word overlap scoring for fuzzy matching.

        Args:
            item_text: Checklist item text
            accomplishment_text: Full accomplishment text
            accomplishment_words: Pre-computed word set for accomplishment

        Returns:
            True if items match
        """
        item_normalized = self._normalize_for_matching(item_text)
        item_words = set(item_normalized.split())

        # Skip very short items (likely generic)
        if len(item_words) < 2:
            return False

        # Calculate word overlap
        overlap = len(item_words & accomplishment_words)

        # Require significant overlap
        # At least 50% of item words should be in accomplishment
        min_overlap = max(2, len(item_words) // 2)

        return overlap >= min_overlap

    def _add_progress_entry(
        self,
        task: Task,
        accomplishment_text: str,
        session_id: str,
        session_date: str,
    ) -> bool:
        """Add a progress entry to task body.

        Args:
            task: Task to update
            accomplishment_text: Accomplishment text
            session_id: Session identifier
            session_date: Session date

        Returns:
            True if entry was added
        """
        # Format entry
        short_session_id = session_id[:8] if len(session_id) > 8 else session_id
        entry = f"- {session_date}: {accomplishment_text} (session: {short_session_id})"

        # Find or create Progress section
        if "## Progress" in task.body:
            # Append to existing section
            lines = task.body.split("\n")
            new_lines: list[str] = []
            in_progress = False
            entry_added = False

            for i, line in enumerate(lines):
                new_lines.append(line)
                if line.strip() == "## Progress":
                    in_progress = True
                elif in_progress and not entry_added:
                    # Add entry after the heading
                    new_lines.append("")
                    new_lines.append(entry)
                    entry_added = True
                    in_progress = False

            if not entry_added:
                # Progress section was at end
                new_lines.append("")
                new_lines.append(entry)

            task.body = "\n".join(new_lines)
        else:
            # Create new Progress section before Relationships
            if "## Relationships" in task.body:
                task.body = task.body.replace(
                    "## Relationships",
                    f"## Progress\n\n{entry}\n\n## Relationships",
                )
            else:
                # Append at end
                task.body = f"{task.body.rstrip()}\n\n## Progress\n\n{entry}"

        return True

    def sync_from_insights_file(self, insights_path: Path) -> TaskSyncReport:
        """Sync accomplishments from an insights JSON file.

        Args:
            insights_path: Path to session insights JSON file

        Returns:
            TaskSyncReport with sync results
        """
        import json

        with open(insights_path, encoding="utf-8") as f:
            insights = json.load(f)

        return self.sync_accomplishments_to_tasks(insights)


def sync_task_from_session(
    task_id: str,
    accomplishment: str,
    session_id: str,
    session_date: str | None = None,
) -> SyncResult:
    """Convenience function to sync a single task.

    Args:
        task_id: Task ID to update
        accomplishment: Accomplishment text
        session_id: Session identifier
        session_date: Session date (defaults to today)

    Returns:
        SyncResult with sync outcome
    """
    if session_date is None:
        session_date = date.today().isoformat()

    service = TaskSyncService()
    insights = {
        "session_id": session_id,
        "date": session_date,
        "accomplishments": [{"task_id": task_id, "text": accomplishment}],
    }

    report = service.sync_accomplishments_to_tasks(insights)
    if report.results:
        return report.results[0]

    return SyncResult(
        task_id=task_id,
        task_title="",
        checklist_items_marked=[],
        progress_entry_added=False,
        success=False,
        error="No result generated",
    )
