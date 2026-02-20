"""Tests for PKB visualization features (#563, #564)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.task_graph import (
    TYPE_SHAPES,
    extract_ego_subgraph,
    generate_dot,
)


def _sample_graph_nodes_edges():
    """Sample graph data for visualization testing."""
    nodes = [
        {"id": "goal-1", "path": "/data/goals/publish.md", "label": "Publish",
         "node_type": "goal", "status": "active", "priority": 0, "downstream_weight": 8.0},
        {"id": "task-1", "path": "/data/tasks/write-paper.md", "label": "Write Paper",
         "node_type": "task", "status": "active", "priority": 1, "parent": "goal-1",
         "downstream_weight": 3.5, "stakeholder_exposure": True},
        {"id": "task-2", "path": "/data/tasks/lit-review.md", "label": "Lit Review",
         "node_type": "task", "status": "done", "priority": 2},
        {"id": "daily-1", "path": "/data/daily/2026-01-15.md", "label": "2026-01-15",
         "node_type": "daily", "status": None},
        {"id": "knowledge-1", "path": "/data/knowledge/methods.md", "label": "Methods",
         "node_type": "knowledge", "status": None},
        {"id": "person-1", "path": "/data/people/alice.md", "label": "Alice",
         "node_type": "person", "status": None},
        {"id": "orphan-1", "path": "/data/notes/random.md", "label": "Random",
         "node_type": "note", "status": None},
    ]
    edges = [
        {"source": "task-1", "target": "goal-1", "type": "parent"},
        {"source": "task-1", "target": "task-2", "type": "depends_on"},
        {"source": "daily-1", "target": "task-1", "type": "link"},
        {"source": "knowledge-1", "target": "task-1", "type": "link"},
        {"source": "person-1", "target": "task-1", "type": "link"},
    ]
    return nodes, edges


# ── #563: Ego-subgraph extraction ─────────────────────────────────


class TestEgoSubgraph:
    """Test extract_ego_subgraph function."""

    def test_ego_depth_1(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, sub_edges = extract_ego_subgraph(nodes, edges, "task-1", depth=1)
        sub_ids = {n["id"] for n in sub_nodes}
        # task-1 + direct neighbors: goal-1, task-2, daily-1, knowledge-1, person-1
        assert "task-1" in sub_ids
        assert "goal-1" in sub_ids
        assert "daily-1" in sub_ids
        assert "knowledge-1" in sub_ids
        assert "person-1" in sub_ids
        # orphan is NOT connected
        assert "orphan-1" not in sub_ids

    def test_ego_depth_0(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, _ = extract_ego_subgraph(nodes, edges, "task-1", depth=0)
        assert len(sub_nodes) == 1
        assert sub_nodes[0]["id"] == "task-1"

    def test_ego_depth_2_includes_transitive(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, _ = extract_ego_subgraph(nodes, edges, "daily-1", depth=2)
        sub_ids = {n["id"] for n in sub_nodes}
        # daily-1 -> task-1 -> goal-1, task-2, knowledge-1, person-1
        assert "daily-1" in sub_ids
        assert "task-1" in sub_ids
        assert "goal-1" in sub_ids

    def test_ego_by_label(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, _ = extract_ego_subgraph(nodes, edges, "Write Paper", depth=1)
        sub_ids = {n["id"] for n in sub_nodes}
        assert "task-1" in sub_ids

    def test_ego_by_filename(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, _ = extract_ego_subgraph(nodes, edges, "write-paper", depth=1)
        sub_ids = {n["id"] for n in sub_nodes}
        assert "task-1" in sub_ids

    def test_ego_unknown_node(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, sub_edges = extract_ego_subgraph(nodes, edges, "nonexistent", depth=1)
        assert len(sub_nodes) == 0
        assert len(sub_edges) == 0

    def test_ego_edges_filtered(self):
        nodes, edges = _sample_graph_nodes_edges()
        sub_nodes, sub_edges = extract_ego_subgraph(nodes, edges, "task-1", depth=1)
        # All edges should connect nodes within the subgraph
        sub_ids = {n["id"] for n in sub_nodes}
        for e in sub_edges:
            assert e["source"] in sub_ids
            assert e["target"] in sub_ids


# ── #563: Cross-type rendering ───────────────────────────────────


class TestCrossTypeRendering:
    """Test cross-type node shapes and styling."""

    def test_pkb_types_have_shapes(self):
        """All PKB node types must have shape mappings."""
        pkb_types = ["daily", "knowledge", "person", "context", "template", "note"]
        for ntype in pkb_types:
            assert ntype in TYPE_SHAPES, f"Missing shape for type: {ntype}"

    def test_shapes_are_distinct(self):
        """Key types should have visually distinct shapes."""
        assert TYPE_SHAPES["goal"] == "ellipse"
        assert TYPE_SHAPES["project"] == "box3d"
        assert TYPE_SHAPES["task"] == "box"
        assert TYPE_SHAPES["daily"] == "plaintext"
        assert TYPE_SHAPES["person"] == "circle"
        assert TYPE_SHAPES["knowledge"] == "note"

    def test_generate_dot_with_cross_types(self):
        """DOT generation handles cross-type nodes."""
        nodes, edges = _sample_graph_nodes_edges()
        dot = generate_dot(nodes, edges, include_orphans=True)

        # Should include all node types with correct shapes
        assert "shape=ellipse" in dot  # goal
        assert "shape=box" in dot  # task
        assert "shape=plaintext" in dot  # daily
        assert "shape=circle" in dot  # person

    def test_generate_dot_status_colors(self):
        """Status colors applied to nodes."""
        nodes, edges = _sample_graph_nodes_edges()
        dot = generate_dot(nodes, edges, include_orphans=True)

        assert '#cce5ff' in dot  # active (blue)
        assert '#d4edda' in dot  # done (green)

    def test_generate_dot_downstream_weight(self):
        """Downstream weight shown in labels."""
        nodes, edges = _sample_graph_nodes_edges()
        dot = generate_dot(nodes, edges, include_orphans=True)

        # task-1 has downstream_weight=3.5
        assert "3.5" in dot

    def test_generate_dot_stakeholder_exposure(self):
        """Stakeholder exposure gets double border."""
        nodes, edges = _sample_graph_nodes_edges()
        dot = generate_dot(nodes, edges, include_orphans=True)

        assert "peripheries=2" in dot
