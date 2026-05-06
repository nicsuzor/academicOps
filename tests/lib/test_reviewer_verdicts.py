"""Tests for the reviewer verdict parser (Build B of Safeguard ROI v0)."""

from lib.reviewer_verdicts import (
    build_subagent_verdicts,
    count_issues,
    extract_verdict,
    last_assistant_text,
)
from lib.transcript_parser import Entry


class TestExtractVerdict:
    def test_bare_token_at_start(self):
        assert extract_verdict("APPROVE\n\nLooks good.") == "APPROVE"

    def test_lowercase_token(self):
        assert extract_verdict("revise\n\n- issue 1") == "REVISE"

    def test_markdown_header(self):
        assert extract_verdict("# Verdict: PASS\n") == "PASS"

    def test_bold_label(self):
        assert extract_verdict("**Verdict:** FAIL — see below") == "FAIL"

    def test_bold_inline(self):
        assert extract_verdict("**Verdict: ESCALATE**\n") == "ESCALATE"

    def test_em_dash_separator(self):
        assert extract_verdict("Verdict — APPROVE\n") == "APPROVE"

    def test_no_match_for_unknown_token(self):
        # The real-world case the spec must NOT misclassify: a "Verdict: OK ..."
        # message uses the word but no canonical token, so we must return None.
        assert extract_verdict("**Verdict: OK with minor WARN**\n- a\n- b") is None

    def test_no_match_for_word_extension(self):
        # "APPROVED" must not match APPROVE because of the trailing word
        # boundary.
        assert extract_verdict("APPROVED\nfollowing review") is None

    def test_empty_text(self):
        assert extract_verdict("") is None
        assert extract_verdict(None) is None  # type: ignore[arg-type]

    def test_skips_blank_lines(self):
        assert extract_verdict("\n\n   \n## REVISE\n") == "REVISE"

    def test_first_match_wins_top_to_bottom(self):
        text = "## APPROVE\n\nDetails:\n- but consider FAIL"
        assert extract_verdict(text) == "APPROVE"

    def test_does_not_scan_arbitrarily_deep(self):
        # A token buried 50 lines down should be ignored — verdicts are
        # supposed to live near the top.
        body = "\n".join("filler" for _ in range(50))
        assert extract_verdict(body + "\nAPPROVE\n") is None


class TestCountIssues:
    def test_empty(self):
        assert count_issues("") == 0

    def test_dash_bullets(self):
        text = "Summary\n\n- one\n- two\n- three\n"
        assert count_issues(text) == 3

    def test_star_bullets_and_numbered_mixed(self):
        text = "* a\n* b\n\n1. x\n2. y\n"
        assert count_issues(text) == 4

    def test_indented_bullets_count(self):
        text = "  - nested\n    * deeper\n1. first\n"
        assert count_issues(text) == 3

    def test_dash_inside_prose_does_not_count(self):
        # "- " at start of line is the trigger; a bare hyphen in prose is not.
        text = "this - is not a list\nneither is this -- one\n"
        assert count_issues(text) == 0


class TestLastAssistantText:
    def test_empty_list(self):
        assert last_assistant_text([]) == ""

    def test_picks_last_assistant(self):
        entries = [
            Entry(type="assistant", message={"content": [{"type": "text", "text": "first"}]}),
            Entry(type="user", message={"content": "in between"}),
            Entry(type="assistant", message={"content": [{"type": "text", "text": "LAST"}]}),
        ]
        assert last_assistant_text(entries) == "LAST"

    def test_skips_thinking_blocks(self):
        entries = [
            Entry(
                type="assistant",
                message={
                    "content": [
                        {"type": "thinking", "thinking": "internal"},
                        {"type": "text", "text": "spoken"},
                    ]
                },
            ),
        ]
        assert last_assistant_text(entries) == "spoken"

    def test_string_content(self):
        entries = [Entry(type="assistant", message={"content": "bare string"})]
        assert last_assistant_text(entries) == "bare string"

    def test_assistant_with_only_tool_use_falls_back_to_earlier(self):
        # If the very last assistant entry has no text (only tool_use blocks),
        # fall back to the prior assistant text. Subagents normally end on a
        # verdict text block, so this only matters at the tail; we'd rather
        # surface the most recent textual content than return "".
        entries = [
            Entry(type="assistant", message={"content": [{"type": "text", "text": "verdict"}]}),
            Entry(type="assistant", message={"content": [{"type": "tool_use", "name": "Read"}]}),
        ]
        assert last_assistant_text(entries) == "verdict"


class TestBuildSubagentVerdicts:
    def test_no_subagents_returns_empty(self):
        assert build_subagent_verdicts([], None, None) == []
        assert build_subagent_verdicts([], {}, {}) == []

    def test_emits_one_row_per_invocation_with_tokens(self):
        # Main session: a Task tool_use to subagent_type=rbg with tool_id "tu1"
        # and a tool_result that links to agentId "agentA".
        main = [
            Entry(
                type="assistant",
                message={
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "tu1",
                            "name": "Task",
                            "input": {"subagent_type": "rbg"},
                        }
                    ]
                },
            ),
            Entry(
                type="user",
                message={"content": [{"type": "tool_result", "tool_use_id": "tu1"}]},
                tool_use_result={"agentId": "agentA"},
            ),
        ]
        agent_entries = {
            "agentA": [
                Entry(
                    type="assistant",
                    message={
                        "content": [
                            {
                                "type": "text",
                                "text": "## Verdict: REVISE\n\n- one\n- two\n- three",
                            }
                        ]
                    },
                ),
            ]
        }
        by_agent = {"agentA": {"input": 100, "output": 50, "cache_create": 0, "cache_read": 0}}
        rows = build_subagent_verdicts(main, agent_entries, by_agent)
        assert rows == [
            {
                "invocation_id": "agentA",
                "agent_id": "rbg",
                "verdict": "REVISE",
                "issues_count": 3,
                "tokens": 150,
            }
        ]

    def test_unparseable_message_yields_null_verdict(self):
        agent_entries = {
            "agentZ": [
                Entry(
                    type="assistant",
                    message={"content": [{"type": "text", "text": "Looks fine to me, no issues."}]},
                ),
            ]
        }
        rows = build_subagent_verdicts([], agent_entries, {})
        assert len(rows) == 1
        row = rows[0]
        assert row["invocation_id"] == "agentZ"
        assert row["verdict"] is None
        assert row["issues_count"] == 0
        assert row["tokens"] == 0
        assert row["agent_id"] is None

    def test_unmapped_invocation_keeps_invocation_id(self):
        # When the main entries don't expose a Task tool_use we can't recover
        # the subagent_type, but we still emit the row.
        agent_entries = {
            "orphan": [
                Entry(
                    type="assistant",
                    message={"content": [{"type": "text", "text": "APPROVE\n- nit"}]},
                ),
            ]
        }
        rows = build_subagent_verdicts([], agent_entries, {"orphan": {"input": 5, "output": 5}})
        assert rows == [
            {
                "invocation_id": "orphan",
                "agent_id": None,
                "verdict": "APPROVE",
                "issues_count": 1,
                "tokens": 10,
            }
        ]

    def test_multiple_invocations_preserve_order(self):
        main = [
            Entry(
                type="assistant",
                message={
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "Task",
                            "input": {"subagent_type": "rbg"},
                        },
                        {
                            "type": "tool_use",
                            "id": "t2",
                            "name": "Task",
                            "input": {"subagent_type": "marsha"},
                        },
                    ]
                },
            ),
            Entry(
                type="user",
                message={"content": [{"type": "tool_result", "tool_use_id": "t1"}]},
                tool_use_result={"agentId": "a1"},
            ),
            Entry(
                type="user",
                message={"content": [{"type": "tool_result", "tool_use_id": "t2"}]},
                tool_use_result={"agentId": "a2"},
            ),
        ]
        agent_entries = {
            "a1": [
                Entry(
                    type="assistant",
                    message={"content": [{"type": "text", "text": "APPROVE"}]},
                )
            ],
            "a2": [
                Entry(
                    type="assistant",
                    message={"content": [{"type": "text", "text": "FAIL\n- bad"}]},
                )
            ],
        }
        rows = build_subagent_verdicts(main, agent_entries, {})
        assert [r["agent_id"] for r in rows] == ["rbg", "marsha"]
        assert [r["verdict"] for r in rows] == ["APPROVE", "FAIL"]
        assert rows[1]["issues_count"] == 1


class TestUsageStatsIntegration:
    def test_to_token_metrics_includes_subagent_verdicts(self):
        from lib.transcript_parser import UsageStats

        stats = UsageStats()
        stats.subagent_verdicts = [
            {
                "invocation_id": "a1",
                "agent_id": "rbg",
                "verdict": "APPROVE",
                "issues_count": 0,
                "tokens": 1234,
            }
        ]
        metrics = stats.to_token_metrics()
        assert metrics["subagent_verdicts"] == stats.subagent_verdicts

    def test_to_token_metrics_default_is_empty_list(self):
        from lib.transcript_parser import UsageStats

        stats = UsageStats()
        metrics = stats.to_token_metrics()
        assert metrics["subagent_verdicts"] == []
