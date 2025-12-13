#!/usr/bin/env python3
"""
Find potential duplicate markdown files based on title similarity.

Usage:
    python find_duplicates.py              # Find potential duplicates
    python find_duplicates.py --threshold 0.8  # Adjust similarity threshold
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path

import yaml


def extract_title(file_path: Path) -> str | None:
    """Extract title from frontmatter or H1 heading."""
    try:
        content = file_path.read_text()
    except Exception:
        return None

    # Try frontmatter
    if content.startswith("---"):
        lines = content.split("\n")
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                try:
                    fm_text = "\n".join(lines[1:i])
                    fm = yaml.safe_load(fm_text) or {}
                    if "title" in fm:
                        return str(fm["title"])
                except Exception:
                    pass
                break

    # Try H1 heading
    for line in content.split("\n"):
        if line.startswith("# ") and not line.startswith("##"):
            return line[2:].strip()

    return None


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Lowercase
    title = title.lower()
    # Remove common prefixes/suffixes
    title = re.sub(r"^\s*(draft|wip|todo|note|context)[\s:-]*", "", title)
    title = re.sub(r"[\s:-]*(draft|wip|v\d+)?\s*$", "", title)
    # Remove dates
    title = re.sub(r"\d{4}[-/]\d{2}[-/]\d{2}", "", title)
    title = re.sub(r"\(\d{4}\)", "", title)
    # Remove special characters
    title = re.sub(r"[^\w\s]", " ", title)
    # Normalize whitespace
    title = " ".join(title.split())
    return title


def jaccard_similarity(s1: str, s2: str) -> float:
    """Calculate Jaccard similarity between two strings."""
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def find_duplicates(data_dir: Path, threshold: float = 0.7) -> list[list[tuple[Path, str]]]:
    """Find groups of potentially duplicate files.

    Returns list of groups, where each group is a list of (path, title) tuples.
    """
    # Collect all titles
    files_with_titles = []
    for file_path in data_dir.rglob("*.md"):
        title = extract_title(file_path)
        if title:
            files_with_titles.append((file_path, title, normalize_title(title)))

    # Group by normalized title (exact matches)
    exact_groups = defaultdict(list)
    for path, title, norm_title in files_with_titles:
        if norm_title:
            exact_groups[norm_title].append((path, title))

    # Find exact duplicates
    duplicate_groups = []
    for norm_title, files in exact_groups.items():
        if len(files) > 1:
            duplicate_groups.append(files)

    # Find similar titles (fuzzy matching)
    processed = set()
    for i, (path1, title1, norm1) in enumerate(files_with_titles):
        if path1 in processed or not norm1:
            continue

        similar_group = [(path1, title1)]

        for j, (path2, title2, norm2) in enumerate(files_with_titles[i + 1:], i + 1):
            if path2 in processed or not norm2:
                continue

            # Skip if already exact match
            if norm1 == norm2:
                continue

            sim = jaccard_similarity(norm1, norm2)
            if sim >= threshold:
                similar_group.append((path2, title2))
                processed.add(path2)

        if len(similar_group) > 1:
            duplicate_groups.append(similar_group)
            processed.add(path1)

    return duplicate_groups


def main():
    parser = argparse.ArgumentParser(description="Find potential duplicate markdown files")
    parser.add_argument("--threshold", type=float, default=0.7, help="Similarity threshold (0-1)")
    parser.add_argument("--repo-root", default=".", help="Repository root")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_dir = repo_root / "data"

    if not data_dir.exists():
        print(f"Error: data/ directory not found at {data_dir}")
        return

    print(f"Scanning for potential duplicates (threshold: {args.threshold})...\n")

    groups = find_duplicates(data_dir, threshold=args.threshold)

    if not groups:
        print("No potential duplicates found.")
        return

    print(f"Found {len(groups)} groups of potential duplicates:\n")

    for i, group in enumerate(groups, 1):
        print(f"Group {i}:")
        for path, title in group:
            rel_path = path.relative_to(repo_root)
            print(f"  - {rel_path}")
            print(f"    Title: {title}")
        print()

    print(f"\nTotal: {len(groups)} groups, {sum(len(g) for g in groups)} files")
    print("\nReview these manually to decide which to keep/merge.")


if __name__ == "__main__":
    main()
