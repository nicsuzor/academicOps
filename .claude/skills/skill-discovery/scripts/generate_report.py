#!/usr/bin/env python3
"""
Generate Report - Create human-readable discovery report

This script:
- Loads scored candidates
- Sorts by priority
- Generates detailed markdown report
- Includes migration roadmap

Usage:
    generate_report.py --input <scored-candidates.json> --output <report.md>
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def generate_report(scored_data: Dict) -> str:
    """Generate markdown report from scored candidates."""

    report = f"""# Skill Discovery Report

**Repository**: {scored_data['repository']}
**Scan Date**: {datetime.now().strftime('%Y-%m-%d')}
**Candidates Found**: {scored_data['total_candidates']}

## Summary Statistics

- Critical Priority: {scored_data['priority_counts']['Critical']} candidates
- High Priority: {scored_data['priority_counts']['High']} candidates
- Medium Priority: {scored_data['priority_counts']['Medium']} candidates
- Low Priority: {scored_data['priority_counts']['Low']} candidates

"""

    # Group by priority
    for priority in ['Critical', 'High', 'Medium', 'Low']:
        candidates = [c for c in scored_data['candidates'] if c['priority'] == priority]

        if not candidates:
            continue

        report += f"## {priority} Priority Candidates\n\n"

        for i, cand in enumerate(candidates, 1):
            report += f"### {i}. {cand['suggested_name']} (Score: {cand['total_score']}/100)\n\n"

            report += "**Why Migrate**:\n"
            report += f"- Duplication score: {cand['scores']['duplication']}/40\n"
            report += f"- Complexity score: {cand['scores']['complexity']}/30\n"
            report += f"- Portability score: {cand['scores']['portability']}/20\n"
            report += f"- Code content score: {cand['scores']['code_content']}/10\n\n"

            report += "**Content**:\n"
            report += f"- {cand['details']['workflow_sections']} workflow sections\n"
            report += f"- {cand['details']['numbered_lists']} numbered lists (procedures)\n"
            report += f"- {cand['details']['code_examples']} code examples\n\n"

            report += "**Source File**:\n"
            report += f"- `{cand['file']}` ({cand['category']})\n\n"

            report += "**Next Steps**:\n"
            report += f"1. Use skill-migration to create `{cand['suggested_name']}` skill\n"
            report += f"2. Extract workflow from `{cand['file']}`\n"
            report += f"3. Clean up source file after migration\n\n"

            report += "---\n\n"

    # Migration roadmap
    report += "## Migration Roadmap\n\n"
    report += "**Recommended Order**:\n\n"

    critical_and_high = [c for c in scored_data['candidates']
                         if c['priority'] in ['Critical', 'High']]

    for i, cand in enumerate(critical_and_high[:10], 1):  # Top 10
        report += f"{i}. `{cand['suggested_name']}` (score: {cand['total_score']}) - {cand['file']}\n"

    report += f"\n**Estimated Impact**: {len(critical_and_high)} high-value migrations\n"
    report += f"**Files to be cleaned**: {scored_data['total_candidates']} files\n\n"

    report += "## Next Steps\n\n"
    report += "Use skill-migration for each candidate, starting with Critical priority:\n\n"
    report += "```\n"

    # Provide first few commands
    for cand in scored_data['candidates'][:3]:
        report += f'# {cand["priority"]} priority:\n'
        report += f'Use skill-migration to create {cand["suggested_name"]} skill from {cand["file"]}\n\n'

    report += "```\n"

    return report


def main():
    if len(sys.argv) < 5 or sys.argv[1] != '--input' or sys.argv[3] != '--output':
        print("Usage: generate_report.py --input <scored-candidates.json> --output <report.md>")
        sys.exit(1)

    input_file = sys.argv[2]
    output_file = sys.argv[4]

    # Load scored candidates
    if not Path(input_file).exists():
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    scored_data = json.loads(Path(input_file).read_text())

    print(f"Generating report for {scored_data['total_candidates']} candidates...")

    # Generate report
    report = generate_report(scored_data)

    # Write output
    Path(output_file).write_text(report)

    print(f"\nDiscovery report written to: {output_file}")
    print(f"\nHighest priority candidate: {scored_data['candidates'][0]['suggested_name']} "
          f"(score: {scored_data['candidates'][0]['total_score']})")


if __name__ == "__main__":
    main()
