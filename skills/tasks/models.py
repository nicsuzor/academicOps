"""Pydantic models for task management.

Type-safe models for MCP tool inputs and outputs with validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TaskFilter(BaseModel):
    """Filter criteria for viewing tasks."""

    priority: list[int] | None = Field(
        default=None,
        description="Filter by priority levels (0-3)",
    )
    project: str | None = Field(default=None, description="Filter by project slug")
    status: str | None = Field(default=None, description="Filter by status")
    classification: str | None = Field(
        default=None, description="Filter by classification type"
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: list[int] | None) -> list[int] | None:
        """Validate priority values are in valid range."""
        if v is None:
            return v
        for p in v:
            if p < 0 or p > 3:
                msg = f"Priority must be 0-3, got {p}"
                raise ValueError(msg)
        return v


class ViewTasksRequest(BaseModel):
    """Request parameters for view_tasks tool."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(
        default=10, ge=1, le=100, description="Tasks per page (max 100)"
    )
    sort: Literal["priority", "date", "due"] = Field(
        default="priority", description="Sort order"
    )
    compact: bool = Field(
        default=False, description="Compact one-line format vs full details"
    )
    filters: TaskFilter | None = Field(default=None, description="Filter criteria")


class Task(BaseModel):
    """Task data model."""

    title: str = Field(description="Task title")
    priority: int | None = Field(default=None, ge=0, le=3, description="Priority 0-3")
    type: str = Field(default="todo", description="Task type")
    project: str | None = Field(default=None, description="Project slug")
    classification: str | None = Field(default=None, description="Classification type")
    created: datetime = Field(description="Creation timestamp")
    due: datetime | None = Field(default=None, description="Due date")
    status: str = Field(default="inbox", description="Task status")
    archived_at: datetime | None = Field(default=None, description="Archive timestamp")
    tags: list[str] = Field(default_factory=list, description="Tags")
    filename: str | None = Field(default=None, description="Source filename")
    body: str | None = Field(default=None, description="Task body content")


class ViewTasksResponse(BaseModel):
    """Response from view_tasks tool."""

    success: bool = Field(description="Operation success status")
    total_tasks: int = Field(description="Total tasks matching filters")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Tasks per page")
    tasks: list[Task] = Field(description="Task list for current page")
    message: str | None = Field(default=None, description="Optional status message")


class ArchiveTasksRequest(BaseModel):
    """Request parameters for archive_tasks tool."""

    identifiers: list[str] = Field(
        min_length=1,
        description="Task identifiers to archive (index, task ID, or filename)",
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Ensure identifiers are non-empty strings."""
        if not v:
            msg = "At least one identifier required"
            raise ValueError(msg)
        for identifier in v:
            if not identifier or not identifier.strip():
                msg = "Identifier cannot be empty"
                raise ValueError(msg)
        return v


class ArchiveResult(BaseModel):
    """Result for a single archive operation."""

    model_config = {"populate_by_name": True}

    success: bool = Field(description="Operation success")
    message: str = Field(description="Status or error message")
    from_path: str | None = Field(default=None, alias="from", description="Source path")
    to_path: str | None = Field(
        default=None, alias="to", description="Destination path"
    )
    resolved_from: str | None = Field(default=None, description="Original identifier")
    identifier: str | None = Field(default=None, description="Identifier used")


class ArchiveTasksResponse(BaseModel):
    """Response from archive_tasks tool."""

    success: bool = Field(description="Overall operation success")
    results: list[ArchiveResult] = Field(
        description="Per-file results with status and message"
    )
    success_count: int = Field(description="Number of successful operations")
    failure_count: int = Field(description="Number of failed operations")


class UnarchiveTasksRequest(BaseModel):
    """Request parameters for unarchive_tasks tool."""

    identifiers: list[str] = Field(
        min_length=1, description="Task identifiers to unarchive (task ID or filename)"
    )

    @field_validator("identifiers")
    @classmethod
    def validate_identifiers(cls, v: list[str]) -> list[str]:
        """Ensure identifiers are non-empty strings."""
        if not v:
            msg = "At least one identifier required"
            raise ValueError(msg)
        for identifier in v:
            if not identifier or not identifier.strip():
                msg = "Identifier cannot be empty"
                raise ValueError(msg)
        return v


class UnarchiveTasksResponse(BaseModel):
    """Response from unarchive_tasks tool."""

    success: bool = Field(description="Overall operation success")
    results: list[ArchiveResult] = Field(
        description="Per-file results with status and message"
    )
    success_count: int = Field(description="Number of successful operations")
    failure_count: int = Field(description="Number of failed operations")


class CreateTaskRequest(BaseModel):
    """Request parameters for create_task tool."""

    title: str = Field(min_length=1, description="Task title (required)")
    priority: int | None = Field(default=None, ge=0, le=3, description="Priority 0-3")
    type: str = Field(default="todo", description="Task type")
    project: str | None = Field(default=None, description="Project slug")
    due: datetime | None = Field(default=None, description="Due date")
    body: str = Field(default="", description="Task body content")
    tags: list[str] = Field(default_factory=list, description="Task tags")
    slug: str | None = Field(default=None, description="Optional slug for human-readable task ID")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is non-empty."""
        if not v.strip():
            msg = "Title cannot be empty"
            raise ValueError(msg)
        return v.strip()


class CreateTaskResponse(BaseModel):
    """Response from create_task tool."""

    success: bool = Field(description="Operation success status")
    task_id: str | None = Field(default=None, description="Generated task ID")
    filename: str | None = Field(default=None, description="Created filename")
    path: str | None = Field(default=None, description="Full path to created file")
    message: str | None = Field(default=None, description="Status or error message")


class ModifyTaskRequest(BaseModel):
    """Request parameters for modify_task tool."""

    identifier: str = Field(
        min_length=1, description="Task identifier (index, task ID, or filename)"
    )

    # Fields that can be updated (all optional)
    title: str | None = Field(default=None, min_length=1, description="New task title")
    priority: int | None = Field(
        default=None, ge=0, le=3, description="New priority 0-3"
    )
    project: str | None = Field(default=None, description="New project slug")
    classification: str | None = Field(default=None, description="New classification")
    due: datetime | None = Field(default=None, description="New due date")
    status: str | None = Field(default=None, description="New status")
    body: str | None = Field(default=None, description="New body content")

    # Tag operations
    add_tags: list[str] = Field(default_factory=list, description="Tags to add")
    remove_tags: list[str] = Field(default_factory=list, description="Tags to remove")


class ModifyTaskResponse(BaseModel):
    """Response from modify_task tool."""

    success: bool = Field(description="Operation success status")
    message: str | None = Field(default=None, description="Status or error message")
    modified_fields: list[str] | None = Field(
        default=None, description="List of fields that were modified"
    )
    task_id: str | None = Field(default=None, description="Task ID that was modified")


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(default=False, description="Always False for errors")
    error_type: str = Field(description="Error class name")
    message: str = Field(description="Human-readable error message")
    context: dict[str, str] | None = Field(
        default=None, description="Additional error context"
    )
