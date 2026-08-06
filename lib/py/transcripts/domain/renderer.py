"""Renders a NormalizedSession to Markdown, HTML, and JSON formats."""

from __future__ import annotations

import html
import json
from typing import Any

from transcripts.domain.secret_redaction import redact_obj
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


def _render_subagent_index(session: NormalizedSession, filename_base: str) -> list[str]:
    """A one-row-per-subagent table naming every sidechain the session spawned."""
    if not session.subagents:
        return []

    lines = [
        "## 🧵 Subagents",
        "",
        f"{len(session.subagents)} subagent conversation(s) ran under this session. "
        f"Their full transcripts are in the "
        f"[Full Markdown Details](./{_escape_html(filename_base)}.full.md).",
        "",
        "| # | Agent | Type | Depth | Events | Tokens | Started | Task |",
        "|---|-------|------|-------|--------|--------|---------|------|",
    ]
    for idx, subagent in enumerate(session.subagents, start=1):
        started, _ = _subagent_time_range(subagent)
        raw_desc = (subagent.description or "").strip().replace("\n", " ")
        if len(raw_desc) > 80:
            raw_desc = raw_desc[:77] + "..."
        description = _escape_html(raw_desc).replace("|", "\\|")
        lines.append(
            f"| {idx} | `{subagent.label}` | {_escape_html(subagent.agent_type or '')} | "
            f"{_depth_label(subagent)} | {len(subagent.events)} | {subagent.tokens_used} | "
            f"{_escape_html(started)} | {description} |"
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
        content_snippet = _escape_html(content_snippet).replace("|", "\\|")

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


def _format_tool_output_markdown(content: str) -> list[str]:
    """Format tool output in Markdown with escaping or collapsible details blocks."""
    byte_count = len(content.encode("utf-8"))
    is_large = len(content) > 500 or len(content.splitlines()) > 10
    fence = _get_code_fence(content)
    if is_large:
        return [
            f"<details><summary>Tool Output ({byte_count} bytes)</summary>",
            "",
            fence,
            content,
            fence,
            "",
            "</details>",
            "",
        ]
    return [
        fence,
        content,
        fence,
        "",
    ]


def _render_events_markdown(
    events: list[NormalizedEvent],
    subagent_lookup: dict[str, tuple[int, SubagentTranscript]] | None = None,
) -> list[str]:
    """Render a conversation event by event, in order."""
    lookup = subagent_lookup or {}
    lines: list[str] = []
    for event in events:
        emoji = "📋"
        if event.source == "user":
            is_human = event.meta.get("is_human", True)
            prompt_kind = event.meta.get("prompt_kind", "user")
            if not is_human:
                emoji = f"📌 Injected Context (`{prompt_kind}`)"
            else:
                emoji = "🤷 User"
        elif event.source == "model":
            emoji = "🤖 Assistant"
        elif event.source == "tool":
            emoji = "🛠️ Tool"
        elif event.source == "system":
            emoji = "📌 System"

        ts_str = f" `({event.timestamp})`" if event.timestamp else ""
        lines.append(f"#### {emoji}{ts_str}")
        lines.append("")

        if event.thinking:
            lines.extend(
                [
                    "> [!NOTE]",
                    "> **Thinking Process:**",
                    *(f"> {_escape_html(line)}" for line in event.thinking.splitlines()),
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

        if content:
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
                    lines.append(_escape_html(human_text))
                    lines.append("")
                if injected_text:
                    lines.extend(
                        [
                            "> [!NOTE]",
                            f"> **Injected Context (`{prompt_kind}`):**",
                            *(f"> {_escape_html(line)}" for line in injected_text.splitlines()),
                            "",
                        ]
                    )
            elif event.source == "tool" or event.type == "tool_output":
                lines.extend(_format_tool_output_markdown(content))
            else:
                lines.append(_escape_html(content))
                lines.append("")

        if event.tool_calls:
            lines.append("**Tool Calls:**")
            for tc in event.tool_calls:
                lines.append(f"- Call `{tc.name}` with args:")
                lines.append("  ```json")
                lines.append(_dump_tool_args(tc.args, indent=4))
                lines.append("  ```")
                spawned = lookup.get(tc.call_id or "")
                if spawned:
                    idx, subagent = spawned
                    lines.append(f"  → **spawned Subagent {idx}: `{subagent.label}`** (see below)")
            lines.append("")

        tool_use_id = event.meta.get("tool_use_id") if event.type == "tool_output" else None
        returned = lookup.get(tool_use_id or "")
        if returned:
            idx, subagent = returned
            lines.append(f"↩ **Subagent {idx}: `{subagent.label}` returned here.**")
            lines.append("")

        lines.append("---")
        lines.append("")
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
            header.extend(["", f"> {_escape_html(subagent.description.strip())}"])
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


def _escape_html(text: str) -> str:
    return html.escape(str(text), quote=True)


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

        ts_str = f'<span class="timestamp">({event.timestamp})</span>' if event.timestamp else ""

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
                '</details>'
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
            byte_count = len(content.encode("utf-8"))
            is_large = len(content) > 500 or len(content.splitlines()) > 10
            content_escaped = _escape_html(content)
            if is_large:
                content_html_rendered = (
                    f'<details class="tool-output-details">'
                    f'<summary>Tool Output ({byte_count} bytes)</summary>'
                    f'<pre><code>{content_escaped}</code></pre>'
                    f'</details>'
                )
            else:
                content_html_rendered = f'<div class="content"><pre><code>{content_escaped}</code></pre></div>'
        else:
            content_escaped = _escape_html(content).replace("\n", "<br>")
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
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    return controller_md, full_md, md, html, json_sidecar

