"""Bridge to the PKB MCP server for polecat task operations.

After the task_storage/task_model migration to PKB MCP, the old
lib.task_storage module is no longer present. This module talks to the
``pkb mcp`` server over JSON-RPC/stdio to get and update tasks — the
same interface that Claude Code and Gemini CLI use.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from typing import Any


class PkbTask:
    """Duck-types the task attributes needed by polecat run."""

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
        self.tags: list = fm.get("tags", []) or []
        self.depends_on: list = data.get("depends_on", []) or []
        self.soft_depends_on: list = fm.get("soft_depends_on", []) or []
        self.assignee: str | None = fm.get("assignee")
        self.pr_url: str | None = fm.get("pr_url")
        self.pr: str | None = fm.get("pr")


class PkbClient:
    """Thin MCP client that talks to ``pkb mcp`` over stdio JSON-RPC."""

    def __init__(self):
        pkb_bin = shutil.which("pkb")
        if pkb_bin is None:
            raise RuntimeError("pkb binary not found on PATH")
        self._proc = subprocess.Popen(
            [pkb_bin, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self._id = 0
        self._initialize()

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send(self, msg: dict) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.write((json.dumps(msg) + "\n").encode())
        self._proc.stdin.flush()

    def _recv(self) -> dict | None:
        assert self._proc.stdout is not None
        line = self._proc.stdout.readline()
        if not line:
            return None
        return json.loads(line)

    def _initialize(self) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "polecat", "version": "0.1"},
                },
            }
        )
        self._recv()  # consume initialize result
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, name: str, arguments: dict) -> Any:
        """Call an MCP tool and return the parsed JSON content."""
        self._send(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        resp = self._recv()
        if resp is None:
            return None
        result = resp.get("result", {})
        if result.get("isError"):
            err_text = result.get("content", [{}])[0].get("text", "unknown error")
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
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except Exception:
            self._proc.kill()


# Module-level singleton, lazily initialized
_client: PkbClient | None = None


def _get_client() -> PkbClient:
    global _client
    if _client is None:
        _client = PkbClient()
    return _client


def get_task(task_id: str) -> PkbTask | None:
    """Retrieve a task by ID via the PKB MCP server."""
    data = _get_client().call_tool("get_task", {"id": task_id})
    if data is None or not isinstance(data, dict):
        return None
    return PkbTask(data)


def update_task(task_id: str, **kwargs: str) -> bool:
    """Update task fields via the PKB MCP server.

    Supported kwargs: status, assignee, priority, project, tags.
    """
    updates = {k: v for k, v in kwargs.items() if v is not None}
    result = _get_client().call_tool("update_task", {"id": task_id, "updates": updates})
    return result is not None
