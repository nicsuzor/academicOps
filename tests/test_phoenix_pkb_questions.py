"""test_phoenix_pkb_questions.py: parse relative offsets, boundaries, and metric aggregations."""

import importlib.util
import json
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
    t30m = pkbq.parse_relative_or_iso("30m")
    assert abs((now - timedelta(minutes=30) - t30m).total_seconds()) < 5

    t24h = pkbq.parse_relative_or_iso("24h")
    assert abs((now - timedelta(hours=24) - t24h).total_seconds()) < 5

    t7d = pkbq.parse_relative_or_iso("7d")
    assert abs((now - timedelta(days=7) - t7d).total_seconds()) < 5

    t2w = pkbq.parse_relative_or_iso("2w")
    assert abs((now - timedelta(weeks=2) - t2w).total_seconds()) < 5

    t45s = pkbq.parse_relative_or_iso("45s")
    assert abs((now - timedelta(seconds=45) - t45s).total_seconds()) < 5

    t_iso = pkbq.parse_relative_or_iso("2026-11-05T06:00:00Z")
    assert t_iso.year == 2026
    assert t_iso.month == 11
    assert t_iso.day == 5
    assert t_iso.hour == 6

    with pytest.raises(pkbq.ConfigError):
        pkbq.parse_relative_or_iso("invalid-timestamp")


def test_query_pkb_qa_turns_mocked():
    session_id = "00000000-0000-0000-0000-000000000001"
    trace_id = "00000000000000000000000000000001"

    # Mock execute_sql to return staged rows
    def mock_exec_sql(mcp_url: str, sql: str):
        if "s.name = 'aops-debug.UserPromptSubmit'" in sql:
            return {
                "rows": [
                    [
                        "span_p1",
                        trace_id,
                        "2026-11-05 06:30:00.000000",
                        "2026-11-05 06:30:00.000000",
                        session_id,
                        '{"prompt": "<channel source=\\"plugin:ida-telegram:telegram\\">how does x work?</channel>", "prompt_id": "pr_1"}',
                    ]
                ]
            }
        elif "s.name = 'mcp__plugin_ida-telegram_telegram__reply'" in sql:
            return {
                "rows": [
                    [
                        "span_r1",
                        "2026-11-05 06:30:20.000000",
                        "2026-11-05 06:30:25.000000",
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
            "http://localhost:8080/mcp", t_start, t_end, channel="telegram"
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
        assert summary["main_ratio"] == 100.0


def test_empty_results_and_table_format(capsys):
    t_start = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
    t_end = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)

    # Empty candidate turns
    with patch.object(pkbq, "execute_sql", return_value={"rows": []}):
        rows, summary = pkbq.query_pkb_qa_turns("http://localhost:8080/mcp", t_start, t_end)
        assert rows == []
        assert "main_ratio" in summary
        assert summary["main_ratio"] == 0.0
        assert summary["subagent_ratio"] == 0.0

        # Must not raise KeyError
        pkbq.print_table(rows, summary, t_start, t_end)
        captured = capsys.readouterr()
        assert "No PKB questions answered in the specified window." in captured.out
        assert "PKB Q&A EFFICIENCY" in captured.out

    # Candidate turns present but none qualify with PKB tools
    def mock_no_qualifying_sql(mcp_url: str, sql: str):
        if "s.name = 'aops-debug.UserPromptSubmit'" in sql:
            return {
                "rows": [
                    [
                        "span_p1",
                        "00000000000000000000000000000001",
                        "2026-11-05 06:30:00.000000",
                        "2026-11-05 06:30:00.000000",
                        "00000000-0000-0000-0000-000000000001",
                        '{"prompt": "plain question", "prompt_id": "pr_1"}',
                    ]
                ]
            }
        elif "s.name = 'claude-code-turn'" in sql:
            return {
                "rows": [
                    [
                        "span_t1",
                        "2026-11-05 06:30:00.000000",
                        "2026-11-05 06:30:30.000000",
                        "00000000-0000-0000-0000-000000000001",
                    ]
                ]
            }
        return {"rows": []}

    with patch.object(pkbq, "execute_sql", side_effect=mock_no_qualifying_sql):
        rows, summary = pkbq.query_pkb_qa_turns("http://localhost:8080/mcp", t_start, t_end)
        assert rows == []
        assert "main_ratio" in summary
        assert summary["main_ratio"] == 0.0
        pkbq.print_table(rows, summary, t_start, t_end)
        captured = capsys.readouterr()
        assert "No PKB questions answered in the specified window." in captured.out


def test_excluded_prompts():
    executed_sqls = []

    def mock_exec_sql(mcp_url: str, sql: str):
        executed_sqls.append(sql)
        if "s.name = 'aops-debug.UserPromptSubmit'" in sql:
            return {
                "rows": [
                    [
                        "s1",
                        "t1",
                        "2026-11-05 06:00:00",
                        "2026-11-05 06:00:00",
                        "sid1",
                        '{"prompt": "/daily note"}',
                    ],
                    [
                        "s2",
                        "t2",
                        "2026-11-05 06:01:00",
                        "2026-11-05 06:01:00",
                        "sid1",
                        '{"prompt": "/reconcile now"}',
                    ],
                    [
                        "s3",
                        "t3",
                        "2026-11-05 06:02:00",
                        "2026-11-05 06:02:00",
                        "sid1",
                        '{"prompt": "<task-notification> task-123"}',
                    ],
                    [
                        "s4",
                        "t4",
                        "2026-11-05 06:03:00",
                        "2026-11-05 06:03:00",
                        "sid1",
                        '{"prompt": "reacted 👍 to 42"}',
                    ],
                ]
            }
        return {"rows": []}

    with patch.object(pkbq, "execute_sql", side_effect=mock_exec_sql):
        t_start = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
        t_end = datetime(2026, 11, 5, 7, 0, tzinfo=UTC)
        rows, summary = pkbq.query_pkb_qa_turns("http://localhost:8080/mcp", t_start, t_end)
        # All 4 prompts should be excluded
        assert rows == []
        assert summary["total_questions"] == 0


def test_project_filtering():
    captured_sqls = []

    def mock_exec_sql(mcp_url: str, sql: str):
        captured_sqls.append(sql)
        return {"rows": []}

    with patch.object(pkbq, "execute_sql", side_effect=mock_exec_sql):
        t_start = datetime(2026, 11, 5, 6, 0, tzinfo=UTC)
        t_end = datetime(2026, 11, 5, 7, 0, tzinfo=UTC)
        pkbq.query_pkb_qa_turns("http://localhost:8080/mcp", t_start, t_end, project="academicops")

        prompt_sql = next(s for s in captured_sqls if "aops-debug.UserPromptSubmit" in s)
        assert "JOIN projects p ON p.id = t.project_rowid" in prompt_sql
        assert "p.name = 'academicops'" in prompt_sql


def test_cli_main_table_and_json(capsys, monkeypatch):
    mock_summary = {
        "total_questions": 1,
        "mean_calls": 2.0,
        "p50": 2,
        "p90": 2,
        "min_calls": 2,
        "max_calls": 2,
        "subagent_ratio": 50.0,
        "main_ratio": 50.0,
        "subagent_calls": 1,
        "main_calls": 1,
        "total_calls": 2,
        "in_tokens": 100,
        "out_tokens": 50,
    }
    mock_rows = [
        {
            "session_id": "00000000-0000-0000-0000-000000000001",
            "trace_id": "00000000000000000000000000000001",
            "start_time": "2026-11-05 06:00:00+00:00",
            "end_time": "2026-11-05 06:01:00+00:00",
            "prompt": "what is x?",
            "llm_calls": 2,
            "subagent_calls": 1,
            "main_calls": 1,
            "tools": "mcp.search",
            "in_tokens": 100,
            "out_tokens": 50,
        }
    ]

    with patch.object(pkbq, "query_pkb_qa_turns", return_value=(mock_rows, mock_summary)):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "phoenix_pkb_questions.py",
                "--base-url",
                "http://localhost:8080/mcp",
                "--since",
                "24h",
                "--project",
                "aops",
                "--format",
                "table",
            ],
        )
        assert pkbq.main() == 0
        captured = capsys.readouterr()
        assert "PKB Q&A EFFICIENCY" in captured.out
        assert "what is x?" in captured.out

        # JSON format
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "phoenix_pkb_questions.py",
                "--base-url",
                "http://localhost:8080/mcp",
                "--since",
                "24h",
                "--format",
                "json",
            ],
        )
        assert pkbq.main() == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["summary"]["total_questions"] == 1
        assert len(data["questions"]) == 1

    # Empty rows in table format returns EXIT_EMPTY
    with patch.object(
        pkbq, "query_pkb_qa_turns", return_value=([], {**mock_summary, "total_questions": 0})
    ):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "phoenix_pkb_questions.py",
                "--base-url",
                "http://localhost:8080/mcp",
                "--format",
                "table",
            ],
        )
        assert pkbq.main() == pkbq.EXIT_EMPTY


def test_cli_main_errors(monkeypatch):
    # Missing base-url
    monkeypatch.delenv("PHOENIX_MCP_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["phoenix_pkb_questions.py"])
    assert pkbq.main() == pkbq.EXIT_CONFIG

    # Invalid timestamp
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phoenix_pkb_questions.py",
            "--base-url",
            "http://localhost:8080/mcp",
            "--start",
            "invalid-time",
        ],
    )
    assert pkbq.main() == pkbq.EXIT_CONFIG

    # start > end
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phoenix_pkb_questions.py",
            "--base-url",
            "http://localhost:8080/mcp",
            "--start",
            "2026-11-06T00:00:00Z",
            "--until",
            "2026-11-05T00:00:00Z",
        ],
    )
    assert pkbq.main() == pkbq.EXIT_CONFIG
