#!/usr/bin/env python3
"""Review how many LLM calls (incl. all subagents) it takes to answer a PKB question.

Implements the canonical question-boundary definition and LLM call attribution rules
established in PKB design note [[note_51ae72dc]] §2 and reviewed under [[aops_e4fc717c]].

Definitions
-----------
1. Initiating Boundary (T_prompt):
   An inbound user prompt submit span (name = 'aops-debug.UserPromptSubmit' or root
   'claude-code-turn' / root CHAIN). Filters out automated framework maintenance
   commands (/daily, /reconcile, /dispatch, /dump, /mine).

2. Terminal Boundary (T_complete):
   The terminal completion of that prompt turn in the same session, defined as
   max(T_reply) for all reply spans (mcp__plugin_ida-telegram_telegram__reply) emitted
   during that turn (clustered to eliminate multi-chunk double-counting), or the
   root turn's end_time, clamped before any subsequent prompt in the same session.

3. PKB Qualification:
   Between T_prompt and T_complete, the session or any subagent executes at least
   one PKB retrieval tool span (mcp.search, mcp.get_document, mcp.get_task,
   mcp.list_documents, mcp.list_tasks, mcp.export_graph, or pkb_* tools).

4. Attribution Rule:
   Attribution matches: session(L) == session(Q) AND T_prompt <= start_time(L) <= T_complete.
   Measures native claude_code.llm_request spans (splitting repl_main_thread vs
   agent.custom subagents) or general LLM spans (span_kind = 'LLM').

Configuration is flags or environment:
  --base-url or $PHOENIX_MCP_URL
  --project or $PHOENIX_MCP_PROJECT

Examples:
  uv run python phoenix_pkb_questions.py --since 24h
  uv run python phoenix_pkb_questions.py --start "2026-11-05 06:00:00+00:00" --end "2026-11-05 23:25:00+00:00"
  uv run python phoenix_pkb_questions.py --since 7d --channel telegram --format json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from typing import Any

BASE_URL_ENV_VAR = "PHOENIX_MCP_URL"
PROJECT_ENV_VAR = "PHOENIX_MCP_PROJECT"
_ACCESS_TOKEN_PAIRS = (("DISPATCHER_MCP_TOKEN_ID", "DISPATCHER_MCP_TOKEN_SECRET"),)
_MCP_SESSIONS: dict[str, str] = {}
HTTP_TIMEOUT = 120

EXIT_CONFIG = 2
EXIT_EMPTY = 1

EXCLUDED_COMMANDS = ("/daily", "/reconcile", "/dispatch", "/dump", "/mine")

PKB_TOOL_PATTERNS = (
    "mcp.search",
    "mcp.get_",
    "mcp.list_",
    "mcp.export_",
    "pkb_search",
    "pkb_get_",
    "pkb_list_",
    "pkb_code_mode",
)


class ConfigError(Exception):
    """A required input is missing or unusable."""


def parse_relative_or_iso(value: str) -> datetime:
    """Parse relative offsets like '24h', '7d', '14d', '30m' or ISO timestamps into UTC."""
    val = value.strip().lower()
    now = datetime.now(UTC)
    m = re.fullmatch(r"(\d+)\s*([mhdws])", val)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        if unit == "m":
            return now - timedelta(minutes=num)
        if unit == "h":
            return now - timedelta(hours=num)
        if unit == "d":
            return now - timedelta(days=num)
        if unit == "w":
            return now - timedelta(weeks=num)
        if unit == "s":
            return now - timedelta(seconds=num)

    text = value.strip().replace(" ", "T")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ConfigError(f"cannot parse time {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S+00:00")


def _mcp_headers(session_id: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {
        "User-Agent": "academicOps/0.10 (session-trace)",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    for id_var, secret_var in _ACCESS_TOKEN_PAIRS:
        cf_id = os.environ.get(id_var)
        cf_secret = os.environ.get(secret_var)
        if cf_id and cf_secret:
            headers["CF-Access-Client-Id"] = cf_id
            headers["CF-Access-Client-Secret"] = cf_secret
            break
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


def _mcp_init_session(mcp_url: str) -> str:
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "academicOps-session-trace", "version": "0.10"},
        },
    }
    request = urllib.request.Request(
        mcp_url,
        data=json.dumps(init_payload).encode("utf-8"),
        headers=_mcp_headers(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            session_id = response.headers.get("mcp-session-id")
            if not session_id:
                raise ConfigError(f"MCP initialize at {mcp_url} returned no mcp-session-id header")
            _MCP_SESSIONS[mcp_url] = session_id
            return session_id
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {mcp_url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {mcp_url}: {exc.reason}") from exc


def execute_sql(mcp_url: str, sql: str) -> dict[str, Any]:
    """Execute analytical SQL against Phoenix via MCP executeSql tool call."""
    session_id = _MCP_SESSIONS.get(mcp_url) or _mcp_init_session(mcp_url)
    clean_sql = " ".join(sql.strip().split())
    code = f'return await call_tool("executeSql", {json.dumps({"sql": clean_sql})})'
    call_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "phoenix_execute",
            "arguments": {"code": code},
        },
    }
    request = urllib.request.Request(
        mcp_url,
        data=json.dumps(call_payload).encode("utf-8"),
        headers=_mcp_headers(session_id),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            raw_body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise ConfigError(f"HTTP {exc.code} from {mcp_url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ConfigError(f"cannot reach {mcp_url}: {exc.reason}") from exc

    for line in raw_body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
                res = data.get("result", {})
                content = res.get("content", [])
                if content and isinstance(content[0], dict) and "text" in content[0]:
                    text = content[0]["text"]
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"raw": text}
                return res
            except json.JSONDecodeError:
                continue

    raise ConfigError(f"failed to extract SQL result from response: {raw_body[:400]}")


def query_pkb_qa_turns(
    mcp_url: str,
    start_time: datetime,
    end_time: datetime,
    channel: str = "all",
    session_filter: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Discover, qualify, and attribute LLM calls for PKB-answered questions in the time window."""
    t_start_iso = iso_utc(start_time)
    t_end_iso = iso_utc(end_time)
    extended_end_iso = iso_utc(end_time + timedelta(minutes=30))

    # Stage 1: Prompt Turns Discovery
    channel_cond = ""
    if channel == "telegram":
        channel_cond = (
            "AND (json_extract(s.attributes, '$.input.value') LIKE '%plugin:ida-telegram:telegram%' "
            "OR json_extract(s.attributes, '$.input.value') LIKE '%source=\"telegram\"%') "
        )

    session_cond = ""
    if session_filter:
        session_cond = f"AND json_extract(s.attributes, '$.session.id') LIKE '{session_filter}%' "

    sql_prompts = f"""
    SELECT 
        s.span_id,
        t.trace_id,
        s.start_time,
        s.end_time,
        json_extract(s.attributes, '$.session.id') as session_id,
        json_extract(s.attributes, '$.input.value') as input_val
    FROM spans s
    JOIN traces t ON s.trace_rowid = t.id
    WHERE s.name = 'aops-debug.UserPromptSubmit'
      AND s.start_time >= '{t_start_iso}'
      AND s.start_time <= '{t_end_iso}'
      {channel_cond}
      {session_cond}
    ORDER BY s.start_time
    LIMIT 5000
    """
    prompt_res = execute_sql(mcp_url, sql_prompts)
    if "error" in prompt_res:
        raise ConfigError(f"Phoenix SQL prompt query failed: {prompt_res['error']}")

    prompt_rows = prompt_res.get("rows", [])

    # Fetch Reply Spans within window
    sql_replies = f"""
    SELECT 
        s.span_id,
        s.start_time,
        s.end_time,
        json_extract(s.attributes, '$.session.id') as session_id
    FROM spans s
    WHERE s.name = 'mcp__plugin_ida-telegram_telegram__reply'
      AND s.start_time >= '{t_start_iso}'
      AND s.start_time <= '{extended_end_iso}'
    ORDER BY s.start_time
    LIMIT 5000
    """
    reply_res = execute_sql(mcp_url, sql_replies)
    reply_rows = reply_res.get("rows", []) if "error" not in reply_res else []

    replies_by_sid: dict[str, list[list[Any]]] = {}
    for r in reply_rows:
        replies_by_sid.setdefault(r[3], []).append(r)

    # Fetch root turn spans as fallback for CLI/non-telegram turns
    sql_turns = f"""
    SELECT 
        s.span_id,
        s.start_time,
        s.end_time,
        json_extract(s.attributes, '$.session.id') as session_id
    FROM spans s
    WHERE s.name = 'claude-code-turn'
      AND s.start_time >= '{t_start_iso}'
      AND s.start_time <= '{extended_end_iso}'
    ORDER BY s.start_time
    LIMIT 5000
    """
    turn_res = execute_sql(mcp_url, sql_turns)
    turn_rows = turn_res.get("rows", []) if "error" not in turn_res else []

    turns_by_sid: dict[str, list[list[Any]]] = {}
    for r in turn_rows:
        turns_by_sid.setdefault(r[3], []).append(r)

    # Group candidate prompt turns by session to bound by next prompt
    prompts_by_session: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str]] = set()

    for r in prompt_rows:
        span_id, trace_id, start_time_str, end_time_str, session_id, input_val = r
        try:
            parsed = json.loads(input_val) if input_val else {}
        except Exception:
            parsed = {}
        prompt_text = parsed.get("prompt", "") or input_val or ""
        prompt_id = parsed.get("prompt_id") or span_id

        m = re.search(r"<channel[^>]*>(.*?)</channel>", prompt_text, re.DOTALL)
        clean_text = m.group(1).strip() if m else prompt_text.strip()

        # Semantic Exclusion: maintenance commands
        if any(clean_text.startswith(cmd) for cmd in EXCLUDED_COMMANDS):
            continue

        key = (session_id, prompt_id if parsed.get("prompt_id") else start_time_str[:19])
        if key in seen:
            continue
        seen.add(key)

        prompts_by_session.setdefault(session_id, []).append(
            {
                "span_id": span_id,
                "trace_id": trace_id,
                "start_time_str": start_time_str,
                "clean_text": clean_text,
            }
        )

    candidate_turns: list[dict[str, Any]] = []

    for session_id, s_prompts in prompts_by_session.items():
        s_prompts.sort(key=lambda p: p["start_time_str"])
        sess_replies = replies_by_sid.get(session_id, [])
        sess_turns = turns_by_sid.get(session_id, [])

        for idx_p, p in enumerate(s_prompts):
            start_time_str = p["start_time_str"]
            next_start_time_str = (
                s_prompts[idx_p + 1]["start_time_str"] if idx_p + 1 < len(s_prompts) else None
            )

            # Candidate replies must start at or after this prompt, but before next prompt
            reps = [
                rep
                for rep in sess_replies
                if rep[1] >= start_time_str
                and (not next_start_time_str or rep[1] < next_start_time_str)
            ]
            t_complete = None
            if reps:
                t_complete = max(rep[2] for rep in reps)
            else:
                # Fall back to root turn span
                t_spans = [
                    ts
                    for ts in sess_turns
                    if ts[1] >= start_time_str
                    and (not next_start_time_str or ts[1] < next_start_time_str)
                ]
                if t_spans:
                    t_complete = t_spans[0][2]

            if not t_complete:
                continue

            candidate_turns.append(
                {
                    "idx": len(candidate_turns),
                    "session_id": session_id,
                    "start_time": start_time_str + "+00:00",
                    "end_time": t_complete + "+00:00",
                    "trace_id": p["trace_id"],
                    "prompt": p["clean_text"],
                }
            )

    if not candidate_turns:
        return [], {
            "total_questions": 0,
            "mean_calls": 0.0,
            "p50": 0,
            "p90": 0,
            "min_calls": 0,
            "max_calls": 0,
            "subagent_ratio": 0.0,
            "subagent_calls": 0,
            "main_calls": 0,
            "total_calls": 0,
            "in_tokens": 0,
            "out_tokens": 0,
        }

    # Stage 2: Batch check PKB tools for candidate turns using CTE VALUES join
    batch_size = 10
    qualifying_turns: list[dict[str, Any]] = []

    for i in range(0, len(candidate_turns), batch_size):
        batch = candidate_turns[i : i + batch_size]
        vals = ", ".join(
            f"({t['idx']}, '{t['session_id']}', '{t['start_time']}', '{t['end_time']}')"
            for t in batch
        )
        tool_pattern_clauses = " OR ".join(f"s.name LIKE '%{p}%'" for p in PKB_TOOL_PATTERNS)
        sql = f"""
        WITH turns(id, sid, t0, t1) AS (VALUES {vals})
        SELECT t.id, count(DISTINCT s.span_id) as tool_count, group_concat(DISTINCT s.name) as tools
        FROM turns t
        JOIN spans s ON json_extract(s.attributes, '$.session.id') = t.sid
          AND s.start_time >= t.t0 AND s.start_time <= t.t1
        WHERE ({tool_pattern_clauses})
        GROUP BY t.id
        """
        tool_res = execute_sql(mcp_url, sql)
        for row in tool_res.get("rows", []):
            turn_idx = row[0]
            t = candidate_turns[turn_idx]
            t["tools"] = row[2]
            qualifying_turns.append(t)

    if not qualifying_turns:
        return [], {
            "total_questions": 0,
            "mean_calls": 0.0,
            "p50": 0,
            "p90": 0,
            "min_calls": 0,
            "max_calls": 0,
            "subagent_ratio": 0.0,
            "subagent_calls": 0,
            "main_calls": 0,
            "total_calls": 0,
            "in_tokens": 0,
            "out_tokens": 0,
        }

    # Stage 3: LLM calls rollup for qualifying turns using CTE VALUES join
    for i in range(0, len(qualifying_turns), batch_size):
        batch = qualifying_turns[i : i + batch_size]
        vals = ", ".join(
            f"({t['idx']}, '{t['session_id']}', '{t['start_time']}', '{t['end_time']}')"
            for t in batch
        )
        sql = f"""
        WITH turns(id, sid, t0, t1) AS (VALUES {vals})
        SELECT 
            t.id,
            count(DISTINCT s.span_id) as total_llm,
            count(DISTINCT CASE WHEN s.name = 'claude_code.llm_request' THEN s.span_id END) as native_llm,
            count(DISTINCT CASE WHEN json_extract(s.attributes, '$.query_source_safe') = 'agent.custom' THEN s.span_id END) as subagent_llm,
            sum(coalesce(s.llm_token_count_prompt, 0)) as in_tokens,
            sum(coalesce(s.llm_token_count_completion, 0)) as out_tokens
        FROM turns t
        JOIN spans s ON json_extract(s.attributes, '$.session.id') = t.sid
          AND s.start_time >= t.t0 AND s.start_time <= t.t1
        WHERE (s.name = 'claude_code.llm_request' OR s.span_kind = 'LLM')
        GROUP BY t.id
        """
        llm_res = execute_sql(mcp_url, sql)
        for row in llm_res.get("rows", []):
            turn_idx = row[0]
            for t in batch:
                if t["idx"] == turn_idx:
                    t["total_llm"] = row[1]
                    t["native_llm"] = row[2]
                    t["subagent_llm"] = row[3]
                    t["in_tokens"] = row[4] or 0
                    t["out_tokens"] = row[5] or 0
                    break

    # Format question rows
    rows: list[dict[str, Any]] = []
    all_calls: list[int] = []

    for q in qualifying_turns:
        calls = q.get("native_llm") or q.get("total_llm", 0)
        sub = q.get("subagent_llm", 0)
        main = max(calls - sub, 0)
        all_calls.append(calls)

        rows.append(
            {
                "session_id": q["session_id"],
                "trace_id": q["trace_id"],
                "start_time": q["start_time"],
                "end_time": q["end_time"],
                "prompt": q["prompt"],
                "llm_calls": calls,
                "subagent_calls": sub,
                "main_calls": main,
                "tools": q.get("tools", ""),
                "in_tokens": q.get("in_tokens", 0),
                "out_tokens": q.get("out_tokens", 0),
            }
        )

    all_calls_sorted = sorted(all_calls)
    n = len(all_calls_sorted)
    mean_calls = sum(all_calls_sorted) / n if n else 0.0
    p50 = all_calls_sorted[n // 2] if n else 0
    p90_idx = int(0.9 * n)
    p90 = all_calls_sorted[min(p90_idx, n - 1)] if n else 0
    min_calls = all_calls_sorted[0] if n else 0
    max_calls = all_calls_sorted[-1] if n else 0

    total_sub = sum(r["subagent_calls"] for r in rows)
    total_calls = sum(all_calls)
    sub_ratio = round((total_sub / total_calls * 100), 1) if total_calls else 0.0
    total_in = sum(r["in_tokens"] for r in rows)
    total_out = sum(r["out_tokens"] for r in rows)

    summary = {
        "total_questions": n,
        "mean_calls": round(mean_calls, 1),
        "p50": p50,
        "p90": p90,
        "min_calls": min_calls,
        "max_calls": max_calls,
        "subagent_ratio": sub_ratio,
        "main_ratio": round(100.0 - sub_ratio, 1) if total_calls else 0.0,
        "subagent_calls": total_sub,
        "main_calls": total_calls - total_sub,
        "total_calls": total_calls,
        "in_tokens": total_in,
        "out_tokens": total_out,
    }

    return rows, summary


def print_table(
    rows: list[dict[str, Any]], summary: dict[str, Any], start_time: datetime, end_time: datetime
) -> None:
    print(
        f"\n┌{'─' * 76}┐\n"
        f"│ PKB Q&A EFFICIENCY ({start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC){' ' * (76 - 44 - len(start_time.strftime('%Y-%m-%d %H:%M')) - len(end_time.strftime('%Y-%m-%d %H:%M')))}│\n"
        f"├{'─' * 76}┤\n"
        f"│   {summary['mean_calls']:<4.1f} LLM Calls / Question{' ' * 50}│\n"
        f"│   P50: {summary['p50']:<2} | P90: {summary['p90']:<2} | Min/Max: {summary['min_calls']}/{summary['max_calls']:<2} | Questions: {summary['total_questions']:<3}{' ' * 28}│\n"
        f"│   ■ Subagent Compute: {summary['subagent_ratio']:<4.1f}%   ■ Main Thread: {summary['main_ratio']:<4.1f}%{' ' * 27}│\n"
        f"└{'─' * 76}┘\n"
    )

    if not rows:
        print("No PKB questions answered in the specified window.")
        return

    print(
        f"{'#':<3} {'Time Window (UTC)':<19} {'Session':<9} {'Calls':<6} {'Sub':<4} {'Main':<5} {'PKB Tools':<16} {'Prompt Preview'}"
    )
    print(f"{'-' * 3} {'-' * 19} {'-' * 9} {'-' * 6} {'-' * 4} {'-' * 5} {'-' * 16} {'-' * 30}")

    for idx, r in enumerate(rows, 1):
        t_span = f"{r['start_time'][11:16]} → {r['end_time'][11:16]}"
        sid = r["session_id"][:8]
        calls = r["llm_calls"]
        sub = r["subagent_calls"]
        main = r["main_calls"]
        tools = r["tools"].split(",")[0] if r["tools"] else ""
        prompt = r["prompt"].replace("\n", " ")[:30]
        print(f"{idx:<3} {t_span:<19} {sid:<9} {calls:<6} {sub:<4} {main:<5} {tools:<16} {prompt}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query Phoenix for LLM calls per PKB-answered question."
    )
    parser.add_argument(
        "--since", default="24h", help="Start time or duration (e.g. 24h, 7d, or ISO datetime)"
    )
    parser.add_argument("--until", "--end", help="End time (ISO datetime, defaults to now UTC)")
    parser.add_argument("--start", help="Alias for --since")
    parser.add_argument(
        "--channel",
        choices=["all", "telegram"],
        default="all",
        help="Filter prompt channel (default: all)",
    )
    parser.add_argument("--session", help="Filter by specific session ID prefix")
    parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format (table or json)"
    )
    parser.add_argument("--base-url", help=f"Phoenix base URL (or ${BASE_URL_ENV_VAR})")
    parser.add_argument("--project", help=f"Phoenix project (or ${PROJECT_ENV_VAR})")

    args = parser.parse_args()

    mcp_url = (args.base_url or os.environ.get(BASE_URL_ENV_VAR, "")).strip()
    if not mcp_url:
        print(
            f"error: no Phoenix MCP URL. Pass --base-url or set {BASE_URL_ENV_VAR}", file=sys.stderr
        )
        return EXIT_CONFIG

    start_raw = args.start or args.since
    try:
        start_time = parse_relative_or_iso(start_raw)
        end_time = parse_relative_or_iso(args.until) if args.until else datetime.now(UTC)
    except ConfigError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_CONFIG

    if start_time > end_time:
        print("error: --start must be before --end", file=sys.stderr)
        return EXIT_CONFIG

    try:
        rows, summary = query_pkb_qa_turns(
            mcp_url,
            start_time,
            end_time,
            channel=args.channel,
            session_filter=args.session,
        )
    except ConfigError as err:
        print(f"error: {err}", file=sys.stderr)
        return EXIT_CONFIG
    except Exception as exc:
        print(f"error: unexpected query failure: {exc}", file=sys.stderr)
        return EXIT_CONFIG

    if args.format == "json":
        payload = {
            "window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "channel": args.channel,
            },
            "summary": summary,
            "questions": rows,
        }
        print(json.dumps(payload, indent=2))
    else:
        print_table(rows, summary, start_time, end_time)

    return 0


if __name__ == "__main__":
    sys.exit(main())
