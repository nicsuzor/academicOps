#!/usr/bin/env python3
"""
Extract Workflow - Analyzes source files to identify extractable workflow sections

This script scans agent definitions and documentation to find:
- Numbered lists (step-by-step procedures)
- Sections with workflow-related headers
- Repeated patterns across multiple files
- Code examples and templates

Usage:
    extract_workflow.py <source-file> [--output <json-file>]

Examples:
    extract_workflow.py agents/REVIEW.md
    extract_workflow.py docs/git-workflow.md --output extracted.json
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any


def extract_numbered_lists(content: str) -> List[Dict[str, Any]]:
    """
    Extract numbered lists from markdown content.

    Returns list of dicts with:
    - start_line: Line number where list starts
    - items: List of items in the numbered list
    - context: Surrounding header/text for context
    """
    lines = content.split('\n')
    numbered_lists = []
    current_list = None
    current_header = ""

    for i, line in enumerate(lines, 1):
        # Track current header context
        if line.startswith('#'):
            current_header = line.strip('# ').strip()
            continue

        # Check for numbered list item
        if re.match(r'^\s*\d+\.\s+', line):
            if current_list is None:
                current_list = {
                    'start_line': i,
                    'context': current_header,
                    'items': []
                }
            current_list['items'].append(line.strip())
        elif current_list is not None:
            # End of numbered list
            if len(current_list['items']) >= 3:  # Only save lists with 3+ items
                numbered_lists.append(current_list)
            current_list = None

    # Don't forget last list
    if current_list and len(current_list['items']) >= 3:
        numbered_lists.append(current_list)

    return numbered_lists


def extract_workflow_sections(content: str) -> List[Dict[str, Any]]:
    """
    Extract sections with workflow-related headers.

    Looks for headers containing: workflow, process, procedure, steps, how to
    """
    workflow_keywords = ['workflow', 'process', 'procedure', 'steps', 'how to', 'guide']

    lines = content.split('\n')
    sections = []
    current_section = None

    for i, line in enumerate(lines, 1):
        # Check for header with workflow keyword
        if line.startswith('#'):
            header_text = line.strip('# ').strip().lower()
            if any(keyword in header_text for keyword in workflow_keywords):
                # Save previous section if exists
                if current_section and len(current_section['content']) > 50:
                    sections.append(current_section)

                # Start new section
                current_section = {
                    'start_line': i,
                    'header': line.strip('# ').strip(),
                    'content': ''
                }
            elif current_section:
                # End current section when we hit next header
                if len(current_section['content']) > 50:
                    sections.append(current_section)
                current_section = None
        elif current_section:
            current_section['content'] += line + '\n'

    # Don't forget last section
    if current_section and len(current_section['content']) > 50:
        sections.append(current_section)

    return sections


def extract_code_examples(content: str) -> List[Dict[str, Any]]:
    """
    Extract code blocks and command examples.
    """
    lines = content.split('\n')
    examples = []
    in_code_block = False
    current_example = None
    current_header = ""

    for i, line in enumerate(lines, 1):
        if line.startswith('#'):
            current_header = line.strip('# ').strip()
            continue

        if line.strip().startswith('```'):
            if not in_code_block:
                # Start of code block
                in_code_block = True
                language = line.strip('`').strip() or 'text'
                current_example = {
                    'start_line': i,
                    'context': current_header,
                    'language': language,
                    'code': ''
                }
            else:
                # End of code block
                in_code_block = False
                if current_example:
                    examples.append(current_example)
                    current_example = None
        elif in_code_block and current_example:
            current_example['code'] += line + '\n'

    return examples


def suggest_skill_name(file_path: str, extracted_data: Dict[str, Any]) -> str:
    """
    Suggest a skill name based on file path and extracted content.
    """
    # Get base name from file
    base_name = Path(file_path).stem.lower()

    # Check for common patterns in headers
    headers = set()
    for section in extracted_data.get('workflow_sections', []):
        # Extract key words from headers
        header = section['header'].lower()
        for word in ['commit', 'test', 'review', 'git', 'workflow', 'validation']:
            if word in header:
                headers.add(word)

    # Combine insights
    if headers:
        return '-'.join(sorted(headers))
    else:
        return base_name.replace('_', '-')


def analyze_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a source file and extract workflow information.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    content = path.read_text()

    # Extract different types of content
    numbered_lists = extract_numbered_lists(content)
    workflow_sections = extract_workflow_sections(content)
    code_examples = extract_code_examples(content)

    # Build result
    result = {
        'source_file': str(path),
        'numbered_lists': numbered_lists,
        'workflow_sections': workflow_sections,
        'code_examples': code_examples,
        'stats': {
            'numbered_lists_found': len(numbered_lists),
            'workflow_sections_found': len(workflow_sections),
            'code_examples_found': len(code_examples)
        }
    }

    # Add suggested skill name
    result['suggested_skill_name'] = suggest_skill_name(file_path, result)

    # Add confidence score
    confidence = 0
    if numbered_lists:
        confidence += min(len(numbered_lists) * 20, 40)
    if workflow_sections:
        confidence += min(len(workflow_sections) * 20, 40)
    if code_examples:
        confidence += min(len(code_examples) * 5, 20)

    result['confidence_score'] = min(confidence, 100)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_workflow.py <source-file> [--output <json-file>]")
        print("\nExamples:")
        print("  extract_workflow.py agents/REVIEW.md")
        print("  extract_workflow.py docs/git-workflow.md --output extracted.json")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None

    # Check for output file parameter
    if len(sys.argv) >= 4 and sys.argv[2] == '--output':
        output_file = sys.argv[3]

    print(f"Analyzing {source_file}...")
    result = analyze_file(source_file)

    # Output results
    if output_file:
        Path(output_file).write_text(json.dumps(result, indent=2))
        print(f"\nResults written to {output_file}")
    else:
        print("\n" + json.dumps(result, indent=2))

    # Print summary
    print(f"\n--- Summary ---")
    print(f"Source: {result['source_file']}")
    print(f"Suggested skill name: {result['suggested_skill_name']}")
    print(f"Confidence score: {result['confidence_score']}/100")
    print(f"\nExtracted:")
    print(f"  - {result['stats']['numbered_lists_found']} numbered lists")
    print(f"  - {result['stats']['workflow_sections_found']} workflow sections")
    print(f"  - {result['stats']['code_examples_found']} code examples")

    if result['confidence_score'] >= 70:
        print(f"\n✅ High confidence - this file contains substantial workflow content")
    elif result['confidence_score'] >= 40:
        print(f"\n⚠️  Medium confidence - file has some workflow content")
    else:
        print(f"\n❌ Low confidence - file may not have significant workflow content")


if __name__ == "__main__":
    main()
