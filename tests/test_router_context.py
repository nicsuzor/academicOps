"""Tests for extract_router_context() function.

Tests that session transcript data can be extracted and formatted for
the prompt router to make skill/workflow decisions.
"""

from __future__ import annotations

import json
import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

log = logging.getLogger(__name__)


def _make_timestamp(offset_seconds: int = 0) -> str:
    """Generate ISO timestamp with optional offset from base time."""
    from datetime import timedelta

    base = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    ts = base + timedelta(seconds=offset_seconds)
    return ts.isoformat().replace("+00:00", "Z")


def _create_user_entry(prompt: str, offset: int = 0) -> dict:
    """Create a user message entry with list content format (API format)."""
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [{"type": "text", "text": prompt}]
        },
    }


def _create_user_entry_string_format(prompt: str, offset: int = 0) -> dict:
    """Create a user message entry with string content format (command format).

    This is the format used by /commands like /do, /commit, etc.
    The content is a plain string, not a list of blocks.
    """
    return {
        "type": "user",
        "uuid": f"user-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": prompt  # String, not list!
        },
    }


def _create_assistant_entry(offset: int = 0) -> dict:
    """Create an assistant response entry."""
    return {
        "type": "assistant",
        "uuid": f"assistant-{offset}",
        "timestamp": _make_timestamp(offset + 1),
        "message": {
            "content": [{"type": "text", "text": "I'll help with that."}]
        },
    }


def _create_skill_invocation_entry(skill_name: str, offset: int = 0) -> dict:
    """Create an assistant entry with Skill tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"skill-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"tool-{offset}",
                    "name": "Skill",
                    "input": {"skill": skill_name},
                }
            ]
        },
    }


def _create_todowrite_entry(todos: list[dict], offset: int = 0) -> dict:
    """Create an assistant entry with TodoWrite tool invocation."""
    return {
        "type": "assistant",
        "uuid": f"todo-{offset}",
        "timestamp": _make_timestamp(offset),
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"todo-tool-{offset}",
                    "name": "TodoWrite",
                    "input": {"todos": todos},
                }
            ]
        },
    }


@pytest.fixture
def session_jsonl_file(tmp_path: Path) -> Path:
    """Create a temporary JSONL file with realistic session data.

    Contains:
    - 5 user prompts
    - 1 Skill("framework") invocation
    - 1 TodoWrite with mixed status items (2 completed, 1 in_progress, 1 pending)
    """
    session_file = tmp_path / "test-session.jsonl"

    entries = [
        # User prompt 1
        _create_user_entry(
            "Help me understand the project structure and identify key files",
            offset=0,
        ),
        _create_assistant_entry(offset=1),
        # User prompt 2
        _create_user_entry(
            "Now let's focus on the authentication module - review the code",
            offset=10,
        ),
        _create_assistant_entry(offset=11),
        # User prompt 3
        _create_user_entry(
            "Can you explain how the middleware chain works in this framework?",
            offset=20,
        ),
        _create_assistant_entry(offset=21),
        # Skill invocation
        _create_skill_invocation_entry("framework", offset=25),
        # User prompt 4
        _create_user_entry(
            "What are the testing patterns used here? I need to add new tests",
            offset=30,
        ),
        _create_assistant_entry(offset=31),
        # TodoWrite with mixed statuses
        _create_todowrite_entry(
            todos=[
                {"content": "Review existing tests", "status": "completed", "activeForm": "Reviewing tests"},
                {"content": "Add unit tests for auth", "status": "completed", "activeForm": "Adding tests"},
                {"content": "Write integration tests", "status": "in_progress", "activeForm": "Writing tests"},
                {"content": "Update test documentation", "status": "pending", "activeForm": "Updating docs"},
            ],
            offset=35,
        ),
        # User prompt 5
        _create_user_entry(
            "Now implement the test for the login endpoint with mocking",
            offset=40,
        ),
        _create_assistant_entry(offset=41),
    ]

    with session_file.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return session_file


class TestExtractRouterContext:
    """Tests for extract_router_context() function."""

    def test_extract_router_context_returns_formatted_markdown(
        self, session_jsonl_file: Path
    ) -> None:
        """Test that extract_router_context returns formatted markdown with expected sections.

        Expected failure: ImportError or AttributeError - function doesn't exist yet.
        """
        from lib.session_reader import extract_router_context

        result = extract_router_context(session_jsonl_file)

        # Verify result is a string (markdown)
        assert isinstance(result, str), "Result should be a markdown string"

        # Verify user prompts section exists with recent prompts
        assert "login endpoint" in result.lower(), (
            "Should contain most recent user prompt about login endpoint"
        )
        assert "testing patterns" in result.lower(), (
            "Should contain user prompt about testing patterns"
        )

        # Verify active skill is shown
        assert "framework" in result.lower(), (
            "Should show 'framework' as the active/recent skill"
        )

        # Verify TodoWrite summary shows status counts
        assert "completed" in result.lower() or "2" in result, (
            "Should show completed task count or status"
        )
        assert "in_progress" in result.lower() or "1" in result, (
            "Should show in_progress task count or status"
        )
        assert "pending" in result.lower() or "1" in result, (
            "Should show pending task count or status"
        )

    def test_extract_router_context_truncates_long_prompts(
        self, tmp_path: Path
    ) -> None:
        """Test that long user prompts are truncated to ~100 chars."""
        from lib.session_reader import extract_router_context

        # Create session with one very long prompt
        session_file = tmp_path / "long-prompt-session.jsonl"
        long_prompt = "A" * 500  # 500 character prompt

        entries = [
            _create_user_entry(long_prompt, offset=0),
            _create_assistant_entry(offset=1),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # The original 500-char prompt should be truncated
        # Check that we don't have 500 consecutive 'A's
        assert "A" * 200 not in result, (
            "Long prompts should be truncated to ~100 chars"
        )

    def test_extract_router_context_limits_to_recent_prompts(
        self, tmp_path: Path
    ) -> None:
        """Test that only last 3-5 user prompts are included."""
        from lib.session_reader import extract_router_context

        # Create session with 10 distinct user prompts
        session_file = tmp_path / "many-prompts-session.jsonl"
        entries = []

        for i in range(10):
            entries.append(
                _create_user_entry(f"User prompt number {i} with unique content", offset=i * 10)
            )
            entries.append(_create_assistant_entry(offset=i * 10 + 1))

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # Should NOT contain early prompts (0, 1, 2)
        assert "prompt number 0" not in result.lower(), (
            "Should not contain oldest prompts"
        )
        assert "prompt number 1" not in result.lower(), (
            "Should not contain oldest prompts"
        )

        # Should contain recent prompts (at least 8 or 9)
        assert "prompt number 9" in result.lower(), (
            "Should contain most recent prompt"
        )

    def test_extract_router_context_empty_session(self, tmp_path: Path) -> None:
        """Test that empty session (0 turns) returns empty string."""
        from lib.session_reader import extract_router_context

        # Create empty JSONL file
        session_file = tmp_path / "empty-session.jsonl"
        session_file.touch()

        result = extract_router_context(session_file)

        assert result == "", "Empty session should return empty string"

    def test_extract_router_context_slash_only_session(self, tmp_path: Path) -> None:
        """Test that slash-only commands are skipped, returning minimal context.

        Sessions with only /commit, /help etc. should skip those commands
        and return empty or minimal context since there's no real user prompt.
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "slash-only-session.jsonl"

        # Create session with only slash commands
        entries = [
            _create_user_entry("/commit", offset=0),
            _create_assistant_entry(offset=1),
            _create_user_entry("/help", offset=10),
            _create_assistant_entry(offset=11),
            _create_user_entry("/clear", offset=20),
            _create_assistant_entry(offset=21),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # Should either be empty or not contain the slash commands
        # (implementation may vary - either skip them entirely or include them)
        # The key is it should NOT crash and should handle gracefully
        assert isinstance(result, str), "Should return a string even for slash-only session"
        # If not empty, verify it's well-formed (doesn't have parsing errors)
        if result:
            assert "Recent prompts" in result or "prompt" in result.lower(), (
                "If non-empty, should have standard format"
            )

    def test_extract_router_context_malformed_jsonl(self, tmp_path: Path) -> None:
        """Test that malformed JSONL lines are gracefully skipped.

        Invalid JSON lines should not crash; function should skip bad entries
        and return what it can parse.
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "malformed-session.jsonl"

        # Mix of valid and invalid entries
        valid_entry_1 = _create_user_entry("First valid prompt", offset=0)
        valid_entry_2 = _create_user_entry("Second valid prompt", offset=10)
        valid_entry_3 = _create_assistant_entry(offset=11)

        with session_file.open("w", encoding="utf-8") as f:
            f.write(json.dumps(valid_entry_1) + "\n")
            f.write("this is not valid json\n")
            f.write("{incomplete json\n")
            f.write(json.dumps(valid_entry_2) + "\n")
            f.write('{"type": "user", "missing": "message field"}\n')
            f.write(json.dumps(valid_entry_3) + "\n")

        result = extract_router_context(session_file)

        # Should not crash and should return a string
        assert isinstance(result, str), "Should return a string even with malformed lines"
        # Should still extract at least one valid prompt
        if result:
            # Should contain at least one of the valid prompts
            has_valid_content = (
                "first valid" in result.lower() or
                "second valid" in result.lower()
            )
            assert has_valid_content, "Should extract valid prompts despite malformed lines"

    def test_extract_router_context_no_todowrite(self, tmp_path: Path) -> None:
        """Test that session without TodoWrite omits 'Tasks:' line.

        Per spec: 'No TodoWrite calls' -> 'Omit "Tasks:" line'
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "no-todowrite-session.jsonl"

        # Create session with prompts and skill but NO TodoWrite
        entries = [
            _create_user_entry("Start working on the feature", offset=0),
            _create_assistant_entry(offset=1),
            _create_skill_invocation_entry("python-dev", offset=5),
            _create_user_entry("Now add the tests", offset=10),
            _create_assistant_entry(offset=11),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # Should not contain Tasks line since no TodoWrite was called
        assert "tasks:" not in result.lower(), (
            "Should omit 'Tasks:' line when no TodoWrite calls in session"
        )
        # But should still have other content
        assert "python-dev" in result.lower() or "prompt" in result.lower(), (
            "Should still have skill or prompt content"
        )

    def test_extract_router_context_no_skill_invocation(self, tmp_path: Path) -> None:
        """Test that session without Skill invocation omits 'Active:' line.

        Per spec: 'No Skill calls' -> 'Omit "Active:" line'
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "no-skill-session.jsonl"

        # Create session with prompts and TodoWrite but NO Skill invocation
        entries = [
            _create_user_entry("Help me fix this bug", offset=0),
            _create_assistant_entry(offset=1),
            _create_user_entry("Now try another approach", offset=10),
            _create_assistant_entry(offset=11),
            _create_todowrite_entry(
                todos=[
                    {"content": "Fix bug", "status": "in_progress", "activeForm": "Fixing bug"},
                    {"content": "Add tests", "status": "pending", "activeForm": "Adding tests"},
                ],
                offset=15,
            ),
            _create_user_entry("That worked, continue", offset=20),
            _create_assistant_entry(offset=21),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # Should not contain Active line since no Skill was invoked
        assert "active:" not in result.lower(), (
            "Should omit 'Active:' line when no Skill invocations in session"
        )
        # But should still have tasks content
        assert "task" in result.lower() or "pending" in result.lower() or "in_progress" in result.lower(), (
            "Should still have task content from TodoWrite"
        )

    def test_extract_router_context_string_content_format(self, tmp_path: Path) -> None:
        """Test that string content format (used by /commands) is handled.

        Commands like /do, /commit use string format: {"content": "text"}
        instead of list format: {"content": [{"type": "text", "text": "..."}]}

        This was a bug fixed in 2026-01: extract_router_context only handled
        list format, silently skipping string format entries.
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "string-format-session.jsonl"

        # Mix of string format (commands) and list format (regular prompts)
        entries = [
            # Command using string format
            _create_user_entry_string_format(
                "<command-name>/do</command-name>\n<command-args>fix the bug</command-args>",
                offset=0,
            ),
            _create_assistant_entry(offset=1),
            # Regular prompt using list format
            _create_user_entry("Now test the fix", offset=10),
            _create_assistant_entry(offset=11),
            # Another command in string format
            _create_user_entry_string_format(
                "save that to the output directory",
                offset=20,
            ),
            _create_assistant_entry(offset=21),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # Should extract prompts from BOTH formats
        assert "fix the bug" in result.lower() or "/do" in result, (
            "Should extract string-format command content"
        )
        assert "test the fix" in result.lower(), (
            "Should extract list-format prompt content"
        )
        assert "save that" in result.lower() or "output directory" in result.lower(), (
            "Should extract follow-up string-format prompt"
        )

    def test_extract_router_context_mixed_format_ordering(self, tmp_path: Path) -> None:
        """Test that mixed format entries are extracted in correct order.

        Recent prompts should appear in chronological order regardless of
        whether they use string or list content format.
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "mixed-order-session.jsonl"

        entries = [
            _create_user_entry_string_format("first prompt string format", offset=0),
            _create_assistant_entry(offset=1),
            _create_user_entry("second prompt list format", offset=10),
            _create_assistant_entry(offset=11),
            _create_user_entry_string_format("third prompt string format", offset=20),
            _create_assistant_entry(offset=21),
        ]

        with session_file.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        result = extract_router_context(session_file)

        # All three prompts should be present
        assert "first prompt" in result.lower(), "Should contain first prompt"
        assert "second prompt" in result.lower(), "Should contain second prompt"
        assert "third prompt" in result.lower(), "Should contain third prompt"

        # Verify order: first should appear before third in the output
        first_pos = result.lower().find("first prompt")
        third_pos = result.lower().find("third prompt")
        assert first_pos < third_pos, "Prompts should appear in chronological order"


@pytest.mark.demo
class TestExtractRouterContextDemo:
    """Demo tests showing real extract_router_context behavior.

    Run with: uv run pytest tests/test_router_context.py -k demo -v --log-cli-level=INFO
    """

    def test_demo_extract_from_real_session(self) -> None:
        """Given a real session transcript, show what context is extracted.

        This demo uses actual session files to reveal:
        - What prompts are captured
        - How they're formatted
        - Token efficiency of the output
        """
        from lib.session_reader import extract_router_context

        # Find real session transcripts
        session_dir = Path.home() / ".claude/projects/-Users-suzor-src-academicOps"
        if not session_dir.exists():
            pytest.skip("No session directory found")

        sessions = sorted(
            [s for s in session_dir.glob("*.jsonl") if not s.name.startswith("agent-")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not sessions:
            pytest.skip("No session files found")

        current = sessions[0]
        log.info("=" * 70)
        log.info("SESSION: %s", current.name)
        log.info("SIZE: %d bytes", current.stat().st_size)
        log.info("=" * 70)

        # Extract context
        context = extract_router_context(current)

        log.info("EXTRACTED CONTEXT (%d chars):", len(context))
        log.info("-" * 70)
        for line in context.split("\n"):
            log.info("  %s", line)
        log.info("-" * 70)

        # Analyze token efficiency
        assert len(context) < 2000, "Context should be compact (<2000 chars)"
        assert "Session Context" in context or context == "", "Should have header or be empty"

    def test_demo_show_raw_vs_extracted(self, tmp_path: Path) -> None:
        """Given mixed content formats, show what gets extracted vs filtered.

        Demonstrates:
        - String format (commands) vs list format (regular prompts)
        - XML markup in commands
        - Agent notifications
        - What's kept vs discarded
        """
        from lib.session_reader import extract_router_context

        log.info("=" * 70)
        log.info("RAW ENTRIES vs EXTRACTED CONTEXT")
        log.info("=" * 70)

        session_file = tmp_path / "demo-session.jsonl"

        # Create realistic mixed content
        entries = [
            # Command with XML markup (string format)
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-01T10:00:00Z",
                "message": {
                    "content": "<command-message>do</command-message>\n<command-name>/do</command-name>\n<command-args>fix the hydrator context bug</command-args>"
                },
            },
            {"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:01:00Z", "message": {"content": [{"type": "text", "text": "I'll fix that."}]}},
            # Regular prompt (list format)
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-01T10:02:00Z",
                "message": {
                    "content": [{"type": "text", "text": "now run the tests to verify"}]
                },
            },
            {"type": "assistant", "uuid": "a2", "timestamp": "2026-01-01T10:03:00Z", "message": {"content": [{"type": "text", "text": "Running tests..."}]}},
            # Agent notification (noise)
            {
                "type": "user",
                "uuid": "u3",
                "timestamp": "2026-01-01T10:04:00Z",
                "message": {
                    "content": "<agent-notification>\n<agent-id>aa7d721</agent-id>\n<status>completed</status>\n</agent-notification>"
                },
            },
            # Follow-up prompt
            {
                "type": "user",
                "uuid": "u4",
                "timestamp": "2026-01-01T10:05:00Z",
                "message": {
                    "content": "save that output to the results directory"
                },
            },
        ]

        # Log raw entries
        log.info("RAW USER ENTRIES:")
        for i, entry in enumerate(entries):
            if entry["type"] == "user":
                content = entry["message"]["content"]
                if isinstance(content, str):
                    preview = content[:80].replace("\n", "\\n")
                else:
                    preview = content[0]["text"][:80] if content else "(empty)"
                log.info("  %d. [%s] %s...", i + 1, type(content).__name__, preview)

        with session_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        # Extract and show
        context = extract_router_context(session_file)

        log.info("")
        log.info("EXTRACTED CONTEXT:")
        log.info("-" * 50)
        for line in context.split("\n"):
            log.info("  %s", line)
        log.info("-" * 50)

        log.info("")
        log.info("ANALYSIS:")
        log.info("  - XML markup preserved: %s", "<command" in context)
        log.info("  - Agent notification included: %s", "agent-notification" in context)
        log.info("  - Useful prompt text included: %s", "fix" in context.lower() or "test" in context.lower())
        log.info("  - Total chars: %d", len(context))

        # This test SHOWS behavior, doesn't assert correctness
        # The output helps us decide what to improve
        assert context, "Should extract some context"

    def test_demo_token_analysis(self, tmp_path: Path) -> None:
        """Analyze token efficiency: useful content vs noise ratio.

        Shows breakdown of extracted context to identify waste.
        """
        from lib.session_reader import extract_router_context

        log.info("=" * 70)
        log.info("TOKEN EFFICIENCY ANALYSIS")
        log.info("=" * 70)

        session_file = tmp_path / "analysis-session.jsonl"

        # Typical session content
        entries = [
            # Real command
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-01T10:00:00Z",
                "message": {"content": "<command-message>do</command-message>\n<command-name>/do</command-name>\n<command-args>implement the new caching layer for API responses</command-args>"},
            },
            {"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:01:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
            # Follow-up
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-01T10:02:00Z",
                "message": {"content": [{"type": "text", "text": "add tests for the edge cases we discussed"}]},
            },
            {"type": "assistant", "uuid": "a2", "timestamp": "2026-01-01T10:03:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
            # Context-dependent prompt (the case we're trying to help)
            {
                "type": "user",
                "uuid": "u3",
                "timestamp": "2026-01-01T10:04:00Z",
                "message": {"content": "now save that to the output folder"},
            },
        ]

        with session_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        context = extract_router_context(session_file)

        # Analyze content breakdown
        lines = context.split("\n")
        header_chars = len("## Session Context\n\nRecent prompts:\n")
        prompt_chars = sum(len(line) for line in lines if line.startswith('1.') or line.startswith('2.') or line.startswith('3.'))
        other_chars = len(context) - header_chars - prompt_chars

        log.info("CONTENT BREAKDOWN:")
        log.info("  Header/structure: ~%d chars", header_chars)
        log.info("  Prompt content: ~%d chars", prompt_chars)
        log.info("  Other (tasks, skills): ~%d chars", other_chars)
        log.info("  TOTAL: %d chars", len(context))
        log.info("")

        # What SHOULD the hydrator see?
        ideal = """User asked: implement caching layer
User asked: add edge case tests
User asked: save that to output folder"""
        log.info("IDEAL CONTEXT (~%d chars):", len(ideal))
        for line in ideal.split("\n"):
            log.info("  %s", line)
        log.info("")

        log.info("CURRENT CONTEXT:")
        for line in context.split("\n"):
            log.info("  %s", line)

        log.info("")
        log.info("WASTE: XML tags, truncated text, structure overhead")

        assert context, "Should have context"


class TestCleanPromptExtraction:
    """Tests for improved prompt extraction that strips noise."""

    def test_strips_command_xml_markup(self, tmp_path: Path) -> None:
        """Given a command with XML markup, extract only the args content.

        Commands like /do wrap content in XML:
        <command-message>do</command-message>
        <command-name>/do</command-name>
        <command-args>actual user intent here</command-args>

        We should extract just "actual user intent here".
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "command-session.jsonl"

        entries = [
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-01T10:00:00Z",
                "message": {
                    "content": "<command-message>do</command-message>\n<command-name>/do</command-name>\n<command-args>fix the hydrator context bug</command-args>"
                },
            },
            {"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:01:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
        ]

        with session_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        context = extract_router_context(session_file)

        # Should contain the actual command args, not XML markup
        assert "fix the hydrator" in context.lower(), "Should extract command args content"
        # Should NOT contain XML tags
        assert "<command-message>" not in context, "Should strip <command-message> tag"
        assert "<command-name>" not in context, "Should strip <command-name> tag"
        assert "<command-args>" not in context, "Should strip <command-args> tag"

    def test_filters_agent_notifications(self, tmp_path: Path) -> None:
        """Given agent notifications, filter them out entirely.

        Agent notifications are system messages, not user intent:
        <agent-notification>
        <agent-id>aa7d721</agent-id>
        <status>completed</status>
        </agent-notification>

        These should be completely excluded from context.
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "notification-session.jsonl"

        entries = [
            # Real user prompt
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-01T10:00:00Z",
                "message": {"content": [{"type": "text", "text": "run the tests please"}]},
            },
            {"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:01:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
            # Agent notification (should be filtered)
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-01T10:02:00Z",
                "message": {
                    "content": "<agent-notification>\n<agent-id>aa7d721</agent-id>\n<output-file>/tmp/output.txt</output-file>\n<status>completed</status>\n</agent-notification>"
                },
            },
            # Follow-up real prompt
            {
                "type": "user",
                "uuid": "u3",
                "timestamp": "2026-01-01T10:03:00Z",
                "message": {"content": "save that to the output folder"},
            },
        ]

        with session_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        context = extract_router_context(session_file)

        # Should contain real prompts
        assert "run the tests" in context.lower(), "Should include real user prompt"
        assert "save that" in context.lower(), "Should include follow-up prompt"
        # Should NOT contain agent notification content
        assert "agent-notification" not in context, "Should filter out agent notifications"
        assert "aa7d721" not in context, "Should not include agent IDs"

    def test_combined_cleaning(self, tmp_path: Path) -> None:
        """Given mixed content, apply all cleaning rules together.

        Verifies the full pipeline:
        1. Strip command XML
        2. Filter notifications
        3. Keep clean prompts
        """
        from lib.session_reader import extract_router_context

        session_file = tmp_path / "mixed-session.jsonl"

        entries = [
            # Command with XML
            {
                "type": "user",
                "uuid": "u1",
                "timestamp": "2026-01-01T10:00:00Z",
                "message": {"content": "<command-message>do</command-message>\n<command-name>/do</command-name>\n<command-args>implement caching layer</command-args>"},
            },
            {"type": "assistant", "uuid": "a1", "timestamp": "2026-01-01T10:01:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
            # Agent notification (filter out)
            {
                "type": "user",
                "uuid": "u2",
                "timestamp": "2026-01-01T10:02:00Z",
                "message": {"content": "<agent-notification>\n<agent-id>xyz123</agent-id>\n<status>completed</status>\n</agent-notification>"},
            },
            # Clean prompt
            {
                "type": "user",
                "uuid": "u3",
                "timestamp": "2026-01-01T10:03:00Z",
                "message": {"content": [{"type": "text", "text": "add tests for edge cases"}]},
            },
            {"type": "assistant", "uuid": "a3", "timestamp": "2026-01-01T10:04:00Z", "message": {"content": [{"type": "text", "text": "Done"}]}},
            # Context-dependent prompt
            {
                "type": "user",
                "uuid": "u4",
                "timestamp": "2026-01-01T10:05:00Z",
                "message": {"content": "save that to output folder"},
            },
        ]

        with session_file.open("w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        context = extract_router_context(session_file)

        # Verify cleaning worked
        assert "caching layer" in context.lower(), "Should extract command args"
        assert "add tests" in context.lower(), "Should keep clean prompts"
        assert "save that" in context.lower(), "Should keep context-dependent prompts"
        assert "<command" not in context, "Should strip all XML markup"
        assert "agent-notification" not in context, "Should filter notifications"
        assert "xyz123" not in context, "Should not include agent IDs"
