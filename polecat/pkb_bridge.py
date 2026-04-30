"""Bridge to the PKB MCP server for polecat task operations.

Connects to the PKB MCP server over HTTP (Streamable HTTP transport).
The server URL is read from the ``PKB_MCP_URL`` environment variable.
"""

from __future__ import annotations

import json
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from typing import Any

_SLOW_THRESHOLD_MS = float(os.environ.get("PKB_SLOW_THRESHOLD_MS", 500))


class PkbTask:
    """Duck-types the task attributes needed by polecat commands."""

    def __init__(self, data: dict[str, Any]):
        fm = data.get("frontmatter", {})
        self.id: str = fm.get("id") or data.get("id", "")
        self.title: str = fm.get("title") or data.get("title", "")
        self.body: str = data.get("body", "")
        # project can be in frontmatter or computed at top level
        self.project: str | None = fm.get("project") or data.get("project")
        self.type: str = fm.get("type") or data.get("type", "task")
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
        # Side-channel annotation set by claim paths for rollback on failure.
        self._prior_status: str | None = None
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

        max_attempts = 4
        for attempt in range(max_attempts):
            try:
                req = urllib.request.Request(self._url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    # Capture session ID from response headers
                    sid = resp.headers.get("Mcp-Session-Id")
                    if sid:
                        self._session_id = sid
                    raw = resp.read().decode()
                return _parse_sse_json(raw)
            except (TimeoutError, urllib.error.URLError) as e:
                # Catch TimeoutError (3.11+) or URLError that wraps a timeout
                is_timeout = isinstance(e, TimeoutError) or (
                    isinstance(e, urllib.error.URLError) and "timed out" in str(e).lower()
                )
                if not is_timeout or attempt == max_attempts - 1:
                    raise

                # Exponential backoff: 1s, 2s, 4s (+ jitter)
                delay = (2**attempt) + random.uniform(0, 1)
                print(
                    f"PKB PKB timeout (attempt {attempt + 1}/{max_attempts}): "
                    f"retrying in {delay:.1f}s...",
                    file=sys.stderr,
                )
                time.sleep(delay)

        return None

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
        from polecat.observability import metrics

        start_time = time.perf_counter()
        success = False
        try:
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

            # Top-level JSON-RPC error
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

            success = True
            content = result.get("content", [])
            if not content:
                return None

            text = content[0].get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Some tools return plain text (e.g. list_tasks returns markdown)
                return text
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log structured performance data
            perf_entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "tool": name,
                "duration_ms": round(duration_ms, 2),
                "success": success,
                "args": arguments,
            }
            # Emit JSON line for easy parsing
            print(f"[PKB_PERF] {json.dumps(perf_entry)}", file=sys.stderr)

            # Record via standard observability
            metrics._emit(
                "pkb_tool_latency", tool=name, duration_ms=round(duration_ms, 2), success=success
            )

            # Slow-call threshold logging (default 500ms)
            if duration_ms > _SLOW_THRESHOLD_MS:
                print(
                    f"[PKB_SLOW_CALL] tool={name} duration={duration_ms:.2f}ms "
                    f"threshold={_SLOW_THRESHOLD_MS}ms args={json.dumps(arguments)}",
                    file=sys.stderr,
                )

            # Update in-memory history for p50/p95/p99
            if not hasattr(self, "_latencies"):
                self._latencies: dict[str, list[float]] = {}
            if name not in self._latencies:
                self._latencies[name] = []

            history = self._latencies[name]
            history.append(duration_ms)
            if len(history) > 1000:
                history.pop(0)

    def get_perf_stats(self) -> dict[str, dict[str, float]]:
        """Calculate p50/p95/p99 latency stats per tool."""
        if not hasattr(self, "_latencies"):
            return {}

        results = {}
        for name, latencies in self._latencies.items():
            if not latencies:
                continue
            sorted_lats = sorted(latencies)
            count = len(sorted_lats)
            results[name] = {
                "count": count,
                "p50": round(statistics.median(sorted_lats), 2),
                "p95": round(statistics.quantiles(sorted_lats, n=100)[94], 2)
                if count >= 2
                else round(sorted_lats[-1], 2),
                "p99": round(statistics.quantiles(sorted_lats, n=100)[98], 2)
                if count >= 2
                else round(sorted_lats[-1], 2),
                "max": round(sorted_lats[-1], 2),
                "avg": round(statistics.mean(latencies), 2),
            }
        return results

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


def complete_task(
    task_id: str | None = None,
    id: str | None = None,
    completion_evidence: str | None = None,
) -> bool:
    """Mark a task as complete via the PKB MCP server.

    Supports both 'task_id' (positional) and 'id' (named) to reduce friction.
    ``completion_evidence`` describes what was done — optional but strongly recommended.
    """
    final_id = task_id or id
    if not final_id:
        raise ValueError("Task ID must be provided")
    params: dict[str, Any] = {"id": final_id}
    if completion_evidence:
        params["completion_evidence"] = completion_evidence
    result = _get_client().call_tool("complete_task", params)
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

    # Reject checklist items in body — they diverge from the subtask graph
    body = params.get("body", "")
    if isinstance(body, str) and re.search(r"(?m)^\s*[-*+]\s+\[[ xX]\]", body):
        raise ValueError(
            "Task body contains checklist items. "
            "Checklists in task bodies diverge from the subtask graph over time. "
            "Use create_task(parent=...) or decompose_task() instead of embedding "
            "checklists in the body. See: Nectar incident."
        )

    result = _get_client().call_tool("create_task", params)
    if result and isinstance(result, dict):
        fm = result.get("frontmatter")
        if not fm or not fm.get("id"):
            raise RuntimeError(
                f"PKB create_task response missing frontmatter.id — "
                f"is the server running nicsuzor/mem#194? Got: {result!r}"
            )
        return fm["id"]
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

    When ``pr_url`` is provided, it is format-validated and (unless
    ``POLECAT_SKIP_PR_URL_CHECK=1``) live-verified via ``gh`` before the
    release is recorded. This is the A3/A8 integrity gate: the framework
    must not accept a fabricated PR URL as evidence of completion.
    Validation failures raise ``PRURLValidationError``; the MCP call is not
    made and the task stays in its pre-release state.
    """
    if pr_url:
        from polecat.validation import verify_pr_url_live

        verify_pr_url_live(pr_url)

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


def get_task_children(task_id: str, recursive: bool = False) -> str | None:
    """Retrieve children of a task as a markdown string."""
    data = _get_client().call_tool("get_task_children", {"id": task_id, "recursive": recursive})
    if data is None or not isinstance(data, str):
        return None
    return data


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
        # Optimization: pass project to server. Note: the server filter currently
        # only matches literal frontmatter fields and fails to find nested tasks
        # (recall failure). We still filter client-side to ensure correctness,
        # and we surface a warning if the server returned fewer results than
        # exist in the project subtree.
        args["project"] = project

    text = _get_client().call_tool("list_tasks", args)
    if not text or not isinstance(text, str):
        return []

    ids = _parse_task_ids_from_markdown(text)

    # For accurate project filtering, we fetch the set of IDs in the project's subtree.
    # This bypasses the recall failure in the server-side project filter.
    project_task_ids = None
    project_node_id = None  # tracked separately so it is excluded from recall-failure count
    if project:
        subtree_md = get_task_children(project, recursive=True)
        if subtree_md:
            project_task_ids = {
                line.split("`")[1]
                for line in subtree_md.splitlines()
                if (" `- `" in line or line.strip().startswith("- `"))
                and "`" in line
                and len(line.split("`")) >= 2
            }
            # Resolve slug → real ID from header ("## Children of `id` (Title)").
            # Add to the filter set so the project node itself is not excluded if
            # the server ever returns it; track separately for count purposes.
            first_line = subtree_md.splitlines()[0]
            if "`" in first_line:
                project_node_id = first_line.split("`")[1]
                project_task_ids.add(project_node_id)

    tasks = []
    for tid in ids:
        if project_task_ids is not None and tid not in project_task_ids:
            continue
        t = get_task(tid)
        if t is not None:
            tasks.append(t)

    # Recall failure detection: skip when a status filter is applied because
    # len(tasks) will naturally be less than the full subtree count.
    if project and not status and project_task_ids:
        # Exclude the project node itself — it is not a task.
        child_count = len(project_task_ids) - (
            1 if project_node_id and project_node_id in project_task_ids else 0
        )
        if child_count > len(tasks):
            print(
                f"Warning: list_tasks(project='{project}') returned {len(tasks)} tasks, "
                f"but project subtree has {child_count} nodes. The project filter "
                "may have missed nested tasks (recall failure). Use "
                "get_task_children for complete subtree access.",
                file=sys.stderr,
            )

    return tasks


def get_ready_tasks(project: str | None = None) -> list[PkbTask]:
    """Get actionable leaf tasks sorted by priority + weight."""
    return list_tasks(status="ready", project=project)
