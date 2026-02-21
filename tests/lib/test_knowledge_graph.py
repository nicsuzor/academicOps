"""Tests for PKB-wide Knowledge Graph (#555, #556, #557)."""

from __future__ import annotations

import pytest
from lib.knowledge_graph import KnowledgeGraph, infer_node_type

# ── Fixtures ──────────────────────────────────────────────────────


def _sample_graph_data() -> dict:
    """Build a sample graph.json structure for testing."""
    return {
        "nodes": [
            {
                "id": "node-task-1",
                "path": "/data/aops/tasks/20260101-write-paper.md",
                "label": "Write Paper",
                "node_type": "task",
                "status": "active",
                "priority": 1,
                "tags": ["research"],
                "downstream_weight": 3.5,
            },
            {
                "id": "node-goal-1",
                "path": "/data/goals/publish-research.md",
                "label": "Publish Research",
                "node_type": "goal",
                "status": "active",
                "priority": 0,
                "downstream_weight": 8.0,
            },
            {
                "id": "node-daily-1",
                "path": "/data/daily/2026-01-15.md",
                "label": "2026-01-15",
                "node_type": None,  # Should be inferred as 'daily'
                "status": None,
            },
            {
                "id": "node-knowledge-1",
                "path": "/data/knowledge/methodology-notes.md",
                "label": "Methodology Notes",
                "node_type": None,  # Should be inferred as 'knowledge'
            },
            {
                "id": "node-person-1",
                "path": "/data/people/alice.md",
                "label": "Alice",
                "node_type": None,  # Should be inferred as 'person'
            },
            {
                "id": "node-orphan-1",
                "path": "/data/notes/random-thought.md",
                "label": "Random Thought",
                "node_type": None,  # Should default to 'note'
            },
        ],
        "edges": [
            {"source": "node-task-1", "target": "node-goal-1", "type": "parent"},
            {"source": "node-daily-1", "target": "node-task-1", "type": "link"},
            {"source": "node-knowledge-1", "target": "node-task-1", "type": "link"},
            {"source": "node-person-1", "target": "node-task-1", "type": "link"},
            {"source": "node-task-1", "target": "node-knowledge-1", "type": "link"},
        ],
    }


@pytest.fixture
def kg() -> KnowledgeGraph:
    """KnowledgeGraph loaded with sample data."""
    g = KnowledgeGraph.__new__(KnowledgeGraph)
    g._data_root = None
    g._graph = None
    g._resolution_map = {}
    g._loaded = False
    g.load_from_dict(_sample_graph_data())
    return g


# ── #555: KnowledgeGraph class ───────────────────────────────────


class TestKnowledgeGraphLoad:
    """Test KnowledgeGraph.load() and data ingestion."""

    def test_load_from_dict(self, kg: KnowledgeGraph):
        assert kg.node_count == 6
        assert kg.edge_count == 5

    def test_node_returns_metadata(self, kg: KnowledgeGraph):
        node = kg.node("node-task-1")
        assert node is not None
        assert node["label"] == "Write Paper"
        assert node["status"] == "active"
        assert node["priority"] == 1

    def test_node_returns_none_for_unknown(self, kg: KnowledgeGraph):
        assert kg.node("nonexistent") is None

    def test_has_node(self, kg: KnowledgeGraph):
        assert kg.has_node("node-task-1")
        assert not kg.has_node("nonexistent")

    def test_neighbors_returns_outgoing(self, kg: KnowledgeGraph):
        # node-task-1 has edges to goal-1 and knowledge-1
        nbrs = kg.neighbors("node-task-1")
        labels = {n["label"] for n in nbrs}
        assert "Publish Research" in labels
        assert "Methodology Notes" in labels

    def test_neighbors_filtered_by_edge_type(self, kg: KnowledgeGraph):
        nbrs = kg.neighbors("node-task-1", edge_types=["parent"])
        assert len(nbrs) == 1
        assert nbrs[0]["label"] == "Publish Research"

    def test_backlinks_returns_incoming(self, kg: KnowledgeGraph):
        # node-task-1 is linked TO by daily-1, knowledge-1, person-1
        bls = kg.backlinks("node-task-1")
        labels = {b["label"] for b in bls}
        assert "2026-01-15" in labels
        assert "Methodology Notes" in labels
        assert "Alice" in labels

    def test_backlinks_by_type_groups(self, kg: KnowledgeGraph):
        groups = kg.backlinks_by_type("node-task-1")
        assert "daily" in groups
        assert "knowledge" in groups
        assert "person" in groups

    def test_shortest_path(self, kg: KnowledgeGraph):
        path = kg.shortest_path("node-daily-1", "node-goal-1")
        assert path is not None
        assert len(path) == 3  # daily -> task -> goal
        assert path[0]["label"] == "2026-01-15"
        assert path[-1]["label"] == "Publish Research"

    def test_shortest_path_no_connection(self, kg: KnowledgeGraph):
        # orphan is not connected
        path = kg.shortest_path("node-orphan-1", "node-task-1")
        assert path is None

    def test_subgraph_depth_1(self, kg: KnowledgeGraph):
        sub = kg.subgraph("node-task-1", depth=1)
        # Should include task-1 and its direct neighbors
        assert "node-task-1" in sub.nodes()
        assert "node-goal-1" in sub.nodes()
        assert "node-daily-1" in sub.nodes()
        # But NOT orphan (not connected)
        assert "node-orphan-1" not in sub.nodes()

    def test_subgraph_depth_0(self, kg: KnowledgeGraph):
        sub = kg.subgraph("node-task-1", depth=0)
        assert len(sub.nodes()) == 1

    def test_stats(self, kg: KnowledgeGraph):
        s = kg.stats()
        assert s["nodes"] == 6
        assert s["edges"] == 5
        assert s["orphan_count"] == 1  # node-orphan-1

    def test_type_counts(self, kg: KnowledgeGraph):
        counts = kg.type_counts()
        assert counts["task"] == 1
        assert counts["goal"] == 1
        assert counts["daily"] == 1
        assert counts["knowledge"] == 1
        assert counts["person"] == 1
        assert counts["note"] == 1

    def test_edge_type_counts(self, kg: KnowledgeGraph):
        counts = kg.edge_type_counts()
        assert counts["link"] == 4
        assert counts["parent"] == 1


class TestKnowledgeGraphTraversal:
    """Test advanced traversal methods."""

    def test_all_shortest_paths(self, kg: KnowledgeGraph):
        paths = kg.all_shortest_paths("node-daily-1", "node-goal-1", max_paths=3)
        assert len(paths) >= 1
        # Each path should be length 3
        assert all(len(p) == 3 for p in paths)

    def test_connected_components(self, kg: KnowledgeGraph):
        comps = kg.connected_components()
        assert len(comps) == 2  # main component + orphan
        assert len(comps[0]) == 5  # main component
        assert len(comps[1]) == 1  # orphan

    def test_orphans(self, kg: KnowledgeGraph):
        orphans = kg.orphans()
        assert len(orphans) == 1
        assert orphans[0]["label"] == "Random Thought"

    def test_orphans_filtered_by_type(self, kg: KnowledgeGraph):
        orphans = kg.orphans(types=["task"])
        assert len(orphans) == 0

    def test_importance_connectivity_gap(self, kg: KnowledgeGraph):
        gaps = kg.importance_connectivity_gap()
        # node-orphan-1 has 0 connections, should appear if importance > 1
        # node-goal-1 has high downstream_weight, moderate connections
        assert isinstance(gaps, list)


# ── #556: Resolution Map ─────────────────────────────────────────


class TestResolutionMap:
    """Test unified node identity resolution."""

    def test_resolve_by_node_id(self, kg: KnowledgeGraph):
        assert kg.resolve("node-task-1") == "node-task-1"

    def test_resolve_by_filename_stem(self, kg: KnowledgeGraph):
        # filename stem: "20260101-write-paper"
        assert kg.resolve("20260101-write-paper") == "node-task-1"

    def test_resolve_by_label(self, kg: KnowledgeGraph):
        assert kg.resolve("Write Paper") == "node-task-1"

    def test_resolve_case_insensitive(self, kg: KnowledgeGraph):
        assert kg.resolve("write paper") == "node-task-1"
        assert kg.resolve("WRITE PAPER") == "node-task-1"

    def test_resolve_by_path_basename(self, kg: KnowledgeGraph):
        # Can resolve using path basename without extension
        assert kg.resolve("tasks/20260101-write-paper") is not None

    def test_resolve_returns_none_for_unknown(self, kg: KnowledgeGraph):
        assert kg.resolve("totally-unknown") is None

    def test_resolve_or_fail_raises(self, kg: KnowledgeGraph):
        with pytest.raises(KeyError, match="Cannot resolve"):
            kg.resolve_or_fail("totally-unknown")

    def test_fuzzy_resolve(self, kg: KnowledgeGraph):
        results = kg.fuzzy_resolve("write-paper", threshold=50)
        assert len(results) > 0
        # Best match should be node-task-1
        assert results[0][0] == "node-task-1"

    def test_node_accepts_resolvable_query(self, kg: KnowledgeGraph):
        """Node access works with resolvable names, not just raw IDs."""
        node = kg.node("Write Paper")
        assert node is not None
        assert node["id"] == "node-task-1"

    def test_neighbors_accepts_resolvable_query(self, kg: KnowledgeGraph):
        nbrs = kg.neighbors("Write Paper")
        assert len(nbrs) > 0

    def test_backlinks_accepts_resolvable_query(self, kg: KnowledgeGraph):
        bls = kg.backlinks("Write Paper")
        assert len(bls) > 0


# ── #557: Node Type Classification ───────────────────────────────


class TestNodeTypeClassification:
    """Test directory-based type inference."""

    def test_infer_daily(self):
        assert infer_node_type("/data/daily/2026-01-15.md") == "daily"

    def test_infer_knowledge(self):
        assert infer_node_type("/data/knowledge/notes.md") == "knowledge"

    def test_infer_project(self):
        assert infer_node_type("/data/projects/my-project/README.md") == "project"

    def test_infer_goal(self):
        assert infer_node_type("/data/goals/publish.md") == "goal"

    def test_infer_person(self):
        assert infer_node_type("/data/people/alice.md") == "person"

    def test_infer_task(self):
        assert infer_node_type("/data/aops/tasks/some-task.md") == "task"

    def test_infer_context(self):
        assert infer_node_type("/data/context/review.md") == "context"

    def test_infer_default_note(self):
        assert infer_node_type("/data/misc/random.md") == "note"

    def test_explicit_type_preserved(self, kg: KnowledgeGraph):
        """Nodes with explicit frontmatter type keep it."""
        node = kg.node("node-task-1")
        assert node["node_type"] == "task"

    def test_missing_type_inferred(self, kg: KnowledgeGraph):
        """Nodes without type get inferred from directory."""
        node = kg.node("node-daily-1")
        assert node["node_type"] == "daily"

        node = kg.node("node-knowledge-1")
        assert node["node_type"] == "knowledge"

        node = kg.node("node-person-1")
        assert node["node_type"] == "person"

    def test_fallback_to_note(self, kg: KnowledgeGraph):
        """Nodes in unknown directories get type 'note'."""
        node = kg.node("node-orphan-1")
        assert node["node_type"] == "note"

    def test_every_node_has_type(self, kg: KnowledgeGraph):
        """Every node must have a non-null node_type."""
        for nid in kg.graph.nodes():
            attrs = kg.graph.nodes[nid]
            assert attrs.get("node_type") is not None, f"Node {nid} has no type"
