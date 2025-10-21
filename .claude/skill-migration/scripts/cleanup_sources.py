#!/usr/bin/env python3
"""
Cleanup Sources - Assists with removing migrated content from source files

This script helps maintain DRY by:
- Identifying sections in source files that match skill content
- Generating Edit tool commands to remove content
- Suggesting replacement text (skill references)
- Creating backups before modification

Usage:
    cleanup_sources.py --skill <skill-path> --sources <file1> [file2 ...]

Examples:
    cleanup_sources.py --skill .claude/git-commit --sources agents/REVIEW.md
    cleanup_sources.py --skill .claude/test-workflow --sources agents/TEST-CLEANER.md agents/SUPERVISOR.md
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
from difflib import SequenceMatcher


class SourceCleaner:
    """Handles cleanup of migrated content from source files."""

    def __init__(self, skill_path: str):
        self.skill_path = Path(skill_path)
        self.skill_name = self.skill_path.name

        # Load skill content
        skill_md = self.skill_path / 'SKILL.md'
        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        self.skill_content = skill_md.read_text()

    def find_matching_sections(self, source_file: str, similarity_threshold: float = 0.6) -> List[Dict]:
        """
        Find sections in source file that match skill content.

        Returns list of matches with line numbers and similarity scores.
        """
        source_path = Path(source_file)
        if not source_path.exists():
            print(f"Warning: Source file not found: {source_file}")
            return []

        source_content = source_path.read_text()
        source_lines = source_content.split('\n')

        # Extract sections from source
        sections = self._extract_sections(source_content)

        # Find matches
        matches = []
        for section in sections:
            similarity = self._calculate_similarity(section['content'], self.skill_content)
            if similarity >= similarity_threshold:
                matches.append({
                    'file': source_file,
                    'header': section['header'],
                    'start_line': section['start_line'],
                    'end_line': section['end_line'],
                    'similarity': similarity,
                    'content': section['content']
                })

        return matches

    def _extract_sections(self, content: str) -> List[Dict]:
        """
        Extract sections from markdown content.
        """
        lines = content.split('\n')
        sections = []
        current_section = None
        current_level = 0

        for i, line in enumerate(lines, 1):
            # Check for header
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    current_section['end_line'] = i - 1
                    sections.append(current_section)

                # Start new section
                level = len(line) - len(line.lstrip('#'))
                current_level = level
                current_section = {
                    'header': line.strip('# ').strip(),
                    'level': level,
                    'start_line': i,
                    'content': ''
                }
            elif current_section:
                # Add to current section
                current_section['content'] += line + '\n'

        # Don't forget last section
        if current_section:
            current_section['end_line'] = len(lines)
            sections.append(current_section)

        return sections

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text blocks.
        """
        # Use sequence matcher for basic similarity
        matcher = SequenceMatcher(None, text1.lower(), text2.lower())
        return matcher.ratio()

    def suggest_replacement(self, source_file: str, match: Dict) -> str:
        """
        Suggest replacement text for a matched section.
        """
        # Create a reference to the skill
        replacement = f"## {match['header']}\n\n"
        replacement += f"Use the `{self.skill_name}` skill for this workflow.\n"

        return replacement

    def create_backup(self, source_file: str) -> str:
        """
        Create backup of source file before modification.
        """
        source_path = Path(source_file)
        backup_path = source_path.with_suffix(source_path.suffix + '.backup')

        # Copy to backup
        backup_path.write_text(source_path.read_text())
        return str(backup_path)

    def generate_cleanup_report(self, sources: List[str]) -> Dict:
        """
        Generate report of what content should be removed from sources.
        """
        report = {
            'skill': self.skill_name,
            'sources_analyzed': len(sources),
            'matches_found': [],
            'recommendations': []
        }

        for source in sources:
            matches = self.find_matching_sections(source)
            if matches:
                report['matches_found'].extend(matches)

                for match in matches:
                    report['recommendations'].append({
                        'file': source,
                        'action': 'remove_and_replace',
                        'section': match['header'],
                        'lines': f"{match['start_line']}-{match['end_line']}",
                        'similarity': f"{match['similarity']:.0%}",
                        'replacement': self.suggest_replacement(source, match)
                    })

        return report


def print_report(report: Dict):
    """
    Print cleanup report in human-readable format.
    """
    print(f"\n{'='*70}")
    print(f"Cleanup Report for '{report['skill']}' skill")
    print(f"{'='*70}\n")

    print(f"Sources analyzed: {report['sources_analyzed']}")
    print(f"Matching sections found: {len(report['matches_found'])}\n")

    if not report['recommendations']:
        print("✅ No matching content found in source files.")
        print("   Sources are already clean or skill content is entirely new.\n")
        return

    print("Recommendations:\n")

    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec['file']}")
        print(f"   Section: {rec['section']} (lines {rec['lines']})")
        print(f"   Similarity: {rec['similarity']}")
        print(f"   Action: {rec['action']}")
        print(f"   Suggested replacement:")
        print(f"   {'-'*60}")
        for line in rec['replacement'].split('\n'):
            print(f"   {line}")
        print(f"   {'-'*60}\n")

    print("\nNext Steps:")
    print("1. Review each recommendation above")
    print("2. For each section to remove:")
    print("   - Create backup: cp <file> <file>.backup")
    print("   - Use Edit tool to remove old content")
    print("   - Use Edit tool to add skill reference")
    print("3. Verify no duplication remains:")
    print(f"   - Grep for key phrases from skill in source files")
    print(f"   - Ensure skill is authoritative source\n")


def main():
    if len(sys.argv) < 5 or sys.argv[1] != '--skill' or sys.argv[3] != '--sources':
        print("Usage: cleanup_sources.py --skill <skill-path> --sources <file1> [file2 ...]")
        print("\nExamples:")
        print("  cleanup_sources.py --skill .claude/git-commit --sources agents/REVIEW.md")
        print("  cleanup_sources.py --skill .claude/test-workflow --sources agents/TEST-CLEANER.md agents/SUPERVISOR.md")
        sys.exit(1)

    skill_path = sys.argv[2]
    sources = sys.argv[4:]

    # Validate skill path
    if not Path(skill_path).exists():
        print(f"Error: Skill path not found: {skill_path}", file=sys.stderr)
        sys.exit(1)

    # Initialize cleaner
    print(f"Analyzing skill: {skill_path}")
    print(f"Checking {len(sources)} source file(s)...\n")

    cleaner = SourceCleaner(skill_path)

    # Generate report
    report = cleaner.generate_cleanup_report(sources)

    # Print report
    print_report(report)

    # Optionally create backups
    if report['recommendations']:
        print("\n⚠️  Manual Review Required")
        print("This tool provides recommendations but does not automatically modify files.")
        print("Review the suggestions above and use Edit tool to make changes.\n")


if __name__ == "__main__":
    main()
