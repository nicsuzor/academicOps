"""Tests for `transcript.py --ledger` (aops task_bd1d28ba).

The ledger is a thin reader over data lib.transcript_parser.build_user_prompts
already computed and persisted as the ``user_prompts`` field on every
summaries/*.json — these tests seed summary JSON fixtures directly rather than
re-deriving prompts from raw jsonl, mirroring what the ledger code itself
does. A prior attempt (PR #2176) was rejected for hand-rolling a second,
worse prompt miner against markdown transcripts; do not repeat that pattern
here either.
"""

import importlib.util
import json
import sys
from pathlib import Path

from lib.paths import get_sessions_repo, get_summaries_dir


def _load_transcript_script():
    """Dynamically import scripts/transcript.py (not a package-relative module)."""
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "aops-core" / "scripts" / "transcript.py"
    spec = importlib.util.spec_from_file_location("transcript_script_ledger", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["transcript_script_ledger"] = module
    spec.loader.exec_module(module)
    return module


def _write_summary(
    name: str,
    *,
    session_id: str,
    surface: str,
    date: str,
    user_prompts: list[dict],
    repo: str | None = None,
    task_id: str | None = None,
    pull_requests: list[int] | None = None,
    summary: str | None = None,
    outcome: str | None = None,
) -> Path:
    month_dir = get_summaries_dir() / date[:7]
    month_dir.mkdir(parents=True, exist_ok=True)
    path = month_dir / name
    data = {
        "session_id": session_id,
        "surface": surface,
        "date": date,
        "user_prompts": user_prompts,
        "repo": repo,
        "task_id": task_id,
        "pull_requests": pull_requests,
        "summary": summary,
        "outcome": outcome,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _read_ledger() -> list[str]:
    ledger_path = get_sessions_repo() / "state" / "prompt_ledger.md"
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if ln.startswith("- [")]


class TestGenerateLedgerBasics:
    def test_filters_to_nic_surfaces_only(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-aaaaaaaa-junior-claude-session.json",
            session_id="aaaaaaaa",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[
                {"timestamp": "2026-07-06T09:00:00+10:00", "text": "fix the CI pipeline"}
            ],
        )
        _write_summary(
            "20260706-0901-bbbbbbbb-gha-claude-session.json",
            session_id="bbbbbbbb",
            surface="github-actions",
            date="2026-07-06T09:01:00+10:00",
            user_prompts=[
                {"timestamp": "2026-07-06T09:01:00+10:00", "text": "agent-authored dispatch"}
            ],
        )
        _write_summary(
            "20260706-0902-cccccccc-polecat-claude-session.json",
            session_id="cccccccc",
            surface="claude-polecat",
            date="2026-07-06T09:02:00+10:00",
            user_prompts=[
                {"timestamp": "2026-07-06T09:02:00+10:00", "text": "worker dispatch text"}
            ],
        )

        rc = transcript_script.generate_prompt_ledger("2026-07-06")
        assert rc == 0

        lines = _read_ledger()
        assert len(lines) == 1
        assert "aaaaaaaa" in lines[0]
        assert "fix the CI pipeline" in lines[0]
        assert "bbbbbbbb" not in "".join(lines)
        assert "cccccccc" not in "".join(lines)

    def test_drops_interrupted_noise(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-1000-dddddddd-junior-claude-session.json",
            session_id="dddddddd",
            surface="claude-code-cli",
            date="2026-07-06T10:00:00+10:00",
            user_prompts=[
                {"timestamp": "2026-07-06T10:00:00+10:00", "text": "[Request interrupted by user]"},
                {"timestamp": "2026-07-06T10:01:00+10:00", "text": "a real question"},
            ],
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 1
        assert "a real question" in lines[0]
        assert "interrupted" not in lines[0].lower()

    def test_since_filter_excludes_earlier_prompts(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260701-0900-eeeeeeee-junior-claude-session.json",
            session_id="eeeeeeee",
            surface="claude-code-cli",
            date="2026-07-01T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-01T09:00:00+10:00", "text": "an old prompt"}],
        )
        _write_summary(
            "20260707-0900-ffffffff-junior-claude-session.json",
            session_id="ffffffff",
            surface="claude-code-cli",
            date="2026-07-07T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-07T09:00:00+10:00", "text": "a recent prompt"}],
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 1
        assert "a recent prompt" in lines[0]

    def test_reverse_date_sorted(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-11111111-junior-claude-session.json",
            session_id="11111111",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-06T09:00:00+10:00", "text": "earlier prompt"}],
        )
        _write_summary(
            "20260708-0900-22222222-junior-claude-session.json",
            session_id="22222222",
            surface="claude-code-cli",
            date="2026-07-08T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-08T09:00:00+10:00", "text": "later prompt"}],
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 2
        assert "later prompt" in lines[0]
        assert "earlier prompt" in lines[1]

    def test_invalid_since_returns_error(self) -> None:
        transcript_script = _load_transcript_script()
        rc = transcript_script.generate_prompt_ledger("not-a-date")
        assert rc == 1


class TestOutcomeLinkHonesty:
    """The honesty-mandated core of the ledger: outcome/link are populated
    ONLY when unambiguously attributable, never copied onto multiple prompts.
    """

    def test_single_prompt_session_resolves_pr_link(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-33333333-aops-claude-session.json",
            session_id="33333333",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-06T09:00:00+10:00", "text": "ship the fix"}],
            repo="aops",
            pull_requests=[2120],
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 1
        assert "github.com/nicsuzor/academicOps/pull/2120" in lines[0]

    def test_single_prompt_session_resolves_task_link(self) -> None:
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-44444444-junior-claude-session.json",
            session_id="44444444",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-06T09:00:00+10:00", "text": "start the task"}],
            task_id="`aops-fef39347`",
            summary="Did the thing.",
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 1
        assert "task:aops-fef39347" in lines[0]
        assert "Did the thing." in lines[0]

    def test_multi_prompt_session_never_attributes_outcome(self) -> None:
        """A session with 3 prompts and a resolved task/PR must NOT stamp
        that outcome/link onto every row — that misattributes which prompt
        produced it. All three rows keep blank outcome/link fields.
        """
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-55555555-aops-claude-session.json",
            session_id="55555555",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[
                {"timestamp": "2026-07-06T09:00:00+10:00", "text": "first question"},
                {"timestamp": "2026-07-06T09:05:00+10:00", "text": "second question"},
                {"timestamp": "2026-07-06T09:10:00+10:00", "text": "third question"},
            ],
            repo="aops",
            pull_requests=[2145],
            summary="Session completed.",
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 3
        for line in lines:
            # Format is "... [question] [outcome] [link]" — the last two
            # bracket groups must both be empty.
            assert line.rstrip().endswith("[] []"), line

    def test_no_reflection_leaves_outcome_link_blank(self) -> None:
        """Honesty: a single-prompt session with no summary/outcome/task/PR
        at all must render empty brackets, never a fabricated placeholder.
        """
        transcript_script = _load_transcript_script()

        _write_summary(
            "20260706-0900-66666666-junior-claude-session.json",
            session_id="66666666",
            surface="claude-code-cli",
            date="2026-07-06T09:00:00+10:00",
            user_prompts=[{"timestamp": "2026-07-06T09:00:00+10:00", "text": "just asking"}],
        )

        transcript_script.generate_prompt_ledger("2026-07-06")
        lines = _read_ledger()
        assert len(lines) == 1
        assert lines[0].rstrip().endswith("[] []")


class TestLedgerHelpers:
    def test_task_link_rejects_non_pkb_shaped_ids(self) -> None:
        transcript_script = _load_transcript_script()
        # Free-form ad-hoc id that doesn't match the <project>-<8hex> shape.
        assert transcript_script._ledger_task_link({"task_id": "adhoc-sessions"}) == ""

    def test_task_link_strips_backticks(self) -> None:
        transcript_script = _load_transcript_script()
        assert (
            transcript_script._ledger_task_link({"task_id": "`aops-fef39347`"})
            == "task:aops-fef39347"
        )

    def test_question_text_collapses_whitespace(self) -> None:
        transcript_script = _load_transcript_script()
        raw = "line one\n\n  line two\twith tabs"
        assert transcript_script._ledger_question_text(raw) == "line one line two with tabs"

    def test_question_text_truncates_long_prompts(self) -> None:
        transcript_script = _load_transcript_script()
        raw = "word " * 100
        result = transcript_script._ledger_question_text(raw)
        assert len(result) <= 141
        assert result.endswith("…")
