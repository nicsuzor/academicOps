#!/usr/bin/env python3
"""Tests for polecat/pkb_bridge.py — friction fixes and error handling.

Friction-fix tests: cover alias support (id/task_id, title/task_title, id/path)
added in the PKB MCP tool signature friction PR.

Error-handling tests: regression for ``PkbClient.call_tool`` silently returning
``None`` whenever the server produced a top-level JSON-RPC ``error`` object.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "polecat"))

from polecat.pkb_bridge import (  # noqa: E402
    PkbClient,
    PkbTask,
    append,
    complete_task,
    create_task,
    get_task,
    update_task,
)

# ---------------------------------------------------------------------------
# Friction-fix tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    with patch("polecat.pkb_bridge._get_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_get_task_positional_id(mock_client):
    mock_client.call_tool.return_value = {"frontmatter": {"id": "task-1", "title": "Test"}}

    task = get_task("task-1")

    assert task.id == "task-1"
    mock_client.call_tool.assert_called_once_with("get_task", {"id": "task-1"})


def test_get_task_named_id(mock_client):
    mock_client.call_tool.return_value = {"frontmatter": {"id": "task-1", "title": "Test"}}

    task = get_task(id="task-1")

    assert task.id == "task-1"
    mock_client.call_tool.assert_called_once_with("get_task", {"id": "task-1"})


def test_complete_task_positional_id(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    complete_task("task-1")

    mock_client.call_tool.assert_called_once_with("complete_task", {"id": "task-1"})


def test_complete_task_named_id(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    complete_task(id="task-1")

    mock_client.call_tool.assert_called_once_with("complete_task", {"id": "task-1"})


def test_create_task_with_title(mock_client):
    mock_client.call_tool.return_value = {"id": "task-123"}

    task_id = create_task(title="My Title")

    assert task_id == "task-123"
    mock_client.call_tool.assert_called_once_with("create_task", {"title": "My Title"})


def test_create_task_with_task_title_alias(mock_client):
    mock_client.call_tool.return_value = {"id": "task-123"}

    # Friction fix: 'task_title' should be accepted as 'title'
    task_id = create_task(task_title="My Title")

    assert task_id == "task-123"
    mock_client.call_tool.assert_called_once_with("create_task", {"title": "My Title"})


def test_update_task_positional_id(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    update_task("task-1", status="done")

    mock_client.call_tool.assert_called_once_with(
        "update_task", {"id": "task-1", "updates": {"status": "done"}}
    )


def test_update_task_named_id(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    # Friction fix: 'id' as named arg should work
    update_task(id="task-1", status="done")

    mock_client.call_tool.assert_called_once_with(
        "update_task", {"id": "task-1", "updates": {"status": "done"}}
    )


def test_append_with_id(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    append(id="doc-1", content="hello")

    mock_client.call_tool.assert_called_once_with("append", {"id": "doc-1", "content": "hello"})


def test_append_with_path_alias(mock_client):
    mock_client.call_tool.return_value = {"success": True}

    # Friction fix: 'path' should be accepted as 'id'
    append(path="notes/todo.md", content="hello")

    mock_client.call_tool.assert_called_once_with(
        "append", {"id": "notes/todo.md", "content": "hello"}
    )


# ---------------------------------------------------------------------------
# Error-handling tests (PkbClient.call_tool)
# ---------------------------------------------------------------------------


def _make_client() -> PkbClient:
    """Build a PkbClient without firing the real initialize() handshake."""
    with patch.object(PkbClient, "_initialize", lambda self: None):
        return PkbClient("http://unit-test.invalid/mcp")


class TestCallToolErrorHandling:
    def test_jsonrpc_error_is_logged_to_stderr(self, capsys):
        client = _make_client()
        err_resp = {
            "jsonrpc": "2.0",
            "id": 7,
            "error": {
                "code": -32602,
                "message": (
                    "Missing required parameter: parent. Tasks must have a "
                    "parent node. Only goal, learn, and project types can be "
                    "root-level."
                ),
            },
        }
        with patch.object(PkbClient, "_post", return_value=err_resp):
            result = client.call_tool("create_task", {"title": "x"})

        captured = capsys.readouterr()
        assert result is None, "call_tool must return None on JSON-RPC error"
        assert "PKB MCP error" in captured.err, (
            f"JSON-RPC error must reach stderr; got stderr={captured.err!r}"
        )
        assert "-32602" in captured.err
        assert "Missing required parameter: parent" in captured.err
        assert "create_task" in captured.err, "log line must identify the failing tool"

    def test_error_without_message_still_logged(self, capsys):
        client = _make_client()
        err_resp = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000}}
        with patch.object(PkbClient, "_post", return_value=err_resp):
            result = client.call_tool("get_task", {"id": "bad"})

        assert result is None
        captured = capsys.readouterr()
        assert "PKB MCP error" in captured.err
        assert "-32000" in captured.err

    def test_is_error_branch_still_logs(self, capsys):
        """The isError result branch must still work (no regression)."""
        client = _make_client()
        resp = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "isError": True,
                "content": [{"type": "text", "text": "tool-level failure"}],
            },
        }
        with patch.object(PkbClient, "_post", return_value=resp):
            result = client.call_tool("update_task", {"id": "x"})

        assert result is None
        captured = capsys.readouterr()
        assert "PKB error (update_task)" in captured.err
        assert "tool-level failure" in captured.err

    def test_happy_path_parses_json_content(self, capsys):
        """Non-error path: parsed JSON is returned and stderr is clean."""
        client = _make_client()
        resp = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [{"type": "text", "text": '{"frontmatter": {"id": "task-123"}}'}]
            },
        }
        with patch.object(PkbClient, "_post", return_value=resp):
            result = client.call_tool("get_task", {"id": "task-123"})

        assert isinstance(result, dict)
        assert result["frontmatter"]["id"] == "task-123"
        captured = capsys.readouterr()
        assert captured.err == "", f"happy path must not log to stderr; got {captured.err!r}"

    def test_happy_path_returns_plain_text_when_not_json(self):
        """list_tasks returns a markdown table — plain text fallback path."""
        client = _make_client()
        resp = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {"content": [{"type": "text", "text": "| # | ID | ... |"}]},
        }
        with patch.object(PkbClient, "_post", return_value=resp):
            result = client.call_tool("list_tasks", {})

        assert result == "| # | ID | ... |"

    def test_none_response_returns_none(self):
        client = _make_client()
        with patch.object(PkbClient, "_post", return_value=None):
            assert client.call_tool("anything", {}) is None


class TestPkbTaskDeadlineFields:
    def _make_task(self, extra: dict | None = None) -> PkbTask:
        data: dict = {
            "frontmatter": {"id": "task-abc", "title": "Test task"},
            "body": "",
        }
        if extra:
            data.update(extra)
        return PkbTask(data)

    def test_fields_populated(self):
        task = self._make_task(
            {
                "due": "2026-05-13",
                "effort": "1w",
                "consequence": "Project delayed",
            }
        )
        assert task.due == "2026-05-13"
        assert task.effort == "1w"
        assert task.consequence == "Project delayed"

    def test_backward_compat_no_fields(self):
        task = self._make_task()
        assert task.due is None
        assert task.effort is None
        assert task.consequence is None

    def test_days_until_due_future(self):
        task = self._make_task({"due": "2026-04-20"})
        with patch("polecat.pkb_bridge.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 13)
            mock_date.fromisoformat.side_effect = date.fromisoformat
            result = task.days_until_due
        assert result == 7

    def test_days_until_due_past(self):
        task = self._make_task({"due": "2026-04-06"})
        with patch("polecat.pkb_bridge.date") as mock_date:
            mock_date.today.return_value = date(2026, 4, 13)
            mock_date.fromisoformat.side_effect = date.fromisoformat
            result = task.days_until_due
        assert result == -7

    def test_days_until_due_no_due_date(self):
        task = self._make_task()
        assert task.days_until_due is None

    def test_days_until_due_invalid_date(self):
        task = self._make_task({"due": "not-a-date"})
        assert task.days_until_due is None
