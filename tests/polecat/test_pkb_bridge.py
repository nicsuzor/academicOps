"""Tests for polecat PKB bridge friction fixes."""

from unittest.mock import MagicMock, patch

import pytest

from polecat.pkb_bridge import append, complete_task, create_task, get_task, update_task


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
