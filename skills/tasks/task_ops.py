"""Shared task operations library.

Core task management operations extracted from existing scripts.
Used by both MCP server and CLI scripts.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from skills.tasks.models import Subtask, Task


class TaskDirectoryNotFoundError(Exception):
    """Raised when data directory doesn't exist."""


class InvalidTaskFormatError(Exception):
    """Raised when task file has invalid format."""


class TaskNotFoundError(Exception):
    """Raised when task file doesn't exist."""


def sanitize_slug(slug: str, max_length: int = 50) -> str:
    """Sanitize slug to lowercase alphanumeric-plus-hyphens format.

    Args:
        slug: Input string to sanitize
        max_length: Maximum length for result (default: 50)

    Returns:
        Sanitized slug string

    Raises:
        ValueError: If result is empty after sanitization
    """
    # Convert to lowercase
    result = slug.lower()

    # Replace non-alphanumeric chars with hyphens
    result = re.sub(r"[^a-z0-9]+", "-", result)

    # Collapse multiple hyphens to single hyphen
    result = re.sub(r"-+", "-", result)

    # Strip leading/trailing hyphens
    result = result.strip("-")

    # Truncate to max_length
    result = result[:max_length]

    # Fail fast if empty
    if not result:
        msg = f"Sanitized slug is empty for input: {slug!r}"
        raise ValueError(msg)

    return result


def get_data_dir(data_dir_override: Path | None = None) -> Path:
    """Get data directory path with fail-fast validation.

    Args:
        data_dir_override: Optional explicit data directory path

    Returns:
        Validated Path to data directory

    Raises:
        TaskDirectoryNotFoundError: If data directory doesn't exist
    """
    if data_dir_override:
        data_dir = data_dir_override
    else:
        # Use ACA_DATA environment variable
        aca_data = os.environ.get("ACA_DATA")
        if not aca_data:
            msg = "ACA_DATA environment variable not set"
            raise TaskDirectoryNotFoundError(msg)
        data_dir = Path(aca_data)

    if not data_dir.exists():
        msg = f"Data directory not found: {data_dir}. Set $ACA_DATA to valid path."
        raise TaskDirectoryNotFoundError(msg)

    return data_dir


def _parse_frontmatter(content: str, filename: str) -> dict[str, Any]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown file content
        filename: Filename for error messages

    Returns:
        Parsed frontmatter dictionary

    Raises:
        InvalidTaskFormatError: If frontmatter is invalid
    """
    if not content.startswith("---"):
        msg = f"No frontmatter in {filename}: must start with ---"
        raise InvalidTaskFormatError(msg)

    parts = content.split("---", 2)
    if len(parts) < 3:
        msg = f"Invalid frontmatter in {filename}"
        raise InvalidTaskFormatError(msg)

    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        msg = f"YAML parse error in {filename}: {e}"
        raise InvalidTaskFormatError(msg) from e

    if not isinstance(frontmatter, dict):
        msg = f"Frontmatter is not a dictionary in {filename}"
        raise InvalidTaskFormatError(msg)

    return frontmatter


def _extract_context_section(raw_body: str) -> str:
    """Extract Context section from properly formatted body.

    Args:
        raw_body: Full body content after frontmatter

    Returns:
        Extracted context text or original body if no Context section
    """
    if "## Context" not in raw_body:
        return raw_body

    context_start = raw_body.find("## Context")
    context_section = raw_body[context_start:]
    lines = context_section.split("\n")

    context_lines = []
    for line in lines[1:]:  # Skip "## Context" line
        if line.strip().startswith("##"):
            break
        context_lines.append(line)

    return "\n".join(context_lines).strip()


def _parse_subtasks(raw_body: str) -> list[Subtask]:
    """Parse checkbox subtasks from task body.

    Matches markdown checkbox format: - [ ] text or - [x] text

    Args:
        raw_body: Full body content after frontmatter

    Returns:
        List of Subtask objects
    """
    subtasks = []
    # Match: - [ ] text  or  - [x] text  (case insensitive x)
    pattern = re.compile(r"^-\s*\[([ xX])\]\s+(.+)$", re.MULTILINE)

    for match in pattern.finditer(raw_body):
        checkbox = match.group(1)
        text = match.group(2).strip()
        completed = checkbox.lower() == "x"
        subtasks.append(Subtask(text=text, completed=completed))

    return subtasks


def _parse_iso_timestamp(ts: str | datetime | None) -> datetime | None:
    """Parse ISO timestamp string to datetime.

    Args:
        ts: Timestamp string, datetime, or None

    Returns:
        Parsed datetime with timezone or None
    """
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts

    try:
        s = str(ts)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def _extract_priority_from_tags(tags: list[Any]) -> int | None:
    """Extract priority value from priority-pN tags.

    Args:
        tags: List of tag strings

    Returns:
        Priority integer or None if not found
    """
    if not isinstance(tags, list):
        return None

    for tag in tags:
        if isinstance(tag, str) and tag.startswith("priority-p"):
            try:
                return int(tag.replace("priority-p", ""))
            except (ValueError, IndexError):
                pass

    return None


def load_task_from_file(file_path: Path) -> Task:
    """Load task from markdown file with YAML frontmatter.

    Args:
        file_path: Path to task markdown file

    Returns:
        Task model populated from file

    Raises:
        TaskNotFoundError: If file doesn't exist
        InvalidTaskFormatError: If file format is invalid
    """
    if not file_path.exists():
        msg = f"Task file not found: {file_path}"
        raise TaskNotFoundError(msg)

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        msg = f"Cannot read {file_path}: {e}"
        raise InvalidTaskFormatError(msg) from e

    # Parse frontmatter and body
    frontmatter = _parse_frontmatter(content, file_path.name)
    raw_body = content.split("---", 2)[2].strip()
    body = _extract_context_section(raw_body)

    # Extract priority from frontmatter or tags
    priority = frontmatter.get("priority")
    if priority is None:
        priority = _extract_priority_from_tags(frontmatter.get("tags", []))

    # Parse subtasks from body
    subtasks = _parse_subtasks(raw_body)

    # Build Task model
    return Task(
        title=frontmatter.get("title", "Untitled"),
        priority=priority,
        type=frontmatter.get("type", "todo"),
        project=frontmatter.get("project"),
        classification=frontmatter.get("classification"),
        created=_parse_iso_timestamp(frontmatter.get("created")) or datetime.now(UTC),
        due=_parse_iso_timestamp(frontmatter.get("due")),
        status=frontmatter.get("status", "inbox"),
        archived_at=_parse_iso_timestamp(frontmatter.get("archived_at")),
        tags=frontmatter.get("tags", []),
        filename=file_path.name,
        body=body,
        subtasks=subtasks,
    )


def save_task_to_file(task: Task, file_path: Path) -> None:
    """Save task to markdown file with properly formatted YAML frontmatter.

    Generates format with:
    - Proper frontmatter (permalink, task_id, aliases, etc.)
    - Structured body (# Title, ## Context, ## Observations, ## Relations)

    Args:
        task: Task model to save
        file_path: Destination file path

    Raises:
        IOError: If file cannot be written
    """
    # Extract task ID from filename (YYYYMMDD-xxxxxxxx)
    task_id = file_path.stem  # filename without .md

    # Build properly formatted frontmatter
    frontmatter: dict[str, Any] = {
        "title": task.title,
        "permalink": f"{task_id}-1",  # permalink format
        "type": "task",  # consistent type
        "tags": task.tags,
        "created": task.created.isoformat(),
        "modified": datetime.now(UTC).isoformat(),
        "task_id": task_id,
        "status": task.status,
        "aliases": [task_id],
    }

    # Add optional fields
    if task.priority is not None:
        frontmatter["priority"] = task.priority
    if task.project:
        frontmatter["project"] = task.project
    if task.classification:
        frontmatter["classification"] = task.classification
    if task.due:
        frontmatter["due"] = task.due.isoformat()
    if task.archived_at:
        frontmatter["archived_at"] = task.archived_at.isoformat()

    # Add metadata dict if we have project-specific data
    # (for now, just placeholder - can extend later)
    metadata_dict = {}
    if metadata_dict:
        frontmatter["metadata"] = metadata_dict

    # Serialize to YAML
    yaml_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)

    # Build properly formatted body structure
    # Extract context from body if it exists, otherwise use title
    body_content = task.body or ""

    # Build structured body
    body_parts = [
        f"# {task.title}",
        "",
        "## Context",
        "",
        body_content if body_content else f"Task: {task.title}",
        "",
        "## Observations",
        "",
        # Add priority tag if set
        f"- [task] {task.title} #status-{task.status}"
        + (f" #priority-p{task.priority}" if task.priority is not None else ""),
    ]

    # Add classification observation only if classification is set
    # (don't duplicate what's in frontmatter)

    # Add project tag if set
    if task.project:
        body_parts.append(
            f"- [project] Project: {task.project} #project-{task.project}"
        )

    body_parts.extend(
        [
            "",
            "## Relations",
            "",
        ]
    )

    structured_body = "\n".join(body_parts)

    # Combine frontmatter and body
    content = f"---\n{yaml_str}---\n{structured_body}"

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write file
    try:
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        msg = f"Failed to write {file_path}: {e}"
        raise OSError(msg) from e


def _load_tasks_from_directory(
    directory: Path, skip_archived: bool = False
) -> list[Task]:
    """Load all valid tasks from a directory.

    Args:
        directory: Directory to scan for task files
        skip_archived: Whether to skip tasks with archived_at set

    Returns:
        List of successfully loaded tasks
    """
    tasks: list[Task] = []

    if not directory.exists():
        return tasks

    for file_path in directory.glob("*.md"):
        try:
            task = load_task_from_file(file_path)
            if skip_archived and task.archived_at:
                continue
            tasks.append(task)
        except (InvalidTaskFormatError, TaskNotFoundError):
            # Skip invalid tasks
            continue

    return tasks


def load_all_tasks(data_dir: Path, include_archived: bool = False) -> list[Task]:
    """Load all tasks from inbox and queue directories.

    Args:
        data_dir: Data directory path
        include_archived: Whether to include archived tasks

    Returns:
        List of Task models
    """
    tasks: list[Task] = []

    # Load from inbox and queue
    tasks.extend(
        _load_tasks_from_directory(data_dir / "tasks/inbox", not include_archived)
    )
    tasks.extend(
        _load_tasks_from_directory(data_dir / "tasks/queue", not include_archived)
    )

    # Load from archived if requested
    if include_archived:
        tasks.extend(
            _load_tasks_from_directory(data_dir / "tasks/archived", skip_archived=False)
        )

    return tasks


def find_task_file(filename: str, data_dir: Path) -> Path | None:
    """Find task file in inbox or queue directories.

    Args:
        filename: Task filename (with or without .md extension)
        data_dir: Data directory path

    Returns:
        Path to task file or None if not found
    """
    if not filename.endswith(".md"):
        filename = filename + ".md"

    inbox = data_dir / "tasks/inbox"
    queue = data_dir / "tasks/queue"

    # Check inbox first
    inbox_path = inbox / filename
    if inbox_path.exists():
        return inbox_path

    # Check queue
    queue_path = queue / filename
    if queue_path.exists():
        return queue_path

    return None


def find_archived_task_file(filename: str, data_dir: Path) -> Path | None:
    """Find task file in archived directory.

    Args:
        filename: Task filename (with or without .md extension)
        data_dir: Data directory path

    Returns:
        Path to archived task file or None if not found
    """
    if not filename.endswith(".md"):
        filename = filename + ".md"

    archived = data_dir / "tasks/archived"
    archived_path = archived / filename

    if archived_path.exists():
        return archived_path

    return None


def resolve_identifier(identifier: str, data_dir: Path) -> str:
    """Resolve task identifier to filename.

    Supports multiple identifier formats:
    - Index from current view: "3", "#3" → resolves from current_view.json
    - Task ID without extension: "20251110-abc123" → adds .md
    - Full filename: "20251110-abc123.md" → used as-is

    Args:
        identifier: Task identifier in any supported format
        data_dir: Data directory path

    Returns:
        Resolved filename (with .md extension)

    Raises:
        ValueError: If identifier format is invalid or index cannot be resolved
    """
    # Remove # prefix if present
    clean_id = identifier.strip()
    if clean_id.startswith("#"):
        clean_id = clean_id[1:]

    # Check if it's a numeric index
    if clean_id.isdigit():
        index = int(clean_id)

        # Try to resolve from current_view.json
        view_path = data_dir / "views/current_view.json"
        if not view_path.exists():
            msg = (
                f"Cannot resolve index #{index}: no current view. "
                f"Run view_tasks first to generate index mapping."
            )
            raise ValueError(msg)

        try:
            view_data = json.loads(view_path.read_text(encoding="utf-8"))
            tasks = view_data.get("tasks", [])

            # Find task with matching index
            for task in tasks:
                # Check both 'index' field and list position
                task_index = task.get("index")
                if task_index == index:
                    filename = task.get("filename")
                    if not filename:
                        msg = f"Task at index #{index} has no filename in view"
                        raise ValueError(msg)
                    return filename

            # Index not found in current view
            total = view_data.get("total_tasks", 0)
            displayed = view_data.get("displayed_range", "unknown")
            msg = (
                f"Index #{index} not found in current view "
                f"(showing {displayed} of {total} tasks). "
                f"Try view_tasks with different page or filters."
            )
            raise ValueError(msg)

        except json.JSONDecodeError as e:
            msg = f"Cannot parse current view: {e}"
            raise ValueError(msg) from e

    # Not an index - treat as filename/task-id
    # If it already has .md extension, use as-is
    if clean_id.endswith(".md"):
        return clean_id

    # Otherwise add .md extension
    return clean_id + ".md"


def archive_task(filename: str, data_dir: Path) -> dict[str, Any]:
    """Archive a task by moving it to archived folder.

    Args:
        filename: Task filename
        data_dir: Data directory path

    Returns:
        Result dictionary with success status and message
    """
    # Find task in inbox or queue
    task_path = find_task_file(filename, data_dir)
    if not task_path:
        return {"success": False, "message": f"Task not found: {filename}"}

    # Load and update task
    try:
        task = load_task_from_file(task_path)
        task.status = "archived"
        task.archived_at = datetime.now(UTC)
    except Exception as e:
        return {"success": False, "message": f"Failed to load task: {e}"}

    # Save to archived location
    archived_dir = data_dir / "tasks/archived"
    archived_dir.mkdir(parents=True, exist_ok=True)
    archived_path = archived_dir / task_path.name

    try:
        save_task_to_file(task, archived_path)
        # Remove original
        task_path.unlink()

        return {
            "success": True,
            "message": f"Archived: {task_path.name}",
            "from": str(task_path.relative_to(data_dir)),
            "to": str(archived_path.relative_to(data_dir)),
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to archive task: {e}"}


def unarchive_task(filename: str, data_dir: Path) -> dict[str, Any]:
    """Unarchive a task by moving it back to inbox.

    Args:
        filename: Task filename
        data_dir: Data directory path

    Returns:
        Result dictionary with success status and message
    """
    # Find task in archived
    task_path = find_archived_task_file(filename, data_dir)
    if not task_path:
        return {"success": False, "message": f"Archived task not found: {filename}"}

    # Load and update task
    try:
        task = load_task_from_file(task_path)
        task.status = "inbox"
        task.archived_at = None
    except Exception as e:
        return {"success": False, "message": f"Failed to load task: {e}"}

    # Save to inbox location
    inbox_dir = data_dir / "tasks/inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    inbox_path = inbox_dir / task_path.name

    try:
        save_task_to_file(task, inbox_path)
        # Remove from archived
        task_path.unlink()

        return {
            "success": True,
            "message": f"Unarchived: {task_path.name}",
            "from": str(task_path.relative_to(data_dir)),
            "to": str(inbox_path.relative_to(data_dir)),
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to unarchive task: {e}"}


def _apply_field_updates(
    task: Task, modified_fields: list[str], **updates: Any
) -> None:
    """Apply field updates to task and track changes.

    Args:
        task: Task to modify
        modified_fields: List to append modified field names to
        **updates: Field name to value mapping (None values are skipped)
    """
    field_map = {
        "title": "title",
        "priority": "priority",
        "project": "project",
        "classification": "classification",
        "due": "due",
        "status": "status",
        "body": "body",
    }

    for field_name, attr_name in field_map.items():
        value = updates.get(field_name)
        if value is not None:
            setattr(task, attr_name, value)
            modified_fields.append(field_name)


def _apply_tag_operations(
    task: Task,
    modified_fields: list[str],
    add_tags: list[str] | None,
    remove_tags: list[str] | None,
) -> None:
    """Apply tag add/remove operations to task.

    Args:
        task: Task to modify
        modified_fields: List to append operation names to
        add_tags: Tags to add
        remove_tags: Tags to remove
    """
    if add_tags:
        for tag in add_tags:
            if tag not in task.tags:
                task.tags.append(tag)
        modified_fields.append("tags (added)")

    if remove_tags:
        for tag in remove_tags:
            if tag in task.tags:
                task.tags.remove(tag)
        modified_fields.append("tags (removed)")


def modify_task(
    identifier: str,
    data_dir: Path,
    title: str | None = None,
    priority: int | None = None,
    project: str | None = None,
    classification: str | None = None,
    due: datetime | None = None,
    status: str | None = None,
    body: str | None = None,
    add_tags: list[str] | None = None,
    remove_tags: list[str] | None = None,
) -> dict[str, Any]:
    """Modify an existing task.

    Args:
        identifier: Task identifier (index, task ID, or filename)
        data_dir: Data directory path
        title: New title (optional)
        priority: New priority (optional)
        project: New project (optional)
        classification: New classification (optional)
        due: New due date (optional)
        status: New status (optional)
        body: New body content (optional)
        add_tags: Tags to add (optional)
        remove_tags: Tags to remove (optional)

    Returns:
        Result dictionary with success status, modified fields, and task info
    """
    # Resolve identifier to filename
    try:
        filename = resolve_identifier(identifier, data_dir)
    except ValueError as e:
        return {"success": False, "message": f"Cannot resolve identifier: {e}"}

    # Find task file
    task_path = find_task_file(filename, data_dir)
    if not task_path:
        return {"success": False, "message": f"Task not found: {filename}"}

    # Load existing task
    try:
        task = load_task_from_file(task_path)
    except Exception as e:
        return {"success": False, "message": f"Failed to load task: {e}"}

    # Apply modifications
    modified_fields: list[str] = []
    _apply_field_updates(
        task,
        modified_fields,
        title=title,
        priority=priority,
        project=project,
        classification=classification,
        due=due,
        status=status,
        body=body,
    )
    _apply_tag_operations(task, modified_fields, add_tags, remove_tags)

    # Save updated task
    try:
        save_task_to_file(task, task_path)
        return {
            "success": True,
            "message": f"Modified task: {filename}",
            "modified_fields": modified_fields,
            "task_id": task_path.stem,
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to save modified task: {e}"}


def list_tasks(
    data_dir: Path,
    include_archived: bool = False,
    priority: int | None = None,
    project: str | None = None,
    status: str | None = None,
) -> list[Task]:
    """List tasks with optional filtering.

    Args:
        data_dir: Data directory path
        include_archived: Whether to include archived tasks
        priority: Filter by priority level
        project: Filter by project slug
        status: Filter by status

    Returns:
        Filtered list of Task models
    """
    tasks = load_all_tasks(data_dir, include_archived=include_archived)

    # Apply filters
    if priority is not None:
        tasks = [t for t in tasks if t.priority == priority]

    if project is not None:
        tasks = [t for t in tasks if t.project == project]

    if status is not None:
        tasks = [t for t in tasks if t.status == status]

    return tasks


def create_task(
    title: str,
    data_dir: Path,
    priority: int | None = None,
    task_type: str = "todo",
    project: str | None = None,
    due: datetime | None = None,
    body: str = "",
    tags: list[str] | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """Create a new task.

    Args:
        title: Task title (required)
        data_dir: Data directory path
        priority: Priority level 0-3
        task_type: Task type
        project: Project slug
        due: Due date
        body: Task body content
        tags: Task tags
        slug: Optional slug for task_id (sanitized if provided)

    Returns:
        Result dictionary with task_id, filename, path, and success status
    """
    # Generate task ID: YYYYMMDD-slug (use sanitized title if no slug provided)
    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    sanitized = sanitize_slug(slug if slug else title)
    task_id = f"{timestamp}-{sanitized}"
    filename = f"{task_id}.md"

    # Check for duplicate slug
    inbox_dir = data_dir / "tasks/inbox"
    potential_path = inbox_dir / filename
    if potential_path.exists():
        return {
            "success": False,
            "message": f"Task with slug '{sanitized}' already exists for today: {filename}",
        }

    # Create task model
    task = Task(
        title=title,
        priority=priority,
        type=task_type,
        project=project,
        created=datetime.now(UTC),
        due=due,
        status="inbox",
        tags=tags or [],
        filename=filename,
        body=body,
    )

    # Save to inbox
    inbox_dir = data_dir / "tasks/inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    task_path = inbox_dir / filename

    try:
        save_task_to_file(task, task_path)

        return {
            "success": True,
            "task_id": task_id,
            "filename": filename,
            "path": str(task_path.relative_to(data_dir)),
            "message": f"Created task: {filename}",
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create task: {e}",
        }
