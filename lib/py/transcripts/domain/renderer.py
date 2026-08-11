"""Renders a NormalizedSession to Markdown, HTML, and JSON formats."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from transcripts.domain.secret_redaction import redact_obj, redact_secrets
from transcripts.model import NormalizedEvent, NormalizedSession, SubagentTranscript

# The summary .md is meant to stay comfortably readable (~25K tokens or
# less) even for very large sessions — the full chronological detail
# already lives in the separate `.full.md` render. An uncapped Event Index
# (one row per event) defeats that: a 2000-event session produced a
# ~250K-char "summary". Cap the table and point overflow at the full file.
MAX_EVENT_INDEX_ROWS = 200

# Subagent conversations are where most of a multi-agent session's work now
# happens, and they dwarf the trunk: the largest session on record renders a
# 5.9M-char trunk and 11.5M chars of sidechains. Only `.full.md` claims to be
# complete, so that is the one artifact that carries them event by event. The
# budget below is a safety valve against a runaway session producing a file no
# reader or tool can open — subagents past it are still named, counted, and
# costed in every artifact, so nothing vanishes silently.
MAX_SUBAGENT_FULL_MD_CHARS = 8_000_000


def _dump_tool_args(args: Any, indent: int) -> str:
    """Serialise a tool call's arguments for embedding in Markdown or HTML.

    Redaction happens here, on the arguments themselves, because once they are
    serialised a credential's quotes are escaped and the write-time text pass
    matches the backslash instead of the value — ``export GH_TOKEN="ghp_..."``
    reads as ``"export GH_TOKEN=\\"ghp_...\\""`` and the token survives. The
    text pass at the write chokepoint still runs over the whole document; this
    is the pass that can see the value.
    """
    return json.dumps(redact_obj(args), indent=indent)


def _get_filename_base(slug: str, started_at: str, correlation: dict[str, str | None]) -> str:
    from datetime import UTC, datetime

    try:
        dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(UTC)

    date_str = dt.strftime("%Y%m%d")
    hour_str = dt.strftime("%H")
    project = correlation.get("project") or "adhoc"
    return f"{date_str}-{hour_str}-{project}-{slug}"


def _render_front_matter(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
) -> list[str]:
    """YAML front-matter shared by Markdown renders.

    `tokens_used` / `cost_usd` stay trunk-only so their meaning does not shift
    under existing consumers; the whole-session figures are additional keys.
    """
    return [
        "---",
        f"session_id: {session.session_id}",
        f"slug: {slug}",
        f"started_at: {started_at}",
        f"last_modified: {last_modified}",
        f"ended_at: {ended_at}",
        f"has_user_context: {str(has_user_context).lower()}",
        f"project: {correlation.get('project') or ''}",
        f"task_id: {correlation.get('task_id') or ''}",
        f"pr_number: {correlation.get('pr_number') or ''}",
        f"tokens_used: {session.tokens_used}",
        f"cost_usd: {session.cost_usd:.6f}",
        f"controller_tokens: {session.controller_tokens}",
        f"subagent_tokens: {session.subagent_tokens}",
        f"controller_cost_usd: {session.controller_cost_usd:.6f}",
        f"subagent_cost_usd: {session.subagent_cost_usd:.6f}",
        f"subagent_count: {len(session.subagents)}",
        f"total_event_count: {session.total_event_count}",
        f"total_tokens_used: {session.total_tokens_used}",
        f"total_cost_usd: {session.total_cost_usd:.6f}",
        "---",
        "",
    ]


def _subagent_time_range(subagent: SubagentTranscript) -> tuple[str, str]:
    """First and last event timestamp of a subagent's conversation."""
    stamps = [event.timestamp for event in subagent.events if event.timestamp]
    if not stamps:
        return "", ""
    return min(stamps), max(stamps)


def _depth_label(subagent: SubagentTranscript) -> str:
    """`spawn_depth` rendered for a reader, with its own honesty caveat."""
    depth = "?" if subagent.spawn_depth is None else str(subagent.spawn_depth)
    return f"{depth} (fork)" if subagent.is_fork else depth


@dataclass
class SubagentTreeNode:
    subagent: SubagentTranscript
    level_label: str  # "L1", "L2", "L1 (unlinked)", "L2 (orphaned: ...)"
    call_path: str  # "main/pauli/marsha"
    parent_label: str  # "main", "pauli"
    index_str: str  # "1", "1.1", "2"
    children: list[SubagentTreeNode] = field(default_factory=list)


def _build_subagent_tree(session: NormalizedSession) -> list[SubagentTreeNode]:
    """Construct a hierarchical subagent call tree based on parent_agent_id linkages."""
    if not session.subagents:
        return []

    sub_by_id = {sub.agent_id: sub for sub in session.subagents}
    children_map: dict[str, list[SubagentTranscript]] = {}
    roots: list[SubagentTranscript] = []

    for sub in session.subagents:
        pid = sub.parent_agent_id
        if not pid:
            roots.append(sub)
            if f"unlinked_subagent: {sub.agent_id}" not in session.degraded:
                session.degraded.append(f"unlinked_subagent: {sub.agent_id}")
        elif pid == session.session_id or pid == "main":
            roots.append(sub)
        elif pid in sub_by_id:
            children_map.setdefault(pid, []).append(sub)
        else:
            # Orphaned parent reference
            roots.append(sub)
            if f"orphaned_subagent_parent: {pid}" not in session.degraded:
                session.degraded.append(f"orphaned_subagent_parent: {pid}")

    if not roots and session.subagents:
        # All subagents are in a cyclic reference loop with no entry root
        roots.append(session.subagents[0])
        if f"cycle_detected_subagent: {session.subagents[0].agent_id}" not in session.degraded:
            session.degraded.append(f"cycle_detected_subagent: {session.subagents[0].agent_id}")

    all_visited: set[str] = set()

    def build_nodes(
        subagents: list[SubagentTranscript],
        parent_path: str,
        parent_label: str,
        depth: int,
        parent_index_prefix: str,
        ancestor_visited: set[str],
        start_idx: int = 1,
    ) -> list[SubagentTreeNode]:
        label_counts: dict[str, int] = {}
        for s in subagents:
            label_counts[s.label] = label_counts.get(s.label, 0) + 1

        nodes: list[SubagentTreeNode] = []
        for idx, sub in enumerate(subagents, start=start_idx):
            if sub.agent_id in ancestor_visited:
                # Cycle detected
                if f"cycle_detected_subagent: {sub.agent_id}" not in session.degraded:
                    session.degraded.append(f"cycle_detected_subagent: {sub.agent_id}")
                continue

            if sub.agent_id in all_visited:
                continue

            all_visited.add(sub.agent_id)
            index_str = f"{parent_index_prefix}{idx}" if parent_index_prefix else str(idx)

            if label_counts[sub.label] > 1:
                seg_label = f"{sub.label}-{sub.agent_id[:8]}"
            else:
                seg_label = sub.label

            pid = sub.parent_agent_id
            if depth == 1:
                if pid == "main" or pid == session.session_id:
                    level_label = "L1"
                    node_path = f"{parent_path}/{seg_label}"
                elif pid in sub_by_id:
                    level_label = "L1"
                    node_path = f"{parent_path}/{seg_label}"
                elif not pid:
                    level_label = "L1 (unlinked)"
                    node_path = f"{parent_path}/unlinked/{seg_label}"
                else:
                    level_label = f"L2 (orphaned: {pid[:8]})"
                    node_path = f"{parent_path}/orphaned/{seg_label}"
            else:
                level_label = f"L{depth}"
                node_path = f"{parent_path}/{seg_label}"

            child_subs = children_map.get(sub.agent_id, [])
            new_ancestor_visited = ancestor_visited | {sub.agent_id}
            children_nodes = build_nodes(
                child_subs,
                node_path,
                sub.label,
                depth + 1,
                f"{index_str}.",
                new_ancestor_visited,
            )

            nodes.append(
                SubagentTreeNode(
                    subagent=sub,
                    level_label=level_label,
                    call_path=node_path,
                    parent_label=parent_label,
                    index_str=index_str,
                    children=children_nodes,
                )
            )
        return nodes

    tree_nodes = build_nodes(roots, "main", "main", 1, "", set())

    while len(all_visited) < len(session.subagents):
        unvisited = [s for s in session.subagents if s.agent_id not in all_visited]
        if not unvisited:
            break
        for sub in unvisited:
            pid = sub.parent_agent_id
            if pid and pid not in ("main", session.session_id) and pid not in sub_by_id:
                if f"orphaned_subagent_parent: {pid}" not in session.degraded:
                    session.degraded.append(f"orphaned_subagent_parent: {pid}")
            else:
                if f"cycle_detected_subagent: {sub.agent_id}" not in session.degraded:
                    session.degraded.append(f"cycle_detected_subagent: {sub.agent_id}")

        extra_nodes = build_nodes(
            unvisited, "main", "main", 1, "", set(), start_idx=len(tree_nodes) + 1
        )
        if not extra_nodes:
            break
        tree_nodes.extend(extra_nodes)

    return tree_nodes


def _fmt_tok(n: int) -> str:
    """Format token count into human-readable compact string (e.g. 1k, 120k, 13M)."""
    if n < 1_000:
        return str(n)
    if n >= 1_000_000:
        val = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{val}M"
    val = f"{n / 1_000:.1f}".rstrip("0").rstrip(".")
    return f"{val}k"


def _render_subagent_index(session: NormalizedSession, filename_base: str) -> list[str]:
    """Render hierarchical L1/L2 subagent call tree with ASCII tree block and enriched table."""
    if not session.subagents:
        return []

    lines = [
        "## 🧵 Subagents",
        "",
        f"{len(session.subagents)} subagent conversation(s) ran under this session. "
        f"Their full transcripts are in the "
        f"[Full Markdown Details](./{_md_text(filename_base)}.full.md).",
        "",
        "### Subagent Call Tree Lineage",
        "",
        "```",
        f"main (Controlling Agent) [{_fmt_tok(session.controller_tokens)} tok | ${session.controller_cost_usd:.2f}]",
    ]

    tree_nodes = _build_subagent_tree(session)

    def render_ascii_tree(nodes: list[SubagentTreeNode], prefix: str = "") -> None:
        for i, node in enumerate(nodes):
            is_last = i == len(nodes) - 1
            connector = "└── " if is_last else "├── "
            sub = node.subagent

            clean_level = (
                node.level_label.split(" ")[0] if "(" in node.level_label else node.level_label
            )
            if not sub.agent_type or sub.label == sub.agent_type:
                display_name = sub.label
            else:
                display_name = f"{sub.label} ({sub.agent_type})"
            level_str = f" ({clean_level})"

            if sub.input_tokens or sub.cache_read_input_tokens or sub.output_tokens:
                split_str = (
                    f"in: {_fmt_tok(sub.input_tokens)}, "
                    f"cr: {_fmt_tok(sub.cache_read_input_tokens)}, "
                    f"cw: {_fmt_tok(sub.cache_creation_input_tokens)}, "
                    f"out: {_fmt_tok(sub.output_tokens)}"
                )
                metrics_str = (
                    f" [{_fmt_tok(sub.tokens_used)} tok ({split_str}) | ${sub.cost_usd:.2f}]"
                )
            else:
                metrics_str = f" [{_fmt_tok(sub.tokens_used)} tok | ${sub.cost_usd:.2f}]"

            dot = "." if "." not in node.index_str else ""
            raw_desc = (sub.description or "").strip().replace("\n", " ")
            desc_str = (
                f" — {raw_desc[:57]}..."
                if len(raw_desc) > 60
                else (f" — {raw_desc}" if raw_desc else "")
            )
            lines.append(
                f"{prefix}{connector}{node.index_str}{dot} {display_name}{level_str}{metrics_str}{desc_str}"
            )

            child_prefix = prefix + ("    " if is_last else "│   ")
            render_ascii_tree(node.children, child_prefix)

    render_ascii_tree(tree_nodes)
    lines.extend(["```", ""])

    # Render Enriched Subagent Index Table
    lines.extend(
        [
            "| Level | Call Path | Agent Label | Type | Parent Agent | Events | Tokens (in / cr / out) | USD Cost | Task / Description |",
            "|-------|-----------|-------------|------|--------------|--------|------------------------|----------|--------------------|",
        ]
    )

    def flatten_tree(nodes: list[SubagentTreeNode]) -> list[SubagentTreeNode]:
        flat = []
        for n in nodes:
            flat.append(n)
            flat.extend(flatten_tree(n.children))
        return flat

    for node in flatten_tree(tree_nodes):
        sub = node.subagent
        raw_desc = (sub.description or "").strip().replace("\n", " ")
        if len(raw_desc) > 80:
            raw_desc = raw_desc[:77] + "..."
        description = _md_text(raw_desc).replace("|", "\\|")

        if sub.input_tokens or sub.cache_read_input_tokens or sub.output_tokens:
            tok_detail = f"{_fmt_tok(sub.tokens_used)} (in: {_fmt_tok(sub.input_tokens)}, cr: {_fmt_tok(sub.cache_read_input_tokens)}, out: {_fmt_tok(sub.output_tokens)})"
        else:
            tok_detail = f"{_fmt_tok(sub.tokens_used)}"

        lines.append(
            f"| {node.level_label} | `{node.call_path}` | `{sub.label}` | "
            f"{_md_text(sub.agent_type or '')} | `{node.parent_label}` | "
            f"{len(sub.events)} | {tok_detail} | ${sub.cost_usd:.2f} | {description} |"
        )

    lines.append("")
    return lines


def render_to_markdown(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
) -> str:
    """Render a summary/index of NormalizedSession to Markdown with YAML front-matter."""
    yaml_lines = _render_front_matter(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation
    )

    filename_base = _get_filename_base(slug, started_at, correlation)
    content_lines = [
        f"# Session {session.session_id} Summary",
        "",
        f"For the complete chronological details, see the [Controlling Agent Details](./{filename_base}.controller.md), [Full Markdown Details](./{filename_base}.full.md), or the [HTML View](./{filename_base}.html).",
        "",
    ]

    if insights:
        content_lines.extend(
            [
                "## 📝 Insights & Reflections",
                "",
                insights,
                "",
            ]
        )

    content_lines.extend(_render_subagent_index(session, filename_base))

    content_lines.extend(
        [
            "## 📊 Event Index",
            "",
            "| # | Event Type | Source | Timestamp | Summary / Snippet |",
            "|---|------------|--------|-----------|-------------------|",
        ]
    )

    total_events = len(session.events)
    truncated = total_events > MAX_EVENT_INDEX_ROWS
    events_to_index = session.events[:MAX_EVENT_INDEX_ROWS] if truncated else session.events

    for idx, event in enumerate(events_to_index, start=1):
        source_name = event.source or "unknown"
        event_type = event.type or "unknown"
        ts = event.timestamp or ""

        # Make a short single-line snippet of the content
        content_snippet = ""
        content_str = event.content or ""
        if not isinstance(content_str, str):
            if isinstance(content_str, list):
                content_str = "\n".join(str(item) for item in content_str)
            else:
                content_str = str(content_str)
        if content_str:
            content_snippet = content_str.strip().replace("\n", " ")
            if len(content_snippet) > 80:
                content_snippet = content_snippet[:77] + "..."
        content_snippet = _md_text(content_snippet).replace("|", "\\|")

        content_lines.append(
            f"| {idx} | `{event_type}` | **{source_name}** | {ts} | {content_snippet} |"
        )

    if truncated:
        remaining = total_events - MAX_EVENT_INDEX_ROWS
        content_lines.append(
            f"| … | … | … | … | **+{remaining} more events — see the "
            f"[Full Markdown Details](./{filename_base}.full.md)** |"
        )

    content_lines.append("")
    return "\n".join(yaml_lines) + "\n".join(content_lines)


def _build_subagent_lookup(
    session: NormalizedSession,
) -> dict[str, tuple[int, SubagentTranscript]]:
    """Map a spawning `tool_use_id` to `(index, subagent)`, 1-indexed."""
    return {
        subagent.parent_tool_use_id: (idx, subagent)
        for idx, subagent in enumerate(session.subagents, start=1)
        if subagent.parent_tool_use_id
    }


def _get_code_fence(content: str) -> str:
    import re

    matches = re.findall(r"`+", content)
    max_len = max((len(m) for m in matches), default=0)
    fence_len = max(3, max_len + 1)
    return "`" * fence_len


def _is_error_event(event: NormalizedEvent) -> bool:
    """Determine whether a transcript event represents an error or termination cutoff."""
    if event.meta.get("is_error") is True:
        return True
    exit_code = event.meta.get("exit_code")
    if exit_code is not None and exit_code != 0:
        return True
    content_lower = str(event.content or "").lower()
    if event.source == "tool" or event.type == "tool_output":
        if "command not found" in content_lower:
            return True
        import re

        for m in re.finditer(r"exit code:\s*(\d+)", content_lower):
            if int(m.group(1)) != 0:
                return True
    if event.source == "system" and (
        event.meta.get("is_cutoff") is True
        or "limit exceeded" in content_lower
        or "spend limit" in content_lower
        or event.meta.get("error_type") is not None
    ):
        return True
    return False


def _format_error_block_markdown(
    event: NormalizedEvent,
    tool_call_names: dict[str, str] | None = None,
    cumulative_cost_usd: float | None = None,
) -> list[str]:
    """Format tool execution errors, subagent failures, and system cutoffs into [!ERROR_BLOCK] callouts."""
    content = str(event.content or "").strip()
    content_lower = content.lower()

    # 1. Error Type Classification
    error_type = event.meta.get("error_type")
    if not error_type:
        if event.source == "system":
            if "spend limit" in content_lower or "limit" in content_lower:
                error_type = "Org Spend Limit Cutoff"
            elif "context" in content_lower:
                error_type = "Context Window Limit Exceeded"
            else:
                error_type = "System Termination"
        elif event.source == "tool" or event.type == "tool_output":
            if "command not found" in content_lower:
                error_type = "Tool Execution Failure"
            else:
                error_type = "Tool Execution Failure"
        else:
            error_type = "Execution Error"

    # 2. Source Event / Tool
    tool_use_id = event.meta.get("tool_use_id") or ""
    tool_name = (
        event.meta.get("tool_name")
        or event.meta.get("name")
        or (tool_call_names.get(tool_use_id) if tool_call_names and tool_use_id else None)
    )

    if not tool_name and event.source == "system":
        source_tool_str = "`Session Termination`"
    elif tool_name:
        source_tool_str = f"`{tool_name}` (`{tool_use_id}`)" if tool_use_id else f"`{tool_name}`"
    elif event.source == "tool" or event.type == "tool_output":
        source_tool_str = f"`Tool` (`{tool_use_id}`)" if tool_use_id else "`Tool`"
    else:
        source_tool_str = f"`{event.source or 'System Event'}`"

    # 3. Status / Exit Code
    exit_code = event.meta.get("exit_code")
    if exit_code is not None:
        status_str = str(exit_code)
    elif "exit code: 127" in content_lower:
        status_str = "127"
    elif "exit code:" in content_lower:
        import re

        m = re.search(r"exit code:\s*(\d+)", content, re.IGNORECASE)
        status_str = m.group(1) if m else "1"
    elif event.source == "system":
        limit_usd = event.meta.get("limit_usd")
        if cumulative_cost_usd is not None and limit_usd is not None:
            status_str = f"Limit Exceeded (${cumulative_cost_usd:.4f} / ${limit_usd:.4f})"
        elif cumulative_cost_usd is not None:
            status_str = f"Limit Exceeded (${cumulative_cost_usd:.4f})"
        else:
            status_str = str(event.meta.get("status", "Terminated"))
    else:
        status_str = str(event.meta.get("status", "1"))

    # 4. Message & Truncation (>500 chars or >10 lines)
    is_large = len(content) > 500 or len(content.splitlines()) > 10
    lines = content.splitlines()
    if is_large:
        summary_msg = "\n".join(lines[:5])
    else:
        summary_msg = content

    # 5. Impact
    impact = event.meta.get("impact")
    if not impact:
        if error_type == "Org Spend Limit Cutoff":
            impact = "Session terminated immediately. Subagent calls aborted."
        elif "command not found" in content_lower:
            impact = "Tool call failed; assistant requested fallback execution."
        elif event.source == "tool" or event.type == "tool_output":
            impact = "Tool execution returned error status; operation unfulfilled."
        else:
            impact = "Event execution degraded or halted."

    # Build Callout Lines
    block = [
        "> [!ERROR_BLOCK]",
        f"> **Error Type:** `{error_type}`",
        f"> **Source Event / Tool:** {source_tool_str}",
        f"> **Status / Exit Code:** `{status_str}`",
    ]

    msg_lines = summary_msg.splitlines()
    if msg_lines:
        if len(msg_lines) == 1:
            block.append(f"> **Message:** `{msg_lines[0]}`")
        else:
            block.append(f"> **Message:** {_md_text(msg_lines[0])}")
            for ml in msg_lines[1:]:
                block.append(f"> {_md_text(ml)}")
    else:
        block.append("> **Message:** (empty error message)")

    block.append(f"> **Impact:** {impact}")

    if is_large:
        fence = _get_code_fence(content)
        block.extend(
            [
                "> <details><summary>Full Error Output</summary>",
                ">",
                f"> {fence}",
                *(f"> {line}" for line in content.splitlines()),
                f"> {fence}",
                ">",
                "> </details>",
            ]
        )

    block.append("")
    return block


def truncate_lines(text: str, max_lines: int = 10) -> str:
    """Truncate text to max_lines, appending a count of omitted lines if truncated."""
    if not text:
        return ""
    lines = text.strip().split("\n")
    if len(lines) <= max_lines:
        return "\n".join(lines)
    omitted = len(lines) - max_lines
    return "\n".join(lines[:max_lines]) + f"\n... (truncated {omitted} lines)"


def _strip_command_runtime_header(content: str) -> tuple[str, str | None]:
    """Parse Created At / Completed At from tool output, returning (clean_content, duration_str)."""
    match = re.search(
        r"^Created At:\s*(?P<start>[^\n]+)\nCompleted At:\s*(?P<end>[^\n]+)\n?",
        content,
    )
    if not match:
        return content, None

    try:
        start_dt = datetime.fromisoformat(match.group("start").strip())
        end_dt = datetime.fromisoformat(match.group("end").strip())
        dur_sec = max((end_dt - start_dt).total_seconds(), 0.0)
        if dur_sec < 60:
            dur_str = f"{dur_sec:.1f}s" if dur_sec >= 0.1 else f"{int(dur_sec * 1000)}ms"
        else:
            mins = int(dur_sec // 60)
            secs = int(dur_sec % 60)
            dur_str = f"{mins}m {secs}s"

        clean_content = content[match.end() :]
        return clean_content, dur_str
    except Exception:
        return content, None


def _format_tool_output_markdown(content: str, max_lines: int = 10) -> list[str]:
    """Format tool output in Markdown with line truncation for large outputs."""
    clean_content, dur_str = _strip_command_runtime_header(content)
    if not clean_content or not clean_content.strip():
        dur_suffix = f" (duration: {dur_str})" if dur_str else ""
        return [f"*(tool output clean exit with no stdout{dur_suffix})*", ""]

    byte_count = len(clean_content.encode("utf-8"))
    lines_count = len(clean_content.splitlines())
    fence = _get_code_fence(clean_content)
    dur_label = f" | duration: {dur_str}" if dur_str else ""

    if lines_count > max_lines:
        truncated_content = truncate_lines(clean_content, max_lines=max_lines)
        return [
            f"<details><summary>Tool Output ({byte_count} bytes{dur_label})</summary>",
            "",
            fence,
            truncated_content,
            fence,
            "",
            "</details>",
            "",
        ]
    return [
        fence,
        clean_content.strip(),
        fence,
        "",
    ]


def _get_subagent_final_response(subagent: SubagentTranscript) -> str:
    """Extract the final text response or summary returned by a subagent."""
    for ev in reversed(subagent.events):
        if ev.source == "model" and ev.content and ev.content.strip():
            return ev.content.strip()
        if ev.type == "tool_output" and ev.content and ev.content.strip():
            return ev.content.strip()
    return subagent.description or ""


def _render_events_markdown(
    events: list[NormalizedEvent],
    subagent_lookup: dict[str, tuple[int, SubagentTranscript]] | None = None,
) -> list[str]:
    """Render a conversation event by event in turn-by-turn markdown format."""
    lookup = subagent_lookup or {}
    lines: list[str] = []

    # Map tool call ids to tool names for error callout context
    tool_call_names: dict[str, str] = {}
    for ev in events:
        if ev.tool_calls:
            for tc in ev.tool_calls:
                if tc.call_id:
                    tool_call_names[tc.call_id] = tc.name

    turn_num = 1
    for event in events:
        lines.append(f"### Turn {turn_num}:")
        lines.append("")

        # Render per-step token pill for assistant turns carrying usage metadata
        if event.source == "model" and "usage" in event.meta:
            u = event.meta["usage"]
            inp = u.get("input_tokens", 0)
            outp = u.get("output_tokens", 0)
            cr = u.get("cache_read_input_tokens", 0)
            cc = u.get("cache_creation_input_tokens", 0)
            step_cost = u.get("step_cost_usd", 0.0)
            cum_cost = u.get("cumulative_cost_usd", 0.0)

            tot_tokens = inp + outp + cr + cc
            if tot_tokens > 0:
                cache_parts = []
                if cr > 0:
                    cache_parts.append(f"`{cr:,}` cache read")
                if cc > 0:
                    cache_parts.append(f"`{cc:,}` cache write")

                cache_str = f" ({', '.join(cache_parts)})" if cache_parts else ""

                if "unknown_model" in event.meta:
                    cost_str = f"N/A (unknown model: {event.meta['unknown_model']})"
                else:
                    cost_str = f"`${step_cost:.4f}`"

                pill_line = (
                    f"> **Tokens:** `{inp:,}` in{cache_str} | `{outp:,}` out | "
                    f"**Step Cost:** {cost_str} | **Cumulative:** `${cum_cost:.4f}`"
                )
                lines.append(pill_line)
                lines.append("")

        if event.thinking:
            lines.extend(
                [
                    "> [!NOTE]",
                    "> **Thinking Process:**",
                    *(f"> {_md_text(line)}" for line in event.thinking.splitlines()),
                    "",
                ]
            )
        elif event.thinking_opaque:
            lines.extend(
                [
                    "> [!NOTE]",
                    "> **Thinking Process:** not recoverable — Claude Code returned this "
                    "block empty (signature only). This model turn did reason before "
                    "acting; the reasoning text itself cannot be shown.",
                    "",
                ]
            )

        content = event.content or ""
        if not isinstance(content, str):
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            else:
                content = str(content)

        ts_str = f" `({event.timestamp})`" if event.timestamp else ""

        if event.source == "user":
            is_human = event.meta.get("is_human", True)
            prompt_kind = event.meta.get("prompt_kind", "user")
            human_text = (
                event.meta.get("human_content")
                if "human_content" in event.meta
                else (content if is_human else "")
            )
            injected_text = (
                event.meta.get("injected_content")
                if "injected_content" in event.meta
                else (content if not is_human else "")
            )

            if is_human and human_text:
                lines.append(f"#### 🤷 User{ts_str}")
                lines.append("")
                lines.append(_md_text(human_text))
                lines.append("")
            if injected_text:
                lines.append(f"#### 📌 Injected Context (`{prompt_kind}`){ts_str}")
                lines.append("")
                lines.extend(
                    [
                        "> [!NOTE]",
                        f"> **Injected Context (`{prompt_kind}`):**",
                        *(f"> {_md_text(line)}" for line in injected_text.splitlines()),
                        "",
                    ]
                )

        elif event.source == "model" and content and not event.tool_calls:
            model_name = event.meta.get("model") or "assistant"
            agent_name = event.meta.get("agent_name") or event.meta.get("agent_type") or "main"
            lines.append(f"#### 🤖 Assistant (`{agent_name}`, `{model_name}`){ts_str}")
            lines.append("")
            lines.append("```")
            lines.append(content.strip())
            lines.append("```")
            lines.append("")

        elif event.source == "tool" or event.type == "tool_output":
            if _is_error_event(event):
                lines.extend(_format_error_block_markdown(event, tool_call_names=tool_call_names))
            elif (
                "REPORTING PROTOCOL" in content
                or "EVIDENCE CONTRACT" in content
                or "hook" in content.lower()
            ):
                lines.append(f"#### hook: stop{ts_str}")
                lines.append("")
                lines.append("```")
                lines.append(truncate_lines(content, max_lines=10))
                lines.append("```")
                lines.append("")
            else:
                lines.append(f"#### 🛠️ Tool Output{ts_str}")
                lines.extend(_format_tool_output_markdown(content, max_lines=10))

        elif event.source == "system":
            if _is_error_event(event):
                lines.extend(_format_error_block_markdown(event, tool_call_names=tool_call_names))
            else:
                lines.append(f"#### 📌 System{ts_str}")
                lines.append("")
                lines.append(_md_text(content))
                lines.append("")

        elif content and not event.tool_calls:
            lines.append(f"#### Message{ts_str}")
            lines.append("")
            lines.append(_md_text(content))
            lines.append("")

        if event.tool_calls:
            for tc in event.tool_calls:
                args = tc.args or {}
                summary = args.get("toolSummary") or args.get("toolAction")
                if summary:
                    lines.append(f"#### 🛠️ Tool call: `{tc.name}` — *{summary}*{ts_str}")
                else:
                    lines.append(f"#### 🛠️ Tool call: `{tc.name}`{ts_str}")
                lines.append("")

                spawned = lookup.get(tc.call_id or "")
                if spawned:
                    idx, subagent = spawned
                    model_part = f", `{subagent.model}`" if subagent.model else ""
                    type_part = f"`{subagent.agent_type}`" if subagent.agent_type else ""

                    if (
                        subagent.label
                        and subagent.agent_type
                        and subagent.label != subagent.agent_type
                    ):
                        label_str = f"`{subagent.label}` ({type_part}{model_part})"
                    elif subagent.label:
                        label_str = (
                            f"`{subagent.label}` ({model_part.strip(', ')})"
                            if model_part
                            else f"`{subagent.label}`"
                        )
                    else:
                        label_str = f"{type_part}{model_part}"

                    tok_str = f"`{_fmt_tok(subagent.tokens_used)}` tok | `${subagent.cost_usd:.2f}`"
                    lines.append(f"  → **spawned Subagent {idx}: {label_str}** [{tok_str}]")
                    lines.append("")

                    prompt_text = (
                        subagent.description
                        or (tc.args.get("prompt") if tc.args else None)
                        or (tc.args.get("description") if tc.args else None)
                    )
                    if prompt_text:
                        lines.append("  ```")
                        lines.append(truncate_lines(str(prompt_text), max_lines=10))
                        lines.append("  ```")
                        lines.append("")

                    resp_text = _get_subagent_final_response(subagent)
                    if resp_text:
                        lines.append("  > **Subagent Response:**")
                        lines.extend(
                            f"  > {_md_text(line)}"
                            for line in truncate_lines(resp_text, max_lines=10).splitlines()
                        )
                        lines.append("")
                else:
                    clean_args = {
                        k: v for k, v in args.items() if k not in ("toolAction", "toolSummary")
                    }
                    if clean_args:
                        lines.append("```json")
                        lines.append(
                            truncate_lines(_dump_tool_args(clean_args, indent=2), max_lines=15)
                        )
                        lines.append("```")
                        lines.append("")

        tool_use_id = event.meta.get("tool_use_id") if event.type == "tool_output" else None
        returned = lookup.get(tool_use_id or "")
        if returned:
            idx, subagent = returned
            type_part = (
                f" (`{subagent.agent_type}`)"
                if subagent.agent_type and subagent.agent_type != subagent.label
                else ""
            )
            lines.append(
                f"↩ **Subagent {idx}: `{subagent.label}`{type_part} returned to main session.**"
            )
            lines.append("")

            resp_text = _get_subagent_final_response(subagent) or content
            clean_resp, _ = _strip_command_runtime_header(resp_text)
            if clean_resp and clean_resp.strip():
                lines.append("  > **Message returned to main session:**")
                lines.extend(
                    f"  > {_md_text(line)}"
                    for line in truncate_lines(clean_resp.strip(), max_lines=10).splitlines()
                )
                lines.append("")

        if event.meta.get("stop_reason") or event.type == "stop":
            stop_reason = event.meta.get("stop_reason") or "Session stop sequence reached"
            lines.append(f"#### stop{ts_str}")
            lines.append("```")
            lines.append(stop_reason)
            lines.append("```")
            lines.append("")

        lines.append("---")
        lines.append("")
        turn_num += 1

    return lines


def _render_subagent_transcripts(session: NormalizedSession) -> list[str]:
    """Render every subagent conversation in full, up to the size budget."""
    if not session.subagents:
        return []

    lines = [
        "## 🧵 Subagent Transcripts",
        "",
        f"{len(session.subagents)} subagent conversation(s) ran under this session, "
        f"carrying {session.total_event_count - len(session.events)} events.",
        "",
    ]

    lookup = _build_subagent_lookup(session)
    budget = MAX_SUBAGENT_FULL_MD_CHARS
    for idx, subagent in enumerate(session.subagents, start=1):
        started, ended = _subagent_time_range(subagent)
        heading_level = min(max((subagent.spawn_depth or 1) + 2, 3), 6)
        fork_tag = " (fork)" if subagent.is_fork else ""
        header = [
            f"{'#' * heading_level} 🧵 Subagent {idx}: {subagent.label}{fork_tag}",
            "",
            f"- agent_id: `{subagent.agent_id}`",
            f"- agent_type: `{subagent.agent_type or 'unknown'}`",
            f"- spawn_depth: {_depth_label(subagent)}",
            f"- events: {len(subagent.events)}",
            f"- tokens_used: {subagent.tokens_used}",
            f"- cost_usd: {subagent.cost_usd:.6f}",
            f"- window: {started or 'unknown'} → {ended or 'unknown'}",
        ]
        if subagent.parent_agent_id:
            header.append(f"- spawned_by: `{subagent.parent_agent_id}`")
        if subagent.description:
            header.extend(["", f"> {_md_text(subagent.description.strip())}"])
        header.append("")

        body = _render_events_markdown(subagent.events, lookup)
        rendered = header + body
        cost = sum(len(line) + 1 for line in rendered)
        if cost > budget:
            remaining = session.subagents[idx - 1 :]
            omitted_events = sum(len(sub.events) for sub in remaining)
            lines.extend(
                [
                    "> [!WARNING]",
                    f"> Size budget of {MAX_SUBAGENT_FULL_MD_CHARS} characters reached. "
                    f"{len(remaining)} subagent transcript(s) totalling {omitted_events} "
                    f"events are listed in the summary view but not expanded here: "
                    + ", ".join(f"`{sub.label}`" for sub in remaining),
                    "",
                ]
            )
            break
        budget -= cost
        lines.extend(rendered)

    return lines


def render_to_controller_markdown(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
) -> str:
    """Render controlling agent full timeline to Markdown with YAML front-matter."""
    yaml_lines = _render_front_matter(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation
    )

    filename_base = _get_filename_base(slug, started_at, correlation)
    content_lines = [
        f"# Session {session.session_id} Controlling Agent Transcript",
        "",
        f"Back to [Summary View](./{filename_base}.md) or see the [Full Markdown Details](./{filename_base}.full.md) or the [HTML View](./{filename_base}.html).",
        "",
    ]

    if insights:
        content_lines.extend(
            [
                "## 📝 Insights & Reflections",
                "",
                insights,
                "",
            ]
        )

    content_lines.extend(_render_subagent_index(session, filename_base))
    content_lines.extend(
        [
            "## 📜 Chronological Events",
            "",
        ]
    )
    content_lines.extend(_render_events_markdown(session.events, _build_subagent_lookup(session)))

    return "\n".join(yaml_lines) + "\n".join(content_lines)


def render_to_full_markdown(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
) -> str:
    """Render a NormalizedSession to full chronological Markdown with YAML front-matter."""
    yaml_lines = _render_front_matter(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation
    )

    filename_base = _get_filename_base(slug, started_at, correlation)
    content_lines = [
        f"# Session {session.session_id} Full Transcript",
        "",
        f"Back to [Summary View](./{filename_base}.md) or see the [Controlling Agent View](./{filename_base}.controller.md) or the [HTML View](./{filename_base}.html).",
        "",
    ]

    if insights:
        content_lines.extend(
            [
                "## 📝 Insights & Reflections",
                "",
                insights,
                "",
            ]
        )

    content_lines.extend(
        [
            "## 📜 Chronological Events",
            "",
        ]
    )
    content_lines.extend(_render_events_markdown(session.events, _build_subagent_lookup(session)))
    content_lines.extend(_render_subagent_transcripts(session))

    return "\n".join(yaml_lines) + "\n".join(content_lines)


def _md_text(text: str) -> str:
    """Carry text into a Markdown tier verbatim.

    Markdown is not HTML, and an escaped corpus cannot be rescanned for
    secrets. See "Escaping and redaction" in `specs/transcript-pipeline.md`,
    which owns this contract.
    """
    return str(text)


def _escape_html(text: str) -> str:
    """Redact, then escape, a fragment for embedding in the HTML tier.

    The redaction is not incidental to the escaping: escaping re-encodes the
    very bytes the secret patterns match, so it has to happen second. See
    "Escaping and redaction" in `specs/transcript-pipeline.md`, which owns
    this contract and states the general rule this is one instance of.
    """
    return html.escape(redact_secrets(str(text)), quote=True)


def _render_subagent_html(session: NormalizedSession, filename_base: str) -> str:
    """A card per subagent."""
    if not session.subagents:
        return ""

    rows = []
    for idx, subagent in enumerate(session.subagents, start=1):
        started, ended = _subagent_time_range(subagent)
        description = _escape_html((subagent.description or "").strip())
        rows.append(
            f"<tr><td>{idx}</td>"
            f"<td><code>{_escape_html(subagent.label)}</code></td>"
            f"<td>{_escape_html(subagent.agent_type or '')}</td>"
            f"<td>{len(subagent.events)}</td>"
            f"<td>{subagent.tokens_used}</td>"
            f"<td>{_escape_html(started)} → {_escape_html(ended)}</td>"
            f"<td>{description}</td></tr>"
        )

    return f"""
        <h2>Subagents</h2>
        <p>{len(session.subagents)} subagent conversation(s) ran under this session,
        carrying {session.total_event_count - len(session.events)} events. Their full
        transcripts are in <a href="./{_escape_html(filename_base)}.full.md">{_escape_html(filename_base)}.full.md</a>.</p>
        <table class="subagents">
            <thead><tr><th>#</th><th>Agent</th><th>Type</th><th>Events</th>
            <th>Tokens</th><th>Window</th><th>Task</th></tr></thead>
            <tbody>{"".join(rows)}</tbody>
        </table>
        """


def render_to_html(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
) -> str:
    """Render a NormalizedSession to a beautiful standalone HTML document."""
    events_html = []
    for event in session.events:
        source_class = event.source or "unknown"
        is_human = event.meta.get("is_human", True) if event.source == "user" else True
        prompt_kind = event.meta.get("prompt_kind", "user") if event.source == "user" else ""

        if event.source == "user":
            if not is_human:
                source_class = "user injected"
                header_title = f"INJECTED CONTEXT ({prompt_kind.upper()})"
            else:
                source_class = "user human"
                header_title = "USER (HUMAN)"
        else:
            header_title = source_class.upper()

        # `event.source` and `event.timestamp` are transcript data, so they are
        # attacker-controlled: both land in the DOM below, one inside a class
        # attribute. Escape at the point of emission.
        source_class = _escape_html(source_class)
        header_title = _escape_html(header_title)
        ts_str = (
            f'<span class="timestamp">({_escape_html(event.timestamp)})</span>'
            if event.timestamp
            else ""
        )

        # Format thinking
        thinking_html = ""
        if event.thinking:
            esc_thinking = _escape_html(event.thinking)
            thinking_html = (
                f'<details class="thinking-details" open><summary><strong>Thinking Process</strong></summary>'
                f'<div class="thinking">{esc_thinking}</div></details>'
            )
        elif event.thinking_opaque:
            thinking_html = (
                '<details class="thinking-details"><summary><strong>Thinking Process</strong></summary>'
                '<div class="thinking">not recoverable — Claude Code returned this block empty (signature only).</div>'
                "</details>"
            )

        content = event.content or ""
        if not isinstance(content, str):
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            else:
                content = str(content)

        if event.source == "user":
            human_text = (
                event.meta.get("human_content")
                if "human_content" in event.meta
                else (content if is_human else "")
            )
            injected_text = (
                event.meta.get("injected_content")
                if "injected_content" in event.meta
                else (content if not is_human else "")
            )

            content_parts_html = []
            if is_human and human_text:
                h_esc = _escape_html(human_text).replace("\n", "<br>")
                content_parts_html.append(
                    f'<div class="content"><span class="badge human-badge">Human Prompt</span><br>{h_esc}</div>'
                )
            if injected_text:
                inj_esc = _escape_html(injected_text).replace("\n", "<br>")
                content_parts_html.append(
                    f'<div class="injected-box"><span class="badge injected-badge">Injected Context ({_escape_html(prompt_kind)})</span><br>{inj_esc}</div>'
                )
            content_html_rendered = "".join(content_parts_html)
        elif event.source == "tool" or event.type == "tool_output":
            is_err = _is_error_event(event)
            byte_count = len(content.encode("utf-8"))
            is_large = len(content) > 500 or len(content.splitlines()) > 10
            content_escaped = _escape_html(content)
            if is_err:
                source_class = "tool error"
                if is_large:
                    content_html_rendered = (
                        f'<div class="error-box">'
                        f'<span class="badge error-badge">ERROR BLOCK</span>'
                        f'<details class="tool-output-details">'
                        f"<summary>Full Error Output ({byte_count} bytes)</summary>"
                        f"<pre><code>{content_escaped}</code></pre>"
                        f"</details></div>"
                    )
                else:
                    content_html_rendered = (
                        f'<div class="error-box">'
                        f'<span class="badge error-badge">ERROR BLOCK</span>'
                        f"<pre><code>{content_escaped}</code></pre></div>"
                    )
            else:
                if is_large:
                    content_html_rendered = (
                        f'<details class="tool-output-details">'
                        f"<summary>Tool Output ({byte_count} bytes)</summary>"
                        f"<pre><code>{content_escaped}</code></pre>"
                        f"</details>"
                    )
                else:
                    content_html_rendered = (
                        f'<div class="content"><pre><code>{content_escaped}</code></pre></div>'
                    )
        else:
            is_err = _is_error_event(event)
            content_escaped = _escape_html(content).replace("\n", "<br>")
            if is_err:
                source_class = f"{source_class} error"
                content_html_rendered = (
                    f'<div class="error-box">'
                    f'<span class="badge error-badge">ERROR BLOCK</span>'
                    f'<div class="content">{content_escaped}</div></div>'
                )
            else:
                content_html_rendered = f'<div class="content">{content_escaped}</div>'

        # Format tool calls
        tc_html = ""
        if event.tool_calls:
            tc_html_parts = []
            for tc in event.tool_calls:
                args_json = _dump_tool_args(tc.args, indent=2)
                tc_html_parts.append(
                    f"<li>Call <code>{_escape_html(tc.name)}</code> with:<pre><code>{_escape_html(args_json)}</code></pre></li>"
                )
            tc_html = f'<div class="tool-calls"><strong>Tool Calls:</strong><ul>{"".join(tc_html_parts)}</ul></div>'

        events_html.append(f"""
        <div class="event {source_class}">
            <div class="event-header">
                <strong>{header_title}</strong> {ts_str}
            </div>
            {thinking_html}
            {content_html_rendered}
            {tc_html}
        </div>
        """)

    insights_section = ""
    if insights:
        insights_section = f"""
        <div class="insights">
            <h2>Insights & Reflections</h2>
            <p>{_escape_html(insights).replace(chr(10), "<br>")}</p>
        </div>
        """

    subagents_section = _render_subagent_html(
        session, _get_filename_base(slug, started_at, correlation)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Session {_escape_html(session.session_id)}</title>
    <style>
        body {{
            background-color: #0f0f11;
            color: #e4e4e7;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 2rem 1rem;
            line-height: 1.6;
        }}
        h1, h2 {{
            color: #ffffff;
            border-bottom: 1px solid #27272a;
            padding-bottom: 0.5rem;
        }}
        .meta-box {{
            background: linear-gradient(135deg, #18181b, #09090b);
            border: 1px solid #27272a;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .meta-item strong {{
            color: #a1a1aa;
            display: block;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}
        .insights {{
            background-color: #1e1b4b;
            border-left: 4px solid #6366f1;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 2rem;
        }}
        .event {{
            background-color: #18181b;
            border: 1px solid #27272a;
            border-radius: 6px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }}
        .event-header {{
            color: #a1a1aa;
            font-size: 0.85rem;
            margin-bottom: 0.75rem;
            border-bottom: 1px solid #27272a;
            padding-bottom: 0.25rem;
        }}
        .user.human {{ border-left: 4px solid #3b82f6; }}
        .user.injected {{ border-left: 4px solid #8b5cf6; background-color: #1a1625; }}
        .injected-box {{
            background-color: #12101d;
            border: 1px dashed #6366f1;
            padding: 0.75rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            font-size: 0.9rem;
            color: #c7d2fe;
        }}
        .badge {{
            font-size: 0.75rem;
            padding: 0.1rem 0.4rem;
            border-radius: 3px;
            font-weight: bold;
        }}
        .human-badge {{ background-color: #1d4ed8; color: #ffffff; }}
        .injected-badge {{ background-color: #6d28d9; color: #ffffff; }}
        .assistant {{ border-left: 4px solid #10b981; }}
        .tool {{ border-left: 4px solid #eab308; }}
        .system {{ border-left: 4px solid #71717a; }}
        .thinking {{
            background-color: #121214;
            border: 1px dashed #3f3f46;
            padding: 0.75rem;
            border-radius: 4px;
            color: #a1a1aa;
            font-style: italic;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }}
        .tool-calls pre {{
            background-color: #121214;
            padding: 0.75rem;
            border-radius: 4px;
            border: 1px solid #27272a;
        }}
        details.tool-output-details summary, details.thinking-details summary {{
            cursor: pointer;
            color: #a1a1aa;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }}
        details.tool-output-details pre {{
            background-color: #121214;
            padding: 0.75rem;
            border-radius: 4px;
            border: 1px solid #27272a;
            overflow-x: auto;
        }}
        .timestamp {{
            float: right;
            font-size: 0.8rem;
        }}
        table.subagents {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-bottom: 2rem;
        }}
        table.subagents th, table.subagents td {{
            border: 1px solid #27272a;
            padding: 0.4rem 0.6rem;
            text-align: left;
            vertical-align: top;
        }}
        table.subagents th {{ color: #a1a1aa; }}
        .error-box {{
            background-color: #2a1215;
            border: 1px solid #991b1b;
            padding: 0.75rem;
            border-radius: 4px;
            margin-top: 0.5rem;
        }}
        .error-badge {{
            background-color: #dc2626;
            color: #ffffff;
            margin-bottom: 0.5rem;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <h1>Session {_escape_html(session.session_id)}</h1>
    
    <div class="meta-box">
        <div class="meta-grid">
            <div class="meta-item"><strong>Slug</strong>{_escape_html(slug)}</div>
            <div class="meta-item"><strong>Started At</strong>{_escape_html(started_at)}</div>
            <div class="meta-item"><strong>Ended At</strong>{_escape_html(ended_at)}</div>
            <div class="meta-item"><strong>User Context</strong>{str(has_user_context)}</div>
            <div class="meta-item"><strong>Project</strong>{_escape_html(correlation.get("project") or "N/A")}</div>
            <div class="meta-item"><strong>Task ID</strong>{_escape_html(correlation.get("task_id") or "N/A")}</div>
            <div class="meta-item"><strong>Tokens Used</strong>{session.total_tokens_used}</div>
            <div class="meta-item"><strong>Cost (USD)</strong>${session.total_cost_usd:.6f}</div>
            <div class="meta-item"><strong>Subagents</strong>{len(session.subagents)}</div>
        </div>
    </div>

    {insights_section}

    {subagents_section}

    <h2>Timeline</h2>
    <div class="events">
        {"".join(events_html)}
    </div>
</body>
</html>
"""
    return html


def build_json_sidecar(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
    source_content_hash: str | None = None,
) -> dict[str, Any]:
    """Build the metadata sidecar as data."""
    user_prompts = []
    injected_prompts = []
    for event in session.events:
        if event.source == "user" and event.type == "message":
            is_human = event.meta.get("is_human", True)
            human_text = (
                event.meta.get("human_content")
                if "human_content" in event.meta
                else (event.content if is_human else "")
            )
            injected_text = (
                event.meta.get("injected_content")
                if "injected_content" in event.meta
                else (event.content if not is_human else "")
            )

            if human_text and human_text.strip():
                user_prompts.append(
                    {
                        "text": human_text.strip(),
                        "timestamp": event.timestamp,
                    }
                )
            if injected_text and injected_text.strip():
                injected_prompts.append(
                    {
                        "text": injected_text.strip(),
                        "timestamp": event.timestamp,
                        "kind": event.meta.get("prompt_kind", "injected"),
                    }
                )

    data: dict[str, Any] = {
        "session_id": session.session_id,
        "slug": slug,
        "started_at": started_at,
        "last_modified": last_modified,
        "ended_at": ended_at,
        "has_user_context": has_user_context,
        "project": correlation.get("project"),
        "task_id": correlation.get("task_id"),
        "pr_number": correlation.get("pr_number"),
        "insights": insights,
        "source_content_hash": source_content_hash,
        "event_count": len(session.events),
        "tokens_used": session.tokens_used,
        "cost_usd": session.cost_usd,
        "controller_tokens": session.controller_tokens,
        "subagent_tokens": session.subagent_tokens,
        "controller_cost_usd": session.controller_cost_usd,
        "subagent_cost_usd": session.subagent_cost_usd,
        "total_event_count": session.total_event_count,
        "total_tokens_used": session.total_tokens_used,
        "total_cost_usd": session.total_cost_usd,
        "subagents": [
            {
                "agent_id": subagent.agent_id,
                "agent_type": subagent.agent_type,
                "name": subagent.name,
                "description": subagent.description,
                "parent_agent_id": subagent.parent_agent_id,
                "parent_tool_use_id": subagent.parent_tool_use_id,
                "event_count": len(subagent.events),
                "tokens_used": subagent.tokens_used,
                "cost_usd": subagent.cost_usd,
                "started_at": _subagent_time_range(subagent)[0],
                "ended_at": _subagent_time_range(subagent)[1],
            }
            for subagent in session.subagents
        ],
        "user_prompts": user_prompts,
        "injected_prompts": injected_prompts,
        "surface": correlation.get("project") or "cli",
        "date": started_at,
    }

    return data


def render_to_json(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
    source_content_hash: str | None = None,
) -> str:
    """Serialise the metadata sidecar."""
    return json.dumps(
        build_json_sidecar(
            session,
            slug,
            started_at,
            last_modified,
            ended_at,
            has_user_context,
            correlation,
            insights,
            source_content_hash,
        ),
        indent=2,
    )


def render_session_to_all_formats(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
    source_content_hash: str | None = None,
) -> tuple[str, str, str, str, dict[str, Any]]:
    """Render a session into all 4 output tiers plus JSON sidecar.

    Returns (controller_md, full_md, md, html, json_sidecar).
    """
    controller_md = render_to_controller_markdown(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    full_md = render_to_full_markdown(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    md = render_to_markdown(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    html = render_to_html(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    json_sidecar = build_json_sidecar(
        session,
        slug,
        started_at,
        last_modified,
        ended_at,
        has_user_context,
        correlation,
        insights,
        source_content_hash,
    )
    return controller_md, full_md, md, html, json_sidecar
