"""PKB-wide Knowledge Graph: networkx wrapper for fast-indexer output.

Provides traversable graph of ALL PKB documents (tasks, daily notes, knowledge files,
people, etc.) and their wikilink connections. Loads the graph.json produced by
fast-indexer and exposes traversal, search, and analysis methods.

Implements:
- #555: KnowledgeGraph index class
- #556: Unified node identity resolution map
- #557: Node type classification with directory-based inference

Usage:
    from lib.knowledge_graph import KnowledgeGraph

    kg = KnowledgeGraph()
    kg.build()  # or kg.load(path)

    node = kg.node("some-task-id")
    neighbors = kg.neighbors("some-task-id")
    backlinks = kg.backlinks("some-task-id")
    path = kg.shortest_path("source-id", "target-id")
    sub = kg.subgraph("node-id", depth=2)
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

import networkx as nx

from lib.paths import get_data_root

logger = logging.getLogger(__name__)

# Directory-based type inference rules (#557)
# Maps directory name patterns to node types
_DIRECTORY_TYPE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:^|/)daily(?:/|$)"), "daily"),
    (re.compile(r"(?:^|/)knowledge(?:/|$)"), "knowledge"),
    (re.compile(r"(?:^|/)projects(?:/|$)"), "project"),
    (re.compile(r"(?:^|/)goals(?:/|$)"), "goal"),
    (re.compile(r"(?:^|/)people(?:/|$)"), "person"),
    (re.compile(r"(?:^|/)tasks(?:/|$)"), "task"),
    (re.compile(r"(?:^|/)context(?:/|$)"), "context"),
    (re.compile(r"(?:^|/)templates(?:/|$)"), "template"),
]

DEFAULT_NODE_TYPE = "note"


def infer_node_type(path: str) -> str:
    """Infer node type from file path using directory-based rules.

    Priority: explicit frontmatter type > directory path > default 'note'.

    Args:
        path: File path (absolute or relative).

    Returns:
        Inferred node type string.
    """
    for pattern, node_type in _DIRECTORY_TYPE_RULES:
        if pattern.search(path):
            return node_type
    return DEFAULT_NODE_TYPE


class KnowledgeGraph:
    """PKB-wide knowledge graph backed by networkx.

    Wraps a networkx DiGraph populated from fast-indexer's graph.json output.
    Provides traversal, resolution, and analysis methods for the full PKB.
    """

    def __init__(self, data_root: Path | None = None):
        self._data_root = data_root or get_data_root()
        self._graph: nx.DiGraph = nx.DiGraph()
        # Resolution map: lowercase key -> node_id (#556)
        self._resolution_map: dict[str, str] = {}
        self._loaded = False

    @property
    def graph(self) -> nx.DiGraph:
        """The underlying networkx DiGraph."""
        return self._graph

    @property
    def graph_path(self) -> Path:
        """Path to graph.json file."""
        return self._data_root / "graph.json"

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    # ── Loading ──────────────────────────────────────────────────────

    def load(self, graph_json_path: Path | None = None) -> bool:
        """Load graph from fast-indexer JSON output.

        Args:
            graph_json_path: Path to graph.json. Defaults to $ACA_DATA/graph.json.

        Returns:
            True if loaded successfully.
        """
        path = graph_json_path or self.graph_path
        if not path.exists():
            return False

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            self._ingest(data)
            self._loaded = True
            return True
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Failed to load graph from %s: %s", path, e)
            return False

    def load_from_dict(self, data: dict[str, Any]) -> None:
        """Load graph from a dictionary (useful for testing).

        Args:
            data: Dictionary with 'nodes' and 'edges' keys matching
                  fast-indexer graph.json schema.
        """
        self._ingest(data)
        self._loaded = True

    def _ingest(self, data: dict[str, Any]) -> None:
        """Ingest graph data from parsed JSON.

        Populates the networkx graph, applies node type inference (#557),
        and builds the resolution map (#556).
        """
        self._graph = nx.DiGraph()
        self._resolution_map = {}

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        for node in nodes:
            node_id = node["id"]
            attrs = dict(node)

            # #557: Ensure every node has a non-null node_type
            # Priority: explicit frontmatter > directory path > default 'note'
            if not attrs.get("node_type"):
                attrs["node_type"] = infer_node_type(attrs.get("path", ""))

            self._graph.add_node(node_id, **attrs)

            # #556: Build resolution map
            self._add_resolution_keys(node_id, attrs)

        for edge in edges:
            self._graph.add_edge(
                edge["source"],
                edge["target"],
                edge_type=edge.get("type", "link"),
            )

        logger.info(
            "Knowledge graph loaded: %d nodes, %d edges",
            self._graph.number_of_nodes(),
            self._graph.number_of_edges(),
        )

    def _add_resolution_keys(self, node_id: str, attrs: dict[str, Any]) -> None:
        """Register resolution keys for a node (#556).

        Keys include: node_id, filename stem, label/title, path.
        All keys stored lowercase for case-insensitive lookup.
        """
        keys: list[str] = []

        # The node ID itself
        keys.append(node_id)

        # Filename stem (without extension)
        path_str = attrs.get("path", "")
        if path_str:
            stem = Path(path_str).stem
            keys.append(stem)

        # Label/title
        label = attrs.get("label", "")
        if label:
            keys.append(label)

        # Tags that look like task IDs (e.g., "20260112-write-book")
        # Also handle any explicit id from frontmatter that differs from hash id
        for tag in attrs.get("tags", []) or []:
            if re.match(r"^\d{8}-", tag):
                keys.append(tag)

        for key in keys:
            lower_key = key.lower().strip()
            if lower_key:
                # First writer wins - don't overwrite existing mappings
                if lower_key not in self._resolution_map:
                    self._resolution_map[lower_key] = node_id

    # ── Building ─────────────────────────────────────────────────────

    def build(self) -> bool:
        """Build graph by running fast-indexer, then load result.

        Returns:
            True if graph was built and loaded successfully.
        """
        from lib.task_index import _find_fast_indexer

        binary = _find_fast_indexer()
        if not binary:
            logger.warning("fast-indexer binary not found, cannot build graph")
            return False

        output_base = str(self.graph_path).removesuffix(".json")
        cmd = [
            str(binary),
            str(self._data_root),
            "-f", "json",
            "-o", output_base,
            "--quiet",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.warning(
                    "fast-indexer failed (exit %d): %s", result.returncode, result.stderr
                )
                return False

            return self.load()
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning("Failed to run fast-indexer: %s", e)
            return False

    # ── Resolution (#556) ────────────────────────────────────────────

    def resolve(self, query: str) -> str | None:
        """Resolve a query to a node ID.

        Supports: exact node ID, filename stem, title, permalink.
        Case-insensitive.

        Args:
            query: Search string (task ID, wikilink name, filename, title).

        Returns:
            Node ID if found, None otherwise.
        """
        lower = query.lower().strip()

        # Exact match in resolution map
        if lower in self._resolution_map:
            return self._resolution_map[lower]

        # Try without common prefixes/suffixes
        # e.g., "tasks/my-task" -> "my-task"
        if "/" in lower:
            basename = lower.rsplit("/", 1)[-1]
            if basename in self._resolution_map:
                return self._resolution_map[basename]

        return None

    def resolve_or_fail(self, query: str) -> str:
        """Resolve a query to a node ID, raising if not found.

        Args:
            query: Search string.

        Returns:
            Node ID.

        Raises:
            KeyError: If query cannot be resolved.
        """
        result = self.resolve(query)
        if result is None:
            raise KeyError(f"Cannot resolve '{query}' to a known node")
        return result

    def fuzzy_resolve(self, query: str, threshold: int = 70) -> list[tuple[str, str, int]]:
        """Fuzzy-match a query against resolution map keys.

        Args:
            query: Search string.
            threshold: Minimum match score (0-100).

        Returns:
            List of (node_id, matched_key, score) tuples, sorted by score descending.
        """
        lower = query.lower().strip()
        results: list[tuple[str, str, int]] = []

        for key, node_id in self._resolution_map.items():
            score = _simple_fuzzy_score(lower, key)
            if score >= threshold:
                results.append((node_id, key, score))

        results.sort(key=lambda x: x[2], reverse=True)
        return results

    # ── Node Access ──────────────────────────────────────────────────

    def node(self, node_id: str) -> dict[str, Any] | None:
        """Get full metadata for a node.

        Args:
            node_id: Node ID (or resolvable query).

        Returns:
            Node attributes dict, or None if not found.
        """
        resolved = self.resolve(node_id)
        if resolved is None or resolved not in self._graph:
            return None
        return dict(self._graph.nodes[resolved])

    def has_node(self, query: str) -> bool:
        """Check if a node exists (by ID or resolvable query)."""
        resolved = self.resolve(query)
        return resolved is not None and resolved in self._graph

    # ── Traversal ────────────────────────────────────────────────────

    def neighbors(
        self, node_id: str, edge_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Get nodes adjacent to a given node (outgoing edges).

        Args:
            node_id: Node ID (or resolvable query).
            edge_types: Filter by edge types (e.g., ['link', 'parent']).
                       None means all types.

        Returns:
            List of neighbor node attribute dicts.
        """
        resolved = self.resolve(node_id)
        if resolved is None or resolved not in self._graph:
            return []

        result = []
        for _, target, data in self._graph.out_edges(resolved, data=True):
            if edge_types is None or data.get("edge_type") in edge_types:
                result.append(dict(self._graph.nodes[target]))
        return result

    def backlinks(self, node_id: str) -> list[dict[str, Any]]:
        """Get all nodes that link TO this node (incoming edges).

        Args:
            node_id: Node ID (or resolvable query).

        Returns:
            List of source node attribute dicts with edge_type attached.
        """
        resolved = self.resolve(node_id)
        if resolved is None or resolved not in self._graph:
            return []

        result = []
        for source, _, data in self._graph.in_edges(resolved, data=True):
            node_data = dict(self._graph.nodes[source])
            node_data["_edge_type"] = data.get("edge_type", "link")
            result.append(node_data)
        return result

    def backlinks_by_type(self, node_id: str) -> dict[str, list[dict[str, Any]]]:
        """Get backlinks grouped by source node type.

        Args:
            node_id: Node ID (or resolvable query).

        Returns:
            Dict mapping node_type -> list of source node dicts.
        """
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for bl in self.backlinks(node_id):
            ntype = bl.get("node_type", DEFAULT_NODE_TYPE)
            groups[ntype].append(bl)
        return dict(groups)

    def shortest_path(
        self, source: str, target: str
    ) -> list[dict[str, Any]] | None:
        """Find shortest path between two nodes.

        Uses undirected view for path finding (links are conceptually bidirectional).

        Args:
            source: Source node ID (or resolvable query).
            target: Target node ID (or resolvable query).

        Returns:
            List of node dicts along the path (including source and target),
            or None if no path exists.
        """
        src = self.resolve(source)
        tgt = self.resolve(target)
        if src is None or tgt is None:
            return None
        if src not in self._graph or tgt not in self._graph:
            return None

        try:
            undirected = self._graph.to_undirected()
            path_ids = nx.shortest_path(undirected, src, tgt)
            return [dict(self._graph.nodes[nid]) for nid in path_ids]
        except nx.NetworkXNoPath:
            return None

    def all_shortest_paths(
        self, source: str, target: str, max_paths: int = 3
    ) -> list[list[dict[str, Any]]]:
        """Find up to max_paths shortest paths between two nodes.

        Args:
            source: Source node ID (or resolvable query).
            target: Target node ID (or resolvable query).
            max_paths: Maximum number of paths to return.

        Returns:
            List of paths, each path is a list of node dicts.
        """
        src = self.resolve(source)
        tgt = self.resolve(target)
        if src is None or tgt is None:
            return []
        if src not in self._graph or tgt not in self._graph:
            return []

        try:
            undirected = self._graph.to_undirected()
            paths = []
            for path_ids in nx.all_shortest_paths(undirected, src, tgt):
                paths.append([dict(self._graph.nodes[nid]) for nid in path_ids])
                if len(paths) >= max_paths:
                    break
            return paths
        except nx.NetworkXNoPath:
            return []

    def subgraph(self, node_id: str, depth: int = 2) -> nx.DiGraph:
        """Extract ego-network subgraph around a node.

        Includes all nodes within `depth` hops via ANY edge type,
        using undirected traversal.

        Args:
            node_id: Center node ID (or resolvable query).
            depth: Maximum hop distance from center.

        Returns:
            A new DiGraph containing the subgraph. Empty graph if node not found.
        """
        resolved = self.resolve(node_id)
        if resolved is None or resolved not in self._graph:
            return nx.DiGraph()

        undirected = self._graph.to_undirected()
        ego = nx.ego_graph(undirected, resolved, radius=depth)
        # Return directed subgraph preserving edge directions
        return self._graph.subgraph(ego.nodes()).copy()

    # ── Analysis ─────────────────────────────────────────────────────

    def connected_components(self) -> list[set[str]]:
        """Get connected components of the graph (undirected).

        Returns:
            List of sets of node IDs, one per component, largest first.
        """
        undirected = self._graph.to_undirected()
        components = list(nx.connected_components(undirected))
        components.sort(key=len, reverse=True)
        return components

    def orphans(
        self,
        types: list[str] | None = None,
        min_degree: int = 0,
    ) -> list[dict[str, Any]]:
        """Find nodes with zero or minimal structural connections.

        Args:
            types: Filter by node types. None means all types.
            min_degree: Maximum degree to be considered orphan (default 0 = isolated).

        Returns:
            List of orphan node dicts.
        """
        result = []
        for nid in self._graph.nodes():
            degree = self._graph.degree(nid)
            if degree <= min_degree:
                attrs = dict(self._graph.nodes[nid])
                if types is None or attrs.get("node_type") in types:
                    result.append(attrs)
        return result

    def type_counts(self) -> dict[str, int]:
        """Count nodes by type."""
        counts: dict[str, int] = defaultdict(int)
        for _, attrs in self._graph.nodes(data=True):
            counts[attrs.get("node_type", DEFAULT_NODE_TYPE)] += 1
        return dict(counts)

    def edge_type_counts(self) -> dict[str, int]:
        """Count edges by type."""
        counts: dict[str, int] = defaultdict(int)
        for _, _, data in self._graph.edges(data=True):
            counts[data.get("edge_type", "link")] += 1
        return dict(counts)

    def importance_connectivity_gap(self) -> list[dict[str, Any]]:
        """Find nodes where importance >> connectivity (under-connected important items).

        Importance is based on priority and downstream_weight.
        Connectivity is based on degree (in + out edges) and wikilink count.

        Returns:
            List of dicts with node info and gap score, sorted by gap descending.
        """
        gaps = []
        for nid, attrs in self._graph.nodes(data=True):
            # Importance: priority weight + downstream_weight
            priority = attrs.get("priority")
            if priority is None:
                priority_weight = 0.5  # unknown priority = low weight
            else:
                priority_weight = {0: 5.0, 1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5}.get(
                    priority, 0.5
                )
            downstream = attrs.get("downstream_weight", 0.0)
            importance = priority_weight + downstream

            # Connectivity: degree normalized
            degree = self._graph.degree(nid)
            connectivity = degree

            # Gap: importance much higher than connectivity
            if connectivity == 0:
                gap = importance
            else:
                gap = importance / (1 + connectivity)

            if gap > 1.0:  # Only report meaningful gaps
                gaps.append({
                    "id": nid,
                    "label": attrs.get("label", ""),
                    "node_type": attrs.get("node_type", DEFAULT_NODE_TYPE),
                    "importance": round(importance, 2),
                    "connectivity": connectivity,
                    "gap_score": round(gap, 2),
                    "status": attrs.get("status"),
                    "priority": attrs.get("priority"),
                })

        gaps.sort(key=lambda x: x["gap_score"], reverse=True)
        return gaps

    def stats(self) -> dict[str, Any]:
        """Get graph statistics.

        Returns:
            Dictionary with node/edge counts, type breakdowns, connectivity info.
        """
        undirected = self._graph.to_undirected()
        components = list(nx.connected_components(undirected))

        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "node_types": self.type_counts(),
            "edge_types": self.edge_type_counts(),
            "components": len(components),
            "largest_component": len(max(components, key=len)) if components else 0,
            "orphan_count": len(self.orphans()),
            "resolution_keys": len(self._resolution_map),
        }


def _simple_fuzzy_score(query: str, candidate: str) -> int:
    """Simple fuzzy matching score (0-100).

    Uses substring matching and length ratio as a lightweight
    fuzzy match without external dependencies.
    """
    if query == candidate:
        return 100

    # Substring match
    if query in candidate or candidate in query:
        shorter = min(len(query), len(candidate))
        longer = max(len(query), len(candidate))
        if longer == 0:
            return 0
        return int(80 * shorter / longer)

    # Token overlap
    query_tokens = set(re.split(r"[-_\s/]", query))
    candidate_tokens = set(re.split(r"[-_\s/]", candidate))
    if not query_tokens or not candidate_tokens:
        return 0

    overlap = query_tokens & candidate_tokens
    union = query_tokens | candidate_tokens
    return int(70 * len(overlap) / len(union))
