#!/usr/bin/env python3
"""
Analyze tag usage across markdown files for cleanup opportunities.

Usage:
    python analyze_tags.py                 # Show tag statistics
    python analyze_tags.py --min-count 3   # Show tags used fewer than N times
    python analyze_tags.py --orphans       # Show unused/rare tags for removal
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def extract_tags_from_file(file_path: Path) -> tuple[list[str], list[str]]:
    """Extract tags from frontmatter and inline #tags.

    Returns (frontmatter_tags, inline_tags).
    """
    try:
        content = file_path.read_text()
    except Exception:
        return [], []

    frontmatter_tags = []
    inline_tags = []

    # Extract from frontmatter
    if content.startswith("---"):
        lines = content.split("\n")
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                try:
                    fm_text = "\n".join(lines[1:i])
                    fm = yaml.safe_load(fm_text) or {}
                    if "tags" in fm and isinstance(fm["tags"], list):
                        frontmatter_tags = [str(t) for t in fm["tags"] if t]
                except Exception:
                    pass
                break

    # Extract inline tags (e.g., #tag-name)
    inline_pattern = r"(?<!\[)#([a-zA-Z][a-zA-Z0-9_-]*)"
    inline_tags = re.findall(inline_pattern, content)

    return frontmatter_tags, inline_tags


def analyze_tags(data_dir: Path) -> dict:
    """Analyze tag usage across all files.

    Returns dict with:
        - frontmatter_counts: Counter of frontmatter tags
        - inline_counts: Counter of inline tags
        - tag_files: dict mapping tag -> list of files using it
    """
    frontmatter_counts = Counter()
    inline_counts = Counter()
    tag_files = defaultdict(list)

    for file_path in data_dir.rglob("*.md"):
        fm_tags, inline_tags = extract_tags_from_file(file_path)

        for tag in fm_tags:
            frontmatter_counts[tag] += 1
            tag_files[f"fm:{tag}"].append(file_path)

        for tag in inline_tags:
            inline_counts[tag] += 1
            tag_files[f"inline:{tag}"].append(file_path)

    return {
        "frontmatter_counts": frontmatter_counts,
        "inline_counts": inline_counts,
        "tag_files": tag_files,
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze tag usage in markdown files")
    parser.add_argument("--min-count", type=int, default=3, help="Show tags used fewer than N times")
    parser.add_argument("--orphans", action="store_true", help="Show rare tags for potential removal")
    parser.add_argument("--repo-root", default=".", help="Repository root")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_dir = repo_root / "data"

    if not data_dir.exists():
        print(f"Error: data/ directory not found at {data_dir}")
        return

    print("Analyzing tags...\n")

    results = analyze_tags(data_dir)
    fm_counts = results["frontmatter_counts"]
    inline_counts = results["inline_counts"]
    tag_files = results["tag_files"]

    # Summary statistics
    print("=== Tag Statistics ===\n")
    print(f"Unique frontmatter tags: {len(fm_counts)}")
    print(f"Unique inline tags: {len(inline_counts)}")
    print(f"Total tag usages (frontmatter): {sum(fm_counts.values())}")
    print(f"Total tag usages (inline): {sum(inline_counts.values())}")

    # Most common frontmatter tags
    print("\n=== Top 20 Frontmatter Tags ===\n")
    for tag, count in fm_counts.most_common(20):
        print(f"  {count:4d}  {tag}")

    # Most common inline tags
    print("\n=== Top 20 Inline Tags ===\n")
    for tag, count in inline_counts.most_common(20):
        print(f"  {count:4d}  #{tag}")

    # Rare/orphan tags
    if args.orphans or args.min_count:
        print(f"\n=== Rare Tags (< {args.min_count} uses) ===\n")

        rare_fm = [(tag, count) for tag, count in fm_counts.items() if count < args.min_count]
        rare_inline = [(tag, count) for tag, count in inline_counts.items() if count < args.min_count]

        if rare_fm:
            print("Frontmatter tags for potential removal:")
            for tag, count in sorted(rare_fm, key=lambda x: x[1]):
                files = tag_files.get(f"fm:{tag}", [])
                file_list = ", ".join(str(f.relative_to(repo_root)) for f in files[:3])
                if len(files) > 3:
                    file_list += f" (+{len(files) - 3} more)"
                print(f"  {count:2d}x  {tag}")
                print(f"       in: {file_list}")

        if rare_inline:
            print("\nInline tags for potential consolidation:")
            for tag, count in sorted(rare_inline, key=lambda x: x[1])[:20]:
                print(f"  {count:2d}x  #{tag}")

    # Similar tags (potential typos or variants)
    print("\n=== Potential Tag Variants ===\n")
    all_tags = list(fm_counts.keys()) + list(inline_counts.keys())
    all_tags = list(set(t.lower() for t in all_tags))

    # Group by prefix
    prefix_groups = defaultdict(list)
    for tag in all_tags:
        prefix = tag[:4] if len(tag) >= 4 else tag
        prefix_groups[prefix].append(tag)

    for prefix, tags in sorted(prefix_groups.items()):
        if len(tags) > 1:
            print(f"  Similar: {', '.join(sorted(tags))}")


if __name__ == "__main__":
    main()
