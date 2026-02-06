#!/usr/bin/env python3
"""
Build reference graph from framework files.

Extracts ALL file references and outputs standard node-link JSON and CSV.
Pure state capture - no analysis or computed metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Directories to skip
SKIP_DIRS = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
}

# Files to skip (output files that would create self-references)
SKIP_FILES = {
    "reference-graph.json",
    "reference-graph.csv",
}

# File extensions to scan
SCAN_EXTENSIONS = {".md", ".py", ".json", ".sh"}


@dataclass
class Reference:
    """A single reference found in a file."""

    target: str  # Raw reference text
    ref_type: str  # wikilink, markdown_link, python_import, etc.
    line: int
    raw: str  # Original matched text


@dataclass
class EdgeKey:
    """Unique key for an edge (source + target + ref_type)."""

    source: str
    target: str
    ref_type: str

    def __hash__(self) -> int:
        return hash((self.source, self.target, self.ref_type))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EdgeKey):
            return NotImplemented
        return (
            self.source == other.source
            and self.target == other.target
            and self.ref_type == other.ref_type
        )


@dataclass
class Edge:
    """An edge in the reference graph."""

    source: str
    target: str
    ref_type: str
    path_category: str
    refs: list[dict[str, str | int]] = field(default_factory=list)

    @property
    def weight(self) -> int:
        return len(self.refs)


# Regex patterns for each reference type
PATTERNS: dict[str, re.Pattern[str]] = {
    # [[target]] or [[display|target]] - Obsidian format has display first
    "wikilink": re.compile(r"\[\[([^\]|]+)\]\]"),
    # [[display|target]] - aliased wikilink, capture the target (after |)
    "wikilink_aliased": re.compile(r"\[\[[^\]|]+\|([^\]]+)\]\]"),
    # [text](path) - capture the path
    "markdown_link": re.compile(r"\[[^\]]*\]\(([^)]+)\)"),
    # @path/to/file.ext
    "at_inclusion": re.compile(r"@([a-zA-Z0-9_\-./]+\.[a-z]+)"),
    # from module.path import ...
    "python_import_from": re.compile(r"^from\s+([\w.]+)\s+import", re.MULTILINE),
    # import module.path
    "python_import": re.compile(r"^import\s+([\w.]+)", re.MULTILINE),
    # $VAR/path or ${VAR}/path
    "env_path": re.compile(r"(\$\{?[A-Z_]+\}?/[\w\-./]+)"),
    # "./path" or '../path' or '/absolute/path'
    "path_literal": re.compile(r"""["']([.~/][\w\-./]+(?:\.[a-z]+)?)["']"""),
}


def classify_path(ref_text: str) -> str:
    """Classify a reference path into a category."""
    if ref_text.startswith("$") or "${" in ref_text:
        return "env_var"
    if ref_text.startswith("/"):
        return "absolute"
    if "." in ref_text and not ref_text.startswith(("./", "../")):
        # Could be a Python module (lib.paths) or a file (file.md)
        # If it has no path separators and has dots, likely a module
        if "/" not in ref_text and "\\" not in ref_text:
            parts = ref_text.split(".")
            # If last part looks like extension, it's a file
            if len(parts[-1]) <= 4 and parts[-1].isalpha():
                # Could be .md, .py, .json, etc. - treat as relative
                return "relative"
            return "module"
    return "relative"


def expand_env_path(ref_text: str) -> str | None:
    """
    Expand environment variable paths like $AOPS/file or ${ACA_DATA}/file.

    Returns expanded path string, or None if env var is not set.
    """
    # Match $VAR/path or ${VAR}/path
    match = re.match(r"\$\{?([A-Z_]+)\}?(/.*)?", ref_text)
    if not match:
        return None

    var_name = match.group(1)
    suffix = match.group(2) or ""

    var_value = os.environ.get(var_name)
    if not var_value:
        return None

    return var_value + suffix


def resolve_target(source_path: Path, ref_text: str, root: Path) -> str:
    """
    Attempt to resolve a reference to a canonical path relative to root.

    Returns the resolved path if possible, otherwise returns the raw reference.
    """
    # Handle env vars - try to expand and resolve
    if ref_text.startswith("$") or "${" in ref_text:
        expanded = expand_env_path(ref_text)
        if expanded:
            expanded_path = Path(expanded)
            if expanded_path.exists():
                try:
                    return str(expanded_path.resolve().relative_to(root))
                except ValueError:
                    # Outside root - return expanded absolute path
                    return str(expanded_path.resolve())
        # Can't expand - strip env var prefix for cleaner node name
        clean = re.sub(r"\$\{?[A-Z_]+\}?/?", "", ref_text)
        return clean if clean else ref_text

    # Handle Python modules - convert to path
    if classify_path(ref_text) == "module":
        # lib.paths -> lib/paths.py
        module_path = ref_text.replace(".", "/")
        # Try with .py extension
        py_path = root / f"{module_path}.py"
        if py_path.exists():
            return str(py_path.relative_to(root))
        # Try as directory with __init__.py
        init_path = root / module_path / "__init__.py"
        if init_path.exists():
            return str((root / module_path).relative_to(root))
        # Return as-is
        return ref_text

    # Handle relative paths
    if ref_text.startswith("./") or ref_text.startswith("../"):
        resolved = (source_path.parent / ref_text).resolve()
        try:
            return str(resolved.relative_to(root))
        except ValueError:
            return ref_text

    # Handle absolute paths
    if ref_text.startswith("/"):
        resolved = Path(ref_text)
        if resolved.exists():
            try:
                return str(resolved.relative_to(root))
            except ValueError:
                return ref_text
        return ref_text

    # Handle bare names (like [[README]] or [[AXIOMS.md]])
    # Wrap in try-except for OSError (e.g., path too long)
    try:
        # First try relative to source file's directory
        candidate = source_path.parent / ref_text
        if candidate.exists():
            try:
                return str(candidate.relative_to(root))
            except ValueError:
                pass

        # Try adding .md extension if not present
        if not ref_text.endswith(".md"):
            candidate_md = source_path.parent / f"{ref_text}.md"
            if candidate_md.exists():
                try:
                    return str(candidate_md.relative_to(root))
                except ValueError:
                    pass

        # Try from root
        candidate_root = root / ref_text
        if candidate_root.exists():
            return str(candidate_root.relative_to(root))

        if not ref_text.endswith(".md"):
            candidate_root_md = root / f"{ref_text}.md"
            if candidate_root_md.exists():
                return str(candidate_root_md.relative_to(root))
    except OSError:
        # Path too long or other OS error - can't resolve
        pass

    # Can't resolve - return as-is
    return ref_text


def extract_references(file_path: Path, content: str) -> list[Reference]:
    """Extract all references from file content."""
    refs: list[Reference] = []
    lines = content.split("\n")

    for line_num, line in enumerate(lines, start=1):
        for ref_type, pattern in PATTERNS.items():
            for match in pattern.finditer(line):
                target = match.group(1)
                # Skip empty or obviously invalid targets
                if not target or target.startswith("http"):
                    continue
                refs.append(
                    Reference(
                        target=target,
                        ref_type=ref_type,
                        line=line_num,
                        raw=match.group(0),
                    )
                )

    return refs


def iter_files(root: Path) -> Iterator[Path]:
    """Iterate over all scannable files in root."""
    for path in root.rglob("*"):
        # Skip directories in SKIP_DIRS
        if any(skip in path.parts for skip in SKIP_DIRS):
            continue
        # Skip output files
        if path.name in SKIP_FILES:
            continue
        # Only include files with matching extensions
        if path.is_file() and path.suffix in SCAN_EXTENSIONS:
            yield path


def build_graph(root: Path) -> dict:
    """Build the complete reference graph."""
    real_nodes: set[str] = set()  # Files that actually exist
    edges: dict[EdgeKey, Edge] = {}

    for file_path in iter_files(root):
        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        source = str(file_path.relative_to(root))
        real_nodes.add(source)

        refs = extract_references(file_path, content)
        for ref in refs:
            target = resolve_target(file_path, ref.target, root)
            path_category = classify_path(ref.target)

            # Create or update edge
            key = EdgeKey(source=source, target=target, ref_type=ref.ref_type)
            if key not in edges:
                edges[key] = Edge(
                    source=source,
                    target=target,
                    ref_type=ref.ref_type,
                    path_category=path_category,
                )
            edges[key].refs.append({"line": ref.line, "raw": ref.raw})

    # Filter edges: only keep edges where target exists as a real file
    valid_edges = [e for e in edges.values() if e.target in real_nodes]

    # Build output structure
    return {
        "generated": datetime.now().astimezone().replace(microsecond=0).isoformat(),
        "framework_root": str(root.resolve()),
        "nodes": [{"id": node} for node in sorted(real_nodes)],
        "links": [
            {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "ref_type": edge.ref_type,
                "path_category": edge.path_category,
                "refs": edge.refs,
            }
            for edge in sorted(valid_edges, key=lambda e: (e.source, e.target))
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build reference graph from framework files"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Framework root directory (default: $AOPS or current dir)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (default: <root>/reference-graph.json)",
    )
    args = parser.parse_args()

    # Determine root
    if args.root:
        root = args.root.resolve()
    elif "AOPS" in os.environ:
        root = Path(os.environ["AOPS"]).resolve()
    else:
        root = Path.cwd().resolve()

    if not root.is_dir():
        print(f"Error: Root directory does not exist: {root}", file=sys.stderr)
        return 1

    # Determine output paths
    if args.output:
        json_output = args.output
        csv_output = args.output.with_suffix(".csv")
    else:
        json_output = root / "reference-graph.json"
        csv_output = root / "reference-graph.csv"

    # Build graph
    print(f"Scanning {root}...", file=sys.stderr)
    graph = build_graph(root)
    print(
        f"Found {len(graph['nodes'])} nodes, {len(graph['links'])} edges",
        file=sys.stderr,
    )

    # Write JSON output
    json_output.write_text(json.dumps(graph, indent=2))
    print(f"Wrote {json_output}", file=sys.stderr)

    # Write CSV output (edge list for Cosmograph etc.)
    with csv_output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "weight", "ref_type"])
        for link in graph["links"]:
            writer.writerow(
                [link["source"], link["target"], link["weight"], link["ref_type"]]
            )
    print(f"Wrote {csv_output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
