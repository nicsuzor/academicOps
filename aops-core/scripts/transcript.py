#!/usr/bin/env python3
"""
Session Transcript Generator for Framework Agent.

Generates markdown summaries of Claude Code sessions for framework agent analysis,
including user prompts, agent responses, tool calls, workflow transitions, and QA results.

Usage:
    uv run python aops-core/scripts/transcript.py <session_id_or_path>
    uv run python aops-core/scripts/transcript.py <session_id_or_path> --format=abridged
    uv run python aops-core/scripts/transcript.py <session_id_or_path> --output=transcript.md

Input:
    - Session ID (8+ hex chars) - finds matching session in ~/.claude/projects/
    - Path to session JSONL file
    - Path to existing transcript markdown file

Output:
    Markdown summary suitable for framework agent reflection, containing:
    - User prompts
    - Agent responses (summarized in abridged mode)
    - Tool calls and results
    - Workflow transitions
    - QA gate results
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

# Add framework roots to path for lib imports
SCRIPT_DIR = Path(__file__).parent.resolve()
AOPS_CORE_ROOT = SCRIPT_DIR.parent
FRAMEWORK_ROOT = AOPS_CORE_ROOT.parent

sys.path.insert(0, str(FRAMEWORK_ROOT))
sys.path.insert(0, str(AOPS_CORE_ROOT))

from lib.session_reader import SessionProcessor, find_sessions  # noqa: E402


def find_session_by_id(session_id: str) -> Path | None:
    """Find a session file by session ID prefix.

    Args:
        session_id: Full or partial session ID (UUID hex string)

    Returns:
        Path to session JSONL file, or None if not found
    """
    # Normalize: remove dashes and lowercase
    session_id = session_id.replace("-", "").lower()

    # Find all sessions and match by ID prefix
    sessions = find_sessions()

    for session in sessions:
        # Normalize session ID from file
        file_id = session.session_id.replace("-", "").lower()
        if file_id.startswith(session_id) or session_id.startswith(file_id[:8]):
            return session.path

    return None


def is_session_id(value: str) -> bool:
    """Check if value looks like a session ID (hex string)."""
    clean = value.replace("-", "")
    return len(clean) >= 8 and all(c in "0123456789abcdefABCDEF" for c in clean)


def extract_workflow_markers(content: str) -> list[str]:
    """Extract workflow transition markers from content.

    Looks for patterns like:
    - "Workflow: tdd"
    - "## Workflow: research"
    - Guardrail/QA gate markers
    """
    markers = []

    # Workflow pattern
    workflow_match = re.search(r"\*?\*?Workflow\*?\*?:\s*(\w+)", content, re.IGNORECASE)
    if workflow_match:
        markers.append(f"Workflow: {workflow_match.group(1)}")

    # Guardrail patterns
    guardrail_patterns = [
        r"(require_acceptance_test)",
        r"(verify_before_complete)",
        r"(qa-verifier)",
        r"CHECKPOINT",
    ]
    for pattern in guardrail_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            markers.append(pattern.strip("()"))

    return markers


def generate_framework_summary(
    entries: list,
    session_summary,
    format_type: str = "full",
) -> str:
    """Generate a framework-focused markdown summary.

    Args:
        entries: Parsed session entries
        session_summary: SessionSummary object
        format_type: "full" or "abridged"

    Returns:
        Markdown string optimized for framework agent analysis
    """

    lines = []
    lines.append(f"# Session Transcript: {session_summary.uuid[:8]}")
    lines.append("")

    # Session metadata
    if session_summary.summary and session_summary.summary != "Claude Code Session":
        lines.append(f"**Summary**: {session_summary.summary}")
    if session_summary.edited_files:
        files_str = ", ".join(f"`{f}`" for f in session_summary.edited_files[:5])
        if len(session_summary.edited_files) > 5:
            files_str += f" (+{len(session_summary.edited_files) - 5} more)"
        lines.append(f"**Files edited**: {files_str}")
    lines.append("")

    # Track workflow markers found
    workflow_markers = set()
    qa_results = []
    turn_count = 0

    for entry in entries:
        entry_type = entry.type if hasattr(entry, "type") else entry.get("type", "")

        if entry_type == "user":
            turn_count += 1
            content = ""
            if hasattr(entry, "message") and entry.message:
                content = entry.message.get("content", "")
                if isinstance(content, list):
                    # Handle tool results list
                    content = "[Tool results]"
            elif hasattr(entry, "content"):
                content = str(entry.content)

            # Skip system/hook injected content
            if content.startswith("<system") or content.startswith("<local-command"):
                continue

            # Check for workflow markers
            markers = extract_workflow_markers(content)
            workflow_markers.update(markers)

            # Truncate long content in abridged mode
            if format_type == "abridged" and len(content) > 500:
                content = content[:500] + "..."

            lines.append(f"## User (Turn {turn_count})")
            lines.append("")
            lines.append(content)
            lines.append("")

        elif entry_type == "assistant":
            content = ""
            if hasattr(entry, "message") and entry.message:
                msg = entry.message
                if "content" in msg:
                    if isinstance(msg["content"], list):
                        # Extract text blocks
                        text_parts = []
                        tool_calls = []
                        for block in msg["content"]:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block.get("type") == "tool_use":
                                    tool_calls.append(block.get("name", "unknown"))
                        content = "\n".join(text_parts)
                        if tool_calls:
                            content += f"\n\n**Tools used**: {', '.join(tool_calls)}"
                    else:
                        content = str(msg["content"])

            # Check for workflow markers
            markers = extract_workflow_markers(content)
            workflow_markers.update(markers)

            # Check for QA results
            if "qa-verifier" in content.lower() or "verification" in content.lower():
                qa_match = re.search(
                    r"(PASS|FAIL|WARNING)[:\s]+(.+?)(?:\n|$)", content, re.IGNORECASE
                )
                if qa_match:
                    qa_results.append(f"{qa_match.group(1)}: {qa_match.group(2)[:100]}")

            # Truncate in abridged mode
            if format_type == "abridged" and len(content) > 1000:
                content = content[:1000] + "..."

            lines.append(f"## Assistant (Turn {turn_count})")
            lines.append("")
            lines.append(content)
            lines.append("")

    # Add summary section at end
    lines.append("---")
    lines.append("")
    lines.append("## Session Summary")
    lines.append("")
    lines.append(f"- **Total turns**: {turn_count}")
    if workflow_markers:
        lines.append(f"- **Workflow markers**: {', '.join(sorted(workflow_markers))}")
    if qa_results:
        lines.append("- **QA Results**:")
        for result in qa_results:
            lines.append(f"  - {result}")
    if session_summary.edited_files:
        lines.append(f"- **Files modified**: {len(session_summary.edited_files)}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate session transcript for framework agent analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # By session ID (prefix match)
    uv run python aops-core/scripts/transcript.py a5234d3e

    # By file path
    uv run python aops-core/scripts/transcript.py ~/.claude/projects/foo/session.jsonl

    # Abridged format (shorter, less detail)
    uv run python aops-core/scripts/transcript.py a5234d3e --format=abridged

    # Save to file
    uv run python aops-core/scripts/transcript.py a5234d3e -o transcript.md
        """,
    )

    parser.add_argument(
        "session",
        nargs="?",
        default=None,
        help="Session ID (8+ hex chars) or path to session JSONL/markdown file (optional when --all)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all sessions found in ~/.claude/projects and write transcripts to the output directory",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["full", "abridged"],
        default="full",
        help="Output format: full (default) or abridged",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file path (prints to stdout if not specified)",
    )

    args = parser.parse_args()

    # Resolve session input / batch mode
    session_input = args.session
    session_path: Path | None = None

    # Output dir default (matches previous script location)
    default_output_dir = Path.home() / "writing" / "data" / "sessions" / "claude"
    output_dir = Path(args.output).resolve() if args.output else default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    def _project_name_from_path(p: Path) -> str:
        parts = list(p.parts)
        if "projects" in parts:
            idx = parts.index("projects")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        # fallback to parent directory name
        return p.parent.name

    def _session_id_from_path(p: Path) -> str:
        # try to reuse Session ID if available via filename
        name = p.stem
        m = re.search(r"([0-9a-f]{8,})", name, re.IGNORECASE)
        return m.group(1) if m else name

    def _output_exists(out_dir: Path, sid: str, fmt: str) -> bool:
        pattern = f"*{sid}*-{fmt}.md"
        return any(out_dir.glob(pattern))

    def _is_test_session(p: Path) -> bool:
        """Heuristically detect obvious test/demo sessions to exclude from batch runs.

        Excludes paths under /tmp and filenames or parent folders containing
        keywords like test, demo, scratch, sample, example, tmp, local, dev.
        """
        s = str(p).lower()
        name = p.name.lower()
        parts = [part.lower() for part in p.parts]

        # Exclude /tmp paths
        if s.startswith("/tmp") or "/tmp/" in s:
            return True

        keywords = (
            "test",
            "tests",
            "demo",
            "scratch",
            "sample",
            "example",
            "tmp",
            "local",
            "dev",
        )
        if any(k in name for k in keywords):
            return True
        if any(k in parts for k in keywords):
            return True

        return False

    processor = SessionProcessor()

    if args.all:
        sessions = find_sessions()
        if not sessions:
            print("No sessions found.", file=sys.stderr)
            return 0

        # Exclude obvious test/demo sessions, then process newest-first
        sessions = [
            s
            for s in sessions
            if not _is_test_session(s.path if hasattr(s, "path") else Path(str(s)))
        ]
        # Process newest sessions first (reverse chronological)
        sessions = sorted(
            sessions,
            key=lambda s: s.path.stat().st_mtime
            if hasattr(s, "path") and s.path.exists()
            else 0,
            reverse=True,
        )

        processed = 0
        skipped = 0
        errors = 0

        for s in sessions:
            try:
                session_path = s.path if hasattr(s, "path") else Path(str(s))
                sid = getattr(s, "session_id", None) or _session_id_from_path(
                    session_path
                )
                if _output_exists(output_dir, sid, args.format):
                    skipped += 1
                    continue

                print(f"Processing: {session_path}", file=sys.stderr)
                session_summary, entries, agent_entries = processor.parse_session_file(
                    str(session_path)
                )

                # project and date metadata
                project = _project_name_from_path(session_path)
                date = (
                    datetime.fromtimestamp(session_path.stat().st_mtime)
                    .date()
                    .isoformat()
                )

                output_file = (
                    output_dir / f"{date}-{project}-{sid}-session-{args.format}.md"
                )

                markdown = generate_framework_summary(
                    entries, session_summary, format_type=args.format
                )
                output_file.write_text(markdown, encoding="utf-8")
                processed += 1
                print(f"Written: {output_file}", file=sys.stderr)

            except Exception as e:
                errors += 1
                print(f"Error processing {session_path}: {e}", file=sys.stderr)

        print(f"Processed: {processed}", file=sys.stderr)
        print(f"Skipped: {skipped}", file=sys.stderr)
        print(f"Errors: {errors}", file=sys.stderr)
        return 0

    # Single session mode (existing behavior)
    if not session_input:
        print("Error: must provide a session or use --all", file=sys.stderr)
        return 1

    if Path(session_input).exists():
        session_path = Path(session_input).resolve()
    elif is_session_id(session_input):
        session_path = find_session_by_id(session_input)
        if not session_path:
            print(
                f"Error: No session found matching ID: {session_input}", file=sys.stderr
            )
            return 1
    else:
        print(f"Error: Invalid input: {session_input}", file=sys.stderr)
        print("Expected: session ID (hex) or path to session file", file=sys.stderr)
        return 1

    # Check if input is already a markdown transcript
    if session_path.suffix == ".md":
        # Just read and optionally re-save
        content = session_path.read_text(encoding="utf-8")
        if args.output:
            Path(args.output).write_text(content, encoding="utf-8")
            print(f"Copied transcript to: {args.output}", file=sys.stderr)
        else:
            print(content)
        return 0

    # Process JSONL session file
    processor = SessionProcessor()

    try:
        print(f"Processing: {session_path}", file=sys.stderr)
        session_summary, entries, agent_entries = processor.parse_session_file(
            str(session_path)
        )

        # Always generate both full and abridged transcripts for single session runs
        formats = ["full", "abridged"]

        # compute project/date/sid for filenames
        project = _project_name_from_path(session_path)
        sid = _session_id_from_path(session_path)
        date = datetime.fromtimestamp(session_path.stat().st_mtime).date().isoformat()

        if args.output:
            out = Path(args.output)
            # if user provided a file path, use as base name and create sibling files
            base = out
            if out.is_dir():
                base = out / f"{date}-{project}-{sid}-session"
            else:
                # strip extension
                base = out.with_suffix("")
            for fmt in formats:
                output_file = base.with_name(f"{base.name}-{fmt}.md")
                markdown = generate_framework_summary(
                    entries, session_summary, format_type=fmt
                )
                output_file.write_text(markdown, encoding="utf-8")
                print(f"Written to: {output_file}", file=sys.stderr)

        else:
            # no explicit output: write both to default output dir
            default_output_dir = (
                Path.home() / "writing" / "data" / "sessions" / "claude"
            )
            default_output_dir.mkdir(parents=True, exist_ok=True)
            base = default_output_dir / f"{date}-{project}-{sid}-session"
            for fmt in formats:
                output_file = (
                    default_output_dir / f"{date}-{project}-{sid}-session-{fmt}.md"
                )
                markdown = generate_framework_summary(
                    entries, session_summary, format_type=fmt
                )
                output_file.write_text(markdown, encoding="utf-8")
                print(f"Written to: {output_file}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"Error processing session: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
