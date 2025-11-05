#!/usr/bin/env python3
"""Generate instruction tree documentation from repository scan.

This script scans the academicOps repository to discover all instruction
components (agents, skills, commands, hooks, core) and generates
comprehensive documentation showing the complete instruction tree.

Usage:
    python scripts/generate_instruction_tree.py [--output README.md]

The script:
1. Scans repository for all components
2. Parses @references and symlinks
3. Generates markdown documentation
4. Updates README.md or specified output file
"""

import argparse
import re
from pathlib import Path
from typing import Any


def scan_repository(repo_root: Path) -> dict[str, Any]:
    """Scan repository and discover all instruction components.

    Args:
        repo_root: Path to repository root directory

    Returns:
        Dictionary with keys: 'agents', 'skills', 'commands', 'hooks', 'core'
        Each containing list of discovered components with metadata
    """
    components = {
        'agents': [],
        'skills': [],
        'commands': [],
        'hooks': [],
        'core': {}
    }

    # Scan agents/*.md files
    agents_dir = repo_root / 'agents'
    if agents_dir.exists():
        for agent_file in agents_dir.glob('*.md'):
            components['agents'].append({
                'name': agent_file.stem,
                'file': agent_file.name,
                'path': str(agent_file.relative_to(repo_root))
            })

    # Scan skills/*/ directories
    skills_dir = repo_root / 'skills'
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith('.'):
                components['skills'].append({
                    'name': skill_dir.name,
                    'path': str(skill_dir.relative_to(repo_root))
                })

    # Scan commands/*.md files
    commands_dir = repo_root / 'commands'
    if commands_dir.exists():
        for command_file in commands_dir.glob('*.md'):
            components['commands'].append({
                'name': command_file.stem,
                'file': command_file.name,
                'path': str(command_file.relative_to(repo_root))
            })

    # Scan hooks/*.py files
    hooks_dir = repo_root / 'hooks'
    if hooks_dir.exists():
        for hook_file in hooks_dir.glob('*.py'):
            # Skip __pycache__ and __init__.py
            if hook_file.stem.startswith('__'):
                continue
            components['hooks'].append({
                'name': hook_file.stem,
                'file': hook_file.name,
                'path': str(hook_file.relative_to(repo_root))
            })

    # Scan core/_CORE.md and parse @references
    core_file = repo_root / 'core' / '_CORE.md'
    if core_file.exists():
        core_content = core_file.read_text()
        references = _parse_references(core_content)
        components['core'] = {
            'file': str(core_file.relative_to(repo_root)),
            'references': references
        }

    return components


def _parse_references(content: str) -> list[str]:
    """Parse @reference patterns from markdown content.

    Args:
        content: Markdown file content

    Returns:
        List of referenced file paths (e.g., ['../chunks/AXIOMS.md'])
    """
    # Match @../path/to/file.md patterns
    reference_pattern = r'@([\w/.+-]+\.md)'
    matches = re.findall(reference_pattern, content)
    return matches


def main():
    """Main entry point for script."""
    parser = argparse.ArgumentParser(
        description='Generate instruction tree documentation'
    )
    parser.add_argument(
        '--output',
        default='README.md',
        help='Output file to update (default: README.md)'
    )
    args = parser.parse_args()

    # Get repository root (where script is located)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Scan repository
    components = scan_repository(repo_root)

    # Print summary for now (will generate markdown in next cycle)
    print(f"Scanned repository: {repo_root}")
    print(f"Found {len(components['agents'])} agents")
    print(f"Found {len(components['skills'])} skills")
    print(f"Found {len(components['commands'])} commands")
    print(f"Found {len(components['hooks'])} hooks")
    print(f"Found core with {len(components['core'].get('references', []))} references")


if __name__ == '__main__':
    main()
