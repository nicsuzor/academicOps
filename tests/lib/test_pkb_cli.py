"""Tests for PKB CLI commands (#562).

Tests mem context, mem related, mem trace commands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from scripts.task_cli import main


def _sample_graph_data() -> dict:
    """Sample graph for CLI testing."""
    return {
        "nodes": [
            {
                "id": "task-1",
                "path": "/data/tasks/20260101-write-paper.md",
                "label": "Write Paper",
                "node_type": "task",
                "status": "active",
                "priority": 1,
                "tags": ["research"],
                "parent": "goal-1",
            },
            {
                "id": "goal-1",
                "path": "/data/goals/publish.md",
                "label": "Publish Research",
                "node_type": "goal",
                "status": "active",
                "priority": 0,
                "children": ["task-1"],
            },
            {
                "id": "daily-1",
                "path": "/data/daily/2026-01-15.md",
                "label": "2026-01-15",
                "node_type": None,
            },
            {
                "id": "orphan-1",
                "path": "/data/notes/random.md",
                "label": "Random Thought",
                "node_type": None,
            },
        ],
        "edges": [
            {"source": "task-1", "target": "goal-1", "type": "parent"},
            {"source": "daily-1", "target": "task-1", "type": "link"},
        ],
    }


@pytest.fixture
def cli_graph_dir(tmp_path: Path, monkeypatch) -> Path:
    """Create temp data dir with graph.json for CLI testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "tasks").mkdir()

    graph_path = data_dir / "graph.json"
    graph_path.write_text(json.dumps(_sample_graph_data()), encoding="utf-8")

    monkeypatch.setenv("ACA_DATA", str(data_dir))
    return data_dir


class TestMemContext:
    """Test `task mem context` command."""

    def test_context_by_id(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "context", "task-1"])
        assert result.exit_code == 0
        assert "Write Paper" in result.output

    def test_context_by_label(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "context", "Write Paper"])
        assert result.exit_code == 0
        assert "Write Paper" in result.output

    def test_context_shows_parent(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "context", "task-1"])
        assert result.exit_code == 0
        assert "Publish Research" in result.output

    def test_context_shows_backlinks(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "context", "task-1"])
        assert result.exit_code == 0
        assert "2026-01-15" in result.output

    def test_context_unknown_id(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "context", "nonexistent"])
        assert result.exit_code != 0


class TestMemRelated:
    """Test `task mem related` command."""

    def test_search_finds_results(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "related", "paper"])
        assert result.exit_code == 0
        assert "Write Paper" in result.output

    def test_search_no_results(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "related", "zzzznonexistent"])
        assert result.exit_code == 0
        assert "No results" in result.output

    def test_search_with_type_filter(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "related", "research", "--type", "goal"])
        assert result.exit_code == 0


class TestMemTrace:
    """Test `task mem trace` command."""

    def test_trace_connected(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "trace", "daily-1", "goal-1"])
        assert result.exit_code == 0
        assert "path" in result.output.lower()

    def test_trace_by_label(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "trace", "2026-01-15", "Publish Research"])
        assert result.exit_code == 0

    def test_trace_not_connected(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "trace", "orphan-1", "goal-1"])
        assert result.exit_code != 0  # exits 1 if not connected

    def test_trace_unknown_source(self, cli_graph_dir: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["mem", "trace", "nonexistent", "goal-1"])
        assert result.exit_code != 0
