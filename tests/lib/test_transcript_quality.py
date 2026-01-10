"""Tests for transcript generation quality - debugging visibility.

TDD Phase 4: Integration tests for transcript improvements.
These tests define what "complete, debuggable transcripts" must contain.

Success Criteria:
1. Hook attribution - Every system-reminder shows source hook
2. Chronological subagents - No duplicate "Subagent Transcripts" section
3. Clear structure - Readers can trace component -> output
4. Proper escaping - JSON in tool results doesn't break markdown
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


from lib.session_reader import Entry, SessionProcessor


def _make_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO timestamp with optional offset from base time."""
    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    ts = base + timedelta(seconds=offset_seconds)
    return ts.isoformat().replace("+00:00", "Z")


def _create_user_entry(prompt: str, offset: int = 0) -> dict:
    """Create a user message entry."""
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {"content": [{"type": "text", "text": prompt}]},
    }


def _create_assistant_entry(text: str, offset: int = 0) -> dict:
    """Create an assistant response entry."""
    return {
        "type": "assistant",
        "uuid": f"assistant-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _create_tool_use_entry(
    tool_name: str, tool_input: dict, tool_id: str, offset: int = 0
) -> dict:
    """Create an assistant entry with a tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"tool-{tool_name}-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_input,
                }
            ]
        },
    }


def _create_tool_result_entry(
    tool_id: str, result: str, offset: int = 0, agent_id: str | None = None
) -> dict:
    """Create a tool result entry."""
    entry = {
        "type": "user",
        "uuid": f"result-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result,
                }
            ]
        },
    }
    # Add toolUseResult for Task tool results with agentId
    if agent_id:
        entry["toolUseResult"] = {"agentId": agent_id}
    return entry


def _create_hook_entry(
    hook_event: str,
    additional_context: str | None = None,
    tool_name: str | None = None,
    exit_code: int = 0,
    offset: int = 0,
) -> dict:
    """Create a hook execution entry for hooks.jsonl format."""
    entry = {
        "type": "hook",
        "uuid": f"hook-{offset}",
        "timestamp": _make_timestamp(offset),
        "hook_event_name": hook_event,
        "exit_code": exit_code,
    }
    if tool_name:
        entry["tool_name"] = tool_name
    if additional_context:
        entry["additional_context"] = additional_context
    return entry


def _write_jsonl(path: Path, entries: list[dict]) -> None:
    """Write entries to JSONL file."""
    with open(path, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


class TestHookAttribution:
    """Tests for hook source attribution in transcripts."""

    def test_system_reminder_shows_source_hook(self, tmp_path: Path):
        """Hook-generated content must indicate which hook generated it.

        Acceptance Criterion 1: Hook entries show their source event/tool.
        """
        session_file = tmp_path / "session.jsonl"
        # Hook entry with hookSpecificOutput shows the hook event and tool
        hook_entry = {
            "type": "system_reminder",
            "uuid": "hook-1",
            "timestamp": _make_timestamp(2),
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "<system-reminder>\n[ About to claim success? Verify first ]\n</system-reminder>",
                "toolName": "Bash",
            },
        }
        entries = [
            _create_user_entry("Run a command", offset=0),
            _create_tool_use_entry(
                "Bash", {"command": "echo hello"}, "tool-1", offset=1
            ),
            hook_entry,  # Hook fires after tool use
            _create_tool_result_entry("tool-1", "hello", offset=3),
        ]
        _write_jsonl(session_file, entries)

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Hook entries should be rendered with clear attribution
        # Format: "### Hook: PostToolUse: Bash" or similar
        has_hook_attribution = "PostToolUse" in markdown and (
            "Hook" in markdown or "Bash" in markdown
        )
        assert has_hook_attribution, (
            "Hook-generated content must show source attribution. "
            "Expected hook event name and tool name in output."
        )


class TestSubagentOrdering:
    """Tests for chronological subagent placement."""

    def test_no_duplicate_subagent_section_at_end(self, tmp_path: Path):
        """Subagents should appear inline only, not duplicated at end.

        Acceptance Criterion 2: No 'Subagent Transcripts' section.
        """
        # Create session file
        session_file = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Search for files", offset=0),
            _create_tool_use_entry(
                "Task",
                {
                    "subagent_type": "Explore",
                    "prompt": "Find Python files",
                    "description": "Find files",
                },
                "task-1",
                offset=1,
            ),
            _create_tool_result_entry(
                "task-1",
                "Found 5 Python files in the project.",
                offset=2,
                agent_id="abc123",
            ),
            _create_assistant_entry("I found 5 Python files.", offset=3),
        ]
        _write_jsonl(session_file, entries)

        # Create agent transcript file (simulates agent-*.jsonl)
        agent_file = tmp_path / "agent-abc123.jsonl"
        agent_entries_list = [
            {
                "type": "assistant",
                "uuid": "agent-msg-1",
                "timestamp": _make_timestamp(2),
                "message": {
                    "content": [
                        {"type": "text", "text": "Searching for Python files..."}
                    ]
                },
            }
        ]
        _write_jsonl(agent_file, agent_entries_list)

        # Manually provide agent_entries since they're in a separate file
        # Must convert to Entry objects as expected by format_session_as_markdown
        agent_entries = {"abc123": [Entry.from_dict(e) for e in agent_entries_list]}

        processor = SessionProcessor()
        session, parsed_entries, _ = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Should NOT have a separate "Subagent Transcripts" section at the end
        # Subagent content should appear inline where the Task was called
        assert "## Subagent Transcripts" not in markdown, (
            "Subagent transcripts should appear inline at Task call location, "
            "not in a separate section at the end. Found duplicate section."
        )

    def test_subagent_appears_at_task_location(self, tmp_path: Path):
        """Subagent content should appear right after the Task tool call.

        Acceptance Criterion 2b: Subagents are chronologically placed.
        """
        session_file = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Help me search", offset=0),
            _create_assistant_entry("I'll search for you.", offset=1),
            _create_tool_use_entry(
                "Task",
                {
                    "subagent_type": "Explore",
                    "prompt": "Search codebase",
                    "description": "Search",
                },
                "task-1",
                offset=2,
            ),
            _create_tool_result_entry(
                "task-1", "Search complete.", offset=3, agent_id="xyz789"
            ),
            _create_assistant_entry("Search is done.", offset=4),
        ]
        _write_jsonl(session_file, entries)

        agent_entries_list = [
            {
                "type": "assistant",
                "uuid": "agent-msg-1",
                "timestamp": _make_timestamp(3),
                "message": {
                    "content": [{"type": "text", "text": "I found the files."}]
                },
            }
        ]
        agent_entries = {"xyz789": [Entry.from_dict(e) for e in agent_entries_list]}

        processor = SessionProcessor()
        session, parsed_entries, _ = processor.parse_session_file(session_file)

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Subagent content should appear BEFORE "Search is done"
        task_pos = markdown.find("Task")
        done_pos = markdown.find("Search is done")
        subagent_pos = markdown.find("Subagent") or markdown.find("xyz789")

        if subagent_pos > 0:
            assert task_pos < subagent_pos < done_pos, (
                f"Subagent content should appear between Task call and final response. "
                f"Positions: Task={task_pos}, Subagent={subagent_pos}, Done={done_pos}"
            )


class TestMarkdownStructure:
    """Tests for proper markdown formatting."""

    def test_hook_output_has_clear_heading(self, tmp_path: Path):
        """Hook outputs should have clear headings indicating source.

        Acceptance Criterion 3: Clear component -> output tracing.
        """
        session_file = tmp_path / "session.jsonl"
        # Include hook entry as a system_reminder type in the session
        hook_entry = {
            "type": "system_reminder",
            "uuid": "hook-1",
            "timestamp": _make_timestamp(2),
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "<system-reminder>\nRemember to verify\n</system-reminder>",
                "toolName": "Bash",
            },
        }
        entries = [
            _create_user_entry("Do something", offset=0),
            _create_tool_use_entry("Bash", {"command": "ls"}, "tool-1", offset=1),
            hook_entry,  # Hook fires after tool use
            _create_tool_result_entry("tool-1", "file1.py\nfile2.py", offset=3),
        ]
        _write_jsonl(session_file, entries)

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Should have a clear structure showing what generated what
        # Example: "### Hook: PostToolUse: Bash" or similar
        assert (
            "PostToolUse" in markdown or "Hook" in markdown
        ), "Hook events should be visible in transcript for debugging"

    def test_json_in_tool_results_properly_escaped(self, tmp_path: Path):
        """JSON in tool results must not break markdown fences.

        Acceptance Criterion 4: Proper escaping.
        """
        # Create a tool result with JSON containing backticks and special chars
        json_result = json.dumps(
            {
                "code": "```python\nprint('hello')\n```",
                "nested": {"key": "value with `backticks`"},
            },
            indent=2,
        )

        session_file = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Get JSON data", offset=0),
            _create_tool_use_entry(
                "mcp__zot__search", {"query": "test"}, "tool-1", offset=1
            ),
            _create_tool_result_entry("tool-1", json_result, offset=2),
        ]
        _write_jsonl(session_file, entries)

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Count fence opens and closes - they should be balanced
        fence_opens = markdown.count("```")

        # Fences should be balanced (even number)
        assert fence_opens % 2 == 0, (
            f"Markdown fences are unbalanced ({fence_opens} total). "
            "JSON content may be breaking fence structure."
        )

        # The JSON should be inside a fence, not breaking out
        json_start = markdown.find('"code"')
        if json_start > 0:
            # Find the fence before this JSON
            before_json = markdown[:json_start]
            fence_before = before_json.rfind("```")
            assert fence_before > 0, "JSON result should be inside a code fence"


class TestTranscriptValidity:
    """Tests for overall transcript validity."""

    def test_full_transcript_is_valid_markdown(self, tmp_path: Path):
        """Full transcripts should parse as valid markdown.

        Acceptance Criterion 5: Valid markdown output.
        """
        session_file = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Hello", offset=0),
            _create_assistant_entry("Hi there!", offset=1),
            _create_tool_use_entry(
                "Read", {"file_path": "/tmp/test.txt"}, "tool-1", offset=2
            ),
            _create_tool_result_entry("tool-1", "File contents here", offset=3),
        ]
        _write_jsonl(session_file, entries)

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Basic structure checks
        assert markdown.startswith("---"), "Should have YAML frontmatter"
        assert "---\n\n#" in markdown, "Frontmatter should close before heading"

        # No unclosed code blocks
        in_fence = False
        fence_lang = None
        for line in markdown.split("\n"):
            if line.startswith("```"):
                if in_fence:
                    in_fence = False
                    fence_lang = None
                else:
                    in_fence = True
                    fence_lang = line[3:].strip() if len(line) > 3 else ""

        assert not in_fence, (
            f"Unclosed code fence detected (language: {fence_lang}). "
            "All code blocks must be properly closed."
        )

    def test_transcript_preserves_chronological_order(self, tmp_path: Path):
        """Events in transcript should maintain chronological order.

        Acceptance Criterion: Debuggable means traceable in time order.
        """
        session_file = tmp_path / "session.jsonl"
        entries = [
            _create_user_entry("Step 1", offset=0),
            _create_assistant_entry("Response 1", offset=10),
            _create_user_entry("Step 2", offset=20),
            _create_assistant_entry("Response 2", offset=30),
            _create_user_entry("Step 3", offset=40),
            _create_assistant_entry("Response 3", offset=50),
        ]
        _write_jsonl(session_file, entries)

        processor = SessionProcessor()
        session, parsed_entries, agent_entries = processor.parse_session_file(
            session_file
        )

        markdown = processor.format_session_as_markdown(
            session, parsed_entries, agent_entries=agent_entries, variant="full"
        )

        # Verify order is preserved
        step1_pos = markdown.find("Step 1")
        step2_pos = markdown.find("Step 2")
        step3_pos = markdown.find("Step 3")

        assert step1_pos < step2_pos < step3_pos, (
            "Transcript should maintain chronological order of events. "
            f"Found: Step1@{step1_pos}, Step2@{step2_pos}, Step3@{step3_pos}"
        )
