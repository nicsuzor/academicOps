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
    # Remove dashes and check if it's hex
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
        help="Session ID (8+ hex chars) or path to session JSONL/markdown file",
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

    # Resolve session input
    session_input = args.session
    session_path: Path | None = None

    if Path(session_input).exists():
        session_path = Path(session_input).resolve()
    elif is_session_id(session_input):
        session_path = find_session_by_id(session_input)
        if not session_path:
            print(f"Error: No session found matching ID: {session_input}", file=sys.stderr)
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

        # Generate framework-focused summary
        markdown = generate_framework_summary(
            entries,
            session_summary,
            format_type=args.format,
        )

        if args.output:
            output_path = Path(args.output)
            output_path.write_text(markdown, encoding="utf-8")
            print(f"Written to: {output_path}", file=sys.stderr)
        else:
            print(markdown)

        return 0

    except Exception as e:
        print(f"Error processing session: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
