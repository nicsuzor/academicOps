#!/usr/bin/env python3
"""Extract division of labor from Claude Code session transcripts.

Parses markdown transcripts to show how work is distributed between:
- Main agent (primary Claude instance)
- Subagents (spawned via Task())
- Skills (invoked via Skill())
- Commands (invoked via /command)
- Hooks (framework automation)

Usage:
    python extract_labor.py <transcript.md> [--summary] [--output FILE]

Output:
    JSON with work units and delegation statistics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# =============================================================================
# Parsing Patterns (verified against real transcripts)
# =============================================================================

# Turn boundaries
USER_TURN = re.compile(r"^## User \(Turn (\d+)")
AGENT_TURN = re.compile(r"^## Agent \(Turn (\d+)\)")

# Agent spawning (captures type, model, background flag)
TASK_SPAWN = re.compile(
    r"Task\(subagent_type=\"([^\"]+)\".*?model=\"([^\"]+)\".*?(run_in_background=True)?"
)
SUBAGENT_SECTION = re.compile(r"^### Subagent: ([\w-]+) \((.+)\)")

# Skill/command invocations (multiple formats exist)
INVOCATION = re.compile(r"\*\*Invoked: /([^\s]+) \((skill|command)\)\*\*")
SKILL_INVOKE_ALT = re.compile(r"\*\*🔧 Skill invoked: `([^`]+)`\*\*")

# Hook work units
HOOK_SECTION = re.compile(r"^### Hook: (\w+) ([✓✗])")

# Tool calls (within any agent)
TOOL_CALL = re.compile(r"^- (\w+)\(")
TOOL_ERROR = re.compile(r"^\*\*❌ ERROR:\*\* (\w+)\(")


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class WorkUnit:
    """A discrete unit of work performed during the session."""

    agent_type: str  # "main" | "subagent" | "skill" | "command" | "hook"
    agent_name: str | None  # e.g., "custodiet", "remember", "Stop"
    model: str | None = None  # e.g., "haiku", "opus"
    description: str = ""
    tool_calls: list[str] = field(default_factory=list)
    turn: int | None = None
    run_in_background: bool = False


@dataclass
class DelegationStats:
    """Metrics for delegation patterns."""

    total_work_units: int = 0
    main_agent_units: int = 0
    subagent_units: int = 0
    skill_units: int = 0
    command_units: int = 0
    hook_units: int = 0

    # Ratios (computed)
    delegation_rate: float = 0.0  # (subagent + skill) / total
    skill_coverage: float = 0.0  # skill_units / total

    # Breakdowns
    subagent_types: dict[str, int] = field(default_factory=dict)
    skills_used: list[str] = field(default_factory=list)
    commands_used: list[str] = field(default_factory=list)

    # Async tracking
    background_tasks: int = 0


@dataclass
class LaborAnalysis:
    """Complete division of labor analysis for a session."""

    session_id: str
    date: str
    project: str
    total_turns: int

    work_units: list[WorkUnit] = field(default_factory=list)
    stats: DelegationStats = field(default_factory=DelegationStats)

    # Tool calls by agent type
    tool_calls_by_agent: dict[str, int] = field(default_factory=dict)


# =============================================================================
# Extraction Logic
# =============================================================================


def extract_metadata_from_filename(filename: str) -> dict[str, str]:
    """Extract session metadata from transcript filename.

    Expected format: YYYYMMDD-{project}-{session_id}-{optional-suffix}-abridged.md
    """
    name = Path(filename).stem
    if name.endswith("-abridged"):
        name = name[:-9]
    if name.endswith("-full"):
        name = name[:-5]

    # Extract date (first 8 chars)
    date_raw = name[:8]
    date_formatted = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"

    # Extract session_id (8 hex chars)
    session_match = re.search(r"-([a-f0-9]{8})(?:-|$)", name)
    session_id = session_match.group(1) if session_match else "unknown"

    # Extract project
    project_match = re.match(r"^\d{8}-(.+?)-[a-f0-9]{8}", name)
    if project_match:
        project = project_match.group(1)
    else:
        parts = name[9:].split("-")
        project = parts[0] if parts else "unknown"

    return {
        "session_id": session_id,
        "date": date_formatted,
        "project": project,
    }


def parse_transcript(content: str) -> LaborAnalysis:
    """Parse transcript content and extract work units."""
    lines = content.split("\n")

    # Extract metadata from YAML frontmatter if present
    metadata = {"session_id": "unknown", "date": "unknown", "project": "unknown"}
    in_frontmatter = False
    for line in lines[:30]:  # Check first 30 lines for frontmatter
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            if line.startswith("session_id:"):
                full_id = line.split(":", 1)[1].strip().strip('"')
                metadata["session_id"] = full_id[:8] if len(full_id) > 8 else full_id
            elif line.startswith("date:"):
                metadata["date"] = line.split(":", 1)[1].strip()

    work_units: list[WorkUnit] = []
    current_turn = 0
    current_agent: str = "main"
    tool_calls_by_agent: dict[str, list[str]] = {"main": []}
    max_turn = 0

    for i, line in enumerate(lines):
        # Track turn boundaries
        user_match = USER_TURN.match(line)
        if user_match:
            current_turn = int(user_match.group(1))
            max_turn = max(max_turn, current_turn)
            current_agent = "main"
            continue

        agent_match = AGENT_TURN.match(line)
        if agent_match:
            current_turn = int(agent_match.group(1))
            max_turn = max(max_turn, current_turn)
            current_agent = "main"
            continue

        # Detect subagent sections
        subagent_match = SUBAGENT_SECTION.match(line)
        if subagent_match:
            subagent_type = subagent_match.group(1)
            description = subagent_match.group(2)

            # Look back for Task() spawn to get model
            model = None
            is_background = False
            for j in range(max(0, i - 20), i):
                task_match = TASK_SPAWN.search(lines[j])
                if task_match and task_match.group(1) == subagent_type:
                    model = task_match.group(2)
                    is_background = bool(task_match.group(3))
                    break

            work_units.append(
                WorkUnit(
                    agent_type="subagent",
                    agent_name=subagent_type,
                    model=model,
                    description=description,
                    turn=current_turn,
                    run_in_background=is_background,
                )
            )

            current_agent = f"subagent:{subagent_type}"
            if current_agent not in tool_calls_by_agent:
                tool_calls_by_agent[current_agent] = []
            continue

        # Detect skill/command invocations
        invocation_match = INVOCATION.search(line)
        if invocation_match:
            name = invocation_match.group(1)
            inv_type = invocation_match.group(2)  # "skill" or "command"
            work_units.append(
                WorkUnit(
                    agent_type=inv_type,
                    agent_name=name,
                    turn=current_turn,
                )
            )
            continue

        # Detect alternate skill format
        skill_alt_match = SKILL_INVOKE_ALT.search(line)
        if skill_alt_match:
            name = skill_alt_match.group(1)
            work_units.append(
                WorkUnit(
                    agent_type="skill",
                    agent_name=name,
                    turn=current_turn,
                )
            )
            continue

        # Detect hook sections
        hook_match = HOOK_SECTION.match(line)
        if hook_match:
            hook_name = hook_match.group(1)
            work_units.append(
                WorkUnit(
                    agent_type="hook",
                    agent_name=hook_name,
                    turn=current_turn,
                )
            )
            continue

        # Track tool calls
        tool_match = TOOL_CALL.match(line)
        if tool_match:
            tool_name = tool_match.group(1)
            tool_calls_by_agent.setdefault(current_agent, []).append(tool_name)

        # Track tool errors (still count as tool usage)
        error_match = TOOL_ERROR.search(line)
        if error_match:
            tool_name = error_match.group(1)
            tool_calls_by_agent.setdefault(current_agent, []).append(
                f"{tool_name}(ERROR)"
            )

    # Add main agent work unit if there were main agent tool calls
    if tool_calls_by_agent.get("main"):
        work_units.insert(
            0,
            WorkUnit(
                agent_type="main",
                agent_name=None,
                description="Main agent work",
                tool_calls=tool_calls_by_agent["main"],
            ),
        )

    # Compute statistics
    stats = compute_stats(work_units, tool_calls_by_agent)

    # Compute tool calls by agent (counts)
    tool_counts = {agent: len(calls) for agent, calls in tool_calls_by_agent.items()}

    return LaborAnalysis(
        session_id=metadata["session_id"],
        date=metadata["date"],
        project=metadata["project"],
        total_turns=max_turn,
        work_units=work_units,
        stats=stats,
        tool_calls_by_agent=tool_counts,
    )


def compute_stats(
    work_units: list[WorkUnit], tool_calls_by_agent: dict[str, list[str]]
) -> DelegationStats:
    """Compute delegation statistics from work units."""
    stats = DelegationStats()

    for unit in work_units:
        stats.total_work_units += 1

        if unit.agent_type == "main":
            stats.main_agent_units += 1
        elif unit.agent_type == "subagent":
            stats.subagent_units += 1
            if unit.agent_name:
                stats.subagent_types[unit.agent_name] = (
                    stats.subagent_types.get(unit.agent_name, 0) + 1
                )
            if unit.run_in_background:
                stats.background_tasks += 1
        elif unit.agent_type == "skill":
            stats.skill_units += 1
            if unit.agent_name and unit.agent_name not in stats.skills_used:
                stats.skills_used.append(unit.agent_name)
        elif unit.agent_type == "command":
            stats.command_units += 1
            if unit.agent_name and unit.agent_name not in stats.commands_used:
                stats.commands_used.append(unit.agent_name)
        elif unit.agent_type == "hook":
            stats.hook_units += 1

    # Compute ratios
    if stats.total_work_units > 0:
        delegated = stats.subagent_units + stats.skill_units
        stats.delegation_rate = round(delegated / stats.total_work_units, 3)
        stats.skill_coverage = round(stats.skill_units / stats.total_work_units, 3)

    return stats


# =============================================================================
# Output Formatting
# =============================================================================


def format_summary(analysis: LaborAnalysis) -> str:
    """Format analysis as human-readable summary."""
    lines = [
        f"# Labor Division Analysis: {analysis.session_id}",
        f"Date: {analysis.date} | Project: {analysis.project} | Turns: {analysis.total_turns}",
        "",
        "## Work Distribution",
        f"- Main agent: {analysis.stats.main_agent_units} units",
        f"- Subagents: {analysis.stats.subagent_units} units",
        f"- Skills: {analysis.stats.skill_units} units",
        f"- Commands: {analysis.stats.command_units} units",
        f"- Hooks: {analysis.stats.hook_units} units",
        "",
        "## Delegation Metrics",
        f"- Delegation rate: {analysis.stats.delegation_rate:.1%}",
        f"- Skill coverage: {analysis.stats.skill_coverage:.1%}",
        f"- Background tasks: {analysis.stats.background_tasks}",
        "",
    ]

    if analysis.stats.subagent_types:
        lines.append("## Subagent Types")
        for name, count in sorted(analysis.stats.subagent_types.items()):
            lines.append(f"- {name}: {count}")
        lines.append("")

    if analysis.stats.skills_used:
        lines.append(f"## Skills Used: {', '.join(analysis.stats.skills_used)}")
        lines.append("")

    if analysis.stats.commands_used:
        lines.append(f"## Commands Used: {', '.join(analysis.stats.commands_used)}")
        lines.append("")

    if analysis.tool_calls_by_agent:
        lines.append("## Tool Calls by Agent")
        for agent, count in sorted(
            analysis.tool_calls_by_agent.items(), key=lambda x: -x[1]
        ):
            lines.append(f"- {agent}: {count} calls")

    return "\n".join(lines)


def to_json(analysis: LaborAnalysis) -> dict:
    """Convert analysis to JSON-serializable dict."""
    result = {
        "session_id": analysis.session_id,
        "date": analysis.date,
        "project": analysis.project,
        "total_turns": analysis.total_turns,
        "work_units": [asdict(u) for u in analysis.work_units],
        "stats": asdict(analysis.stats),
        "tool_calls_by_agent": analysis.tool_calls_by_agent,
    }
    return result


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract division of labor from Claude Code session transcripts"
    )
    parser.add_argument("transcript", help="Path to transcript markdown file")
    parser.add_argument(
        "--summary", action="store_true", help="Output human-readable summary"
    )
    parser.add_argument("--output", "-o", help="Write JSON output to file")
    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    if not transcript_path.exists():
        print(f"ERROR: Transcript not found: {transcript_path}", file=sys.stderr)
        return 1

    content = transcript_path.read_text()

    # Update metadata from filename if not in frontmatter
    analysis = parse_transcript(content)
    file_metadata = extract_metadata_from_filename(transcript_path.name)
    if analysis.session_id == "unknown":
        analysis.session_id = file_metadata["session_id"]
    if analysis.date == "unknown":
        analysis.date = file_metadata["date"]
    if analysis.project == "unknown":
        analysis.project = file_metadata["project"]

    if args.summary:
        print(format_summary(analysis))
    elif args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(to_json(analysis), indent=2))
        print(f"Wrote: {output_path}")
    else:
        print(json.dumps(to_json(analysis), indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
