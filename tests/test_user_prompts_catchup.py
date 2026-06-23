"""Behaviour tests for the catch-up timeline (aops-62abcf9d).

Asserts the *behaviour* the catch-up route promises — automated/worker sessions
are collapsed to a one-line abstract, stop-hook boilerplate prompts are dropped,
and genuine interactive sessions are retained in full. Deliberately NO hardcoded
session counts or file lists (brittle mirror tests are banned); every assertion
is on observable behaviour of the classification + render functions.
"""

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
AOPS_CORE = REPO_ROOT / "aops-core"
for p in (str(AOPS_CORE), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from lib.session_naming import is_automated_session  # noqa: E402


def _load_user_prompts():
    """Import the user_prompts script module by path (it lives under scripts/)."""
    spec = importlib.util.spec_from_file_location(
        "user_prompts", AOPS_CORE / "scripts" / "user_prompts.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


up = _load_user_prompts()

STOP_HOOK_BOILERPLATE = (
    "≡ **Before you stop — be honest:**\n"
    "- Have you actually delivered what the user requested?\n"
    "- Make sure you provide a final summary in dot points as the last message."
)


class TestFrontmatterTaskTitle:
    """transcript.py-side AC: generated frontmatter carries task_title."""

    def test_frontmatter_emits_task_title_alongside_task_id(self):
        # Resolution is best-effort; pre-set task_title to avoid a PKB round-trip.
        from datetime import datetime as _dt

        from lib.transcript_parser import Entry, ParsedSession, SessionProcessor

        proc = SessionProcessor()
        summary = ParsedSession(
            uuid="deadbeef12345678",
            repo="junior",
            task_id="aops-62abcf9d",
            task_title="Filter automated sessions from catch-up",
            slug="demo",
        )
        entry = Entry(
            type="user", uuid="u1", parent_uuid="", message={"role": "user", "content": "hi"}
        )
        entry.timestamp = _dt(2026, 6, 6, 9, 0, tzinfo=UTC)
        md = proc.format_session_as_markdown(summary, [entry], variant="full")
        frontmatter = md.split("---", 2)[1]

        assert "task_id: aops-62abcf9d" in frontmatter
        assert 'task_title: "Filter automated sessions from catch-up"' in frontmatter


def _thread(start, **kw):
    base = {
        "start_time": start,
        "session_id": "abcd1234",
        "repo": "junior",
        "model": "claude",
        "slug": "some-slug",
        "url": "$AOPS_SESSIONS/transcripts/2026-06/x-full.md",
        "prompts": [],
        "task_id": None,
        "task_title": None,
        "pr_url": None,
        "is_automated": False,
        "reason": None,
    }
    base.update(kw)
    return base


def _prompt(text, ts="2026-06-06T10:00:00+00:00"):
    return {"timestamp": ts, "type": "user_prompt", "description": text}


# --------------------------------------------------------------------------
# Classification: each documented signal flips a session to automated.
# --------------------------------------------------------------------------


class TestClassification:
    def test_task_id_is_automated(self):
        is_auto, reason = is_automated_session(task_id="aops-123")
        assert is_auto is True
        assert reason == "task"

    def test_polecat_path_is_automated(self):
        is_auto, reason = is_automated_session(
            session_path=Path("/x/aops-sessions/polecats/aops-9/session.jsonl")
        )
        assert is_auto is True
        assert reason == "polecat"

    def test_subagent_path_is_automated(self):
        is_auto, _ = is_automated_session(
            session_path=Path("/x/proj/abc/subagents/agent-deadbeef.jsonl")
        )
        assert is_auto is True

    def test_stop_hook_slug_is_automated(self):
        is_auto, reason = is_automated_session(slug="stop-hook-feedback")
        assert is_auto is True
        assert reason == "stop-hook"

    def test_crew_is_automated(self):
        is_auto, reason = is_automated_session(crew="rbg")
        assert is_auto is True
        assert reason == "crew"

    def test_gemini_worker_is_automated(self):
        is_auto, _ = is_automated_session(
            session_path=Path("/home/x/.gemini/tmp/abc/chats/session-1.json")
        )
        assert is_auto is True

    def test_bare_claude_interactive_is_not_automated(self):
        is_auto, reason = is_automated_session(
            session_path=Path("/home/nic/.claude/projects/-junior/abc.jsonl"),
        )
        assert is_auto is False
        assert reason is None

    @pytest.mark.parametrize(
        "marker",
        ["single-turn", "single-turn-sdk", "single-turn sdk"],
    )
    def test_single_turn_sdk_client_is_automated(self, marker):
        # Library-emitted marker on client; bare interactive path otherwise.
        is_auto, reason = is_automated_session(
            session_path=Path("/home/x/.claude/projects/-junior/abc.jsonl"),
            client=marker,
        )
        assert is_auto is True
        assert reason == "single-turn"

    def test_single_turn_sdk_surface_is_automated(self):
        is_auto, reason = is_automated_session(
            session_path=Path("/home/x/.claude/projects/-junior/abc.jsonl"),
            surface="single-turn-sdk",
        )
        assert is_auto is True
        assert reason == "single-turn"

    def test_single_turn_substring_in_unrelated_field_does_not_match(self):
        # A slug or other field that happens to contain "single-turn" must NOT
        # flip classification — the marker is only meaningful on client/surface.
        is_auto, reason = is_automated_session(
            session_path=Path("/home/nic/.claude/projects/-junior/abc.jsonl"),
            slug="discuss-single-turn-design",
        )
        assert is_auto is False
        assert reason is None

    def test_worker_host_match_is_automated(self, monkeypatch):
        # Mechanism test: a hostname IN the configured set classifies as automated.
        # The specific token "demo-worker" is a test fixture, not an assertion of
        # any real host — patching the module's WORKER_HOSTS proves the set drives
        # the decision (banned mirror-test pattern would assert a literal handle).
        import lib.session_naming as sn

        monkeypatch.setattr(sn, "WORKER_HOSTS", frozenset({"demo-worker"}))
        is_auto, reason = sn.is_automated_session(
            session_path=Path("/home/x/.claude/projects/-junior/abc.jsonl"),
            hostname="demo-worker",
        )
        assert is_auto is True
        assert reason == "worker-host"

    def test_worker_host_miss_is_not_automated(self, monkeypatch):
        # A hostname NOT in the configured set leaves classification untouched.
        import lib.session_naming as sn

        monkeypatch.setattr(sn, "WORKER_HOSTS", frozenset({"demo-worker"}))
        is_auto, reason = sn.is_automated_session(
            session_path=Path("/home/nic/.claude/projects/-junior/abc.jsonl"),
            hostname="some-other-box",
        )
        assert is_auto is False
        assert reason is None

    def test_worker_host_default_set_is_empty(self, monkeypatch):
        # With no env var set and the set empty (the default at module load),
        # hostname alone never triggers automated classification — preserves the
        # "no specific handle in source" property the dash port violated.
        import lib.session_naming as sn

        monkeypatch.setattr(sn, "WORKER_HOSTS", frozenset())
        is_auto, reason = sn.is_automated_session(
            session_path=Path("/home/nic/.claude/projects/-junior/abc.jsonl"),
            hostname="anything",
        )
        assert is_auto is False
        assert reason is None

    def test_stronger_signal_wins_over_worker_host(self, monkeypatch):
        # task_id dominates: even when hostname matches WORKER_HOSTS the reason
        # should be the stronger task signal, not "worker-host".
        import lib.session_naming as sn

        monkeypatch.setattr(sn, "WORKER_HOSTS", frozenset({"demo-worker"}))
        is_auto, reason = sn.is_automated_session(
            task_id="aops-42",
            hostname="demo-worker",
        )
        assert is_auto is True
        assert reason == "task"


# --------------------------------------------------------------------------
# Prompt-level noise: dropped even inside interactive sessions.
# --------------------------------------------------------------------------


class TestNoisePrompts:
    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            STOP_HOOK_BOILERPLATE,
            "<system-reminder>do this</system-reminder>",
            "/daily",
            "y",
            "continue",
        ],
    )
    def test_noise_is_dropped(self, text):
        assert up.is_noise_prompt(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "Please refactor the timeline script to filter workers",
            "/q fix the broken parser please",
        ],
    )
    def test_genuine_prompt_is_kept(self, text):
        assert up.is_noise_prompt(text) is False


# --------------------------------------------------------------------------
# Render behaviour: the three acceptance assertions, end-to-end through render.
# --------------------------------------------------------------------------


class TestRender:
    def _start(self, hour=10):
        return datetime(2026, 6, 6, hour, 0, 0, tzinfo=UTC)

    def test_automated_session_is_collapsed_not_dumped(self):
        worker_prompt = "Implement the whole worker pipeline as described in the task body."
        worker = _thread(
            self._start(9),
            is_automated=True,
            reason="task",
            task_id="aops-deadbeef",
            task_title="Build the thing",
            prompts=[_prompt(worker_prompt)],
        )
        md = "\n".join(up.render([worker], "2026-06-06"))

        # Appendix exists and carries a one-line abstract for the worker.
        assert "## Automated / worker sessions (collapsed)" in md
        assert "aops-deadbeef" in md
        assert "Build the thing" in md
        # The worker's full prompt text is NOT dumped in the body.
        assert worker_prompt not in md
        # No per-prompt heading for the collapsed session.
        assert "### Prompt" not in md

    def test_stop_hook_prompt_dropped_in_interactive_session(self):
        real = "Refactor user_prompts.py to separate workers from my prompts"
        interactive = _thread(
            self._start(10),
            is_automated=False,
            prompts=[_prompt(STOP_HOOK_BOILERPLATE), _prompt(real)],
        )
        md = "\n".join(up.render([interactive], "2026-06-06"))

        assert real in md
        assert "Before you stop" not in md
        # Exactly one prompt survived the noise filter.
        assert md.count("### Prompt") == 1

    def test_interactive_session_retained_in_full(self):
        p1 = "First, audit the redaction path"
        p2 = "Now wire the classifier into the timeline"
        interactive = _thread(
            self._start(11),
            is_automated=False,
            repo="academicOps",
            prompts=[_prompt(p1), _prompt(p2)],
        )
        md = "\n".join(up.render([interactive], "2026-06-06"))

        assert p1 in md
        assert p2 in md
        assert md.count("### Prompt") == 2
        # Interactive session appears in the main body, not the appendix.
        assert "## 2026-06-06 11:00:00 | academicOps" in md

    def test_all_noise_interactive_session_disappears(self):
        interactive = _thread(
            self._start(12),
            is_automated=False,
            prompts=[_prompt("y"), _prompt(STOP_HOOK_BOILERPLATE)],
        )
        md = "\n".join(up.render([interactive], "2026-06-06"))
        assert "### Prompt" not in md

    def test_task_id_recovered_from_polecat_path(self):
        tid = up._task_id_from_path(
            Path("/x/aops-sessions/polecats/aops-abc123/claude-sessions/-workspace/s.jsonl")
        )
        assert tid == "aops-abc123"

    def test_task_id_from_path_none_for_interactive(self):
        assert up._task_id_from_path(Path("/home/nic/.claude/projects/-junior/s.jsonl")) is None

    def test_abstract_title_resolution_order(self):
        # task_title wins.
        assert up.abstract_title(_thread(self._start(), task_title="T", task_id="aops-1")) == "T"
        # pr fallback when no task.
        t = _thread(self._start(), pr_url="https://github.com/o/r/pull/7")
        assert up.abstract_title(t) == "o/r#7"
        # slug fallback when nothing else.
        assert up.abstract_title(_thread(self._start(), slug="my-slug")) == "my-slug"


# --------------------------------------------------------------------------
# File output: freshness header and secret redaction (aops-ec29df30).
# --------------------------------------------------------------------------


class TestFileOutput:
    def test_prepare_file_output_has_generated_header(self):
        lines = ["# User Prompt Timeline", "some content"]
        result = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        assert result.startswith("<!-- generated: 2026-06-24T10:00:00+00:00 -->")

    def test_prepare_file_output_includes_original_content(self):
        lines = ["# Header", "body text"]
        result = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        assert "# Header" in result
        assert "body text" in result

    def test_prepare_file_output_redacts_github_token(self):
        lines = ["export GH_TOKEN=ghp_ABCDEFabcdefABCDEFabcdef123456"]
        result = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        assert "ghp_" not in result
        assert "[REDACTED]" in result

    def test_prepare_file_output_redacts_anthropic_key(self):
        lines = ["AOPS_CC_OAUTH_TOKEN=sk-ant-oat01-someverylongtokenvalue1234567"]
        result = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        assert "sk-ant-" not in result
        assert "[REDACTED]" in result

    def test_prepare_file_output_does_not_redact_normal_text(self):
        lines = ["Please fix the login flow", "and also the redaction pipeline"]
        result = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        assert "Please fix the login flow" in result
        assert "and also the redaction pipeline" in result

    def test_prepare_file_output_ends_with_newline(self):
        result = up._prepare_file_output(["line"], "2026-06-24T10:00:00+00:00")
        assert result.endswith("\n")

    def test_output_file_written_with_freshness_header(self, tmp_path):
        """_prepare_file_output content retains the freshness header after file write/read roundtrip."""
        output_file = tmp_path / "user-prompts-2026-06.txt"
        lines = ["# User Prompt Timeline: Since 2026-06-01", "content"]
        text = up._prepare_file_output(lines, "2026-06-24T10:00:00+00:00")
        output_file.write_text(text, encoding="utf-8")
        content = output_file.read_text()
        assert content.startswith("<!-- generated: 2026-06-24T10:00:00+00:00 -->")
        assert "# User Prompt Timeline" in content
