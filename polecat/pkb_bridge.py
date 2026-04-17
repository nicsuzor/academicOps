"""Bridge to the PKB MCP server for polecat task operations.

Connects to the PKB MCP server over HTTP (Streamable HTTP transport).
The server URL is read from the ``PKB_MCP_URL`` environment variable.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, datetime
from typing import Any


class PkbTask:
    """Duck-types the task attributes needed by polecat commands."""

    def __init__(self, data: dict[str, Any]):
        fm = data.get("frontmatter", {})
        self.id: str = fm.get("id", "")
        self.title: str = fm.get("title", "")
        self.body: str = data.get("body", "")
        self.project: str | None = fm.get("project")
        self.type: str = fm.get("type", "task")
        self.status: str | None = fm.get("status")  # plain string, not enum
        self.parent: str | None = fm.get("parent")
        self.priority: int | None = fm.get("priority")
        self.tags: list = fm.get("tags") or []
        self.depends_on: list = data.get("depends_on") or []
        self.soft_depends_on: list = fm.get("soft_depends_on") or []
        self.assignee: str | None = fm.get("assignee")
        self.pr_url: str | None = fm.get("pr_url")
        self.pr: str | None = fm.get("pr")
        self.due: str | None = data.get("due")  # ISO date string like "2026-05-13"
        self.effort: str | None = data.get("effort")  # XS/S/M/L tier — used for turn-budget
        self.consequence: str | None = data.get(
            "consequence"
        )  # Free text describing what happens if missed
        # Parse modified timestamp
        mod_raw = fm.get("modified")
        self.modified: datetime | None = None
        if mod_raw:
            if isinstance(mod_raw, datetime):
                self.modified = mod_raw
            elif isinstance(mod_raw, str):
                try:
                    self.modified = datetime.fromisoformat(mod_raw)
                except ValueError:
                    pass

    @property
    def days_until_due(self) -> int | None:
        """Days until due date. Negative = overdue. None = no due date set."""
        if not self.due:
            return None
        try:
            due_date = date.fromisoformat(self.due)
            return (due_date - date.today()).days
        except (ValueError, TypeError):
            return None


def _parse_sse_json(raw: str) -> dict | None:
    """Extract the last JSON-RPC response from an SSE stream."""
    for line in raw.splitlines():
        if line.startswith("data: ") and line.strip() != "data:":
            payload = line[len("data: ") :]
            if payload:
                try:
                    return json.loads(payload)
                except json.JSONDecodeError:
                    continue
    return None


class PkbClient:
    """Thin MCP client that talks to the PKB server over HTTP (MCP Streamable HTTP)."""

    def __init__(self, url: str):
        self._url = url
        self._session_id: str | None = None
        self._id = 0
        self._initialize()

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _post(self, body: dict) -> dict | None:
        """POST a JSON-RPC message and parse the SSE response."""
        data = json.dumps(body).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        req = urllib.request.Request(self._url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Capture session ID from response headers
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                self._session_id = sid
            raw = resp.read().decode()

        return _parse_sse_json(raw)

    def _initialize(self) -> None:
        self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "polecat", "version": "0.3"},
                },
            }
        )
        # Send initialized notification (fire-and-forget, no id = notification)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, name: str, arguments: dict) -> Any:
        """Call an MCP tool and return the parsed JSON content."""
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        if resp is None:
            return None
        # Top-level JSON-RPC error (e.g. -32602 "Missing required parameter"). The
        # MCP server returns these instead of a result object, so any code path
        # that reads resp["result"] without checking this will see {} and silently
        # return None, corrupting the caller. Surface the message to stderr so
        # future failures aren't silent — match the isError branch's semantics
        # (log + return None).
        if "error" in resp:
            err = resp["error"] or {}
            code = err.get("code", "?")
            msg = err.get("message", str(err))
            print(f"PKB MCP error {code} ({name}): {msg}", file=sys.stderr)
            return None
        result = resp.get("result", {})
        if result.get("isError"):
            content = result.get("content")
            err_text = "unknown error"
            if content:
                err_text = content[0].get("text", "unknown error")
            print(f"PKB error ({name}): {err_text}", file=sys.stderr)
            return None
        content = result.get("content", [])
        if not content:
            return None
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Some tools return plain text (e.g. list_tasks returns markdown)
            return text

    def close(self) -> None:
        pass  # HTTP is stateless per-request; nothing to tear down


# Module-level singleton, lazily initialized
_client: PkbClient | None = None


def _get_client() -> PkbClient:
    global _client
    if _client is None:
        url = os.environ.get("PKB_MCP_URL")
        if not url:
            raise RuntimeError(
                "PKB_MCP_URL not set. The PKB MCP server must be running "
                "and PKB_MCP_URL must point to its HTTP endpoint."
            )
        _client = PkbClient(url)
    return _client


def _parse_task_ids_from_markdown(text: str) -> list[str]:
    """Extract task IDs from the markdown table returned by list_tasks.

    The table has columns: #, ID, Pri, Status/Weight, Title.
    We extract the ID column values.
    """
    ids = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        # cells[0] is empty (before first |), cells[1] is #, cells[2] is ID
        if len(cells) >= 3:
            candidate = cells[2]
            # Skip header row and separator
            if candidate and candidate != "ID" and not candidate.startswith("-"):
                ids.append(candidate)
    return ids


def get_task(task_id: str | None = None, id: str | None = None) -> PkbTask | None:
    """Retrieve a task by ID via the PKB MCP server.

    Supports both 'task_id' (positional) and 'id' (named) to reduce friction.
    """
    final_id = task_id or id
    if not final_id:
        raise ValueError("Task ID must be provided")
    data = _get_client().call_tool("get_task", {"id": final_id})
    if data is None or not isinstance(data, dict):
        return None
    return PkbTask(data)


def complete_task(task_id: str | None = None, id: str | None = None) -> bool:
    """Mark a task as complete via the PKB MCP server.

    Supports both 'task_id' (positional) and 'id' (named) to reduce friction.
    """
    final_id = task_id or id
    if not final_id:
        raise ValueError("Task ID must be provided")
    result = _get_client().call_tool("complete_task", {"id": final_id})
    return result is not None


def create_task(
    title: str | None = None, task_title: str | None = None, **kwargs: Any
) -> str | None:
    """Create a new task in the PKB.

    Supports both 'title' and 'task_title' (as an alias) to reduce friction.
    Returns the created task ID.
    """
    final_title = title or task_title
    if not final_title:
        raise ValueError("Task title must be provided")

    params = dict(kwargs)
    params["title"] = final_title

    result = _get_client().call_tool("create_task", params)
    if result and isinstance(result, dict):
        # Structured response: id lives in frontmatter dict
        fm = result.get("frontmatter") or {}
        return fm.get("id") or result.get("id")
    return str(result) if result else None


def update_task(task_id: str | None = None, id: str | None = None, **kwargs: Any) -> bool:
    """Update task fields via the PKB MCP server.

    Supports both 'task_id' (positional) and 'id' (named) to reduce friction.
    Supported kwargs: status, assignee, priority, project, tags, body, pr_url,
    due, effort, consequence.
    Pass ``None`` to remove a field.
    """
    final_id = task_id or id
    if not final_id:
        raise ValueError("Task ID must be provided")

    updates = dict(kwargs)

    result = _get_client().call_tool("update_task", {"id": final_id, "updates": updates})
    return result is not None


def append(id: str | None = None, content: str = "", path: str | None = None) -> bool:
    """Append content to a document.

    Supports both 'id' and 'path' (as an alias for id) to reduce friction.
    """
    doc_id = id or path
    if not doc_id:
        raise ValueError("Either 'id' or 'path' must be provided to append")

    result = _get_client().call_tool("append", {"id": doc_id, "content": content})
    return result is not None


def release_task(
    task_id: str,
    status: str,
    summary: str,
    pr_url: str | None = None,
    branch: str | None = None,
    **kwargs: Any,
) -> bool:
    """Release a task via the PKB MCP server's release_task tool.

    Captures what was done (summary) when transitioning to a handoff status.
    Flat parameters — no nested objects.
    """
    params: dict[str, Any] = {"id": task_id, "status": status, "summary": summary}
    if pr_url:
        params["pr_url"] = pr_url
    if branch:
        params["branch"] = branch
    reserved = {"id", "status", "summary"}
    for k, v in kwargs.items():
        if k not in reserved and v is not None:
            params[k] = v
    result = _get_client().call_tool("release_task", params)
    return result is not None


def save_task(task: PkbTask) -> bool:
    """Persist a mutated PkbTask back to PKB.

    Writes all mutable fields via update_task. This mirrors the old
    ``storage.save_task(task)`` pattern where callers mutate attributes
    then save the whole object.
    """
    updates: dict[str, Any] = {
        "status": task.status,
        "assignee": task.assignee,
    }
    # Only include body if it was set (avoid overwriting with empty)
    if task.body is not None:
        updates["body"] = task.body
    if task.pr_url is not None:
        updates["pr_url"] = task.pr_url
    if task.due is not None:
        updates["due"] = task.due
    if task.effort is not None:
        updates["effort"] = task.effort
    if task.consequence is not None:
        updates["consequence"] = task.consequence
    return update_task(task.id, **updates)


def list_tasks(
    status: str | None = None,
    project: str | None = None,
    limit: int = 200,
) -> list[PkbTask]:
    """List tasks, returning hydrated PkbTask objects.

    Calls the MCP list_tasks tool (which returns a markdown table),
    extracts IDs, then hydrates each via get_task.
    """
    args: dict[str, Any] = {"limit": limit}
    if status:
        args["status"] = status
    if project:
        # list_tasks doesn't have a project filter — we filter client-side
        pass

    text = _get_client().call_tool("list_tasks", args)
    if not text or not isinstance(text, str):
        return []

    ids = _parse_task_ids_from_markdown(text)
    tasks = []
    for tid in ids:
        t = get_task(tid)
        if t is not None:
            if project and t.project != project:
                continue
            tasks.append(t)
    return tasks


def get_ready_tasks(project: str | None = None) -> list[PkbTask]:
    """Get actionable leaf tasks sorted by priority + weight."""
    return list_tasks(status="ready", project=project)
