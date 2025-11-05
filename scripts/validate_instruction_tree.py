#!/usr/bin/env python3
"""Validate that instruction tree in README.md is current.

This script checks if the instruction tree documentation in README.md
matches the actual repository state. Used to ensure documentation
stays synchronized with code.

Exit codes:
- 0: Tree is current
- 1: Tree is stale (needs regeneration)

Usage:
    python scripts/validate_instruction_tree.py [repo_root]
"""

import sys
from pathlib import Path


def validate_tree_is_current(repo_root: Path) -> tuple[bool, str]:
    """Validate instruction tree in README.md matches repository state.

    Args:
        repo_root: Path to repository root directory

    Returns:
        Tuple of (is_current: bool, message: str)
        - is_current: True if tree matches repository state
        - message: Empty string if current, error details if stale
    """
    from generate_instruction_tree import scan_repository, generate_markdown_tree

    # Check if README.md exists
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return False, f"README.md not found at {readme_path}"

    # Read current README content
    readme_content = readme_path.read_text()

    # Check if markers exist
    start_marker = "<!-- INSTRUCTION_TREE_START -->"
    end_marker = "<!-- INSTRUCTION_TREE_END -->"

    if start_marker not in readme_content or end_marker not in readme_content:
        return False, f"Instruction tree markers not found in README.md"

    # Extract current tree from README
    start_idx = readme_content.index(start_marker) + len(start_marker)
    end_idx = readme_content.index(end_marker)
    current_tree_in_readme = readme_content[start_idx:end_idx].strip()

    # Generate what tree SHOULD be based on current repository state
    components = scan_repository(repo_root)
    expected_tree = generate_markdown_tree(components, repo_root).strip()

    # Compare
    if current_tree_in_readme == expected_tree:
        return True, "Instruction tree is current"

    # Trees don't match - identify what changed
    # Simple difference detection: check for component names
    readme_lines = set(current_tree_in_readme.split('\n'))
    expected_lines = set(expected_tree.split('\n'))

    added_lines = expected_lines - readme_lines
    removed_lines = readme_lines - expected_lines

    diff_msg = "Instruction tree is stale (mismatch between README.md and repository state).\n"

    if added_lines:
        diff_msg += f"\nNew components in repository not in README:\n"
        for line in sorted(added_lines):
            if line.strip():
                diff_msg += f"  + {line.strip()}\n"

    if removed_lines:
        diff_msg += f"\nComponents in README not in repository:\n"
        for line in sorted(removed_lines):
            if line.strip():
                diff_msg += f"  - {line.strip()}\n"

    diff_msg += f"\nRun: python scripts/generate_instruction_tree.py"

    return False, diff_msg


def main():
    """CLI entry point."""
    # Get repository root from command line or default to current directory
    if len(sys.argv) > 1:
        repo_root = Path(sys.argv[1])
    else:
        repo_root = Path.cwd()

    is_current, message = validate_tree_is_current(repo_root)

    if is_current:
        print(message)
        sys.exit(0)
    else:
        print(message, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
