#!/usr/bin/env python3
"""
Find orphaned and disconnected files in the framework reference graph.

Identifies:
1. Unexpected orphans - files never referenced that probably should be
2. Completely isolated files - no references in or out (potentially dead)
3. Disconnected clusters - groups of files linked to each other but not to main framework
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

# Entry points loaded by external systems (expected to have no incoming refs)
EXPECTED_ORPHAN_PATTERNS = [
    # Entry points
    ".claude/CLAUDE.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "INDEX.md",
]


def is_expected_orphan(path: str) -> bool:
    """Check if a file is expected to have no incoming references."""
    # Commands (loaded by slash command system)
    if path.startswith("commands/"):
        return True
    # Agents (loaded by Task tool)
    if path.startswith("agents/"):
        return True
    # Hooks (loaded by hook system)
    if path.startswith("hooks/") and path.endswith(".py"):
        return True
    if path.startswith("hooks/templates/"):
        return True
    # Test files
    if "test" in path.lower() or path.startswith("tests/"):
        return True
    # Python module markers
    if path.endswith("__init__.py"):
        return True
    # Standalone scripts (invoked directly)
    if path.startswith("scripts/") and path.endswith(".py"):
        return True
    # Config files
    if path.endswith(".json") or path.endswith(".yaml") or path.endswith(".lock"):
        return True
    return Path(path).name in EXPECTED_ORPHAN_PATTERNS


def find_components(nodes: set[str], adj: dict[str, set[str]]) -> list[set[str]]:
    """Find connected components using BFS."""
    visited: set[str] = set()
    components: list[set[str]] = []

    for start in nodes:
        if start in visited:
            continue
        component: set[str] = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            component.add(node)
            for neighbor in adj.get(node, []):
                if neighbor not in visited and neighbor in nodes:
                    queue.append(neighbor)
        components.append(component)

    return sorted(components, key=len, reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find orphaned and disconnected files in the reference graph"
    )
    parser.add_argument(
        "--graph",
        "-g",
        type=Path,
        default=None,
        help="Path to reference-graph.json",
    )
    args = parser.parse_args()

    # Determine graph path
    if args.graph:
        graph_path = args.graph
    else:
        # Default to plugin root (4 levels up from this script)
        plugin_root = Path(__file__).resolve().parent.parent.parent.parent
        graph_path = plugin_root / "reference-graph.json"

    if not graph_path.exists():
        print(
            f"Error: {graph_path} not found. Run reference-map first.",
            file=sys.stderr,
        )
        return 1

    with graph_path.open() as f:
        g = json.load(f)

    nodes = {n["id"] for n in g["nodes"]}
    edges = [(link["source"], link["target"]) for link in g["links"]]

    # Build edge counts and adjacency
    incoming: dict[str, int] = defaultdict(int)
    outgoing: dict[str, int] = defaultdict(int)
    adj: dict[str, set[str]] = defaultdict(set)

    for src, tgt in edges:
        incoming[tgt] += 1
        outgoing[src] += 1
        adj[src].add(tgt)
        adj[tgt].add(src)  # Undirected for component analysis

    # Find orphans
    orphans = [n for n in nodes if incoming[n] == 0]
    unexpected_orphans = [o for o in orphans if not is_expected_orphan(o)]

    # Find isolated (no edges at all)
    isolated = [n for n in nodes if incoming[n] == 0 and outgoing[n] == 0]
    unexpected_isolated = [i for i in isolated if not is_expected_orphan(i)]

    # Find connected components
    components = find_components(nodes, adj)

    # Output
    print("=== GRAPH SUMMARY ===")
    print(f"Total nodes: {len(nodes)}")
    print(f"Total edges: {len(edges)}")
    print(f"Connected components: {len(components)}")
    print(f"Main component size: {len(components[0])}")

    print(f"\n=== UNEXPECTED ORPHANS ({len(unexpected_orphans)}) ===")
    print("Files never referenced that probably should be:\n")
    for o in sorted(unexpected_orphans):
        out = outgoing.get(o, 0)
        status = "(isolated)" if out == 0 else f"(outgoing: {out})"
        print(f"  {o} {status}")

    print(f"\n=== COMPLETELY ISOLATED ({len(unexpected_isolated)}) ===")
    print("Files with NO references in or out (may be dead):\n")
    for i in sorted(unexpected_isolated):
        print(f"  {i}")

    if len(components) > 1:
        # Filter to non-trivial disconnected clusters (>1 node)
        disconnected = [c for c in components[1:] if len(c) > 1]
        if disconnected:
            print(f"\n=== DISCONNECTED CLUSTERS ({len(disconnected)}) ===")
            print("Groups linked to each other but not to main framework:\n")
            for i, comp in enumerate(disconnected, 1):
                print(f"Cluster {i} ({len(comp)} nodes):")
                for n in sorted(comp):
                    print(f"  {n}")
                print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
