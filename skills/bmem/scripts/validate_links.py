#!/usr/bin/env python3
"""
Validate and suggest fixes for wiki-links in markdown files.

Usage:
    python validate_links.py               # Find broken links
    python validate_links.py --suggest     # Suggest similar targets
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path


def extract_wiki_links(content: str) -> list[str]:
    """Extract all [[wiki-links]] from content."""
    # Pattern matches [[target]] or [[target|alias]]
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    return re.findall(pattern, content)


def normalize_link_target(target: str) -> str:
    """Normalize a link target for matching."""
    # Remove path prefixes
    target = target.split("/")[-1]
    # Remove .md extension
    target = re.sub(r"\.md$", "", target)
    # Lowercase
    target = target.lower()
    # Normalize separators
    target = target.replace("-", " ").replace("_", " ")
    return target


def build_file_index(data_dir: Path) -> dict[str, Path]:
    """Build index of all markdown files by normalized name.

    Returns dict mapping normalized_name -> file_path.
    """
    index = {}
    for file_path in data_dir.rglob("*.md"):
        # Index by stem (filename without .md)
        stem = file_path.stem
        norm = normalize_link_target(stem)
        index[norm] = file_path

        # Also index by full relative path
        rel_path = str(file_path.relative_to(data_dir))
        rel_norm = normalize_link_target(rel_path)
        index[rel_norm] = file_path

    return index


def find_similar_targets(target: str, file_index: dict[str, Path], threshold: float = 0.5) -> list[tuple[str, float]]:
    """Find similar file names using Jaccard similarity."""
    norm_target = normalize_link_target(target)
    target_words = set(norm_target.split())

    similar = []
    for norm_name, path in file_index.items():
        name_words = set(norm_name.split())

        # Jaccard similarity on words
        if target_words and name_words:
            intersection = target_words & name_words
            union = target_words | name_words
            similarity = len(intersection) / len(union)

            if similarity >= threshold:
                similar.append((path.stem, similarity))

    return sorted(similar, key=lambda x: -x[1])[:5]


def validate_links(data_dir: Path, suggest: bool = False) -> dict:
    """Validate all wiki-links in markdown files.

    Returns dict with:
        - broken: list of (source_file, target, line_num) for broken links
        - suggestions: dict mapping target -> list of suggested fixes
    """
    file_index = build_file_index(data_dir)

    broken_links = []
    link_sources = defaultdict(list)  # target -> [(source, line)]

    for file_path in data_dir.rglob("*.md"):
        try:
            content = file_path.read_text()
        except Exception:
            continue

        for line_num, line in enumerate(content.split("\n"), 1):
            links = extract_wiki_links(line)
            for target in links:
                norm_target = normalize_link_target(target)

                # Check if target exists
                if norm_target not in file_index:
                    broken_links.append((file_path, target, line_num))
                    link_sources[target].append((file_path, line_num))

    suggestions = {}
    if suggest and broken_links:
        seen_targets = set()
        for _, target, _ in broken_links:
            if target in seen_targets:
                continue
            seen_targets.add(target)

            similar = find_similar_targets(target, file_index)
            if similar:
                suggestions[target] = similar

    return {
        "broken": broken_links,
        "suggestions": suggestions,
        "link_sources": dict(link_sources),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate wiki-links in markdown files")
    parser.add_argument("--suggest", action="store_true", help="Suggest similar targets for broken links")
    parser.add_argument("--repo-root", default=".", help="Repository root")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_dir = repo_root / "data"

    if not data_dir.exists():
        print(f"Error: data/ directory not found at {data_dir}")
        return

    print("Validating wiki-links...\n")

    results = validate_links(data_dir, suggest=args.suggest)
    broken = results["broken"]
    suggestions = results["suggestions"]
    link_sources = results["link_sources"]

    if not broken:
        print("All wiki-links are valid!")
        return

    # Group by target
    print(f"Found {len(broken)} broken links to {len(link_sources)} unique targets:\n")

    for target, sources in sorted(link_sources.items()):
        print(f"[[{target}]] - {len(sources)} reference(s)")
        for source, line_num in sources[:3]:
            rel_path = source.relative_to(repo_root)
            print(f"  - {rel_path}:{line_num}")
        if len(sources) > 3:
            print(f"  ... and {len(sources) - 3} more")

        if args.suggest and target in suggestions:
            print("  Suggestions:")
            for suggestion, score in suggestions[target]:
                print(f"    - [[{suggestion}]] (similarity: {score:.2f})")

        print()

    print(f"\nTotal: {len(broken)} broken links to {len(link_sources)} targets")


if __name__ == "__main__":
    main()
