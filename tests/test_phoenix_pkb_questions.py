"""test_phoenix_pkb_questions.py: parse relative offsets, boundaries, and metric aggregations."""

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "plugins/ida/skills/session-trace/scripts"
sys.path.insert(0, str(SCRIPTS))
_spec = importlib.util.spec_from_file_location(
    "phoenix_pkb_questions", SCRIPTS / "phoenix_pkb_questions.py"
)
pkbq = importlib.util.module_from_spec(_spec)
sys.modules["phoenix_pkb_questions"] = pkbq
_spec.loader.exec_module(pkbq)


def test_parse_relative_or_iso():
    now = datetime.now(UTC)
    t24h = pkbq.parse_relative_or_iso("24h")
    assert abs((now - timedelta(hours=24) - t24h).total_seconds()) < 5

    t7d = pkbq.parse_relative_or_iso("7d")
    assert abs((now - timedelta(days=7) - t7d).total_seconds()) < 5

    t_iso = pkbq.parse_relative_or_iso("2026-11-05T06:00:00Z")
    assert t_iso.year == 2026
    assert t_iso.month == 11
    assert t_iso.day == 5
    assert t_iso.hour == 6

    with pytest.raises(pkbq.ConfigError):
        pkbq.parse_relative_or_iso("invalid-timestamp")


def test_query_pkb_qa_turns_mocked():
    session_id = "ba234716-1508-48be-b2ef-c30a13cb01dc"
    trace_id = "1a959c3fa10308e0de2c02f1dd18a330"

    # Mock execute_sql to return staged rows
    def mock_exec_sql(mcp_url: str, sql: str):
        if "s.name = 'aops-debug.UserPromptSubmit'" in sql:
            return {
                "rows": [
                    [
                        "span_p1",
                        trace_id,
                        "2026-11-05 06:29:30.719257",
                        "2026-11-05 06:29:30.719257",
                        session_id,
                        '{"prompt": "<channel source=\\"plugin:ida-telegram:telegram\\">summarise what you\'re up to</channel>", "prompt_id": "pr_1"}',
                    ]
                ]
            }
        elif "s.name = 'mcp__plugin_ida-telegram_telegram__reply'" in sql:
            return {
                "rows": [
                    [
                        "span_r1",
                        "2026-11-05 06:29:50.509023",
                        "2026-11-05 06:29:52.183806",
                        session_id,
                    ]
                ]
            }
        elif "s.name = 'claude-code-turn'" in sql:
            return {"rows": []}
        elif "tool_count" in sql:
            return {"rows": [[0, 1, "mcp.search"]]}
        elif "native_llm" in sql:
            return {"rows": [[0, 3, 3, 0, 120000, 1000]]}
        return {"rows": []}

    with patch.object(pkbq, "execute_sql", side_effect=mock_exec_sql):
        t_start = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
        t_end = datetime(2026, 11, 5, 23, 25, tzinfo=UTC)
        rows, summary = pkbq.query_pkb_qa_turns(
            "https://mcp.suzor.com/mcp", t_start, t_end, channel="telegram"
        )

        assert len(rows) == 1
        q = rows[0]
        assert q["session_id"] == session_id
        assert q["llm_calls"] == 3
        assert q["subagent_calls"] == 0
        assert q["main_calls"] == 3
        assert summary["total_questions"] == 1
        assert summary["mean_calls"] == 3.0
        assert summary["subagent_ratio"] == 0.0
