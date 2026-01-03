#!/usr/bin/env python3
"""
Audit skill suggestion compliance from session transcripts.

Parses abridged markdown transcripts to extract:
1. Skills suggested by prompt hydration (Skills matched: `X`)
2. Skills actually invoked (🔧 Skill invoked: `Y`)
3. Whether they match

Usage:
    uv run python scripts/audit_skill_compliance.py --days 7
    uv run python scripts/audit_skill_compliance.py --transcript path/to/transcript.md
"""

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class TurnAnalysis:
    """Analysis of a single conversation turn."""

    turn_number: int
    skills_suggested: list[str]
    skills_invoked: list[str]
    followed: bool  # Did agent invoke ANY of the suggested skills?
    commands_suggested: list[str]  # Commands (/) that router incorrectly suggested


# Regex patterns based on actual transcript format
# Old format: "- Skills matched: `framework`, `python-dev`"
SKILLS_MATCHED_PATTERN = re.compile(r"Skills matched:\s*(.+)")
# New format (post 2025-12-31): "**Skill(s)**: framework, python-dev"
SKILLS_NEW_PATTERN = re.compile(r"\*\*Skill\(s\)\*\*:\s*(.+)")
# Pattern: "- **🔧 Skill invoked: `learning-log`**"
SKILL_INVOKED_PATTERN = re.compile(r"🔧 Skill invoked:\s*`([^`]+)`")
# Pattern to extract skill names from backticks
SKILL_NAME_PATTERN = re.compile(r"`([^`]+)`")


def parse_transcript(path: Path) -> list[TurnAnalysis]:
    """
    Extract skill suggestion/invocation pairs from transcript.

    Returns list of TurnAnalysis for each turn that had skill suggestions.
    """
    content = path.read_text()
    lines = content.split("\n")

    turns: list[TurnAnalysis] = []
    current_turn = 0
    current_suggestions: list[str] = []
    current_commands: list[str] = []  # Track commands separately
    current_invocations: list[str] = []

    for i, line in enumerate(lines):
        # Detect turn boundaries (User or Agent turn headers)
        if re.match(r"###\s+(User|Agent)\s+\(Turn\s+\d+", line):
            # Save previous turn if it had suggestions or commands
            if current_suggestions or current_commands:
                followed = any(
                    skill in current_invocations for skill in current_suggestions
                )
                turns.append(
                    TurnAnalysis(
                        turn_number=current_turn,
                        skills_suggested=current_suggestions.copy(),
                        skills_invoked=current_invocations.copy(),
                        followed=followed,
                        commands_suggested=current_commands.copy(),
                    )
                )

            # Start new turn
            turn_match = re.search(r"Turn\s+(\d+)", line)
            current_turn = int(turn_match.group(1)) if turn_match else current_turn + 1
            current_suggestions = []
            current_commands = []
            current_invocations = []

        # Check for skill suggestions (old format with backticks)
        match = SKILLS_MATCHED_PATTERN.search(line)
        if match:
            skills_text = match.group(1)
            all_items = SKILL_NAME_PATTERN.findall(skills_text)
            # Separate commands from skills
            for item in all_items:
                if item.startswith("/"):
                    current_commands.append(item)
                else:
                    current_suggestions.append(item)

        # Check for skill suggestions (new format without backticks)
        match = SKILLS_NEW_PATTERN.search(line)
        if match:
            skills_text = match.group(1).strip()
            # New format: comma-separated, no backticks (e.g., "framework, python-dev")
            # Skip "none" or empty
            if skills_text.lower() not in ("none", "[skill names or \"none\"]", ""):
                for item in skills_text.split(","):
                    item = item.strip()
                    if item and not item.startswith("["):  # Skip template placeholders
                        if item.startswith("/"):
                            current_commands.append(item)
                        else:
                            current_suggestions.append(item)

        # Check for skill invocations
        match = SKILL_INVOKED_PATTERN.search(line)
        if match:
            current_invocations.append(match.group(1))

    # Don't forget the last turn
    if current_suggestions or current_commands:
        followed = any(skill in current_invocations for skill in current_suggestions)
        turns.append(
            TurnAnalysis(
                turn_number=current_turn,
                skills_suggested=current_suggestions.copy(),
                skills_invoked=current_invocations.copy(),
                followed=followed,
                commands_suggested=current_commands.copy(),
            )
        )

    return turns


def calculate_compliance(turns: list[TurnAnalysis]) -> dict:
    """
    Calculate compliance metrics from turn analyses.

    Returns dict with:
        - total_turns: Number of turns with suggestions
        - compliant_turns: Number of turns where suggestion was followed
        - compliance_rate: Ratio (0.0 to 1.0)
        - by_skill: Per-skill breakdown
        - command_suggestions: Count of incorrect command recommendations
    """
    # Filter to turns with actual skill suggestions (not just commands)
    skill_turns = [t for t in turns if t.skills_suggested]

    if not skill_turns:
        total = 0
        compliant = 0
    else:
        total = len(skill_turns)
        compliant = sum(1 for t in skill_turns if t.followed)

    # Per-skill breakdown
    by_skill: dict[str, dict[str, int]] = {}
    for turn in skill_turns:
        for skill in turn.skills_suggested:
            if skill not in by_skill:
                by_skill[skill] = {"total": 0, "compliant": 0}
            by_skill[skill]["total"] += 1
            if turn.followed:
                by_skill[skill]["compliant"] += 1

    # Track command suggestions (router bug)
    command_counts: dict[str, int] = {}
    for turn in turns:
        for cmd in turn.commands_suggested:
            command_counts[cmd] = command_counts.get(cmd, 0) + 1

    return {
        "total_turns": total,
        "compliant_turns": compliant,
        "compliance_rate": compliant / total if total > 0 else 0.0,
        "by_skill": by_skill,
        "command_suggestions": command_counts,
        "total_command_suggestions": sum(command_counts.values()),
    }


def find_transcripts(transcript_dir: Path, days: int) -> list[Path]:
    """Find transcripts from the last N days."""
    cutoff = datetime.now() - timedelta(days=days)
    transcripts = []

    for path in transcript_dir.glob("*-abridged.md"):
        # Parse date from filename (format: YYYYMMDD-...)
        try:
            date_str = path.name[:8]
            file_date = datetime.strptime(date_str, "%Y%m%d")
            if file_date >= cutoff:
                transcripts.append(path)
        except ValueError:
            continue

    return sorted(transcripts)


def format_report(
    results: dict,
    non_compliant_examples: list[tuple[str, TurnAnalysis]],
    period_start: datetime,
    period_end: datetime,
) -> str:
    """Format audit results as human-readable report."""
    lines = [
        f"Skill Compliance Audit ({period_start.strftime('%Y-%m-%d')} to {period_end.strftime('%Y-%m-%d')})",
        "=" * 60,
        "",
        f"Sessions analyzed: {results['sessions_analyzed']}",
        f"Turns with skill suggestions: {results['total_turns']}",
        "",
        f"Compliance Rate: {results['compliance_rate']:.0%} ({results['compliant_turns']}/{results['total_turns']})",
        "",
        "By Suggested Skill:",
    ]

    for skill, stats in sorted(results["by_skill"].items()):
        rate = stats["compliant"] / stats["total"] if stats["total"] > 0 else 0
        lines.append(f"  {skill:15} -> {rate:.0%} compliance ({stats['compliant']}/{stats['total']})")

    # Report command suggestions as router quality issue
    if results.get("command_suggestions"):
        lines.extend([
            "",
            f"Router Quality Issue: {results['total_command_suggestions']} command suggestions",
            "(Commands are user shortcuts, not agent-invocable skills)",
        ])
        for cmd, count in sorted(results["command_suggestions"].items()):
            lines.append(f"  {cmd:15} -> {count} times")

    if non_compliant_examples:
        lines.extend(["", "Non-compliant examples (first 5):"])
        for session_name, turn in non_compliant_examples[:5]:
            lines.append(f"  {session_name}: Turn {turn.turn_number}")
            lines.append(f"    Suggested: {', '.join(turn.skills_suggested)}")
            invoked = ", ".join(turn.skills_invoked) if turn.skills_invoked else "(none)"
            lines.append(f"    Invoked: {invoked}")

    return "\n".join(lines)


def audit_transcripts(transcript_dir: Path, days: int) -> dict:
    """Run audit on recent transcripts, return metrics."""
    transcripts = find_transcripts(transcript_dir, days)

    all_turns: list[TurnAnalysis] = []
    non_compliant_examples: list[tuple[str, TurnAnalysis]] = []

    for path in transcripts:
        turns = parse_transcript(path)
        all_turns.extend(turns)

        # Collect non-compliant examples
        for turn in turns:
            if not turn.followed:
                non_compliant_examples.append((path.stem, turn))

    results = calculate_compliance(all_turns)
    results["sessions_analyzed"] = len(transcripts)

    period_end = datetime.now()
    period_start = period_end - timedelta(days=days)

    report = format_report(results, non_compliant_examples, period_start, period_end)

    return {
        "results": results,
        "report": report,
        "non_compliant_examples": non_compliant_examples,
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Audit skill suggestion compliance from session transcripts."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to analyze (default: 7)",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Analyze a single transcript file",
    )
    parser.add_argument(
        "--transcript-dir",
        type=Path,
        default=Path.home() / "writing" / "data" / "sessions" / "claude",
        help="Directory containing transcripts",
    )

    args = parser.parse_args()

    if args.transcript:
        # Single transcript mode
        turns = parse_transcript(args.transcript)
        results = calculate_compliance(turns)
        print(f"Transcript: {args.transcript.name}")
        print(f"Turns with suggestions: {results['total_turns']}")
        print(f"Compliance rate: {results['compliance_rate']:.0%}")

        for turn in turns:
            status = "✓" if turn.followed else "✗"
            invoked = ", ".join(turn.skills_invoked) if turn.skills_invoked else "(none)"
            print(
                f"  Turn {turn.turn_number}: {status} "
                f"suggested={turn.skills_suggested} invoked={invoked}"
            )
    else:
        # Multi-transcript mode
        audit_result = audit_transcripts(args.transcript_dir, args.days)
        print(audit_result["report"])


if __name__ == "__main__":
    main()
