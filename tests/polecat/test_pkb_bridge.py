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
    release_task,
    update_task,
)
from polecat.validation import PRURLValidationError  # noqa: E402

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
    # create_task now returns structured JSON matching get_task shape
    mock_client.call_tool.return_value = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    task_id = create_task(title="My Title")

    assert task_id == "task-123"
    mock_client.call_tool.assert_called_once_with("create_task", {"title": "My Title"})


def test_create_task_with_task_title_alias(mock_client):
    mock_client.call_tool.return_value = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

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
        # Verify performance logging
        assert "[PKB_PERF]" in captured.err
        assert "get_task" in captured.err

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


class TestCreateTaskChecklistWarning:
    """create_task raises ValueError when body contains - [ ] checklists (subtask divergence prevention)."""

    _task_response = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    def test_raises_on_unchecked_item(self, mock_client):
        with pytest.raises(ValueError, match="checklist items"):
            create_task(title="T", body="Steps:\n- [ ] step one\n")

    def test_raises_on_checked_item(self, mock_client):
        with pytest.raises(ValueError, match="checklist items"):
            create_task(title="T", body="- [x] done step\n")

    def test_raises_on_uppercase_x(self, mock_client):
        with pytest.raises(ValueError, match="checklist items"):
            create_task(title="T", body="- [X] done step\n")

    def test_raises_on_asterisk_marker(self, mock_client):
        with pytest.raises(ValueError, match="checklist items"):
            create_task(title="T", body="* [ ] step one\n")

    def test_raises_on_plus_marker(self, mock_client):
        with pytest.raises(ValueError, match="checklist items"):
            create_task(title="T", body="+ [ ] step one\n")

    def test_no_false_positive_mid_line(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        # Should not raise — mid-line text is not a checklist item
        create_task(title="T", body="mention of - [x] not at line start")

    def test_no_error_without_checklist(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        create_task(title="T", body="Plain context, no checklist here.")

    def test_no_error_on_empty_body(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        create_task(title="T")


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


# ---------------------------------------------------------------------------
# release_task — A3/A8 integrity gate (task-0e4d20a8)
# ---------------------------------------------------------------------------


class TestReleaseTaskPRURLGate:
    """release_task must reject fabricated / unresolvable pr_urls."""

    def test_no_pr_url_bypasses_check(self, mock_client):
        """release_task() without a pr_url must still work (e.g. blocked/cancelled)."""
        mock_client.call_tool.return_value = {"success": True}
        assert release_task("task-1", status="blocked", summary="waiting on X") is True
        mock_client.call_tool.assert_called_once()

    def test_malformed_pr_url_is_rejected_before_mcp_call(self, mock_client):
        with pytest.raises(PRURLValidationError):
            release_task(
                "task-1",
                status="merge_ready",
                summary="done",
                pr_url="not a url",
            )
        mock_client.call_tool.assert_not_called()

    def test_fabricated_org_rejected_when_gh_fails(self, mock_client, monkeypatch):
        """The cheryl 2026-04-18 incident: bogus org. gh exits non-zero → raise."""
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        with (
            patch("polecat.validation.shutil.which", return_value="/usr/bin/gh"),
            patch("polecat.validation.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "Could not resolve to a Repository"
            with pytest.raises(PRURLValidationError):
                release_task(
                    "task-1",
                    status="merge_ready",
                    summary="done",
                    pr_url="https://github.com/academic-ops/academicOps/commit/9841e951",
                )
        mock_client.call_tool.assert_not_called()

    def test_valid_pr_url_passes_and_reaches_mcp(self, mock_client, monkeypatch):
        monkeypatch.delenv("POLECAT_SKIP_PR_URL_CHECK", raising=False)
        mock_client.call_tool.return_value = {"success": True}
        with (
            patch("polecat.validation.shutil.which", return_value="/usr/bin/gh"),
            patch("polecat.validation.subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"state":"OPEN"}'
            mock_run.return_value.stderr = ""
            ok = release_task(
                "task-1",
                status="merge_ready",
                summary="done",
                pr_url="https://github.com/nicsuzor/academicOps/pull/649",
                branch="polecat/task-1",
            )
        assert ok is True
        call = mock_client.call_tool.call_args
        assert call[0][0] == "release_task"
        params = call[0][1]
        assert params["pr_url"] == "https://github.com/nicsuzor/academicOps/pull/649"

    def test_env_skip_bypasses_live_check_but_keeps_format_check(self, mock_client, monkeypatch):
        monkeypatch.setenv("POLECAT_SKIP_PR_URL_CHECK", "1")
        mock_client.call_tool.return_value = {"success": True}
        # Well-formed, live check skipped → passes through.
        assert release_task(
            "task-1",
            status="merge_ready",
            summary="done",
            pr_url="https://github.com/any/repo/pull/1",
        )
        # Malformed still rejected.
        with pytest.raises(PRURLValidationError):
            release_task(
                "task-1",
                status="merge_ready",
                summary="done",
                pr_url="garbage",
            )
