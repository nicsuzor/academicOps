#!/usr/bin/env python3
"""
Convert project markdown files to Basic Memory compliant format.

Usage:
    python project_convert.py [--dry-run]
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import yaml
import re


def extract_metadata(content: str) -> Dict[str, Any]:
    """Extract metadata from project markdown content."""
    metadata = {}

    # Extract priority
    priority_match = re.search(r"\*\*Priority:\*\*\s*P(\d+)", content, re.IGNORECASE)
    if priority_match:
        metadata["priority"] = int(priority_match.group(1))

    # Extract goals (look for links to goal files)
    goal_matches = re.findall(r"\[([^\]]+)\]\(\.\./goals/([^)]+)\)", content)
    if goal_matches:
        metadata["goals"] = [goal[1].replace(".md", "") for goal in goal_matches]

    return metadata


def extract_project_name(filepath: Path) -> str:
    """Extract project name from filename."""
    return filepath.stem


def create_permalink(project_name: str) -> str:
    """Create BM-standard permalink."""
    return f"projects/{project_name}"


def create_title(project_name: str) -> str:
    """Create human-readable title from project name."""
    # Replace hyphens with spaces and title case
    return project_name.replace("-", " ").title()


def extract_description(content: str) -> str:
    """Extract description/context from project content."""
    # Look for Description section
    desc_match = re.search(r"## Description\s*\n\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
    if desc_match:
        return desc_match.group(1).strip()

    # Look for first substantial paragraph after title
    lines = content.split("\n")
    in_content = False
    paragraphs = []
    current_para = []

    for line in lines:
        if line.startswith("# "):
            in_content = True
            continue
        if in_content:
            if line.strip() == "":
                if current_para:
                    paragraphs.append(" ".join(current_para))
                    current_para = []
            elif not line.startswith("#") and not line.startswith("-"):
                current_para.append(line.strip())

    if current_para:
        paragraphs.append(" ".join(current_para))

    # Return first substantial paragraph
    for para in paragraphs:
        if len(para) > 50 and not para.startswith("**"):
            return para

    return "Project documentation"


def extract_observations(content: str, metadata: Dict[str, Any]) -> List[str]:
    """Extract key observations from project content."""
    observations = []

    # Priority observation
    if metadata.get("priority"):
        observations.append(
            f"- [metadata] Priority: P{metadata['priority']} #priority-p{metadata['priority']}"
        )

    # Strategic context
    if "Strategic Context" in content or "Strategy" in content:
        observations.append(
            "- [fact] Project has strategic planning documentation #strategic"
        )

    # Next actions section
    if "## Next Actions" in content or "CRITICAL:" in content:
        observations.append("- [requirement] Active next actions defined #actionable")

    # Milestones/tasks
    if "## Key Tasks" in content or "## Milestones" in content:
        observations.append("- [fact] Milestones and key tasks tracked #planning")

    # Development roadmap
    if "## Development Roadmap" in content or "Horizon" in content:
        observations.append("- [fact] Development roadmap documented #roadmap")

    # Completed work
    if "## Completed" in content or "✓" in content:
        observations.append("- [fact] Completed tasks tracked for reference #history")

    # Current work
    if "## Current Work" in content:
        observations.append("- [fact] Current work status maintained #active")

    return observations


def extract_goal_relations(metadata: Dict[str, Any]) -> List[str]:
    """Extract goal relations from metadata."""
    relations = []

    if metadata.get("goals"):
        for goal in metadata["goals"]:
            # Convert goal filename to title
            goal_title = goal.replace("-", " ").title()
            relations.append(f"- supports [[{goal_title}]]")

    return relations


def format_markdown(filepath: Path, content: str) -> str:
    """Convert project markdown to Basic Memory compliant format."""

    project_name = extract_project_name(filepath)
    title = create_title(project_name)
    permalink = create_permalink(project_name)
    metadata = extract_metadata(content)
    description = extract_description(content)

    # Build BM-compliant frontmatter
    frontmatter = {
        "title": title,
        "permalink": permalink,
        "type": "project",
        "tags": ["project"],
    }

    # Add priority if exists
    if metadata.get("priority"):
        frontmatter["priority"] = metadata["priority"]
        frontmatter["tags"].append(f"priority-p{metadata['priority']}")

    # Add goal tags
    if metadata.get("goals"):
        for goal in metadata["goals"]:
            frontmatter["tags"].append(f"goal:{goal}")

    # Build markdown body with BM structure
    body_parts = [
        f"# {title}",
        "",
        "## Context",
        "",
        description,
        "",
        "## Observations",
        "",
    ]

    # Add observations
    observations = extract_observations(content, metadata)
    body_parts.extend(observations)

    # Add original content reference
    body_parts.append(
        f"- [meta] Original project documentation preserved below #source"
    )

    body_parts.extend(["", "## Relations", ""])

    # Add goal relations
    goal_relations = extract_goal_relations(metadata)
    body_parts.extend(goal_relations)

    body_parts.extend(
        [
            "",
            "---",
            "",
            "## Original Project Documentation",
            "",
            content,
        ]
    )

    # Combine frontmatter and body
    yaml_str = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    md_content = f"---\n{yaml_str}---\n\n" + "\n".join(body_parts)

    return md_content


def convert_project(md_path: Path, output_dir: Path, dry_run: bool = False) -> bool:
    """Convert a single project markdown to BM format."""
    try:
        # Read original markdown
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Generate BM-compliant markdown
        md_content = format_markdown(md_path, content)

        # Determine output filename (same as input)
        output_path = output_dir / md_path.name

        if dry_run:
            print(f"Would convert: {md_path.name} -> {output_path}")
            return True

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write markdown file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"✓ Converted: {md_path.name}")
        return True

    except Exception as e:
        print(f"✗ Error converting {md_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main conversion function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert project markdown to BM format"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be converted"
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data/projects"), help="Input directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/projects"),
        help="Output directory",
    )

    args = parser.parse_args()

    # Find all markdown files
    md_files = list(args.input_dir.glob("*.md"))
    total = len(md_files)

    print(f"Found {total} project markdown files")

    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No files will be written\n")

    # Convert each file
    converted = 0
    failed = 0

    for md_path in md_files:
        if convert_project(md_path, args.output_dir, args.dry_run):
            converted += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Conversion {'simulation' if args.dry_run else 'complete'}:")
    print(f"  Total: {total}")
    print(f"  Converted: {converted}")
    print(f"  Failed: {failed}")
    print(f"{'=' * 60}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
