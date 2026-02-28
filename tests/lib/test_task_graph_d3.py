import sys
from unittest.mock import MagicMock

# Mock streamlit before importing task_graph_d3
sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit.components.v1"] = MagicMock()

from task_graph_d3 import (
    prepare_embedded_graph_data,
)


def _make_graph(nodes, edges=None):
    """Helper to build a graph.json-like dict."""
    return {"nodes": nodes, "edges": edges or []}


def _node(id, **kwargs):
    """Helper to build a graph.json node."""
    defaults = {
        "id": id,
        "label": id,
        "node_type": "task",
        "status": "active",
        "priority": 2,
        "downstream_weight": 0,
        "depth": 0,
    }
    defaults.update(kwargs)
    return defaults


def test_empty_graph():
    result = prepare_embedded_graph_data(_make_graph([]))
    assert result["nodes"] == []
    assert result["links"] == []


def test_single_node():
    graph = _make_graph([_node("t1", label="Task One")])
    result = prepare_embedded_graph_data(graph)

    assert len(result["nodes"]) == 1
    n = result["nodes"][0]
    assert n["id"] == "t1"
    assert n["label"] == "Task One"
    assert n["shape"] == "rect"  # task type
    assert n["status"] == "active"


def test_weight_based_sizing():
    """Nodes with higher downstream_weight should be larger."""
    graph = _make_graph(
        [
            _node("light", downstream_weight=0),
            _node("heavy", downstream_weight=50),
        ]
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    assert nodes["heavy"]["w"] > nodes["light"]["w"]
    assert nodes["heavy"]["h"] > nodes["light"]["h"]


def test_weight_driven_color_intensity():
    """High-weight node fill should differ from low-weight (desaturation)."""
    graph = _make_graph(
        [
            _node("low", downstream_weight=0, status="active"),
            _node("high", downstream_weight=100, status="active"),
        ]
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    # Both are active, but fills should differ due to weight-based desaturation
    assert nodes["low"]["fill"] != nodes["high"]["fill"]
    # High-weight should be closer to the base active fill
    assert nodes["high"]["fill"] != nodes["low"]["fill"]


def test_node_shapes_per_type():
    """Different node_types should get different shapes."""
    graph = _make_graph(
        [
            _node("g1", node_type="goal"),
            _node("p1", node_type="project"),
            _node("e1", node_type="epic"),
            _node("t1", node_type="task"),
        ]
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    assert nodes["g1"]["shape"] == "pill"
    assert nodes["p1"]["shape"] == "rounded"
    assert nodes["e1"]["shape"] == "hexagon"
    assert nodes["t1"]["shape"] == "rect"


def test_edge_type_differentiation():
    """Parent, depends_on, and ref edges should get different colors."""
    graph = _make_graph(
        [_node("a"), _node("b"), _node("c"), _node("d")],
        [
            {"source": "a", "target": "b", "type": "parent"},
            {"source": "c", "target": "d", "type": "depends_on"},
            {"source": "a", "target": "d", "type": "wikilink"},
        ],
    )
    result = prepare_embedded_graph_data(graph)
    links = {(link["source"], link["target"]): link for link in result["links"]}

    parent_link = links[("b", "a")]  # flipped: parent→child
    dep_link = links[("c", "d")]
    ref_link = links[("a", "d")]

    assert parent_link["color"] == "#3b82f6"  # blue
    assert dep_link["color"] in ("#ef4444", "#dc2626")  # red or brighter red
    assert ref_link["color"] == "#94a3b8"  # gray
    assert ref_link["dash"] == "4,3"
    assert ref_link["type"] == "ref"  # wikilink merged to ref


def test_critical_path_edge_width():
    """depends_on edge to a high-weight target should be thicker."""
    graph = _make_graph(
        [
            _node("src", downstream_weight=0),
            _node("tgt", downstream_weight=100),
        ],
        [{"source": "src", "target": "tgt", "type": "depends_on"}],
    )
    result = prepare_embedded_graph_data(graph)
    link = result["links"][0]

    # Critical-path: target weight is 100% of max, so crit_ratio = 1.0 > 0.5
    assert link["width"] > 2.0  # base is 2.0, should be boosted
    assert link["color"] == "#dc2626"  # brighter red


def test_structural_nodes_muted():
    """Structural nodes should get muted fill/text colors."""
    graph = _make_graph([_node("s1", status="done")])
    result = prepare_embedded_graph_data(graph, structural_ids={"s1"})

    n = result["nodes"][0]
    assert n["structural"] is True
    assert n["fill"] == "#e2e8f0"
    assert n["textColor"] == "#94a3b8"


def test_orphan_opacity():
    """Nodes with no edges and zero weight should get reduced opacity."""
    graph = _make_graph([_node("orphan", downstream_weight=0)])
    result = prepare_embedded_graph_data(graph)

    n = result["nodes"][0]
    assert n["opacity"] == 0.5


def test_connected_node_full_opacity():
    """Nodes with edges should have full opacity even with zero weight."""
    graph = _make_graph(
        [_node("a", downstream_weight=0), _node("b", downstream_weight=0)],
        [{"source": "a", "target": "b", "type": "parent"}],
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    assert nodes["a"]["opacity"] == 1.0
    assert nodes["b"]["opacity"] == 1.0


def test_dangling_edges_filtered():
    """Edges referencing missing nodes should be excluded."""
    graph = _make_graph(
        [_node("a")],
        [{"source": "a", "target": "missing", "type": "depends_on"}],
    )
    result = prepare_embedded_graph_data(graph)
    assert len(result["links"]) == 0


def test_badge_for_type():
    """Goals/projects/epics should get type badges, tasks should not."""
    graph = _make_graph(
        [
            _node("g1", node_type="goal"),
            _node("t1", node_type="task"),
        ]
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    assert nodes["g1"]["badge"] == "GOAL"
    assert nodes["t1"]["badge"] == ""


def test_label_truncation():
    """Labels longer than 60 chars should be truncated to 60 chars."""
    long_label = "A" * 70
    graph = _make_graph([_node("t1", label=long_label)])
    result = prepare_embedded_graph_data(graph)

    n = result["nodes"][0]
    assert len(n["label"]) == 60
    assert n["label"].endswith("...")


def test_goal_larger_than_task():
    """Goal nodes should be scaled larger than task nodes at same weight."""
    graph = _make_graph(
        [
            _node("g1", node_type="goal", downstream_weight=5),
            _node("t1", node_type="task", downstream_weight=5),
        ]
    )
    result = prepare_embedded_graph_data(graph)
    nodes = {n["id"]: n for n in result["nodes"]}

    assert nodes["g1"]["w"] > nodes["t1"]["w"]
