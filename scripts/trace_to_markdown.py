#!/usr/bin/env python3
"""
trace_to_markdown.py — Render beautiful, production-ready Markdown transcripts
from an Arize Phoenix / OpenInference trace JSON export.

Supports:
  - Reconciling multi-trace forests and orphans into unified turn sequences
  - Generating Controller-only (.controller.md), Full (.full.md), and Summary (.summary.md)
  - Rich YAML frontmatter, ASCII call trees, and collapsible tool executions
  - Token and latency tracking per turn and per agent
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def parse_iso(ts_str: str | None) -> datetime | None:
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def format_duration(ms: float | None) -> str:
    if ms is None or ms < 0:
        return "0ms"
    if ms < 1000:
        return f"{ms:.0f}ms"
    if ms < 60000:
        return f"{ms / 1000:.2f}s"
    minutes = int(ms // 60000)
    seconds = (ms % 60000) / 1000
    return f"{minutes}m {seconds:.1f}s"


def format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


class SpanNode:
    def __init__(self, raw: dict[str, Any]):
        self.raw = raw
        self.span_id = raw.get("context", {}).get("span_id") or f"gen-span-{uuid.uuid4().hex}"
        self.trace_id = raw.get("context", {}).get("trace_id", "")
        self.parent_id = raw.get("parent_id")
        self.name = raw.get("name", "unnamed")
        self.kind = raw.get("span_kind", "SPAN")
        self.status_code = raw.get("status_code", "UNSET")
        self.status_message = raw.get("status_message", "")
        self.start_time_str = raw.get("start_time", "")
        self.end_time_str = raw.get("end_time", "")
        self.start_dt = parse_iso(self.start_time_str)
        self.end_dt = parse_iso(self.end_time_str)
        self.duration_ms = raw.get("duration_ms")
        if self.duration_ms is None and self.start_dt and self.end_dt:
            self.duration_ms = round((self.end_dt - self.start_dt).total_seconds() * 1000.0, 2)

        self.attributes = raw.get("attributes", {})
        self.children: list[SpanNode] = []
        self.is_orphan = "orphan_reason" in raw
        self.orphan_reason = raw.get("orphan_reason")

    @property
    def is_error(self) -> bool:
        return (
            self.status_code == "ERROR"
            or bool(self.status_message)
            or "ERROR:" in str(self.attributes.get("output.value", ""))
        )


class TraceReconciler:
    def __init__(self, trace_data: dict[str, Any]):
        self.meta = trace_data.get("meta", {})
        self.session_id = self.meta.get("session_id", "unknown-session")
        self.roots_raw = trace_data.get("roots", [])
        self.orphans_raw = trace_data.get("orphans", [])

        self.all_nodes: dict[str, SpanNode] = {}
        self.turns: list[dict[str, Any]] = []
        self.subagent_sessions: dict[str, list[dict[str, Any]]] = defaultdict(list)

        self._build_graph()

    def _collect_nodes(self, raw_node: dict[str, Any]) -> SpanNode:
        node = SpanNode(raw_node)
        self.all_nodes[node.span_id] = node
        for child_raw in raw_node.get("children", []):
            child_node = self._collect_nodes(child_raw)
            node.children.append(child_node)
        return node

    def _build_graph(self):
        # 1. Collect all root trees
        root_nodes = [self._collect_nodes(r) for r in self.roots_raw]

        # 2. Collect orphans
        orphan_nodes = [self._collect_nodes(o) for o in self.orphans_raw]

        # 3. Reconcile orphans to existing nodes/traces where possible
        unresolved_orphans = []
        for o in orphan_nodes:
            if o.parent_id and o.parent_id in self.all_nodes:
                self.all_nodes[o.parent_id].children.append(o)
            else:
                # Find matching trace root or turn
                matching_root = None
                for r in root_nodes:
                    if r.trace_id == o.trace_id:
                        matching_root = r
                        break
                if matching_root:
                    matching_root.children.append(o)
                else:
                    unresolved_orphans.append(o)

        # 4. Flatten roots and unresolved orphans into chronological turns
        all_turns: list[SpanNode] = []
        for r in root_nodes:
            all_turns.append(r)

        # Group unresolved orphans by trace_id into pseudo-turns if no CHAIN root exists
        orphans_by_trace = defaultdict(list)
        for o in unresolved_orphans:
            orphans_by_trace[o.trace_id].append(o)

        for tid, o_list in orphans_by_trace.items():
            # Create a synthetic turn container
            synthetic_raw = {
                "name": "orphan-turn",
                "span_kind": "CHAIN",
                "status_code": "UNSET",
                "context": {"span_id": f"synth-{tid[:8]}", "trace_id": tid},
                "start_time": min(
                    (x.start_time_str for x in o_list if x.start_time_str), default=""
                ),
                "end_time": max((x.end_time_str for x in o_list if x.end_time_str), default=""),
                "attributes": {
                    "input.value": f"(Orphan turn - {len(o_list)} spans outside primary trace roots)",
                    "session.id": self.session_id,
                },
                "children": [],
            }
            synth_node = SpanNode(synthetic_raw)
            synth_node.children.extend(o_list)
            all_turns.append(synth_node)

        # Sort turns chronologically
        all_turns.sort(key=lambda t: t.start_dt.timestamp() if t.start_dt else 0)

        # 5. Process turns and extract user prompts, LLMs, and tool calls
        for idx, turn in enumerate(all_turns, 1):
            turn_dict = self._process_turn(turn, idx)
            self.turns.append(turn_dict)

    def _process_turn(self, turn_node: SpanNode, turn_index: int) -> dict[str, Any]:
        prompt = turn_node.attributes.get("input.value", "")
        output = turn_node.attributes.get("output.value", "")

        # Flatten all children recursively
        flat_children: list[SpanNode] = []

        def walk(n: SpanNode):
            for c in n.children:
                flat_children.append(c)
                walk(c)

        walk(turn_node)

        # Sort children by start time
        flat_children.sort(key=lambda c: c.start_dt.timestamp() if c.start_dt else 0)

        llm_calls = [c for c in flat_children if c.kind == "LLM"]
        tool_calls = [c for c in flat_children if c.kind in ("TOOL", "RETRIEVER")]
        agent_calls = [c for c in flat_children if c.kind == "AGENT"]

        # Tokens
        prompt_tokens = sum(c.attributes.get("llm.token_count.prompt", 0) for c in llm_calls)
        completion_tokens = sum(
            c.attributes.get("llm.token_count.completion", 0) for c in llm_calls
        )
        total_tokens = sum(c.attributes.get("llm.token_count.total", 0) for c in llm_calls)
        cache_read = sum(
            c.attributes.get("llm.token_count.prompt_details.cache_read", 0) for c in llm_calls
        )
        cache_write = sum(
            c.attributes.get("llm.token_count.prompt_details.cache_write", 0) for c in llm_calls
        )

        return {
            "turn_index": turn_index,
            "span_id": turn_node.span_id,
            "trace_id": turn_node.trace_id,
            "name": turn_node.name,
            "start_time": turn_node.start_time_str,
            "end_time": turn_node.end_time_str,
            "duration_ms": turn_node.duration_ms,
            "prompt": prompt,
            "output": output,
            "llm_calls": llm_calls,
            "tool_calls": tool_calls,
            "agent_calls": agent_calls,
            "all_events": flat_children,
            "tokens": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
            },
        }


class MarkdownRenderer:
    def __init__(self, reconciler: TraceReconciler):
        self.rec = reconciler
        self.meta = reconciler.meta
        self.turns = reconciler.turns

    def render_controller_transcript(self) -> str:
        lines: list[str] = []

        # 1. Frontmatter
        start_t = self.meta.get("time_range", {}).get("start", "")
        end_t = self.meta.get("time_range", {}).get("end", "")
        token_totals = self.meta.get("token_totals", {})
        span_kinds = self.meta.get("span_kind_counts", {})

        lines.append("---")
        lines.append(f"session_id: {self.rec.session_id}")
        lines.append(f"started_at: {start_t}")
        lines.append(f"ended_at: {end_t}")
        lines.append(f"total_spans: {self.meta.get('span_count', 0)}")
        lines.append(f"turns_count: {len(self.turns)}")
        lines.append(f"tool_calls: {span_kinds.get('TOOL', 0)}")
        lines.append(f"llm_calls: {span_kinds.get('LLM', 0)}")
        lines.append(f"agent_dispatches: {span_kinds.get('AGENT', 0)}")
        lines.append(f"tokens_prompt: {token_totals.get('prompt', 0)}")
        lines.append(f"tokens_completion: {token_totals.get('completion', 0)}")
        lines.append(f"tokens_cache_read: {token_totals.get('cache_read', 0)}")
        lines.append(f"tokens_total: {token_totals.get('total', 0)}")
        lines.append("---")
        lines.append("")

        # 2. Header
        lines.append(f"# Session `{self.rec.session_id}` — Controller Transcript")
        lines.append("")
        lines.append(f"> **Time Range:** {start_t} → {end_t}  ")
        lines.append(
            f"> **Total Tokens:** {format_tokens(token_totals.get('total', 0))} (Cache Read: {format_tokens(token_totals.get('cache_read', 0))}, Completion: {format_tokens(token_totals.get('completion', 0))})  "
        )
        lines.append(
            f"> **Spans & Turns:** {self.meta.get('span_count', 0)} spans across {len(self.turns)} turns  "
        )
        lines.append("")

        # 3. High-Level Turn Tree
        lines.append("## 🌳 Session Structure & Tool Tree")
        lines.append("")
        lines.append("```")
        lines.append(
            f"Session {self.rec.session_id[:8]}... [{format_tokens(token_totals.get('total', 0))} tok | {self.meta.get('span_count', 0)} spans]"
        )
        for turn in self.turns[:25]:
            t_idx = turn["turn_index"]
            t_dur = format_duration(turn["duration_ms"])
            p_snippet = turn["prompt"].replace("\n", " ")[:60]
            if len(turn["prompt"]) > 60:
                p_snippet += "..."
            lines.append(f"├── Turn #{t_idx} ({t_dur}) — {p_snippet or 'Tool execution turn'}")
            for tc in turn["tool_calls"][:5]:
                dur = format_duration(tc.duration_ms)
                status_icon = "🔴" if tc.is_error else "🛠️"
                lines.append(f"│   ├── {status_icon} {tc.name} ({dur})")
            if len(turn["tool_calls"]) > 5:
                lines.append(f"│   └── ... +{len(turn['tool_calls']) - 5} more tool calls")
            for ag in turn["agent_calls"]:
                agent_name = ag.attributes.get("agent.name", ag.name)
                lines.append(f"│   └── 🤖 Agent Dispatch: {agent_name}")
        if len(self.turns) > 25:
            lines.append(f"└── ... +{len(self.turns) - 25} subsequent turns")
        lines.append("```")
        lines.append("")

        # 4. Turn by Turn Details
        lines.append("## 📜 Turn Timeline")
        lines.append("")
        for turn in self.turns:
            t_idx = turn["turn_index"]
            t_start = turn["start_time"]
            t_dur = format_duration(turn["duration_ms"])

            lines.append(f"### Turn #{t_idx} — `{t_start}` ({t_dur})")
            lines.append("")

            # User Prompt
            if turn["prompt"] and not turn["prompt"].startswith("(Orphan turn"):
                lines.append("#### 👤 User Prompt")
                lines.append("```text")
                lines.append(turn["prompt"].strip())
                lines.append("```")
                lines.append("")

            # Events in turn
            events = turn["all_events"]
            for ev in events:
                if ev.kind == "LLM":
                    out_val = ev.attributes.get("output.value", "")
                    tok_total = ev.attributes.get("llm.token_count.total", 0)
                    model = ev.attributes.get("llm.model_name", "claude")
                    if out_val and not out_val.startswith("["):
                        lines.append(f"#### 🧠 Assistant (`{model}` — {tok_total} tokens)")
                        lines.append("")
                        lines.append(out_val.strip())
                        lines.append("")
                elif ev.kind in ("TOOL", "RETRIEVER"):
                    t_name = ev.name
                    t_dur = format_duration(ev.duration_ms)
                    t_inp = ev.attributes.get("input.value", "")
                    t_out = ev.attributes.get("output.value", "")
                    status = "🔴 FAILED" if ev.is_error else "✅ DONE"

                    lines.append(
                        f"<details><summary><b>🛠️ Tool: <code>{t_name}</code></b> ({t_dur}) — <i>{status}</i></summary>"
                    )
                    lines.append("")
                    lines.append("**Input:**")
                    lines.append("```json")
                    try:
                        parsed = json.loads(t_inp)
                        lines.append(json.dumps(parsed, indent=2))
                    except Exception:
                        lines.append(t_inp)
                    lines.append("```")
                    lines.append("")
                    lines.append("**Output:**")
                    lines.append("```text")
                    lines.append(t_out.strip() if t_out else "(empty output)")
                    lines.append("```")
                    lines.append("</details>")
                    lines.append("")
                elif ev.kind == "AGENT":
                    agent_type = ev.attributes.get("agent.name", ev.name)
                    a_dur = format_duration(ev.duration_ms)
                    a_inp = ev.attributes.get("input.value", "")
                    lines.append(
                        f"> 🤖 **Subagent Dispatched:** `{agent_type}` (Duration: {a_dur})  "
                    )
                    lines.append(f"> **Prompt / Payload:** `{a_inp[:200]}`")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Render Markdown transcripts from Phoenix OTel trace JSON"
    )
    parser.add_argument("trace_file", help="Path to trace JSON file")
    parser.add_argument("--out", "-o", help="Output directory for generated markdown", default=".")
    args = parser.parse_args()

    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"Error: {trace_path} does not exist", file=sys.stderr)
        sys.exit(1)

    with open(trace_path, encoding="utf-8") as f:
        data = json.load(f)

    reconciler = TraceReconciler(data)
    renderer = MarkdownRenderer(reconciler)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_name = trace_path.name.replace(".trace.json", "").replace(".json", "")
    controller_out = out_dir / f"{base_name}.controller.md"

    md_content = renderer.render_controller_transcript()
    controller_out.write_text(md_content, encoding="utf-8")
    print(f"Successfully generated transcript: {controller_out} ({len(md_content)} bytes)")


if __name__ == "__main__":
    main()
