"""Tests for transcript parsing and reflection extraction."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from lib.paths import get_summaries_dir, get_transcripts_dir
from lib.transcript_paths import iter_rotated_files


class TestReflectionExtraction:
    """Test extracting Framework Reflections from transcript."""

    @pytest.fixture
    def parser_module(self):
        """Import the transcript parser module."""
        import lib.transcript_parser as parser

        return parser

    def test_parse_framework_reflection_basic(self, parser_module) -> None:
        """Test parsing a simple Framework Reflection."""
        content = """
Some conversation...

## Framework Reflection

**Prompts**: Used strict prompting.
**Guidance Received**: None.
**Followed**: Yes.
**Outcome**: Success.
**Accomplishments**:
- Fixed the bug.
**Friction Points**: None.
**Root Cause**: Typo.
**Proposed Changes**: None.
**Next Step**: Merge.
"""
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is not None
        assert reflection.get("prompts") == "Used strict prompting."
        assert reflection.get("outcome") == "Success."
        # accomplishments is a list, check membership loosely or exactly
        accomplishments = reflection.get("accomplishments", [])
        assert any("Fixed the bug" in acc for acc in accomplishments)

    def test_parse_framework_reflection_partial(self, parser_module) -> None:
        """Test parsing with missing fields."""
        content = """
## Framework Reflection

**Outcome**: Partial success.
**Next Step**: Retry.
"""
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is not None
        assert reflection.get("outcome") == "Partial success."
        assert reflection.get("next_step") == "Retry."
        assert reflection.get("prompts") is None

    def test_parse_framework_reflection_no_header(self, parser_module) -> None:
        """Should return None if header missing."""
        content = "Just some text."
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is None

    def test_parse_framework_reflection_with_code_fences(self, parser_module) -> None:
        """Test parsing accomplishments with code fences."""
        content = """
## Framework Reflection
**Accomplishments**:
- Fixed the bug.
- ```
- Some code change
- ```python
- print("hello")
"""
        reflection = parser_module.parse_framework_reflection(content)
        assert reflection is not None
        accomplishments = reflection.get("accomplishments", [])
        assert "Fixed the bug." in accomplishments
        assert "Some code change" in accomplishments
        assert 'print("hello")' in accomplishments
        # Ensure no raw code fences remain
        assert not any(acc.startswith("```") for acc in accomplishments)

    @pytest.mark.integration
    def test_extract_reflection_from_live_logs(self, parser_module, original_env) -> None:
        """CRITICAL: Verify extraction works on actual live session logs.

        This test finds recent session logs that contain reflections and
        verifies the extraction pipeline works end-to-end.
        """

        # Use actual sessions directory from environment (bypassing test isolation)
        aops_sessions = original_env.get("AOPS_SESSIONS")
        if aops_sessions:
            sessions_dir = Path(aops_sessions).resolve() / "transcripts"
        else:
            sessions_dir = get_transcripts_dir()

        reflection_files = []

        if sessions_dir.exists():
            for md_file in iter_rotated_files(sessions_dir, "*-full.md"):
                try:
                    content = md_file.read_text(encoding="utf-8")
                    if (
                        "## Framework Reflection" in content
                        or "## framework reflection" in content.lower()
                    ):
                        reflection_files.append(md_file)
                        if len(reflection_files) >= 3:
                            break
                except Exception:
                    continue

        # We must have at least one session with a reflection to test against
        if len(reflection_files) == 0:
            pytest.skip(
                f"No live session logs with Framework Reflections found in {sessions_dir}. "
                "Ensure session transcripts exist for testing."
            )

        # Test extraction on each found file
        successful_extractions = 0
        for md_file in reflection_files:
            content = md_file.read_text(encoding="utf-8")
            reflection = parser_module.parse_framework_reflection(content)

            if reflection and (
                reflection.get("outcome")
                or reflection.get("accomplishments")
                or reflection.get("next_step")
            ):
                successful_extractions += 1
            else:
                print(f"Failed to extract from {md_file.name}")

        assert successful_extractions > 0, "Failed to extract meaningful data from any live log"


class TestSummaryRegenerationOnGrownJsonl:
    """When the source jsonl grows between runs, the summary JSON must
    be refreshed rather than skipped via the 'insights already exist' path.

    Regression: previously transcript.py would early-return on any existing
    insights file, so a session that had been transcribed once with N entries
    would never get its timeline_events updated when the jsonl grew to 2N+M
    entries. (See user bug: session a63851ba had only 2 timeline_events in
    the summary JSON despite 19 user turns in the regenerated transcript.)
    """

    SESSION_UUID = "a63851ba-1234-5678-9abc-def012345678"
    SESSION_ID = "a63851ba"

    @staticmethod
    def _ts(off_min: int) -> str:
        start = datetime(2026, 4, 27, 10, 6, 0, tzinfo=UTC)
        return (start + timedelta(minutes=off_min)).isoformat()

    @classmethod
    def _user_entry(cls, uuid: str, parent: str, text: str, off: int, meta: bool = False) -> dict:
        return {
            "type": "user",
            "uuid": uuid,
            "parentUuid": parent,
            "sessionId": cls.SESSION_UUID,
            "timestamp": cls._ts(off),
            "isMeta": meta,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
            "cwd": "/home/test/note-project",
        }

    @classmethod
    def _assistant_entry(cls, uuid: str, parent: str, text: str, off: int) -> dict:
        return {
            "type": "assistant",
            "uuid": uuid,
            "parentUuid": parent,
            "sessionId": cls.SESSION_UUID,
            "timestamp": cls._ts(off),
            "message": {
                "role": "assistant",
                "model": "claude-opus-4-5",
                "content": [{"type": "text", "text": text}],
                "usage": {
                    "input_tokens": 50,
                    "output_tokens": 25,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 100,
                },
            },
        }

    def _write_jsonl(self, path: Path, entries: list[dict], append: bool = False) -> None:
        mode = "a" if append else "w"
        with open(path, mode, encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def _phase1_entries(self) -> list[dict]:
        # /clear meta + first user prompt + assistant ack
        return [
            self._user_entry("u1", "", "<command-name>/clear</command-name>", 0, meta=True),
            self._user_entry("u2", "u1", "brain through correctly organise my notes", 1),
            self._assistant_entry("a2", "u2", "I'll help with that.", 2),
        ]

    def _phase2_entries(self) -> list[dict]:
        # Simulates the user continuing the session after the first transcript run.
        return [
            self._user_entry("u5", "a2", "why does today's note still have saturday's story?", 6),
            self._assistant_entry("a6", "u5", "Looking into that.", 7),
            self._user_entry("u7", "a6", "did you just delete the note from sunday?", 9),
            self._assistant_entry("a8", "u7", "No, I did not delete it.", 10),
            self._user_entry("u9", "a8", "please show me the current state", 12),
            self._assistant_entry("a10", "u9", "Here's the current state.", 13),
        ]

    def _run_transcript(self, jsonl_path: Path, repo_root: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(repo_root / "aops-core" / "scripts" / "transcript.py"),
                str(jsonl_path),
                "--no-sync",
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def _read_summary(self) -> dict:
        summaries = list(iter_rotated_files(get_summaries_dir(), f"*{self.SESSION_ID}*.json"))
        assert len(summaries) == 1, f"expected exactly one summary, got {summaries}"
        return json.loads(summaries[0].read_text(encoding="utf-8"))

    def test_summary_is_refreshed_when_jsonl_grows(self, tmp_path: Path) -> None:
        repo_root = Path(__file__).parent.parent
        jsonl_path = tmp_path / f"{self.SESSION_UUID}.jsonl"

        # --- Phase 1: write minimal session, run transcript ---
        self._write_jsonl(jsonl_path, self._phase1_entries())
        result1 = self._run_transcript(jsonl_path, repo_root)
        assert result1.returncode == 0, f"phase1 failed:\n{result1.stdout}\n{result1.stderr}"

        summary1 = self._read_summary()
        events1 = summary1.get("timeline_events") or []
        prompts1 = [e for e in events1 if e.get("type") == "user_prompt"]
        # Only 1 non-meta user prompt was written, so we expect 1 user_prompt event.
        assert len(prompts1) == 1, f"phase1 user prompts: {prompts1}"

        # --- Phase 2: append more turns, re-run transcript ---
        self._write_jsonl(jsonl_path, self._phase2_entries(), append=True)
        result2 = self._run_transcript(jsonl_path, repo_root)
        assert result2.returncode == 0, f"phase2 failed:\n{result2.stdout}\n{result2.stderr}"

        summary2 = self._read_summary()
        events2 = summary2.get("timeline_events") or []
        prompts2 = [e for e in events2 if e.get("type") == "user_prompt"]

        # The bug: prompts2 stayed at 1. The fix: prompts2 should reflect all
        # 4 non-meta user prompts (1 from phase1 + 3 from phase2).
        assert len(prompts2) == 4, (
            f"summary JSON did not refresh after jsonl grew: "
            f"got {len(prompts2)} user_prompt events, expected 4. "
            f"events={events2}"
        )

        # Spot-check: the new prompts must actually be present.
        descriptions = [e.get("description", "") for e in prompts2]
        assert any("saturday" in d for d in descriptions), descriptions
        assert any("delete the note from sunday" in d for d in descriptions), descriptions

    def test_existing_reflection_fields_preserved_on_refresh(self, tmp_path: Path) -> None:
        """If the existing summary JSON has a non-empty reflection-derived
        field (e.g. accomplishments, summary) and the new run produces an
        empty value for it, the existing value must be preserved rather
        than clobbered.
        """
        repo_root = Path(__file__).parent.parent
        jsonl_path = tmp_path / f"{self.SESSION_UUID}.jsonl"
        self._write_jsonl(jsonl_path, self._phase1_entries())

        # Phase 1 run
        result1 = self._run_transcript(jsonl_path, repo_root)
        assert result1.returncode == 0, result1.stderr

        summaries = list(iter_rotated_files(get_summaries_dir(), f"*{self.SESSION_ID}*.json"))
        assert len(summaries) == 1
        existing_path = summaries[0]
        existing_data = json.loads(existing_path.read_text(encoding="utf-8"))

        # Inject reflection-derived fields as if a previous reflection-bearing
        # run (or human edit) had populated them.
        existing_data["summary"] = "Hand-authored session summary"
        existing_data["accomplishments"] = ["Did the thing", "Did another thing"]
        existing_data["outcome"] = "success"
        existing_path.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")

        # Phase 2: extend jsonl and re-run
        self._write_jsonl(jsonl_path, self._phase2_entries(), append=True)
        result2 = self._run_transcript(jsonl_path, repo_root)
        assert result2.returncode == 0, result2.stderr

        refreshed = self._read_summary()

        # Timeline grew (the whole point of the refresh)
        prompts = [
            e for e in (refreshed.get("timeline_events") or []) if e.get("type") == "user_prompt"
        ]
        assert len(prompts) == 4

        # And the hand-authored reflection fields survived
        assert refreshed.get("summary") == "Hand-authored session summary"
        assert refreshed.get("accomplishments") == ["Did the thing", "Did another thing"]
        assert refreshed.get("outcome") == "success"


class TestThoughtsAndContext:
    """Tests for Gemini thoughts rendering, Claude thinking blocks, per-turn
    metadata, and Session Context section (tasks df03f1d9 + 8b3e3cfd)."""

    @pytest.fixture
    def processor(self):
        from lib.transcript_parser import SessionProcessor

        return SessionProcessor()

    def _write_gemini_session(self, tmp_path: Path) -> Path:
        data = {
            "sessionId": "abcd1234",
            "projectHash": "xxx",
            "startTime": "2026-04-16T00:10:00Z",
            "lastUpdated": "2026-04-16T00:20:00Z",
            "kind": "chat",
            "messages": [
                {
                    "id": "u1",
                    "type": "user",
                    "timestamp": "2026-04-16T00:10:00Z",
                    "content": "Investigate signal handling.",
                },
                {
                    "id": "g1",
                    "type": "gemini",
                    "timestamp": "2026-04-16T00:10:30Z",
                    "content": "I will investigate.",
                    "model": "gemini-3-flash-preview",
                    "thoughts": [
                        {
                            "subject": "Analyzing Test Coverage",
                            "description": "I've reviewed the existing test...",
                            "timestamp": "2026-04-16T00:10:25Z",
                        }
                    ],
                    "tokens": {
                        "input": 26142,
                        "output": 41,
                        "cached": 21950,
                        "thoughts": 399,
                        "tool": 0,
                        "total": 26582,
                    },
                },
            ],
        }
        path = tmp_path / "session-2026-04-16T00-10-abcd1234.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_gemini_thoughts_rendered_in_full(self, processor, tmp_path):
        path = self._write_gemini_session(tmp_path)
        summary, entries, agents = processor.parse_session_file(str(path))
        md = processor.format_session_as_markdown(
            summary, entries, agents, include_tool_results=True, variant="full"
        )
        assert "💭 Model thoughts" in md
        assert "Analyzing Test Coverage" in md
        assert "<details>" in md

    def test_gemini_thoughts_compact_in_abridged(self, processor, tmp_path):
        path = self._write_gemini_session(tmp_path)
        summary, entries, agents = processor.parse_session_file(str(path))
        md = processor.format_session_as_markdown(
            summary, entries, agents, include_tool_results=False, variant="abridged"
        )
        # Abridged: subject only, no <details>
        assert "Analyzing Test Coverage" in md
        assert "<details>" not in md

    def test_per_turn_meta_shows_model_and_thoughts_tokens(self, processor, tmp_path):
        path = self._write_gemini_session(tmp_path)
        summary, entries, agents = processor.parse_session_file(str(path))
        md = processor.format_session_as_markdown(
            summary, entries, agents, include_tool_results=True, variant="full"
        )
        assert "model=gemini-3-flash-preview" in md
        # input/output tokens
        assert "26,142 in / 41 out" in md
        # thoughts tokens
        assert "399 think" in md
        # cache_read
        assert "21,950 cache" in md

    def test_claude_thinking_block_rendered(self, processor):
        from lib.transcript_parser import Entry, SessionSummary

        entries = [
            Entry(
                type="user",
                uuid="u1",
                timestamp=datetime(2026, 4, 16, 0, 10, tzinfo=UTC),
                message={"content": "Hello"},
            ),
            Entry(
                type="assistant",
                uuid="a1",
                timestamp=datetime(2026, 4, 16, 0, 10, 1, tzinfo=UTC),
                message={
                    "content": [
                        {"type": "thinking", "thinking": "Let me think about this carefully."},
                        {"type": "text", "text": "Here is my answer."},
                    ],
                    "model": "claude-opus-4-7",
                },
                model="claude-opus-4-7",
            ),
        ]
        summary = SessionSummary(uuid="test")
        md = processor.format_session_as_markdown(
            summary, entries, {}, include_tool_results=True, variant="full"
        )
        assert "Extended thinking" in md
        assert "Let me think about this carefully" in md
