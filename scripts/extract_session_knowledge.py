#!/usr/bin/env python3
"""
DEPRECATED: This script calls the Anthropic API directly, violating framework principles.

Use these alternatives instead:
- /transcript - Generate readable transcript from session JSONL
- /log - Extract learning patterns via Claude Code (learning-log skill)
- /bmem - Capture session info to knowledge base

The framework principle (AXIOMS.md #22, hooks/CLAUDE.md) states that all LLM work
should be orchestrated by Claude Code, not via direct API calls from scripts.

This script is preserved for reference but should not be used.

---

Original docstring:

Session Knowledge Extraction Script (DEPRECATED)

Analyzes session logs using an LLM to extract valuable knowledge:
- Decisions made during development
- Lessons learned
- Patterns and workflows discovered
- Solutions to problems
- Important insights

Stores extracted knowledge in categorized markdown files with full provenance.
"""

import argparse
import datetime
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from lib.paths import get_data_root

try:
    from anthropic import Anthropic
except ImportError:
    print("ERROR: anthropic package not installed", file=sys.stderr)
    print("Run: uv add anthropic", file=sys.stderr)
    sys.exit(1)


# LLM Configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
TEMPERATURE = 0.3

# Extraction prompt
EXTRACTION_PROMPT = """You are analyzing a Claude Code session to extract valuable knowledge for a personal knowledge base.

The user is a law professor with ADHD who works on multiple projects. He needs to:
- Capture important decisions and learnings without friction
- Build searchable knowledge across sessions
- Not lose track of insights

Session Summary:
{summary}

Transcript Details:
{transcript_summary}

Extract ONLY significant knowledge that should be preserved long-term. Ignore routine activities.

For each piece of knowledge, determine:
1. Category: Must be one of: decisions, lessons, patterns, solutions, insights, documentation_needs
2. Title: Concise (5-10 words)
3. Description: Clear explanation (2-4 sentences)
4. Tags: Relevant keywords (3-5 tags)
5. Importance: high (critical insight), medium (useful), or low (nice to know)
6. Context: Brief context from session (1 sentence)

Return as JSON array. If no significant knowledge found, return empty array.

Example response:
[
  {
    "category": "decisions",
    "title": "Use JSONL for session logs",
    "description": "Decided to use JSONL format for session logs because it's appendable, line-based for easy streaming, and each entry is self-contained. This enables atomic writes without file locking complexity.",
    "tags": ["logging", "file-format", "jsonl", "architecture"],
    "importance": "medium",
    "context": "While implementing session logging hook for Claude Code."
  }
]

Return ONLY the JSON array, no additional text.
"""


def get_api_key() -> str:
    """Get Anthropic API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        msg = (
            "ANTHROPIC_API_KEY environment variable not set. "
            "Get your API key from https://console.anthropic.com/"
        )
        raise ValueError(msg)
    return api_key


def read_session_log(log_path: Path) -> dict[str, Any]:
    """
    Read and parse a session log file.

    Args:
        log_path: Path to session JSONL file

    Returns:
        Dict with session data (uses last/latest entry if multiple)
    """
    if not log_path.exists():
        msg = f"Session log not found: {log_path}"
        raise FileNotFoundError(msg)

    session_data = None
    with log_path.open() as f:
        for line in f:
            try:
                session_data = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

    if not session_data:
        msg = f"No valid JSON entries in {log_path}"
        raise ValueError(msg)

    return session_data


def extract_knowledge_with_llm(
    client: Anthropic,
    session_data: dict[str, Any],
    model: str = DEFAULT_MODEL,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """
    Use LLM to extract knowledge from session data.

    Args:
        client: Anthropic client
        session_data: Session log data
        model: Model to use
        dry_run: If True, return mock data without API call

    Returns:
        List of extracted knowledge items
    """
    if dry_run:
        print("DRY RUN: Skipping actual API call", file=sys.stderr)
        return [
            {
                "category": "lessons",
                "title": "Test extraction (dry run)",
                "description": "This is a mock extraction for testing.",
                "tags": ["test", "mock"],
                "importance": "low",
                "context": "Dry run mode enabled.",
            }
        ]

    # Prepare prompt
    summary = session_data.get("summary", "No summary available")
    transcript_summary = json.dumps(
        session_data.get("transcript_summary", {}), indent=2
    )

    prompt = EXTRACTION_PROMPT.format(
        summary=summary, transcript_summary=transcript_summary
    )

    # Call LLM with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            response_text = response.content[0].text

            # Parse JSON
            try:
                knowledge_items = json.loads(response_text)
                if not isinstance(knowledge_items, list):
                    msg = "Expected JSON array"
                    raise ValueError(msg)
                return knowledge_items
            except json.JSONDecodeError as e:
                print(
                    f"Warning: Failed to parse LLM response as JSON: {e}",
                    file=sys.stderr,
                )
                print(f"Response: {response_text[:200]}...", file=sys.stderr)
                return []

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2**attempt  # Exponential backoff
                print(
                    f"API call failed (attempt {attempt + 1}/{max_retries}): {e}",
                    file=sys.stderr,
                )
                print(f"Retrying in {wait_time}s...", file=sys.stderr)
                time.sleep(wait_time)
            else:
                print(
                    f"ERROR: API call failed after {max_retries} attempts: {e}",
                    file=sys.stderr,
                )
                raise
    return None


def write_knowledge_item(
    item: dict[str, Any],
    session_data: dict[str, Any],
    session_log_path: Path,
    output_dir: Path,
) -> Path:
    """
    Write a knowledge item to a markdown file.

    Args:
        item: Knowledge item dict
        session_data: Session log data
        session_log_path: Path to original session log
        output_dir: Output directory for knowledge files

    Returns:
        Path to created file
    """
    category = item["category"]
    title = item["title"]
    description = item["description"]
    tags = item.get("tags", [])
    importance = item.get("importance", "medium")
    context = item.get("context", "")

    # Create category directory
    category_dir = output_dir / category
    category_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename from date and title
    date = session_data.get("timestamp", "")[:10]  # YYYY-MM-DD
    if not date:
        date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    # Sanitize title for filename
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in title.lower())
    safe_title = safe_title.replace(" ", "-")[:50]

    filename = f"{date}-{safe_title}.md"
    file_path = category_dir / filename

    # Handle duplicate filenames
    counter = 1
    while file_path.exists():
        filename = f"{date}-{safe_title}-{counter}.md"
        file_path = category_dir / filename
        counter += 1

    # Create markdown content
    content = f"""# {title}

**Date**: {date}
**Session**: {session_data.get("session_id", "unknown")}
**Tags**: {", ".join(tags)}
**Importance**: {importance}

## Context

{context}

## Details

{description}

## Provenance

- Session Log: `{session_log_path.relative_to(output_dir.parent.parent)}`
- Session ID: `{session_data.get("session_id", "unknown")}`
- Extracted: {datetime.datetime.now(datetime.UTC).isoformat()}
"""

    # Write file
    with file_path.open("w") as f:
        f.write(content)

    return file_path


def update_index(
    item: dict[str, Any],
    session_data: dict[str, Any],
    file_path: Path,
    index_path: Path,
) -> None:
    """
    Update the knowledge base index with a new item.

    Args:
        item: Knowledge item dict
        session_data: Session log data
        file_path: Path to markdown file
        index_path: Path to index.jsonl
    """
    date = session_data.get("timestamp", "")[:10]
    if not date:
        date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")

    index_entry = {
        "id": str(uuid.uuid4()),
        "date": date,
        "session_id": session_data.get("session_id", "unknown"),
        "category": item["category"],
        "title": item["title"],
        "tags": item.get("tags", []),
        "importance": item.get("importance", "medium"),
        "file_path": str(file_path),
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Append to index
    with index_path.open("a") as f:
        json.dump(index_entry, f, separators=(",", ":"))
        f.write("\n")


def process_session_log(
    session_log_path: Path,
    output_dir: Path,
    client: Anthropic,
    model: str = DEFAULT_MODEL,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """
    Process a single session log and extract knowledge.

    Args:
        session_log_path: Path to session log file
        output_dir: Output directory for knowledge files
        client: Anthropic client
        model: Model to use
        dry_run: If True, don't make real API calls
        verbose: Print detailed progress

    Returns:
        Number of knowledge items extracted
    """
    if verbose:
        print(f"Processing: {session_log_path}", file=sys.stderr)

    # Read session log
    try:
        session_data = read_session_log(session_log_path)
    except Exception as e:
        print(f"Error reading {session_log_path}: {e}", file=sys.stderr)
        return 0

    # Extract knowledge with LLM
    try:
        knowledge_items = extract_knowledge_with_llm(
            client, session_data, model, dry_run
        )
    except Exception as e:
        print(f"Error extracting knowledge: {e}", file=sys.stderr)
        return 0

    if not knowledge_items:
        if verbose:
            print("  No significant knowledge extracted", file=sys.stderr)
        return 0

    if verbose:
        print(f"  Extracted {len(knowledge_items)} knowledge item(s)", file=sys.stderr)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write each knowledge item
    index_path = output_dir / "index.jsonl"
    for item in knowledge_items:
        try:
            file_path = write_knowledge_item(
                item, session_data, session_log_path, output_dir
            )
            update_index(item, session_data, file_path, index_path)

            if verbose:
                print(
                    f"    [{item['category']}] {item['title']} -> {file_path.name}",
                    file=sys.stderr,
                )
        except Exception as e:
            print(f"Error writing knowledge item: {e}", file=sys.stderr)
            continue

    return len(knowledge_items)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract knowledge from Claude Code session logs using LLM analysis"
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--session-log", type=Path, help="Path to single session log file"
    )
    input_group.add_argument(
        "--sessions-dir", type=Path, help="Directory containing session logs"
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=get_data_root() / "knowledge",
        help="Output directory for knowledge files (default: $ACA_DATA/knowledge)",
    )

    # LLM options
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model to use (default: {DEFAULT_MODEL})",
    )

    # Mode options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making API calls (for testing)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed progress"
    )

    args = parser.parse_args()

    # Get API key (skip in dry-run mode)
    if not args.dry_run:
        try:
            api_key = get_api_key()
            client = Anthropic(api_key=api_key)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
    else:
        client = None  # Not used in dry-run

    # Process session log(s)
    total_items = 0

    if args.session_log:
        # Single file
        total_items = process_session_log(
            args.session_log,
            args.output_dir,
            client,
            args.model,
            args.dry_run,
            args.verbose,
        )
    else:
        # Batch process directory
        if not args.sessions_dir.exists():
            print(f"ERROR: Directory not found: {args.sessions_dir}", file=sys.stderr)
            return 1

        session_files = sorted(args.sessions_dir.glob("*.jsonl"))
        if not session_files:
            print(f"No session logs found in {args.sessions_dir}", file=sys.stderr)
            return 0

        for session_file in session_files:
            items = process_session_log(
                session_file,
                args.output_dir,
                client,
                args.model,
                args.dry_run,
                args.verbose,
            )
            total_items += items

    if args.verbose or total_items > 0:
        print(
            f"\nExtracted {total_items} total knowledge item(s) to {args.output_dir}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
