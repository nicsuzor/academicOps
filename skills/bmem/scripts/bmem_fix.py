#!/usr/bin/env python3
"""
Fix common BMEM compliance issues in markdown files.

Usage:
    python bmem_fix.py --dry-run          # Preview changes
    python bmem_fix.py                     # Apply changes
    python bmem_fix.py data/projects/      # Fix specific directory
"""

import argparse
import re
from pathlib import Path

import yaml


def fix_permalink(permalink) -> str:
    """Fix permalink to be lowercase alphanumeric with hyphens only."""
    if not permalink:
        return ""
    permalink = str(permalink)
    permalink = permalink.lstrip("/")
    permalink = permalink.replace("/", "-")
    permalink = re.sub(r"[^a-z0-9-]", "", permalink.lower())
    permalink = re.sub(r"-+", "-", permalink)
    return permalink.strip("-")


def extract_frontmatter(content: str) -> tuple[dict | None, int, int]:
    """Extract YAML frontmatter from content.

    Returns (frontmatter_dict, start_line, end_line) or (None, 0, 0) if no frontmatter.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, 0, 0

    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None, 0, 0

    try:
        fm_text = "\n".join(lines[1:end_idx])
        frontmatter = yaml.safe_load(fm_text) or {}
        return frontmatter, 0, end_idx
    except yaml.YAMLError:
        return {}, 0, end_idx


def rebuild_frontmatter(fm: dict) -> str:
    """Rebuild frontmatter YAML string with proper ordering."""
    lines = ["---"]
    ordered_keys = ["title", "permalink", "type", "tags"]

    for key in ordered_keys:
        if key in fm:
            value = fm[key]
            if key == "tags" and isinstance(value, list):
                if len(value) == 0:
                    lines.append("tags: []")
                else:
                    lines.append("tags:")
                    for item in value:
                        lines.append(f"  - {item}")
            elif isinstance(value, str) and (":" in value or value.startswith("-") or value.startswith("#")):
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f"{key}: {value}")

    for key, value in fm.items():
        if key in ordered_keys:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        elif isinstance(value, str) and (":" in value or value.startswith("-") or value.startswith("#")):
            lines.append(f'{key}: "{value}"')
        else:
            lines.append(f"{key}: {value}")

    lines.append("---")
    return "\n".join(lines)


def fix_frontmatter(file_path: Path, dry_run: bool = False) -> list[str]:
    """Fix frontmatter issues in a single file."""
    fixes = []
    content = file_path.read_text()

    fm, start, end = extract_frontmatter(content)
    if fm is None:
        return ["No frontmatter found - skipping"]

    lines = content.split("\n")
    modified = False

    # Fix missing title
    if "title" not in fm:
        for line in lines[end + 1:]:
            if line.startswith("# ") and not line.startswith("## "):
                fm["title"] = line[2:].strip()
                fixes.append(f"Added missing title: {fm['title']}")
                modified = True
                break
        if "title" not in fm:
            fm["title"] = file_path.stem.replace("-", " ").replace("_", " ").title()
            fixes.append(f"Added missing title from filename: {fm['title']}")
            modified = True

    # Fix permalink
    if "permalink" in fm:
        old_permalink = fm["permalink"]
        new_permalink = fix_permalink(old_permalink)
        if str(old_permalink) != new_permalink:
            fm["permalink"] = new_permalink
            fixes.append(f"Fixed permalink: '{old_permalink}' -> '{new_permalink}'")
            modified = True

    # Fix missing type
    if "type" not in fm:
        fm["type"] = "note"
        fixes.append("Added missing type: note")
        modified = True

    # Fix missing/empty tags
    if "tags" not in fm:
        fm["tags"] = []
        fixes.append("Added missing tags: []")
        modified = True
    elif not isinstance(fm["tags"], list):
        fm["tags"] = [fm["tags"]] if fm["tags"] else []
        fixes.append("Fixed tags to be a list")
        modified = True

    if modified:
        new_fm = rebuild_frontmatter(fm)
        rest = "\n".join(lines[end + 1:])
        new_content = new_fm + "\n" + rest

        if not dry_run:
            file_path.write_text(new_content)

    return fixes


def fix_h1_heading(file_path: Path, dry_run: bool = False) -> list[str]:
    """Fix H1 heading to match frontmatter title."""
    fixes = []
    content = file_path.read_text()

    fm, start, end = extract_frontmatter(content)
    if fm is None or "title" not in fm:
        return []

    title = str(fm["title"])
    lines = content.split("\n")
    modified = False

    for i in range(end + 1, len(lines)):
        line = lines[i]
        if line.startswith("# ") and not line.startswith("## "):
            h1_text = line[2:].strip().strip("'\"")
            if h1_text != title:
                lines[i] = f"# {title}"
                fixes.append(f"Line {i+1}: Fixed H1 '{h1_text}' -> '{title}'")
                modified = True
            break

    if modified and not dry_run:
        file_path.write_text("\n".join(lines))

    return fixes


def fix_relation_syntax(file_path: Path, dry_run: bool = False) -> list[str]:
    """Fix invalid relation syntax in Relations section."""
    fixes = []
    content = file_path.read_text()
    lines = content.split("\n")

    in_relations = False
    modified = False
    new_lines = []

    for i, line in enumerate(lines):
        if line.strip() == "## Relations":
            in_relations = True
            new_lines.append(line)
            continue

        if in_relations and line.startswith("## "):
            in_relations = False

        if in_relations and line.startswith("- "):
            stripped = line.strip()
            valid_pattern = r"^- ([a-z_]+) \[\[.+\]\](\s*#.*)?$"

            if not re.match(valid_pattern, stripped):
                # Pattern: - **Label**: [[Link]]
                match = re.match(r"^- \*\*[^*]+\*\*:\s*\[\[([^\]]+)\]\]$", stripped)
                if match:
                    link = match.group(1)
                    new_lines.append(f"- relates_to [[{link}]]")
                    fixes.append(f"Line {i+1}: Fixed **Label**: [[Link]] syntax")
                    modified = True
                    continue

                # Pattern: - Label: [[Link]]
                match = re.match(r"^- [A-Za-z][^:]*:\s*\[\[([^\]]+)\]\]$", stripped)
                if match:
                    link = match.group(1)
                    new_lines.append(f"- relates_to [[{link}]]")
                    fixes.append(f"Line {i+1}: Fixed Label: [[Link]] syntax")
                    modified = True
                    continue

                # Pattern: - relates-to [[Link]] (hyphen instead of underscore)
                match = re.match(r"^- ([a-z]+-[a-z_-]+) \[\[([^\]]+)\]\]$", stripped)
                if match:
                    rel_type = match.group(1).replace("-", "_")
                    link = match.group(2)
                    new_lines.append(f"- {rel_type} [[{link}]]")
                    fixes.append(f"Line {i+1}: Fixed hyphenated relation type")
                    modified = True
                    continue

                # Pattern: - [[Link]]: description
                match = re.match(r"^- \[\[([^\]]+)\]\]:?\s*(.*)$", stripped)
                if match:
                    link = match.group(1)
                    desc = match.group(2)
                    new_line = f"- relates_to [[{link}]]"
                    if desc:
                        new_line += f" # {desc}"
                    new_lines.append(new_line)
                    fixes.append(f"Line {i+1}: Fixed [[Link]]: syntax")
                    modified = True
                    continue

                # Pattern: - [[Link]] relation-type (backwards)
                match = re.match(r"^- \[\[([^\]]+)\]\]\s+([a-z_-]+)$", stripped)
                if match:
                    link = match.group(1)
                    rel_type = match.group(2).replace("-", "_")
                    new_lines.append(f"- {rel_type} [[{link}]]")
                    fixes.append(f"Line {i+1}: Fixed backwards relation syntax")
                    modified = True
                    continue

        new_lines.append(line)

    if modified and not dry_run:
        file_path.write_text("\n".join(new_lines))

    return fixes


def add_frontmatter_to_file(file_path: Path, dry_run: bool = False) -> list[str]:
    """Add frontmatter to files that don't have any."""
    fixes = []
    content = file_path.read_text()

    if content.strip().startswith("---"):
        return []

    lines = content.split("\n")
    title = None
    for line in lines:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    if not title:
        title = file_path.stem.replace("-", " ").replace("_", " ")

    permalink = re.sub(r"[^a-z0-9\s-]", "", title.lower())
    permalink = re.sub(r"\s+", "-", permalink)
    permalink = re.sub(r"-+", "-", permalink).strip("-")

    frontmatter = f"""---
title: {title}
permalink: {permalink}
type: note
tags: []
---

"""

    new_content = frontmatter + content

    if not dry_run:
        file_path.write_text(new_content)

    fixes.append(f"Added frontmatter with title: {title}")
    return fixes


def fix_file(file_path: Path, dry_run: bool = False) -> list[str]:
    """Apply all fixes to a single file."""
    all_fixes = []

    # Add frontmatter if missing
    fm_add_fixes = add_frontmatter_to_file(file_path, dry_run=dry_run)
    all_fixes.extend(fm_add_fixes)

    # Fix frontmatter issues
    fm_fixes = fix_frontmatter(file_path, dry_run=dry_run)
    if fm_fixes != ["No frontmatter found - skipping"]:
        all_fixes.extend(fm_fixes)

    # Fix H1 heading
    h1_fixes = fix_h1_heading(file_path, dry_run=dry_run)
    all_fixes.extend(h1_fixes)

    # Fix relation syntax
    rel_fixes = fix_relation_syntax(file_path, dry_run=dry_run)
    all_fixes.extend(rel_fixes)

    return all_fixes


def main():
    parser = argparse.ArgumentParser(description="Fix BMEM compliance issues in markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("paths", nargs="*", help="Specific paths to fix (default: data/)")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    if args.paths:
        files = []
        for path in args.paths:
            p = Path(path)
            if p.is_file():
                files.append(p)
            elif p.is_dir():
                files.extend(p.glob("**/*.md"))
    else:
        files = list(repo_root.glob("data/**/*.md"))

    total_fixes = 0
    files_fixed = 0

    for file_path in sorted(files):
        try:
            all_fixes = fix_file(file_path, dry_run=args.dry_run)

            if all_fixes:
                rel_path = file_path.relative_to(repo_root) if file_path.is_relative_to(repo_root) else file_path
                print(f"\n{rel_path}:")
                for fix in all_fixes:
                    print(f"  - {fix}")
                total_fixes += len(all_fixes)
                files_fixed += 1
        except Exception as e:
            print(f"\nERROR processing {file_path}: {e}")

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Summary:")
    print(f"  Files processed: {len(files)}")
    print(f"  Files with fixes: {files_fixed}")
    print(f"  Total fixes: {total_fixes}")


if __name__ == "__main__":
    main()
