#!/usr/bin/env python3
"""
Ensure every folder in data/ has an index file (folder/folder.md).

Usage:
    python ensure_indexes.py --dry-run     # Preview missing indexes
    python ensure_indexes.py               # Create missing indexes
"""

import argparse
from pathlib import Path


def find_folders_without_index(data_dir: Path) -> list[tuple[Path, Path]]:
    """Find folders that don't have a matching index file.

    Returns list of (folder_path, expected_index_path) tuples.
    """
    missing = []

    for folder in sorted(data_dir.rglob("*")):
        if not folder.is_dir():
            continue

        # Skip hidden folders
        if any(part.startswith(".") for part in folder.parts):
            continue

        # Skip certain folders
        skip_folders = {"__pycache__", "node_modules", ".git", "archived"}
        if folder.name in skip_folders:
            continue

        # Check for index file: folder/folder.md
        expected_index = folder / f"{folder.name}.md"

        if not expected_index.exists():
            # Check if there are any .md files in the folder
            md_files = list(folder.glob("*.md"))
            if md_files or list(folder.iterdir()):  # Has content
                missing.append((folder, expected_index))

    return missing


def create_index_file(folder: Path, index_path: Path, dry_run: bool = False) -> str:
    """Create an index file for a folder."""
    # Generate title from folder name
    title = folder.name.replace("-", " ").replace("_", " ").title()

    # Generate permalink
    rel_path = folder.relative_to(folder.parents[len(folder.parents) - 2])
    permalink = str(rel_path).replace("/", "-").replace("_", "-").lower()
    permalink = "".join(c for c in permalink if c.isalnum() or c == "-")

    # List contents
    contents = []
    for item in sorted(folder.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            subindex = item / f"{item.name}.md"
            if subindex.exists():
                contents.append(f"- [[{item.name}/{item.name}|{item.name}]]")
            else:
                contents.append(f"- 📁 {item.name}/")
        elif item.suffix == ".md" and item != index_path:
            stem = item.stem
            contents.append(f"- [[{stem}]]")

    contents_section = "\n".join(contents) if contents else "*(empty)*"

    content = f"""---
title: {title}
permalink: {permalink}
type: note
tags:
  - index
---

# {title}

Index page for the {folder.name} folder.

## Contents

{contents_section}

## Observations

- [context] This is an auto-generated index file for folder organization #index

## Relations

"""

    if not dry_run:
        index_path.write_text(content)
        return f"Created: {index_path}"
    else:
        return f"Would create: {index_path}"


def main():
    parser = argparse.ArgumentParser(description="Ensure folder index files exist")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be created")
    parser.add_argument("--repo-root", default=".", help="Repository root")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_dir = repo_root / "data"

    if not data_dir.exists():
        print(f"Error: data/ directory not found at {data_dir}")
        return

    missing = find_folders_without_index(data_dir)

    if not missing:
        print("All folders have index files!")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Folders missing index files: {len(missing)}\n")

    for folder, expected_index in missing:
        result = create_index_file(folder, expected_index, dry_run=args.dry_run)
        print(result)

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Total: {len(missing)} index files")


if __name__ == "__main__":
    main()
