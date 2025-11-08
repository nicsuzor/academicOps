#!/usr/bin/env python3
"""Analyze connections between markdown notes."""

import re
from pathlib import Path
from collections import defaultdict
import json


def find_markdown_files(base_path: Path):
    """Find all markdown files in the repository."""
    patterns = [
        "data/**/*.md",
        "docs/**/*.md",
        "talks/*.md",
        "papers/*.md",
        "reviews/**/*.md",
    ]

    files = set()
    for pattern in patterns:
        files.update(base_path.glob(pattern))

    # Exclude certain directories
    excluded = {"node_modules", ".git", "aops"}
    return [f for f in files if not any(ex in f.parts for ex in excluded)]


def extract_links(content: str):
    """Extract all types of links from markdown content."""
    links = set()

    # Wikilinks: [[note]] or [[note|alias]]
    wikilinks = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", content)
    links.update(wikilinks)

    # Markdown links: [text](path.md)
    md_links = re.findall(r"\[([^\]]+)\]\(([^)]+\.md)\)", content)
    links.update(path for _, path in md_links)

    # @ references: @file.md or @../file.md
    at_refs = re.findall(r"@([^\s]+\.md)", content)
    links.update(at_refs)

    # memory:// URIs
    memory_uris = re.findall(r"memory://([^\s)]+)", content)
    links.update(memory_uris)

    return links


def analyze_connections(base_path: Path):
    """Analyze all note connections."""
    files = find_markdown_files(base_path)

    # Build graph
    graph = defaultdict(set)
    backlinks = defaultdict(set)
    file_map = {}

    for file_path in files:
        rel_path = file_path.relative_to(base_path)
        file_map[str(rel_path)] = file_path

        try:
            content = file_path.read_text()
            links = extract_links(content)

            for link in links:
                graph[str(rel_path)].add(link)
                backlinks[link].add(str(rel_path))
        except Exception as e:
            print(f"Error reading {rel_path}: {e}")

    # Find isolated notes (no outgoing or incoming links)
    all_notes = set(file_map.keys())
    linked_notes = set(graph.keys()) | set(backlinks.keys())

    # Resolve links to actual files
    resolved_graph = defaultdict(set)
    for source, targets in graph.items():
        for target in targets:
            # Try to find matching file
            matching = [f for f in all_notes if target in f or f.endswith(target)]
            if matching:
                resolved_graph[source].update(matching)

    isolated = (
        all_notes
        - set(resolved_graph.keys())
        - set(t for targets in resolved_graph.values() for t in targets)
    )

    return {
        "total_notes": len(all_notes),
        "connected_notes": len(linked_notes),
        "isolated_notes": len(isolated),
        "graph": {k: list(v) for k, v in resolved_graph.items()},
        "isolated": sorted(list(isolated)),
        "most_connected": sorted(
            [(note, len(targets)) for note, targets in resolved_graph.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:20],
    }


if __name__ == "__main__":
    base = Path("/home/nic/src/writing")
    results = analyze_connections(base)

    print(f"Total notes: {results['total_notes']}")
    print(f"Connected notes: {results['connected_notes']}")
    print(
        f"Isolated notes: {results['isolated_notes']} ({results['isolated_notes'] / results['total_notes'] * 100:.1f}%)"
    )
    print(f"\nMost connected notes:")
    for note, count in results["most_connected"][:10]:
        print(f"  {note}: {count} links")

    print(f"\nIsolated notes ({len(results['isolated'])} total):")
    for note in results["isolated"][:20]:
        print(f"  {note}")

    # Save full results
    output = base / "scripts" / "note_connections.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull analysis saved to {output}")
