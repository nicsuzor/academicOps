#!/usr/bin/env python3
"""
Score Candidates - Score workflow candidates by migration priority

Scoring criteria (0-100 points):
- Duplication Score (0-40): More files = higher score
- Workflow Complexity (0-30): More steps = higher score
- Portability Value (0-20): Universal workflows score higher
- Code Content (0-10): Has reusable code/templates

Usage:
    score_candidates.py --input <scan-results.json> --duplicates <duplicates.json> --output <scored.json>
"""

import sys
import json
from pathlib import Path
from typing import Dict, List


def score_duplication(candidate: Dict, dup_report: Dict) -> int:
    """Score based on how many files contain this workflow (0-40 points)."""
    file = candidate['file']

    # Find duplication groups containing this file
    max_files = 1
    for group in dup_report.get('groups', []):
        if file in group['files']:
            max_files = max(max_files, group['file_count'])

    if max_files >= 3:
        return 40
    elif max_files == 2:
        return 20
    else:
        return 0


def score_complexity(candidate: Dict) -> int:
    """Score based on workflow complexity (0-30 points)."""
    workflow_count = len(candidate.get('workflow_sections', []))
    list_count = len(candidate.get('numbered_lists', []))

    # Count total steps in numbered lists
    total_steps = sum(len(lst.get('items', [])) for lst in candidate.get('numbered_lists', []))

    if total_steps >= 10 or workflow_count >= 3:
        return 30  # Complex
    elif total_steps >= 4 or workflow_count >= 1:
        return 20  # Medium
    else:
        return 10  # Simple


def score_portability(candidate: Dict) -> int:
    """Score based on portability value (0-20 points)."""
    # Heuristic: check for repo-specific paths in content
    content = ""
    for section in candidate.get('workflow_sections', []):
        content += section.get('content', '')

    repo_indicators = ['bot/', '${OUTER}', '/home/', 'project/', '.claude/']
    repo_count = sum(1 for indicator in repo_indicators if indicator in content)

    if repo_count == 0:
        return 20  # Universal
    elif repo_count <= 2:
        return 10  # Somewhat portable
    else:
        return 5   # Repository-specific


def score_code_content(candidate: Dict) -> int:
    """Score based on code/template content (0-10 points)."""
    code_examples = len(candidate.get('code_examples', []))

    if code_examples >= 3:
        return 10
    elif code_examples >= 1:
        return 5
    else:
        return 0


def assign_priority(score: int) -> str:
    """Assign priority level based on total score."""
    if score >= 80:
        return "Critical"
    elif score >= 60:
        return "High"
    elif score >= 40:
        return "Medium"
    else:
        return "Low"


def score_candidates(scan_results: Dict, dup_report: Dict) -> List[Dict]:
    """Score all candidates and return sorted list."""
    scored = []

    for candidate in scan_results.get('candidates', []):
        scores = {
            'duplication': score_duplication(candidate, dup_report),
            'complexity': score_complexity(candidate),
            'portability': score_portability(candidate),
            'code_content': score_code_content(candidate)
        }

        total_score = sum(scores.values())
        priority = assign_priority(total_score)

        scored.append({
            'file': candidate['file'],
            'suggested_name': candidate['suggested_name'],
            'category': candidate['category'],
            'total_score': total_score,
            'priority': priority,
            'scores': scores,
            'details': {
                'workflow_sections': len(candidate.get('workflow_sections', [])),
                'numbered_lists': len(candidate.get('numbered_lists', [])),
                'code_examples': len(candidate.get('code_examples', []))
            }
        })

    # Sort by total score (descending)
    scored.sort(key=lambda x: x['total_score'], reverse=True)

    return scored


def main():
    if len(sys.argv) < 7:
        print("Usage: score_candidates.py --input <scan-results.json> --duplicates <duplicates.json> --output <scored.json>")
        sys.exit(1)

    input_file = sys.argv[2]
    dup_file = sys.argv[4]
    output_file = sys.argv[6]

    # Load input files
    scan_results = json.loads(Path(input_file).read_text())
    dup_report = json.loads(Path(dup_file).read_text())

    print(f"Scoring {len(scan_results.get('candidates', []))} candidates...")

    # Score candidates
    scored = score_candidates(scan_results, dup_report)

    # Build output
    output = {
        'repository': scan_results.get('repository', 'unknown'),
        'total_candidates': len(scored),
        'priority_counts': {
            'Critical': sum(1 for c in scored if c['priority'] == 'Critical'),
            'High': sum(1 for c in scored if c['priority'] == 'High'),
            'Medium': sum(1 for c in scored if c['priority'] == 'Medium'),
            'Low': sum(1 for c in scored if c['priority'] == 'Low')
        },
        'candidates': scored
    }

    # Write output
    Path(output_file).write_text(json.dumps(output, indent=2))

    print(f"\nScored candidates written to: {output_file}")
    print(f"\nPriority breakdown:")
    for priority, count in output['priority_counts'].items():
        print(f"  {priority}: {count}")


if __name__ == "__main__":
    main()
