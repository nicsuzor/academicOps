#!/usr/bin/env python3
"""
Detect Duplicates - Find duplicated workflows across files

This script:
- Compares workflow content across files
- Calculates similarity scores
- Groups duplicate workflows
- Outputs duplication report

Usage:
    detect_duplicates.py --input <scan-results.json> --output <duplicates.json>

Examples:
    detect_duplicates.py --input scan_results.json --output duplicates.json
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from difflib import SequenceMatcher


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text blocks (0.0 to 1.0)."""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def extract_content_blocks(candidate: Dict) -> List[Dict]:
    """Extract all content blocks from a candidate for comparison."""
    blocks = []

    # Extract workflow sections
    for section in candidate.get('workflow_sections', []):
        blocks.append({
            'type': 'workflow_section',
            'header': section.get('header', ''),
            'content': section.get('content', ''),
            'start_line': section.get('start_line', 0)
        })

    # Extract numbered lists
    for lst in candidate.get('numbered_lists', []):
        content = '\n'.join(lst.get('items', []))
        blocks.append({
            'type': 'numbered_list',
            'header': lst.get('context', ''),
            'content': content,
            'start_line': lst.get('start_line', 0)
        })

    return blocks


def find_duplicates(candidates: List[Dict], similarity_threshold: float = 0.6) -> List[Dict]:
    """
    Find duplicated content across candidates.

    Returns list of duplicate groups with similarity scores.
    """
    duplicates = []

    # Compare each candidate with all others
    for i, cand1 in enumerate(candidates):
        blocks1 = extract_content_blocks(cand1)

        for j, cand2 in enumerate(candidates[i + 1:], start=i + 1):
            blocks2 = extract_content_blocks(cand2)

            # Compare all blocks between these two files
            for block1 in blocks1:
                for block2 in blocks2:
                    # Only compare same type of blocks
                    if block1['type'] != block2['type']:
                        continue

                    similarity = calculate_similarity(block1['content'], block2['content'])

                    if similarity >= similarity_threshold:
                        # Found a duplicate!
                        duplicates.append({
                            'files': [cand1['file'], cand2['file']],
                            'type': block1['type'],
                            'similarity': similarity,
                            'content_preview': {
                                'file1': {
                                    'file': cand1['file'],
                                    'header': block1['header'],
                                    'line': block1['start_line'],
                                    'preview': block1['content'][:200] + '...' if len(block1['content']) > 200 else block1['content']
                                },
                                'file2': {
                                    'file': cand2['file'],
                                    'header': block2['header'],
                                    'line': block2['start_line'],
                                    'preview': block2['content'][:200] + '...' if len(block2['content']) > 200 else block2['content']
                                }
                            }
                        })

    return duplicates


def group_duplicates(duplicates: List[Dict]) -> List[Dict]:
    """
    Group duplicates by similar content to find workflows in 3+ files.
    """
    groups = []

    # Simple grouping: find files that share duplicates
    file_groups = {}

    for dup in duplicates:
        # Create a key based on content similarity
        key = f"{dup['type']}_{int(dup['similarity'] * 100)}"

        if key not in file_groups:
            file_groups[key] = {
                'type': dup['type'],
                'files': set(),
                'avg_similarity': dup['similarity'],
                'count': 0
            }

        file_groups[key]['files'].update(dup['files'])
        file_groups[key]['count'] += 1

    # Convert to list and filter for 2+ files
    for key, group in file_groups.items():
        if len(group['files']) >= 2:
            groups.append({
                'workflow_type': group['type'],
                'file_count': len(group['files']),
                'files': sorted(list(group['files'])),
                'avg_similarity': group['avg_similarity'],
                'duplication_score': len(group['files']) * group['avg_similarity'] * 10
            })

    # Sort by duplication score (descending)
    groups.sort(key=lambda x: x['duplication_score'], reverse=True)

    return groups


def detect_duplicates(scan_results: Dict) -> Dict:
    """
    Main function to detect and group duplicates from scan results.
    """
    candidates = scan_results.get('candidates', [])

    print(f"Analyzing {len(candidates)} candidates for duplicates...")

    # Find all duplicates
    duplicates = find_duplicates(candidates)

    print(f"Found {len(duplicates)} duplicate pairs")

    # Group duplicates
    groups = group_duplicates(duplicates)

    print(f"Grouped into {len(groups)} duplicate groups")

    # Build report
    report = {
        'repository': scan_results.get('repository', 'unknown'),
        'candidates_analyzed': len(candidates),
        'duplicate_pairs_found': len(duplicates),
        'duplicate_groups': len(groups),
        'groups': groups,
        'detailed_duplicates': duplicates[:50]  # Limit detailed output
    }

    return report


def main():
    if len(sys.argv) < 5 or sys.argv[1] != '--input' or sys.argv[3] != '--output':
        print("Usage: detect_duplicates.py --input <scan-results.json> --output <duplicates.json>")
        print("\nExamples:")
        print("  detect_duplicates.py --input scan_results.json --output duplicates.json")
        sys.exit(1)

    input_file = sys.argv[2]
    output_file = sys.argv[4]

    # Load scan results
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    scan_results = json.loads(Path(input_file).read_text())

    # Detect duplicates
    report = detect_duplicates(scan_results)

    # Write output
    Path(output_file).write_text(json.dumps(report, indent=2))

    print(f"\nDuplication report written to: {output_file}")

    # Print summary
    if report['duplicate_groups'] > 0:
        print(f"\nTop duplicate groups:")
        for i, group in enumerate(report['groups'][:5], 1):
            print(f"{i}. {group['workflow_type']} in {group['file_count']} files (score: {group['duplication_score']:.1f})")
    else:
        print("\n✅ No significant duplicates found")


if __name__ == "__main__":
    main()
