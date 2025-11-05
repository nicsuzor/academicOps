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
import yaml
from pathlib import Path
from typing import Any


def _extract_yaml_frontmatter(file_path: Path) -> dict[str, Any]:
    """Extract YAML frontmatter from markdown file.

    Args:
        file_path: Path to markdown file with YAML frontmatter

    Returns:
        Dictionary with frontmatter fields (empty dict if no frontmatter)
    """
    content = file_path.read_text()

    # Match YAML frontmatter between --- delimiters
    frontmatter_pattern = r'^---\n(.*?)\n---'
    match = re.search(frontmatter_pattern, content, re.DOTALL)

    if not match:
        return {}

    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def _extract_python_docstring(file_path: Path) -> str:
    """Extract first line of module docstring from Python file.

    Args:
        file_path: Path to Python file

    Returns:
        First line of docstring (empty string if no docstring)
    """
    content = file_path.read_text()

    # Match module docstring (""" or ''' at start of file, after shebang/comments)
    # Pattern: shebang (optional), any # comments (optional), then """ or '''
    docstring_pattern = r'^(?:#!.*\n)?(?:#.*\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')'
    match = re.search(docstring_pattern, content, re.DOTALL)

    if not match:
        return ''

    # Get first line of docstring, strip whitespace
    docstring_content = match.group(1).strip()
    first_line = docstring_content.split('\n')[0].strip() if docstring_content else ''
    return first_line


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
            frontmatter = _extract_yaml_frontmatter(agent_file)
            components['agents'].append({
                'name': agent_file.stem,
                'file': agent_file.name,
                'path': str(agent_file.relative_to(repo_root)),
                'description': frontmatter.get('description', '')
            })

    # Scan skills/*/ directories
    skills_dir = repo_root / 'skills'
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith('.'):
                # Look for SKILL.md in skill directory
                skill_file = skill_dir / 'SKILL.md'
                description = ''
                if skill_file.exists():
                    frontmatter = _extract_yaml_frontmatter(skill_file)
                    description = frontmatter.get('description', '')

                # Collect symlinks from references/ and resources/ directories
                dependencies = []
                for subdir_name in ['references', 'resources']:
                    subdir = skill_dir / subdir_name
                    if subdir.exists() and subdir.is_dir():
                        for item in subdir.iterdir():
                            if item.is_symlink():
                                # Resolve symlink and get target relative to repo_root
                                target = item.resolve()
                                if target.is_relative_to(repo_root):
                                    relative_target = target.relative_to(repo_root)
                                    dependencies.append(str(relative_target))

                components['skills'].append({
                    'name': skill_dir.name,
                    'path': str(skill_dir.relative_to(repo_root)),
                    'description': description,
                    'dependencies': dependencies
                })

    # Scan commands/*.md files
    commands_dir = repo_root / 'commands'
    if commands_dir.exists():
        for command_file in commands_dir.glob('*.md'):
            frontmatter = _extract_yaml_frontmatter(command_file)
            components['commands'].append({
                'name': command_file.stem,
                'file': command_file.name,
                'path': str(command_file.relative_to(repo_root)),
                'description': frontmatter.get('description', '')
            })

    # Scan hooks/*.py files
    hooks_dir = repo_root / 'hooks'
    if hooks_dir.exists():
        for hook_file in hooks_dir.glob('*.py'):
            # Skip __pycache__ and __init__.py
            if hook_file.stem.startswith('__'):
                continue
            description = _extract_python_docstring(hook_file)
            components['hooks'].append({
                'name': hook_file.stem,
                'file': hook_file.name,
                'path': str(hook_file.relative_to(repo_root)),
                'description': description
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


def generate_markdown_tree(components: dict[str, Any], repo_root: Path) -> str:
    """Generate markdown documentation from scanned components.

    Args:
        components: Dictionary from scan_repository() with component data
        repo_root: Path to repository root (for context)

    Returns:
        Formatted markdown string suitable for README.md insertion
    """
    lines = []

    # Header
    lines.append("## Instruction Tree")
    lines.append("")
    lines.append("This section is auto-generated from repository scan.")
    lines.append(f"Last updated: {repo_root.name} repository")
    lines.append("")

    # Agents Section
    agents = components.get('agents', [])
    lines.append(f"### Agents ({len(agents)})")
    lines.append("")
    if agents:
        lines.append("Specialized agent definitions loaded via slash commands or subagent invocation:")
        lines.append("")
        for agent in sorted(agents, key=lambda x: x['name']):
            description = agent.get('description', '')
            if description:
                lines.append(f"- **{agent['name']}** - {description} (`{agent['path']}`)")
            else:
                lines.append(f"- **{agent['name']}** (`{agent['path']}`)")
        lines.append("")
    else:
        lines.append("No agents found.")
        lines.append("")

    # Skills Section
    skills = components.get('skills', [])
    lines.append(f"### Skills ({len(skills)})")
    lines.append("")
    if skills:
        lines.append("Packaged workflows installed to `~/.claude/skills/`:")
        lines.append("")
        for skill in sorted(skills, key=lambda x: x['name']):
            description = skill.get('description', '')
            if description:
                lines.append(f"- **{skill['name']}** - {description} (`{skill['path']}`)")
            else:
                lines.append(f"- **{skill['name']}** (`{skill['path']}`)")
        lines.append("")
    else:
        lines.append("No skills found.")
        lines.append("")

    # Commands Section
    commands = components.get('commands', [])
    lines.append(f"### Commands ({len(commands)})")
    lines.append("")
    if commands:
        lines.append("Slash commands that load additional context:")
        lines.append("")
        for command in sorted(commands, key=lambda x: x['name']):
            description = command.get('description', '')
            if description:
                lines.append(f"- **/{command['name']}** - {description} (`{command['path']}`)")
            else:
                lines.append(f"- **/{command['name']}** (`{command['path']}`)")
        lines.append("")
    else:
        lines.append("No commands found.")
        lines.append("")

    # Hooks Section
    hooks = components.get('hooks', [])
    lines.append(f"### Hooks ({len(hooks)})")
    lines.append("")
    if hooks:
        lines.append("Validation and enforcement hooks:")
        lines.append("")
        for hook in sorted(hooks, key=lambda x: x['name']):
            description = hook.get('description', '')
            if description:
                lines.append(f"- **{hook['name']}** - {description} (`{hook['path']}`)")
            else:
                lines.append(f"- **{hook['name']}** (`{hook['path']}`)")
        lines.append("")
    else:
        lines.append("No hooks found.")
        lines.append("")

    # Core Section
    core = components.get('core', {})
    if core:
        lines.append("### Core Instructions")
        lines.append("")
        lines.append(f"- **File**: `{core.get('file', 'N/A')}`")
        references = core.get('references', [])
        if references:
            lines.append(f"- **References**: {len(references)} chunks")
            for ref in references:
                lines.append(f"  - `{ref}`")
        lines.append("")

    return '\n'.join(lines)


def update_readme_with_tree(readme_path: Path, tree_content: str) -> None:
    """Update README.md file with new instruction tree content between markers.

    Args:
        readme_path: Path to README.md file to update
        tree_content: New content to insert between markers

    The function looks for marker comments:
        <!-- INSTRUCTION_TREE_START -->
        <!-- INSTRUCTION_TREE_END -->

    And replaces everything between them with tree_content.
    Content before and after markers is preserved.
    """
    # Read current README content
    current_content = readme_path.read_text()

    # Define markers
    start_marker = "<!-- INSTRUCTION_TREE_START -->"
    end_marker = "<!-- INSTRUCTION_TREE_END -->"

    # Find marker positions
    start_idx = current_content.find(start_marker)
    end_idx = current_content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError(
            f"README.md missing markers. Expected {start_marker} and {end_marker}"
        )

    if start_idx >= end_idx:
        raise ValueError("Start marker must come before end marker")

    # Build new content
    # Keep everything before start marker
    before_markers = current_content[:start_idx + len(start_marker)]

    # Add newline, tree content, newline
    new_middle = f"\n{tree_content}\n"

    # Keep everything from end marker onward
    after_markers = current_content[end_idx:]

    # Combine parts
    new_content = before_markers + new_middle + after_markers

    # Write updated content
    readme_path.write_text(new_content)


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
    print(f"Scanning repository: {repo_root}")
    components = scan_repository(repo_root)

    # Print summary
    print(f"Found {len(components['agents'])} agents")
    print(f"Found {len(components['skills'])} skills")
    print(f"Found {len(components['commands'])} commands")
    print(f"Found {len(components['hooks'])} hooks")
    print(f"Found core with {len(components['core'].get('references', []))} references")

    # Generate markdown tree
    print(f"\nGenerating instruction tree markdown...")
    tree_content = generate_markdown_tree(components, repo_root)

    # Update README
    readme_path = repo_root / args.output
    print(f"Updating {readme_path}...")
    update_readme_with_tree(readme_path, tree_content)

    print(f"\n✓ Successfully updated {args.output}")


if __name__ == '__main__':
    main()
