"""Transcript Error Analyzer - Extract and classify errors from session transcripts.

Identifies hydration gaps by analyzing tool errors in Claude Code session JSONL files.
Key insight: "file does not exist" errors from Read/Glob indicate the agent was
searching for information not provided by hydration context.

Error taxonomy:
- hydration_gap: Agent searching for context that should have been provided
- exploration_miss: Agent checking if something exists (benign convention checks)
- stuck_pattern: Repeated attempts at same resource
- hook_denial: Framework hook blocked the tool use
- user_rejection: User rejected the tool use
- tool_failure: Operational errors (exit codes, permissions, etc.)

Used by:
- QA verification workflows
- Session insights pipeline
- Hydration quality diagnostics
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from lib.session_paths import get_claude_project_folder

# Exploration patterns: common convention files agents probe for
_EXPLORATION_PATTERNS = {
    "README.md",
    "README",
    "readme.md",
    "setup.py",
    "setup.cfg",
    "pyproject.toml",
    "package.json",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    ".gitignore",
    "tsconfig.json",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
    "CONTRIBUTING.md",
    "LICENSE",
    "CHANGELOG.md",
}

# Patterns that indicate hook denial
_HOOK_DENIAL_RE = re.compile(r"Hook Pre\w+:\w+ denied this tool", re.IGNORECASE)

# Patterns that indicate user rejection
_USER_REJECTION_RE = re.compile(
    r"user doesn't want to proceed|tool use was rejected|Request interrupted by user",
    re.IGNORECASE,
)

# Patterns that indicate file-not-found type errors
_FILE_NOT_FOUND_RE = re.compile(
    r"File does not exist|No such file or directory|FileNotFoundError",
    re.IGNORECASE,
)


# Severity weights per category.
# Higher = more urgent to investigate.
_SEVERITY: dict[str, tuple[str, int]] = {
    "stuck_pattern": ("high", 3),
    "hydration_gap": ("high", 3),
    "tool_failure": ("medium", 2),
    "hook_denial": ("low", 1),
    "exploration_miss": ("low", 1),
    "user_rejection": ("low", 1),
}

# Stuck patterns with this many repeats or more escalate to critical.
_STUCK_CRITICAL_THRESHOLD = 3


def severity_for(category: str, repeat_count: int = 1) -> tuple[str, int]:
    """Return (severity_label, weight) for an error category.

    stuck_pattern escalates to critical when the same resource fails >= 3 times.
    """
    if category == "stuck_pattern" and repeat_count >= _STUCK_CRITICAL_THRESHOLD:
        return ("critical", 4)
    return _SEVERITY.get(category, ("medium", 2))


@dataclass
class HydrationState:
    """Context available to the agent at the time of an error."""

    active_skill: str | None = None
    recent_prompts: list[str] = field(default_factory=list)
    recent_tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TranscriptError:
    """A single error extracted from a session transcript."""

    timestamp: str | None
    tool_name: str
    tool_input: dict[str, Any]
    tool_input_summary: str
    error_content: str
    hydration_state: HydrationState
    category: str = ""  # Populated by classify_errors


@dataclass
class ErrorAnalysisReport:
    """Summary analysis of errors in a session transcript."""

    session_path: str
    total_errors: int
    errors_by_category: dict[str, int]
    hydration_gap_score: float
    severity_score: float
    errors: list[TranscriptError]

    def to_dict(self) -> dict[str, Any]:
        """Serialize report to dict for JSON output."""
        return {
            "session_path": self.session_path,
            "total_errors": self.total_errors,
            "errors_by_category": dict(self.errors_by_category),
            "hydration_gap_score": self.hydration_gap_score,
            "severity_score": self.severity_score,
            "errors": [
                {
                    "timestamp": e.timestamp,
                    "tool_name": e.tool_name,
                    "tool_input_summary": e.tool_input_summary,
                    "error_content": e.error_content[:300],
                    "category": e.category,
                    "hydration_state": {
                        "active_skill": e.hydration_state.active_skill,
                        "recent_prompts": e.hydration_state.recent_prompts,
                        "recent_tool_calls": e.hydration_state.recent_tool_calls,
                    },
                }
                for e in self.errors
            ],
        }


@dataclass
class IssuePattern:
    """A recurring issue aggregated across multiple sessions."""

    grouping_key: str  # e.g. "hydration_gap:Read:auth.py"
    category: str
    severity_label: str
    severity_weight: int
    count: int  # How many times this pattern occurred
    session_ids: list[str]  # Which sessions had this issue
    sample_error_content: str  # Representative error message
    sample_prompts: list[str]  # User prompts from one instance

    @property
    def weighted_score(self) -> float:
        """Score combining severity weight and frequency."""
        return self.severity_weight * self.count


@dataclass
class MultiSessionReport:
    """Aggregated analysis across multiple recent sessions."""

    sessions_scanned: int
    sessions_with_errors: int
    total_errors: int
    recency_window_hours: float
    investigation_queue: list[IssuePattern]  # Sorted by weighted_score desc
    session_reports: list[ErrorAnalysisReport]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON output."""
        return {
            "sessions_scanned": self.sessions_scanned,
            "sessions_with_errors": self.sessions_with_errors,
            "total_errors": self.total_errors,
            "recency_window_hours": self.recency_window_hours,
            "investigation_queue": [
                {
                    "grouping_key": p.grouping_key,
                    "category": p.category,
                    "severity": p.severity_label,
                    "weight": p.severity_weight,
                    "count": p.count,
                    "weighted_score": p.weighted_score,
                    "sessions": p.session_ids,
                    "sample_error": p.sample_error_content[:200],
                    "sample_prompts": p.sample_prompts[:2],
                }
                for p in self.investigation_queue
            ],
            "session_summaries": [
                {
                    "session": r.session_path,
                    "total_errors": r.total_errors,
                    "severity_score": r.severity_score,
                    "by_category": r.errors_by_category,
                }
                for r in self.session_reports
                if r.total_errors > 0
            ],
        }

    def format_markdown(self) -> str:
        """Format as human-readable markdown investigation report."""
        lines: list[str] = []
        lines.append("# Session Error Investigation Report")
        lines.append("")
        lines.append(
            f"Scanned **{self.sessions_scanned}** sessions "
            f"(last {self.recency_window_hours:.0f}h), "
            f"**{self.sessions_with_errors}** had errors, "
            f"**{self.total_errors}** total errors."
        )
        lines.append("")

        if not self.investigation_queue:
            lines.append("No issues found. All clean.")
            return "\n".join(lines)

        lines.append("## Investigation Queue (by severity x frequency)")
        lines.append("")
        lines.append("| # | Severity | Pattern | Count | Sessions | Score |")
        lines.append("|---|----------|---------|-------|----------|-------|")
        for i, p in enumerate(self.investigation_queue[:20], 1):
            sessions_str = ", ".join(s[:8] for s in p.session_ids[:3])
            if len(p.session_ids) > 3:
                sessions_str += f" +{len(p.session_ids) - 3}"
            lines.append(
                f"| {i} | **{p.severity_label}** | "
                f"`{p.grouping_key}` | {p.count} | "
                f"{sessions_str} | {p.weighted_score:.0f} |"
            )

        lines.append("")
        lines.append("## Top Issues Detail")
        lines.append("")
        for p in self.investigation_queue[:5]:
            lines.append(f"### `{p.grouping_key}`")
            lines.append(f"- **Category**: {p.category}")
            lines.append(f"- **Severity**: {p.severity_label} (weight {p.severity_weight})")
            lines.append(f"- **Occurrences**: {p.count} across {len(p.session_ids)} session(s)")
            lines.append(f"- **Sample error**: `{p.sample_error_content[:150]}`")
            if p.sample_prompts:
                lines.append(f'- **User was asking**: "{p.sample_prompts[0][:100]}"')
            lines.append("")

        return "\n".join(lines)


def _summarize_tool_input(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Create a brief summary of tool input for error context."""
    if tool_name in ("Read", "Write", "Edit"):
        path = tool_input.get("file_path", "")
        if path:
            return path.split("/")[-1] if "/" in path else path
    elif tool_name == "Bash":
        cmd = str(tool_input.get("command", ""))[:60]
        return cmd + "..." if len(cmd) >= 60 else cmd
    elif tool_name == "Glob":
        return tool_input.get("pattern", "")[:40]
    elif tool_name == "Grep":
        return tool_input.get("pattern", "")[:40]
    elif tool_name == "Task":
        return tool_input.get("description", "")[:40]
    elif tool_name == "Skill":
        return tool_input.get("skill", "")

    for v in tool_input.values():
        if isinstance(v, str) and v:
            return v[:40] + "..." if len(v) > 40 else v
    return ""


def _load_entries(session_path: Path) -> list[dict[str, Any]]:
    """Load raw entries from a JSONL session file."""
    entries: list[dict[str, Any]] = []
    with open(session_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def _build_tool_use_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build mapping from tool_use_id to tool info (name, input, timestamp)."""
    tool_map: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if entry.get("type") != "assistant":
            continue
        message = entry.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                tool_id = block.get("id", "")
                if tool_id:
                    tool_map[tool_id] = {
                        "name": block.get("name", "unknown"),
                        "input": block.get("input", {}),
                        "timestamp": entry.get("timestamp"),
                    }
    return tool_map


def _build_hydration_state(entries: list[dict[str, Any]], error_index: int) -> HydrationState:
    """Build the hydration state at the point of an error.

    Looks backward from error_index to find:
    - Most recent Skill invocation (active skill)
    - Recent user prompts (last 3)
    - Recent tool calls (last 5 before the error)
    """
    active_skill: str | None = None
    prompts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    for i in range(error_index - 1, -1, -1):
        entry = entries[i]
        etype = entry.get("type")

        # Collect user prompts
        if etype == "user":
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text and len(prompts) < 3:
                            prompts.append(text)

        # Find most recent Skill invocation
        if etype == "assistant" and active_skill is None:
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") == "Skill"
                    ):
                        active_skill = block.get("input", {}).get("skill")

        # Collect recent tool calls (non-error ones)
        if etype == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if (
                        isinstance(block, dict)
                        and block.get("type") == "tool_use"
                        and block.get("name") != "Skill"
                        and len(tool_calls) < 5
                    ):
                        tool_calls.append(
                            {
                                "tool_name": block.get("name", "unknown"),
                                "input_summary": _summarize_tool_input(
                                    block.get("name", ""), block.get("input", {})
                                ),
                            }
                        )

    # Reverse to get chronological order
    prompts.reverse()
    tool_calls.reverse()

    return HydrationState(
        active_skill=active_skill,
        recent_prompts=prompts,
        recent_tool_calls=tool_calls,
    )


def extract_transcript_errors(session_path: Path) -> list[TranscriptError]:
    """Extract all tool errors from a session JSONL file.

    Each error is enriched with:
    - The tool name and input that caused it
    - The hydration state at time of error (active skill, recent prompts, recent tools)

    Args:
        session_path: Path to session .jsonl file

    Returns:
        List of TranscriptError objects, in chronological order.
    """
    entries = _load_entries(session_path)
    if not entries:
        return []

    tool_map = _build_tool_use_map(entries)
    errors: list[TranscriptError] = []

    for idx, entry in enumerate(entries):
        if entry.get("type") != "user":
            continue

        message = entry.get("message", {})
        content = message.get("content", [])
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            # Check both snake_case and camelCase error flags
            if not (item.get("is_error") or item.get("isError")):
                continue

            tool_id = item.get("tool_use_id") or item.get("toolUseId") or ""
            tool_info = tool_map.get(tool_id, {})
            tool_name = tool_info.get("name", "unknown")
            tool_input = tool_info.get("input", {})
            error_content = str(item.get("content", ""))

            hydration_state = _build_hydration_state(entries, idx)

            errors.append(
                TranscriptError(
                    timestamp=tool_info.get("timestamp") or entry.get("timestamp"),
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_input_summary=_summarize_tool_input(tool_name, tool_input),
                    error_content=error_content,
                    hydration_state=hydration_state,
                )
            )

    return errors


def classify_errors(
    errors: list[TranscriptError],
    entries: list[dict[str, Any]] | None = None,
) -> list[TranscriptError]:
    """Classify errors into diagnostic categories using heuristic rules.

    Classification decision tree:
    1. Hook denial pattern → hook_denial
    2. User rejection pattern → user_rejection
    3. Repeated same-resource errors → stuck_pattern
    4. File-not-found errors:
       a. Filename is a common convention file (README, etc.) → exploration_miss
       b. Filename/path mentioned in recent user prompts → hydration_gap
       c. Default for file-not-found → hydration_gap (agent shouldn't be guessing)
    5. Everything else → tool_failure

    Args:
        errors: List of TranscriptError from extract_transcript_errors
        entries: Raw session entries (optional, used for context enrichment)

    Returns:
        Same errors list with .category populated on each error.
    """
    # Track paths seen for stuck_pattern detection
    path_counts: Counter[str] = Counter()
    path_first_seen: dict[str, int] = {}

    # First pass: count repeated paths
    for i, error in enumerate(errors):
        if error.tool_name in ("Read", "Write", "Edit", "Glob"):
            path = error.tool_input.get("file_path", "") or error.tool_input.get("pattern", "")
            if path:
                path_counts[path] += 1
                if path not in path_first_seen:
                    path_first_seen[path] = i

    # Second pass: classify each error
    for i, error in enumerate(errors):
        error.category = _classify_single_error(error, i, path_counts, path_first_seen)

    return errors


def _classify_single_error(
    error: TranscriptError,
    index: int,
    path_counts: Counter[str],
    path_first_seen: dict[str, int],
) -> str:
    """Classify a single error using the decision tree."""
    content = error.error_content

    # 1. Hook denial
    if _HOOK_DENIAL_RE.search(content):
        return "hook_denial"

    # 2. User rejection
    if _USER_REJECTION_RE.search(content):
        return "user_rejection"

    # 3. Stuck pattern: same path attempted multiple times, and this isn't the first
    if error.tool_name in ("Read", "Write", "Edit", "Glob"):
        path = error.tool_input.get("file_path", "") or error.tool_input.get("pattern", "")
        if path and path_counts.get(path, 0) >= 2 and path_first_seen.get(path) != index:
            return "stuck_pattern"

    # 4. File not found errors
    if _FILE_NOT_FOUND_RE.search(content):
        return _classify_file_not_found(error)

    # 5. Default: tool_failure
    return "tool_failure"


def _classify_file_not_found(error: TranscriptError) -> str:
    """Sub-classify file-not-found errors into exploration_miss or hydration_gap."""
    file_path = error.tool_input.get("file_path", "")
    filename = file_path.split("/")[-1] if "/" in file_path else file_path

    # Convention files that agents commonly probe for
    if filename in _EXPLORATION_PATTERNS:
        return "exploration_miss"

    # If the filename or a significant part of the path appears in recent prompts,
    # that's a strong signal the hydration should have provided it
    for prompt in error.hydration_state.recent_prompts:
        prompt_lower = prompt.lower()
        if filename and filename.lower() in prompt_lower:
            return "hydration_gap"
        # Check if path segments appear in the prompt
        if file_path:
            segments = [s for s in file_path.split("/") if s and len(s) > 3]
            for seg in segments[-3:]:  # Check last 3 meaningful segments
                if seg.lower() in prompt_lower:
                    return "hydration_gap"

    # Default for file-not-found: still a hydration gap.
    # The agent shouldn't be guessing paths if hydration worked properly.
    return "hydration_gap"


def _compute_severity_score(errors: list[TranscriptError]) -> float:
    """Compute total severity score from classified errors.

    Accounts for stuck_pattern escalation when same resource fails >= 3 times.
    """
    # Count all repeats per path (across all categories) for stuck escalation
    path_error_counts: Counter[str] = Counter()
    for e in errors:
        path = e.tool_input.get("file_path", "") or e.tool_input.get("pattern", "")
        if path:
            path_error_counts[path] += 1

    score = 0.0
    for e in errors:
        repeat = 1
        if e.category == "stuck_pattern":
            path = e.tool_input.get("file_path", "") or e.tool_input.get("pattern", "")
            if path:
                repeat = path_error_counts.get(path, 1)
        _, weight = severity_for(e.category, repeat)
        score += weight
    return score


def analyze_transcript(session_path: Path) -> ErrorAnalysisReport:
    """Full analysis pipeline: extract, classify, and summarize.

    Args:
        session_path: Path to session .jsonl file

    Returns:
        ErrorAnalysisReport with all errors classified and summary statistics.
    """
    entries = _load_entries(session_path)
    errors = extract_transcript_errors(session_path)
    classified = classify_errors(errors, entries)

    category_counts: dict[str, int] = {}
    hydration_related = 0
    for error in classified:
        category_counts[error.category] = category_counts.get(error.category, 0) + 1
        if error.category in ("hydration_gap", "stuck_pattern", "exploration_miss"):
            hydration_related += 1

    total = len(classified)
    gap_score = hydration_related / total if total > 0 else 0.0
    sev_score = _compute_severity_score(classified)

    return ErrorAnalysisReport(
        session_path=str(session_path),
        total_errors=total,
        errors_by_category=category_counts,
        hydration_gap_score=gap_score,
        severity_score=sev_score,
        errors=classified,
    )


def _grouping_key(error: TranscriptError) -> str:
    """Build a grouping key for aggregation: category:tool:basename."""
    tool = error.tool_name
    if tool in ("Read", "Write", "Edit"):
        path = error.tool_input.get("file_path", "")
        basename = path.split("/")[-1] if "/" in path else path
        return f"{error.category}:{tool}:{basename}"
    elif tool == "Bash":
        cmd = str(error.tool_input.get("command", ""))
        first_word = cmd.split()[0] if cmd.split() else "unknown"
        return f"{error.category}:{tool}:{first_word}"
    elif tool == "Glob":
        pattern = error.tool_input.get("pattern", "")[:30]
        return f"{error.category}:{tool}:{pattern}"
    else:
        return f"{error.category}:{tool}"


def _find_recent_sessions(
    sessions_dir: Path,
    hours: float = 48.0,
) -> list[Path]:
    """Find recent session JSONL files, excluding hooks and agent files."""
    cutoff = datetime.now(tz=UTC) - timedelta(hours=hours)
    sessions: list[tuple[datetime, Path]] = []

    for f in sessions_dir.glob("*.jsonl"):
        # Skip hooks and agent files
        if "-hooks" in f.name or f.name.startswith("agent-"):
            continue
        # Check modification time
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
        if mtime >= cutoff:
            sessions.append((mtime, f))

    sessions.sort(key=lambda pair: pair[0], reverse=True)
    return [f for _, f in sessions]


def scan_recent_sessions(
    sessions_dir: Path | None = None,
    hours: float = 48.0,
) -> MultiSessionReport:
    """Scan recent sessions and produce a severity-weighted investigation report.

    Args:
        sessions_dir: Directory containing session JSONL files.
            Defaults to ~/.claude/projects/-home-nic-src-academicOps/
        hours: How far back to look (default 48 hours).

    Returns:
        MultiSessionReport with investigation queue sorted by severity * frequency.
    """
    if sessions_dir is None:
        home = Path.home()
        projects_dir = home / ".claude" / "projects"
        # Derive project dir using centralized Claude Code path sanitization
        # (CLAUDE_PROJECT_DIR when set, else CWD; '/' -> '-', '.' -> '_')
        encoded_name = get_claude_project_folder()
        candidate = projects_dir / encoded_name
        if candidate.exists():
            sessions_dir = candidate
        elif projects_dir.exists():
            # Fallback: find most recently modified project dir with JSONL files
            project_dirs = sorted(
                (d for d in projects_dir.iterdir() if d.is_dir()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            sessions_dir = project_dirs[0] if project_dirs else projects_dir
        else:
            sessions_dir = projects_dir

    recent = _find_recent_sessions(sessions_dir, hours)

    reports: list[ErrorAnalysisReport] = []
    all_errors: list[tuple[str, TranscriptError]] = []  # (session_id, error)

    for session_file in recent:
        session_id = session_file.stem[:12]
        try:
            report = analyze_transcript(session_file)
            reports.append(report)
            for e in report.errors:
                all_errors.append((session_id, e))
        except (json.JSONDecodeError, OSError, KeyError, ValueError):
            continue  # Skip corrupt/unreadable/malformed files

    # Aggregate into patterns
    pattern_map: dict[str, dict[str, Any]] = {}
    for session_id, error in all_errors:
        key = _grouping_key(error)
        if key not in pattern_map:
            # Count repeats for this specific error's path
            path = error.tool_input.get("file_path", "") or error.tool_input.get("pattern", "")
            path_count = (
                sum(
                    1
                    for _, e in all_errors
                    if (e.tool_input.get("file_path", "") or e.tool_input.get("pattern", ""))
                    == path
                    and e.category == error.category
                )
                if path
                else 1
            )
            sev_label, sev_weight = severity_for(error.category, path_count)
            pattern_map[key] = {
                "category": error.category,
                "severity_label": sev_label,
                "severity_weight": sev_weight,
                "count": 0,
                "session_ids": [],
                "sample_error_content": error.error_content,
                "sample_prompts": error.hydration_state.recent_prompts[:2],
            }
        p = pattern_map[key]
        p["count"] += 1
        if session_id not in p["session_ids"]:
            p["session_ids"].append(session_id)

    # Build IssuePattern list
    patterns = [
        IssuePattern(
            grouping_key=key,
            category=data["category"],
            severity_label=data["severity_label"],
            severity_weight=data["severity_weight"],
            count=data["count"],
            session_ids=data["session_ids"],
            sample_error_content=data["sample_error_content"],
            sample_prompts=data["sample_prompts"],
        )
        for key, data in pattern_map.items()
    ]

    # Sort by weighted score descending
    patterns.sort(key=lambda p: p.weighted_score, reverse=True)

    sessions_with_errors = sum(1 for r in reports if r.total_errors > 0)
    total_errors = sum(r.total_errors for r in reports)

    return MultiSessionReport(
        sessions_scanned=len(reports),
        sessions_with_errors=sessions_with_errors,
        total_errors=total_errors,
        recency_window_hours=hours,
        investigation_queue=patterns,
        session_reports=sorted(reports, key=lambda r: r.severity_score, reverse=True),
    )
