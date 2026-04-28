#!/usr/bin/env -S uv run python
"""
Build script to generate platform-specific instruction files from CORE.md.
SSoT: .agents/CORE.md
"""

import re
import sys
from pathlib import Path


def process_core_md(src_path: Path, target_platform: str) -> str:
    """
    Process CORE.md and filter sections based on @platforms tags.

    Syntax:
    <!-- @platforms: platform1, platform2 -->
    ... content ...
    <!-- @platforms: all --> (or 'end')
    """
    if not src_path.exists():
        print(f"Warning: {src_path} not found.", file=sys.stderr)
        return ""

    content = src_path.read_text()
    lines = content.splitlines()
    output = []

    # Default is enabled (for lines before any tag)
    current_enabled = True

    # Pattern: <!-- @platforms: platform1, platform2 -->
    tag_pattern = re.compile(r"<!--\s*@platforms:\s*(.*?)\s*-->")

    for line in lines:
        match = tag_pattern.search(line)
        if match:
            platforms_str = match.group(1).strip()
            if platforms_str in ("all", "end"):
                current_enabled = True
            else:
                platforms = [p.strip() for p in platforms_str.split(",")]
                current_enabled = target_platform in platforms
            # We don't include the tag line itself in the output
            continue

        if current_enabled:
            output.append(line)

    return "\n".join(output).strip() + "\n"


def main():
    repo_root = Path(__file__).parent.parent.resolve()
    core_md = repo_root / ".agents" / "CORE.md"

    # Target distributions
    targets = {
        "claude-code": "dist/aops-claude/CLAUDE.md",
        "cowork": "dist/aops-cowork/CLAUDE.md",
        "gemini": "dist/aops-gemini/GEMINI.md",
        "antigravity": "dist/aops-antigravity/GEMINI.md",
        "tools-claude": "dist/aops-tools-claude/CLAUDE.md",
        "tools-gemini": "dist/aops-tools-gemini/GEMINI.md",
    }

    success = True
    for platform, dest_rel_path in targets.items():
        dest_path = repo_root / dest_rel_path

        # In a real build, dist/ directories are created by scripts/build.py.
        # Here we ensure they exist for testing/standalone use.
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Generating {dest_rel_path} for {platform}...")
        processed_content = process_core_md(core_md, platform)

        if not processed_content:
            print(f"  Warning: No content generated for {platform}")

        # Add header warning about auto-generation
        header = "<!-- AUTOMATICALLY GENERATED from .agents/CORE.md - DO NOT EDIT BY HAND -->\n"
        dest_path.write_text(header + processed_content)

    if success:
        print("✓ Core instruction consolidation complete.")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
