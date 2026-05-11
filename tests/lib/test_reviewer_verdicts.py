"""Tests for the reviewer verdict parser (Build B of Safeguard ROI v0).

The contract is now strict: agents must emit a structured trailer using
HTML-comment markers. Anything else parses as ``None`` (fail-open). This
removes the regex-over-prose extraction the earlier iteration used and
which violated the No Shitty NLP axiom (issue #917).
"""

from lib.reviewer_verdicts import (
    build_subagent_verdicts,
    extract_issues_count,
    extract_verdict,
    last_assistant_text,
)
from lib.transcript_parser import Entry


class TestExtractVerdict:
    def test_canonical_marker(self):
        text = "## Verdict\n\nOverall: APPROVE\n\n<!-- aops-verdict: APPROVE -->\n"
        assert extract_verdict(text) == "APPROVE"

    def test_lowercase_value_normalises(self):
        # The marker syntax accepts any case but the canonicalisation
        # is uppercase. Reviewers that accidentally lowercase the token
        # still resolve to the canonical form.
        assert extract_verdict("<!-- aops-verdict: revise -->") == "REVISE"

    def test_marker_anywhere_in_message(self):
        text = (
            "Long preamble.\n\n"
            "Lots of analysis with the word APPROVE and even **Verdict: FAIL** in prose.\n\n"
            "<!-- aops-verdict: ESCALATE -->\n"
        )
        assert extract_verdict(text) == "ESCALATE"

    def test_first_marker_wins(self):
        text = "<!-- aops-verdict: APPROVE -->\n<!-- aops-verdict: FAIL -->\n"
        assert extract_verdict(text) == "APPROVE"

    def test_unknown_token_yields_none(self):
        # The marker is present but the value is not in VERDICT_TOKENS —
        # the parser returns None rather than guessing.
        assert extract_verdict("<!-- aops-verdict: OK -->") is None

    def test_prose_without_marker_yields_none(self):
        # Earlier regex would have extracted from `**Verdict: APPROVE**`
        # in prose. The strict contract refuses to: no marker, no verdict.
        assert extract_verdict("**Verdict: APPROVE** — looks fine.") is None

    def test_markdown_decoration_around_marker_rejected(self):
        # The marker must occupy its own line with no decoration.
        # Embedding it inside other markdown breaks the contract.
        assert extract_verdict("> <!-- aops-verdict: APPROVE -->") is None
        assert extract_verdict("**<!-- aops-verdict: APPROVE -->**") is None

    def test_empty_text(self):
        assert extract_verdict("") is None
        assert extract_verdict(None) is None  # type: ignore[arg-type]

    def test_whitespace_around_marker_tolerated(self):
        assert extract_verdict("   <!--   aops-verdict:  PASS   -->  \n") == "PASS"


class TestExtractIssuesCount:
    def test_canonical_marker(self):
        assert extract_issues_count("<!-- aops-issues: 3 -->") == 3

    def test_zero_is_valid(self):
        assert extract_issues_count("<!-- aops-issues: 0 -->") == 0

    def test_no_marker_returns_none(self):
        # Distinct from "0 issues": absence means we couldn't determine.
        assert extract_issues_count("Some review prose without the marker") is None

    def test_negative_or_non_integer_rejected(self):
        # The marker regex requires \d+, so non-digits never match.
        assert extract_issues_count("<!-- aops-issues: -1 -->") is None
        assert extract_issues_count("<!-- aops-issues: many -->") is None

    def test_first_marker_wins(self):
        text = "<!-- aops-issues: 7 -->\n<!-- aops-issues: 2 -->\n"
        assert extract_issues_count(text) == 7

    def test_empty_text(self):
        assert extract_issues_count("") is None


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
        # fall back to the prior assistant text.
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
                                "text": (
                                    "## Verdict\n\nOverall: REVISE\n\n"
                                    "<!-- aops-verdict: REVISE -->\n"
                                    "<!-- aops-issues: 3 -->\n"
                                ),
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

    def test_unparseable_message_yields_null_fields(self):
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
        assert row["issues_count"] is None
        assert row["tokens"] == 0
        assert row["agent_id"] is None

    def test_unmapped_invocation_keeps_invocation_id(self):
        agent_entries = {
            "orphan": [
                Entry(
                    type="assistant",
                    message={
                        "content": [
                            {
                                "type": "text",
                                "text": "<!-- aops-verdict: APPROVE -->\n<!-- aops-issues: 1 -->\n",
                            }
                        ]
                    },
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
                    message={
                        "content": [
                            {
                                "type": "text",
                                "text": "<!-- aops-verdict: APPROVE -->\n<!-- aops-issues: 0 -->\n",
                            }
                        ]
                    },
                )
            ],
            "a2": [
                Entry(
                    type="assistant",
                    message={
                        "content": [
                            {
                                "type": "text",
                                "text": "<!-- aops-verdict: FAIL -->\n<!-- aops-issues: 1 -->\n",
                            }
                        ]
                    },
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


class TestRemapByAgentKeys:
    """aops-eaf402f5: by_agent UUIDs must resolve to subagent names."""

    def test_known_uuid_resolves_to_subagent_name(self):
        from lib.transcript_parser import _remap_by_agent_keys

        by_agent = {
            "main": {"input": 100, "output": 50, "cache_create": 0, "cache_read": 0},
            "ababa0cf498c0ed61": {"input": 20, "output": 10, "cache_create": 0, "cache_read": 0},
        }
        type_index = {"ababa0cf498c0ed61": "rbg"}
        remapped = _remap_by_agent_keys(by_agent, type_index)
        assert set(remapped.keys()) == {"main", "rbg"}
        assert remapped["rbg"]["input"] == 20

    def test_unknown_uuid_falls_back_to_uuid(self):
        """Acceptance: unknown agents fall back to UUID rather than crashing."""
        from lib.transcript_parser import _remap_by_agent_keys

        by_agent = {"main": {"input": 1, "output": 1, "cache_create": 0, "cache_read": 0}}
        by_agent["orphan-hash"] = {"input": 5, "output": 5, "cache_create": 0, "cache_read": 0}
        remapped = _remap_by_agent_keys(by_agent, type_index={})
        assert "orphan-hash" in remapped

    def test_duplicate_invocations_sum(self):
        from lib.transcript_parser import _remap_by_agent_keys

        by_agent = {
            "uuid1": {"input": 10, "output": 5, "cache_create": 0, "cache_read": 0},
            "uuid2": {"input": 20, "output": 15, "cache_create": 0, "cache_read": 0},
        }
        type_index = {"uuid1": "rbg", "uuid2": "rbg"}
        remapped = _remap_by_agent_keys(by_agent, type_index)
        assert set(remapped.keys()) == {"rbg"}
        assert remapped["rbg"]["input"] == 30
        assert remapped["rbg"]["output"] == 20

    def test_main_is_never_remapped(self):
        from lib.transcript_parser import _remap_by_agent_keys

        by_agent = {"main": {"input": 1, "output": 1, "cache_create": 0, "cache_read": 0}}
        # Adversarial: type_index claims "main" maps elsewhere — must be ignored.
        remapped = _remap_by_agent_keys(by_agent, type_index={"main": "rbg"})
        assert "main" in remapped
        assert "rbg" not in remapped
