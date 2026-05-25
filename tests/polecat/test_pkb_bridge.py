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
    VALID_TASK_STATUSES,
    PkbClient,
    PkbTask,
    _extract_id_from_binding_error,
    _poll_until_bound,
    append,
    complete_task,
    create_task,
    get_task,
    get_task_children,
    list_tasks,
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

    assert task is not None
    assert task.id == "task-1"
    mock_client.call_tool.assert_called_once_with("get_task", {"id": "task-1"})


def test_get_task_named_id(mock_client):
    mock_client.call_tool.return_value = {"frontmatter": {"id": "task-1", "title": "Test"}}

    task = get_task(id="task-1")

    assert task is not None
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
    # New tasks default to priority 3 (planned) and status 'inbox' when not specified.
    mock_client.call_tool.assert_called_once_with(
        "create_task", {"title": "My Title", "priority": 3, "status": "inbox"}
    )


def test_create_task_with_task_title_alias(mock_client):
    mock_client.call_tool.return_value = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    # Friction fix: 'task_title' should be accepted as 'title'
    task_id = create_task(task_title="My Title")

    assert task_id == "task-123"
    mock_client.call_tool.assert_called_once_with(
        "create_task", {"title": "My Title", "priority": 3, "status": "inbox"}
    )


def test_create_task_explicit_priority_preserved(mock_client):
    """Explicit priority should not be overridden by the P3 default."""
    mock_client.call_tool.return_value = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    task_id = create_task(title="Urgent", priority=0)

    assert task_id == "task-123"
    mock_client.call_tool.assert_called_once_with(
        "create_task", {"title": "Urgent", "priority": 0, "status": "inbox"}
    )


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
        assert "[PKB_PERF]" not in captured.err
        assert "get_task" not in captured.err

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


# ---------------------------------------------------------------------------
# list_tasks project filter recall failure visibility (task-7c171a70)
# ---------------------------------------------------------------------------


def test_get_task_children(mock_client):
    mock_client.call_tool.return_value = "## Children of `proj-1` (Title)\n- `task-1` [active] T1"

    res = get_task_children("proj-1", recursive=True)

    assert "task-1" in res
    mock_client.call_tool.assert_called_once_with(
        "get_task_children", {"id": "proj-1", "recursive": True}
    )


def test_list_tasks_project_filter_with_recall_failure_warning(mock_client, capsys):
    # Mock list_tasks to return only 1 task (recall failure)
    mock_client.call_tool.side_effect = [
        # Call 1: list_tasks
        "| # | ID | Pri | Status | Title |\n| 1 | task-1 | 2 | active | T1 |",
        # Call 2: get_task_children (triggered by recall failure detection)
        "## Children of `proj-1` (Title)\n- `task-1` [active] T1\n- `task-2` [active] T2",
        # Call 3: get_task(task-1)
        {"frontmatter": {"id": "task-1", "project": "proj-1"}},
    ]

    tasks = list_tasks(project="proj-1", limit=10)

    assert len(tasks) == 1
    assert tasks[0].id == "task-1"

    captured = capsys.readouterr()
    assert (
        "Warning: list_tasks(project='proj-1') returned 1 tasks, but project subtree has 2 nodes."
        in captured.err
    )


def test_list_tasks_project_filter_accurate_exclusion(mock_client):
    # Mock list_tasks to return 2 tasks, one in project, one not
    # (assuming server filter was too broad or missing)
    mock_client.call_tool.side_effect = [
        # Call 1: list_tasks
        "| # | ID | Pri | Status | Title |\n| 1 | task-1 | 2 | active | T1 |\n| 2 | task-other | 2 | active | Other |",
        # Call 2: get_task_children
        "## Children of `proj-1` (Title)\n- `task-1` [active] T1",
        # Call 3: get_task(task-1)
        {"frontmatter": {"id": "task-1", "project": "proj-1"}},
    ]

    tasks = list_tasks(project="proj-1", limit=10)

    # Should only return task-1 because task-other is not in the subtree
    assert len(tasks) == 1
    assert tasks[0].id == "task-1"


class TestCreateTaskPrefixConsistency:
    """create_task validates type↔ID-prefix↔project consistency."""

    _task_response = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    def test_valid_task_prefix(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T", id="task-123", type="task") == "task-123"

    def test_invalid_task_prefix(self, mock_client):
        with pytest.raises(ValueError, match="ID prefix 'epic-' does not match type 'task'"):
            create_task(title="T", id="epic-123", type="task")

    def test_valid_epic_prefix(self, mock_client):
        mock_client.call_tool.return_value = {"frontmatter": {"id": "epic-123"}}
        assert create_task(title="T", id="epic-123", type="epic") == "epic-123"

    def test_invalid_epic_prefix(self, mock_client):
        with pytest.raises(ValueError, match="ID prefix 'task-' does not match type 'epic'"):
            create_task(title="T", id="task-123", type="epic")

    def test_valid_bug_prefix(self, mock_client):
        mock_client.call_tool.return_value = {"frontmatter": {"id": "bug-123"}}
        # bug prefix is allowed for type task
        assert create_task(title="T", id="bug-123", type="task") == "bug-123"

    def test_invalid_bug_prefix_type(self, mock_client):
        with pytest.raises(ValueError, match="ID prefix 'bug-' is only allowed for type 'task'"):
            create_task(title="T", id="bug-123", type="epic")

    def test_valid_project_prefix(self, mock_client):
        mock_client.call_tool.return_value = {"frontmatter": {"id": "aops-123"}}
        assert create_task(title="T", id="aops-123", project="aops") == "aops-123"

    def test_invalid_project_prefix(self, mock_client):
        with pytest.raises(ValueError, match="ID prefix 'mem-' does not match project 'aops'"):
            create_task(title="T", id="mem-123", project="aops")

    def test_type_prefix_wins_over_project(self, mock_client):
        # Using task- prefix with project aops is allowed even if it doesn't match 'aops-'
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T", id="task-123", project="aops", type="task") == "task-123"

    def test_no_id_bypasses_prefix_check(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T", project="aops", type="task") == "task-123"


# ---------------------------------------------------------------------------
# Auto-inherit project from parent (rename-impossible constraint, #284/#1054)
# ---------------------------------------------------------------------------


class TestCreateTaskProjectInheritance:
    """create_task auto-inherits project from parent when not specified.

    The project slug is permanently embedded in the task ID at creation time;
    update_task cannot rename the prefix. Getting it wrong creates a permanent
    ID/project mismatch. This class verifies the auto-inherit guard.
    """

    _created_task = {
        "frontmatter": {"id": "qut-abc"},
        "body": "",
        "path": "/tasks/qut-abc.md",
    }

    def test_inherits_project_from_parent(self, mock_client):
        """When parent is set and project is omitted, inherit project from parent."""
        mock_client.call_tool.side_effect = [
            # First call: get_task(parent) to read its project
            {"frontmatter": {"id": "qut-parent", "project": "qut"}},
            # Second call: create_task
            self._created_task,
        ]
        task_id = create_task(title="Teaching subtask", parent="qut-parent")
        assert task_id == "qut-abc"
        create_call = mock_client.call_tool.call_args_list[1]
        assert create_call[0][0] == "create_task"
        assert create_call[0][1]["project"] == "qut"

    def test_project_field_at_top_level_also_inherited(self, mock_client):
        """Inherit project from the top-level 'project' key when frontmatter lacks it."""
        mock_client.call_tool.side_effect = [
            {"frontmatter": {"id": "qut-parent"}, "project": "qut"},
            self._created_task,
        ]
        task_id = create_task(title="Teaching subtask", parent="qut-parent")
        assert task_id == "qut-abc"
        assert mock_client.call_tool.call_args_list[1][0][1]["project"] == "qut"

    def test_explicit_project_matching_parent_fetches_to_validate(self, mock_client):
        """When project is explicitly provided, parent is still fetched to enforce consistency."""
        mock_client.call_tool.side_effect = [
            # First call: get_task(parent) to validate project matches
            {"frontmatter": {"id": "qut-parent", "project": "qut"}},
            # Second call: create_task
            self._created_task,
        ]
        task_id = create_task(title="T", parent="qut-parent", project="qut")
        assert task_id == "qut-abc"
        # Two calls: parent validation fetch + create_task
        assert mock_client.call_tool.call_count == 2
        create_call = mock_client.call_tool.call_args_list[1]
        assert create_call[0][0] == "create_task"
        assert create_call[0][1]["project"] == "qut"

    def test_parent_with_no_project_raises(self, mock_client):
        """If parent has no project field, raise with a helpful message."""
        mock_client.call_tool.return_value = {
            "frontmatter": {"id": "orphan-parent"},
            "body": "",
        }
        with pytest.raises(ValueError, match="auto-inherit requires a resolvable ancestor project"):
            create_task(title="T", parent="orphan-parent")

    def test_parent_not_found_raises(self, mock_client):
        """If the parent task is not found, raise with a clear message."""
        mock_client.call_tool.return_value = None
        with pytest.raises(ValueError, match="not found in PKB"):
            create_task(title="T", parent="nonexistent-parent")

    def test_explicit_project_mismatch_raises(self, mock_client):
        """Explicitly-wrong project raises even when project is non-null."""
        mock_client.call_tool.return_value = {
            "frontmatter": {"id": "qut-parent", "project": "qut"},
        }
        with pytest.raises(ValueError, match="does not match parent"):
            create_task(title="T", parent="qut-parent", project="mem")

    def test_explicit_project_matching_parent_succeeds(self, mock_client):
        """Explicit project that matches the parent's project does not raise."""
        mock_client.call_tool.side_effect = [
            {"frontmatter": {"id": "qut-parent", "project": "qut"}},
            self._created_task,
        ]
        task_id = create_task(title="T", parent="qut-parent", project="qut")
        assert task_id == "qut-abc"

    def test_parent_with_no_project_explicit_project_passes(self, mock_client):
        """If parent has no project but caller supplies one, no enforcement (parent unknown)."""
        mock_client.call_tool.side_effect = [
            {"frontmatter": {"id": "orphan-parent"}},
            self._created_task,
        ]
        task_id = create_task(title="T", parent="orphan-parent", project="qut")
        assert task_id == "qut-abc"

    def test_no_parent_no_project_no_inheritance(self, mock_client):
        """Without a parent, no auto-inherit attempt is made (server decides)."""
        mock_client.call_tool.return_value = self._created_task
        task_id = create_task(title="Free task")
        assert task_id == "qut-abc"
        # Only one call — no parent lookup
        mock_client.call_tool.assert_called_once()

    def test_inherits_project_from_ancestor_chain(self, mock_client):
        """Walk the ancestor chain if the direct parent has no project."""
        mock_client.call_tool.side_effect = [
            # Call 1: get_task(sub-epic) -> no project, but has a parent
            {"frontmatter": {"id": "sub-epic", "parent": "root-project"}},
            # Call 2: get_task(root-project) -> has project
            {"frontmatter": {"id": "root-project", "project": "qut"}},
            # Call 3: create_task
            self._created_task,
        ]
        task_id = create_task(title="Deep subtask", parent="sub-epic")
        assert task_id == "qut-abc"
        assert mock_client.call_tool.call_args_list[2][0][1]["project"] == "qut"


# ---------------------------------------------------------------------------
# Indexer binding-lag recovery tests (AC3 / AC4)
# ---------------------------------------------------------------------------


class TestExtractIdFromBindingError:
    """Unit tests for _extract_id_from_binding_error."""

    def test_parses_id_equals_format(self):
        err = (
            "create_task wrote /pkb/tasks/aops-abc123.md but the new node is not yet "
            "visible in the graph (id=aops-abc123). Underlying lookup error: node missing."
        )
        assert _extract_id_from_binding_error(err) == "aops-abc123"

    def test_parses_task_not_found_format(self):
        err = "Task not found: mem-deadbeef"
        assert _extract_id_from_binding_error(err) == "mem-deadbeef"

    def test_id_equals_takes_priority_over_task_not_found(self):
        err = "Task not found: other-id. (id=real-id123)"
        assert _extract_id_from_binding_error(err) == "real-id123"

    def test_returns_none_when_no_match(self):
        assert _extract_id_from_binding_error("some unrelated error") is None

    def test_returns_none_on_empty_string(self):
        assert _extract_id_from_binding_error("") is None


class TestPollUntilBound:
    """Unit tests for _poll_until_bound."""

    def test_returns_id_when_task_appears_on_first_poll(self):
        client = MagicMock()
        client.call_tool.return_value = {"frontmatter": {"id": "aops-abc123"}}

        with (
            patch("polecat.pkb_bridge.time.sleep"),
            patch("polecat.pkb_bridge.time.monotonic", return_value=0),
        ):
            result = _poll_until_bound(client, "aops-abc123", timeout_secs=10)

        assert result == "aops-abc123"
        client.call_tool.assert_called_once_with("get_task", {"id": "aops-abc123"})

    def test_retries_until_task_appears(self):
        client = MagicMock()
        # First poll returns None (still not bound), second returns the task
        client.call_tool.side_effect = [
            None,
            {"frontmatter": {"id": "aops-abc123"}},
        ]

        with (
            patch("polecat.pkb_bridge.time.sleep"),
            patch("polecat.pkb_bridge.time.monotonic", side_effect=[0, 3]),
        ):
            result = _poll_until_bound(client, "aops-abc123", timeout_secs=10)

        assert result == "aops-abc123"
        assert client.call_tool.call_count == 2

    def test_raises_on_timeout(self):
        client = MagicMock()
        client.call_tool.return_value = None

        # monotonic: 0 sets deadline=10, 11 trips the deadline check
        with (
            patch("polecat.pkb_bridge.time.sleep"),
            patch("polecat.pkb_bridge.time.monotonic", side_effect=[0, 11]),
        ):
            with pytest.raises(RuntimeError, match="did not bind it within"):
                _poll_until_bound(client, "aops-abc123", timeout_secs=10)

    def test_timeout_message_mentions_reindex(self):
        client = MagicMock()
        client.call_tool.return_value = None

        with (
            patch("polecat.pkb_bridge.time.sleep"),
            patch("polecat.pkb_bridge.time.monotonic", side_effect=[0, 11]),
        ):
            with pytest.raises(RuntimeError, match="pkb reindex"):
                _poll_until_bound(client, "aops-abc123", timeout_secs=10)


class TestCreateTaskBindingLagRecovery:
    """Integration tests for create_task retry path (AC3)."""

    _BINDING_ERROR = (
        "create_task wrote /pkb/tasks/aops-abc123.md but the new node is not yet "
        "visible in the graph (id=aops-abc123). Underlying lookup error: node missing. "
        "The file is on disk — retry get_task in a moment."
    )

    def test_recovers_when_indexer_binds_during_polling(self):
        """create_task detects binding lag and recovers via _poll_until_bound."""
        with patch("polecat.pkb_bridge._get_client") as mock_get_client:
            client = MagicMock()
            client.call_tool.return_value = None
            client._last_error = self._BINDING_ERROR
            mock_get_client.return_value = client

            with patch(
                "polecat.pkb_bridge._poll_until_bound", return_value="aops-abc123"
            ) as mock_poll:
                result = create_task(title="Binding lag test")

        assert result == "aops-abc123"
        mock_poll.assert_called_once_with(client, "aops-abc123", timeout_secs=10)

    def test_raises_when_polling_times_out(self):
        """create_task propagates RuntimeError from _poll_until_bound on timeout."""
        with patch("polecat.pkb_bridge._get_client") as mock_get_client:
            client = MagicMock()
            client.call_tool.return_value = None
            client._last_error = self._BINDING_ERROR
            mock_get_client.return_value = client

            with patch(
                "polecat.pkb_bridge._poll_until_bound",
                side_effect=RuntimeError("did not bind it within 10s"),
            ):
                with pytest.raises(RuntimeError, match="did not bind it within"):
                    create_task(title="Binding lag timeout")

    def test_returns_none_when_error_unrelated_to_binding(self):
        """Unrelated tool errors are not retried; create_task returns None."""
        with patch("polecat.pkb_bridge._get_client") as mock_get_client:
            client = MagicMock()
            client.call_tool.return_value = None
            client._last_error = "Internal server error: database unavailable"
            mock_get_client.return_value = client

            with patch("polecat.pkb_bridge._poll_until_bound") as mock_poll:
                result = create_task(title="Unrelated error")

        assert result is None
        mock_poll.assert_not_called()

    def test_normal_success_path_unaffected(self):
        """Successful create_task still returns the ID without polling."""
        with patch("polecat.pkb_bridge._get_client") as mock_get_client:
            client = MagicMock()
            client.call_tool.return_value = {"frontmatter": {"id": "aops-abc123"}}
            client._last_error = None
            mock_get_client.return_value = client

            with patch("polecat.pkb_bridge._poll_until_bound") as mock_poll:
                result = create_task(title="Normal task")

        assert result == "aops-abc123"
        mock_poll.assert_not_called()


# ---------------------------------------------------------------------------
# Status validation tests — guards against invalid status values at create time
# ---------------------------------------------------------------------------


class TestCreateTaskStatusValidation:
    """create_task raises ValueError for status values not in VALID_TASK_STATUSES.

    The MCP schema description mistakenly lists 'draft' (as default) and 'active'
    as accepted values; the server rejects both. This guard fires before the MCP
    round-trip so agents get a clear, actionable error.
    """

    _task_response = {
        "frontmatter": {"id": "task-123"},
        "body": "",
        "path": "/tasks/task-123.md",
    }

    def test_rejects_active(self, mock_client):
        with pytest.raises(ValueError, match="Invalid status for create_task: 'active'"):
            create_task(title="T", status="active")

    def test_rejects_draft(self, mock_client):
        with pytest.raises(ValueError, match="Invalid status for create_task: 'draft'"):
            create_task(title="T", status="draft")

    def test_error_message_names_valid_values(self, mock_client):
        with pytest.raises(ValueError, match="inbox"):
            create_task(title="T", status="active")

    def test_error_message_hints_at_mcp_schema_artefact(self, mock_client):
        with pytest.raises(ValueError, match="'draft' and 'active' appear in the MCP schema"):
            create_task(title="T", status="active")

    def test_accepts_all_valid_statuses(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        for status in VALID_TASK_STATUSES:
            assert create_task(title="T", status=status) == "task-123"

    def test_accepts_inbox(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T", status="inbox") == "task-123"

    def test_accepts_ready(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T", status="ready") == "task-123"

    def test_no_status_bypasses_check(self, mock_client):
        mock_client.call_tool.return_value = self._task_response
        assert create_task(title="T") == "task-123"
