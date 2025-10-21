#!/usr/bin/env python3
"""
Generalize Content - Transforms repository-specific content into generalized patterns

This script helps make extracted workflows portable by:
- Replacing hardcoded paths with relative patterns
- Identifying project-specific file references
- Suggesting environment variable replacements
- Flagging content that needs manual review

Usage:
    generalize_content.py --input <json-file> --output <md-file>

Examples:
    generalize_content.py --input extracted.json --output generalized.md
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


class ContentGeneralizer:
    """Handles generalization of repository-specific content."""

    def __init__(self):
        # Patterns that indicate repository-specific content
        self.repo_patterns = [
            (r'/home/[^/]+/[^\s]+', 'Absolute home path'),
            (r'bot/docs/_CHUNKS/', 'Hardcoded bot path'),
            (r'projects/[^/]+/', 'Hardcoded project path'),
            (r'\${OUTER}', 'Parent repo reference'),
            (r'\.claude/[^/]+', 'Claude config path'),
        ]

        # Common path replacements
        self.path_replacements = {
            r'/home/[^/]+/src/[^/]+': 'PROJECT_ROOT',
            r'bot/docs/_CHUNKS/': 'validation rules directory',
            r'projects/([^/]+)/': r'project \1 directory',
        }

    def find_repo_specific_content(self, text: str) -> List[Dict[str, any]]:
        """
        Find repository-specific content that needs generalization.
        """
        findings = []
        for pattern, description in self.repo_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    'type': 'path',
                    'description': description,
                    'match': match.group(0),
                    'start': match.start(),
                    'end': match.end(),
                    'needs_generalization': True
                })
        return findings

    def generalize_paths(self, text: str) -> Tuple[str, List[str]]:
        """
        Replace hardcoded paths with generalized patterns.

        Returns: (generalized_text, list_of_changes)
        """
        changes = []
        result = text

        for pattern, replacement in self.path_replacements.items():
            matches = list(re.finditer(pattern, result))
            if matches:
                result = re.sub(pattern, replacement, result)
                changes.append(f"Replaced '{pattern}' with '{replacement}' ({len(matches)} occurrences)")

        return result, changes

    def suggest_env_vars(self, text: str) -> List[Dict[str, str]]:
        """
        Suggest environment variables for hardcoded values.
        """
        suggestions = []

        # Look for absolute paths
        abs_paths = re.findall(r'/[a-zA-Z0-9_/.-]+', text)
        for path in abs_paths:
            if len(path) > 10:  # Only suggest for substantial paths
                var_name = path.strip('/').replace('/', '_').replace('-', '_').upper()
                suggestions.append({
                    'original': path,
                    'env_var': var_name,
                    'description': f'Environment variable for {path}'
                })

        return suggestions

    def flag_manual_review(self, text: str) -> List[Dict[str, str]]:
        """
        Flag content that likely needs manual review for generalization.
        """
        flags = []

        # Look for specific file names
        specific_files = re.findall(r'`([a-zA-Z0-9_.-]+\.(md|py|yaml|json|toml))`', text)
        for file_match in specific_files:
            filename = file_match[0]
            flags.append({
                'type': 'specific_file',
                'content': filename,
                'suggestion': f'Consider if "{filename}" should be a pattern or example, not requirement'
            })

        # Look for "must" or "required" statements about specific files
        must_statements = re.findall(r'(must|required|always).*?([a-zA-Z0-9_.-]+\.(md|py|yaml))', text, re.IGNORECASE)
        for statement in must_statements:
            flags.append({
                'type': 'requirement',
                'content': ' '.join(statement),
                'suggestion': 'Requirement may be too specific - consider making it a pattern'
            })

        return flags


def generalize_json_extract(input_file: str, output_file: str):
    """
    Process extracted workflow JSON and create generalized markdown.
    """
    # Load input
    data = json.loads(Path(input_file).read_text())

    generalizer = ContentGeneralizer()

    # Start building output
    output = f"# Generalized Workflow from {data['source_file']}\n\n"
    output += f"**Suggested Skill Name**: {data.get('suggested_skill_name', 'unknown')}\n\n"
    output += f"**Confidence Score**: {data.get('confidence_score', 0)}/100\n\n"

    all_changes = []
    all_suggestions = []
    all_flags = []

    # Process workflow sections
    if data.get('workflow_sections'):
        output += "## Workflow Sections\n\n"
        for section in data['workflow_sections']:
            output += f"### {section['header']} (line {section['start_line']})\n\n"

            # Generalize content
            content = section['content']
            generalized, changes = generalizer.generalize_paths(content)
            all_changes.extend(changes)

            # Find repo-specific content
            findings = generalizer.find_repo_specific_content(content)
            if findings:
                output += "_⚠️ Repository-specific content detected - review needed_\n\n"
                all_flags.extend(findings)

            output += generalized + "\n\n"

    # Process numbered lists
    if data.get('numbered_lists'):
        output += "## Procedural Workflows (Numbered Lists)\n\n"
        for lst in data['numbered_lists']:
            output += f"### {lst['context']} (line {lst['start_line']})\n\n"
            for item in lst['items']:
                generalized_item, changes = generalizer.generalize_paths(item)
                all_changes.extend(changes)
                output += generalized_item + "\n"
            output += "\n"

    # Process code examples
    if data.get('code_examples'):
        output += "## Code Examples\n\n"
        for example in data['code_examples']:
            output += f"### {example['context']} (line {example['start_line']})\n\n"
            output += f"```{example['language']}\n"

            # Check for hardcoded content in code
            code = example['code']
            findings = generalizer.find_repo_specific_content(code)
            if findings:
                output += "# ⚠️ Note: This code contains repository-specific paths\n"
                all_flags.extend(findings)

            output += code
            output += "```\n\n"

    # Add generalization report
    output += "---\n\n## Generalization Report\n\n"

    if all_changes:
        output += "### Changes Made\n\n"
        for change in all_changes:
            output += f"- {change}\n"
        output += "\n"

    # Add environment variable suggestions
    content_sample = json.dumps(data)[:5000]  # Sample for analysis
    env_suggestions = generalizer.suggest_env_vars(content_sample)
    if env_suggestions:
        output += "### Environment Variable Suggestions\n\n"
        for suggestion in env_suggestions[:5]:  # Limit to top 5
            output += f"- `{suggestion['env_var']}` for `{suggestion['original']}`\n"
        output += "\n"

    # Add manual review flags
    if all_flags:
        output += "### Manual Review Needed\n\n"
        for flag in all_flags[:10]:  # Limit output
            output += f"- **{flag.get('type', 'unknown')}**: {flag.get('description', flag.get('content', ''))}\n"
            if 'suggestion' in flag:
                output += f"  - {flag['suggestion']}\n"
        output += "\n"

    # Write output
    Path(output_file).write_text(output)
    print(f"✅ Generalized content written to {output_file}")

    # Print summary
    print(f"\nGeneralization Summary:")
    print(f"  - {len(all_changes)} automated replacements")
    print(f"  - {len(env_suggestions)} environment variable suggestions")
    print(f"  - {len(all_flags)} items flagged for manual review")

    if all_flags:
        print(f"\n⚠️  Manual review recommended - {len(all_flags)} repository-specific items detected")
    else:
        print(f"\n✅ Content appears generic - ready for skill creation")


def main():
    if len(sys.argv) < 5 or sys.argv[1] != '--input' or sys.argv[3] != '--output':
        print("Usage: generalize_content.py --input <json-file> --output <md-file>")
        print("\nExamples:")
        print("  generalize_content.py --input extracted.json --output generalized.md")
        sys.exit(1)

    input_file = sys.argv[2]
    output_file = sys.argv[4]

    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Generalizing content from {input_file}...")
    generalize_json_extract(input_file, output_file)


if __name__ == "__main__":
    main()
