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


def _scan_all_instruction_files(repo_root: Path) -> list[str]:
    """Scan repository for ALL instruction markdown files.

    Args:
        repo_root: Path to repository root directory

    Returns:
        List of instruction file paths relative to repo_root
        Includes files from: core/*.md, chunks/*.md, docs/_CHUNKS/*.md
    """
    instruction_files = []

    # Scan core/*.md
    core_dir = repo_root / 'core'
    if core_dir.exists():
        for md_file in core_dir.glob('*.md'):
            instruction_files.append(str(md_file.relative_to(repo_root)))

    # Scan chunks/*.md
    chunks_dir = repo_root / 'chunks'
    if chunks_dir.exists():
        for md_file in chunks_dir.glob('*.md'):
            instruction_files.append(str(md_file.relative_to(repo_root)))

    # Scan docs/_CHUNKS/*.md
    docs_chunks_dir = repo_root / 'docs' / '_CHUNKS'
    if docs_chunks_dir.exists():
        for md_file in docs_chunks_dir.glob('*.md'):
            instruction_files.append(str(md_file.relative_to(repo_root)))

    return instruction_files


def scan_repository(repo_root: Path) -> dict[str, Any]:
    """Scan repository and discover all instruction components.

    Args:
        repo_root: Path to repository root directory

    Returns:
        Dictionary with keys: 'agents', 'skills', 'commands', 'hooks', 'core', 'all_instruction_files'
        Each containing list of discovered components with metadata
    """
    components = {
        'agents': [],
        'skills': [],
        'commands': [],
        'hooks': [],
        'core': {},
        'all_instruction_files': []
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

            # Parse load_instructions.py calls from command content
            content = command_file.read_text()
            dependencies = _parse_load_instructions_calls(content)

            components['commands'].append({
                'name': command_file.stem,
                'file': command_file.name,
                'path': str(command_file.relative_to(repo_root)),
                'description': frontmatter.get('description', ''),
                'dependencies': dependencies
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

    # Scan all instruction files
    components['all_instruction_files'] = _scan_all_instruction_files(repo_root)

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


def _parse_load_instructions_calls(content: str) -> list[str]:
    """Parse load_instructions.py calls from command markdown content.

    Args:
        content: Command markdown file content

    Returns:
        List of instruction filenames (e.g., ['DEVELOPMENT.md', 'TESTING.md'])
    """
    # Match: uv run python ... load_instructions.py FILENAME.md
    # Pattern handles various path formats: ${ACADEMICOPS}/hooks/, $ACADEMICOPS/hooks/, etc.
    load_pattern = r'load_instructions\.py\s+([A-Z_/-]+\.md)'
    matches = re.findall(load_pattern, content)
    return matches


def _build_reverse_index(components: dict[str, Any]) -> dict[str, list[str]]:
    """Build reverse index mapping instruction files to components that use them.

    Args:
        components: Dictionary from scan_repository() with component data

    Returns:
        Dictionary mapping instruction file paths to list of component names
        Example: {'docs/_CHUNKS/MATPLOTLIB.md': ['analyst skill'], ...}
    """
    reverse_index = {}

    # Process skills
    for skill in components.get('skills', []):
        skill_name = f"{skill['name']} skill"
        for dep in skill.get('dependencies', []):
            if dep not in reverse_index:
                reverse_index[dep] = []
            reverse_index[dep].append(skill_name)

    # Process commands
    for command in components.get('commands', []):
        command_name = f"/{command['name']} command"
        for dep in command.get('dependencies', []):
            if dep not in reverse_index:
                reverse_index[dep] = []
            reverse_index[dep].append(command_name)

    return reverse_index


def _truncate_description(description: str, max_words: int = 10) -> str:
    """Truncate description to first clause or max_words.

    Args:
        description: Full description text
        max_words: Maximum number of words to keep (default: 10)

    Returns:
        Truncated description suitable for compact format
    """
    if not description:
        return ''

    # Split on common clause boundaries: period, comma, colon, semicolon, dash, parenthesis
    clause_separators = ['. ', ', ', ': ', '; ', ' - ', ' (', '—']

    # Find first clause boundary
    first_clause = description
    for sep in clause_separators:
        if sep in description:
            parts = description.split(sep, 1)
            if len(parts[0].split()) > 3:  # Only use if clause is meaningful (>3 words)
                first_clause = parts[0]
                break

    # Truncate to max_words if still too long
    words = first_clause.split()
    if len(words) > max_words:
        first_clause = ' '.join(words[:max_words])

    return first_clause.strip()


def generate_markdown_tree(components: dict[str, Any], repo_root: Path, compact: bool = False) -> str:
    """Generate markdown documentation from scanned components.

    Args:
        components: Dictionary from scan_repository() with component data
        repo_root: Path to repository root (for context)
        compact: If True, generate ultra-compact format with truncated descriptions (default: False)

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
        if not compact:
            lines.append("Specialized agent definitions loaded via slash commands or subagent invocation:")
            lines.append("")
        for agent in sorted(agents, key=lambda x: x['name']):
            description = agent.get('description', '')
            if description:
                if compact:
                    truncated_desc = _truncate_description(description)
                    lines.append(f"- {agent['name']} - {truncated_desc}")
                else:
                    lines.append(f"- **{agent['name']}** - {description} (`{agent['path']}`)")
            else:
                if compact:
                    lines.append(f"- {agent['name']}")
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
        if not compact:
            lines.append("Packaged workflows installed to `~/.claude/skills/`:")
            lines.append("")
        for skill in sorted(skills, key=lambda x: x['name']):
            description = skill.get('description', '')
            dependencies = skill.get('dependencies', [])

            if compact:
                # Compact format: inline dependencies
                truncated_desc = _truncate_description(description) if description else ''
                dep_info = ''
                if dependencies:
                    dep_basenames = [Path(d).stem for d in dependencies]  # Remove .md extension
                    dep_info = f" [{', '.join(dep_basenames)}]"

                if truncated_desc:
                    lines.append(f"- {skill['name']} - {truncated_desc}{dep_info}")
                else:
                    lines.append(f"- {skill['name']}{dep_info}")
            else:
                if description:
                    lines.append(f"- **{skill['name']}** - {description} (`{skill['path']}`)")
                else:
                    lines.append(f"- **{skill['name']}** (`{skill['path']}`)")

                # Show dependencies if present
                if dependencies:
                    dep_names = [Path(d).name for d in dependencies]
                    lines.append(f"  - Dependencies: {', '.join(dep_names)}")

        lines.append("")
    else:
        lines.append("No skills found.")
        lines.append("")

    # Commands Section
    commands = components.get('commands', [])
    lines.append(f"### Commands ({len(commands)})")
    lines.append("")
    if commands:
        if not compact:
            lines.append("Slash commands that load additional context:")
            lines.append("")
        for command in sorted(commands, key=lambda x: x['name']):
            description = command.get('description', '')
            dependencies = command.get('dependencies', [])

            if compact:
                truncated_desc = _truncate_description(description) if description else ''
                if truncated_desc:
                    lines.append(f"- /{command['name']} - {truncated_desc}")
                else:
                    lines.append(f"- /{command['name']}")
            else:
                if description:
                    lines.append(f"- **/{command['name']}** - {description} (`{command['path']}`)")
                else:
                    lines.append(f"- **/{command['name']}** (`{command['path']}`)")

                # Show dependencies (load_instructions.py calls) if present
                if dependencies:
                    lines.append(f"  - Loads: {', '.join(dependencies)} (3-tier: framework → personal → project)")

        lines.append("")
    else:
        lines.append("No commands found.")
        lines.append("")

    # Hooks Section
    hooks = components.get('hooks', [])
    lines.append(f"### Hooks ({len(hooks)})")
    lines.append("")
    if hooks:
        if not compact:
            lines.append("Validation and enforcement hooks:")
            lines.append("")
        for hook in sorted(hooks, key=lambda x: x['name']):
            description = hook.get('description', '')
            if compact:
                truncated_desc = _truncate_description(description) if description else ''
                if truncated_desc:
                    lines.append(f"- {hook['name']} - {truncated_desc}")
                else:
                    lines.append(f"- {hook['name']}")
            else:
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
    if core and not compact:
        lines.append("### Core Instructions")
        lines.append("")
        lines.append(f"- **File**: `{core.get('file', 'N/A')}`")
        references = core.get('references', [])
        if references:
            lines.append(f"- **References**: {len(references)} chunks")
            for ref in references:
                lines.append(f"  - `{ref}`")
        lines.append("")

    # Reverse Index Section - Instruction Files (not in compact mode)
    if not compact:
        reverse_index = _build_reverse_index(components)
        if reverse_index:
            lines.append("### Instruction Files")
            lines.append("")
            lines.append("Reverse index showing which components load each instruction file:")
            lines.append("")

            # Group files by directory for better organization
            by_directory = {}
            for filepath, consumers in reverse_index.items():
                directory = str(Path(filepath).parent)
                if directory not in by_directory:
                    by_directory[directory] = []
                by_directory[directory].append((Path(filepath).name, consumers))

            # Output grouped by directory
            for directory in sorted(by_directory.keys()):
                lines.append(f"**{directory}/:**")
                lines.append("")
                for filename, consumers in sorted(by_directory[directory]):
                    consumer_list = ', '.join(sorted(consumers))
                    lines.append(f"- `{filename}` - Used by: {consumer_list}")
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
