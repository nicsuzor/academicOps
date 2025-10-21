#!/usr/bin/env python3
"""
Scan Repository - Orchestrates full repository scan for workflow candidates

This script:
- Finds all agent and documentation files
- Runs extract_workflow.py on each file
- Aggregates results into single dataset
- Outputs consolidated JSON

Usage:
    scan_repository.py [--output <json-file>] [--repo-path <path>]

Examples:
    scan_repository.py --output scan_results.json
    scan_repository.py --repo-path /path/to/repo --output results.json
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any


def find_files(repo_path: Path) -> Dict[str, List[str]]:
    """
    Find all files that might contain workflow content.
    """
    files = {
        'agents': [],
        'documentation': [],
        'commands': [],
        'deprecated': []
    }

    # Find agent files
    for pattern in ['agents/*.md', '.claude/agents.backup/*.md']:
        for file in repo_path.glob(pattern):
            if '.backup' in str(file):
                files['deprecated'].append(str(file.relative_to(repo_path)))
            else:
                files['agents'].append(str(file.relative_to(repo_path)))

    # Find documentation files
    for pattern in ['docs/**/*.md', 'docs/_UNUSED/**/*.md']:
        for file in repo_path.glob(pattern):
            if '_UNUSED' in str(file):
                files['deprecated'].append(str(file.relative_to(repo_path)))
            else:
                files['documentation'].append(str(file.relative_to(repo_path)))

    # Find command files
    for file in repo_path.glob('.claude/commands/*.md'):
        files['commands'].append(str(file.relative_to(repo_path)))

    return files


def extract_workflow_from_file(file_path: str, repo_path: Path) -> Dict[str, Any]:
    """
    Run extract_workflow.py on a single file and return results.
    """
    full_path = repo_path / file_path

    # Call extract_workflow.py script
    script_path = repo_path / '.claude/skill-migration/scripts/extract_workflow.py'

    if not script_path.exists():
        print(f"Warning: extract_workflow.py not found at {script_path}")
        return None

    try:
        result = subprocess.run(
            ['python3', str(script_path), str(full_path)],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            # Parse JSON from output
            # Script outputs JSON followed by summary, so extract JSON part
            output_lines = result.stdout.split('\n')
            json_started = False
            json_lines = []

            for line in output_lines:
                if line.strip().startswith('{'):
                    json_started = True
                if json_started:
                    json_lines.append(line)
                    if line.strip() == '}':
                        break

            if json_lines:
                return json.loads('\n'.join(json_lines))

        print(f"Warning: Failed to extract from {file_path}: {result.stderr}")
        return None

    except Exception as e:
        print(f"Warning: Error processing {file_path}: {e}")
        return None


def scan_repository(repo_path: Path) -> Dict[str, Any]:
    """
    Scan entire repository and aggregate workflow extraction results.
    """
    print(f"Scanning repository: {repo_path}")

    # Find all files
    files = find_files(repo_path)

    total_files = sum(len(files[cat]) for cat in files)
    print(f"\nFound {total_files} files to analyze:")
    for category, file_list in files.items():
        if file_list:
            print(f"  {category}: {len(file_list)} files")

    # Extract workflows from each file
    print("\nExtracting workflows...")
    results = {
        'repository': str(repo_path),
        'files_analyzed': [],
        'candidates': [],
        'stats': {
            'total_files': total_files,
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_workflow_sections': 0,
            'total_numbered_lists': 0,
            'total_code_examples': 0
        }
    }

    for category, file_list in files.items():
        for file_path in file_list:
            print(f"  Processing {file_path}...")

            extraction = extract_workflow_from_file(file_path, repo_path)

            if extraction:
                results['files_analyzed'].append({
                    'path': file_path,
                    'category': category,
                    'extraction': extraction
                })

                # Add as candidate if has workflow content
                if (extraction.get('stats', {}).get('workflow_sections_found', 0) > 0 or
                    extraction.get('stats', {}).get('numbered_lists_found', 0) > 0):

                    results['candidates'].append({
                        'file': file_path,
                        'category': category,
                        'suggested_name': extraction.get('suggested_skill_name', 'unknown'),
                        'confidence': extraction.get('confidence_score', 0),
                        'workflow_sections': extraction.get('workflow_sections', []),
                        'numbered_lists': extraction.get('numbered_lists', []),
                        'code_examples': extraction.get('code_examples', [])
                    })

                # Update stats
                stats = extraction.get('stats', {})
                results['stats']['successful_extractions'] += 1
                results['stats']['total_workflow_sections'] += stats.get('workflow_sections_found', 0)
                results['stats']['total_numbered_lists'] += stats.get('numbered_lists_found', 0)
                results['stats']['total_code_examples'] += stats.get('code_examples_found', 0)
            else:
                results['stats']['failed_extractions'] += 1

    print(f"\nScan complete!")
    print(f"  Successful: {results['stats']['successful_extractions']}")
    print(f"  Failed: {results['stats']['failed_extractions']}")
    print(f"  Candidates found: {len(results['candidates'])}")

    return results


def main():
    # Parse arguments
    output_file = 'scan_results.json'
    repo_path = Path.cwd()

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--repo-path' and i + 1 < len(sys.argv):
            repo_path = Path(sys.argv[i + 1])
            i += 2
        else:
            print(f"Usage: scan_repository.py [--output <json-file>] [--repo-path <path>]")
            print("\nExamples:")
            print("  scan_repository.py --output scan_results.json")
            print("  scan_repository.py --repo-path /path/to/repo --output results.json")
            sys.exit(1)

    # Validate repo path
    if not repo_path.exists():
        print(f"Error: Repository path not found: {repo_path}")
        sys.exit(1)

    # Run scan
    results = scan_repository(repo_path)

    # Write output
    Path(output_file).write_text(json.dumps(results, indent=2))
    print(f"\nResults written to: {output_file}")


if __name__ == "__main__":
    main()
