"""Renders a NormalizedSession to Markdown, HTML, and JSON formats."""

from __future__ import annotations

import json

from transcripts.model import NormalizedSession


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
    yaml_lines = [
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
        "---",
        "",
    ]

    filename_base = _get_filename_base(slug, started_at, correlation)
    content_lines = [
        f"# Session {session.session_id} Summary",
        "",
        f"For the complete chronological details, see the [Full Markdown Details](./{filename_base}.full.md) or the [HTML View](./{filename_base}.html).",
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
            "## 📊 Event Index",
            "",
            "| # | Event Type | Source | Timestamp | Summary / Snippet |",
            "|---|------------|--------|-----------|-------------------|",
        ]
    )

    for idx, event in enumerate(session.events, start=1):
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
        # Escape any pipe symbols in markdown table cell
        content_snippet = content_snippet.replace("|", "\\|")

        content_lines.append(
            f"| {idx} | `{event_type}` | **{source_name}** | {ts} | {content_snippet} |"
        )

    content_lines.append("")
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
    yaml_lines = [
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
        "---",
        "",
    ]

    filename_base = _get_filename_base(slug, started_at, correlation)
    content_lines = [
        f"# Session {session.session_id} Full Transcript",
        "",
        f"Back to [Summary View](./{filename_base}.md) or see the [HTML View](./{filename_base}.html).",
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

    for event in session.events:
        emoji = "📋"
        if event.source == "user":
            emoji = "🤷 User"
        elif event.source == "model":
            emoji = "🤖 Assistant"
        elif event.source == "tool":
            emoji = "🛠️ Tool"
        elif event.source == "system":
            emoji = "📌 System"

        ts_str = f" `({event.timestamp})`" if event.timestamp else ""
        content_lines.append(f"### {emoji}{ts_str}")
        content_lines.append("")

        if event.thinking:
            content_lines.extend(
                [
                    "> [!NOTE]",
                    "> **Thinking Process:**",
                    *(f"> {line}" for line in event.thinking.splitlines()),
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
            content_lines.append(content)
            content_lines.append("")

        if event.tool_calls:
            content_lines.append("**Tool Calls:**")
            for tc in event.tool_calls:
                content_lines.append(f"- Call `{tc.name}` with args:")
                content_lines.append("  ```json")
                content_lines.append(json.dumps(tc.args, indent=4))
                content_lines.append("  ```")
            content_lines.append("")

        content_lines.append("---")
        content_lines.append("")

    return "\n".join(yaml_lines) + "\n".join(content_lines)


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
        ts_str = f'<span class="timestamp">({event.timestamp})</span>' if event.timestamp else ""

        # Format thinking
        thinking_html = ""
        if event.thinking:
            thinking_html = (
                f'<div class="thinking"><strong>Thinking:</strong><br>{event.thinking}</div>'
            )

        content = event.content or ""
        if not isinstance(content, str):
            if isinstance(content, list):
                content = "\n".join(str(item) for item in content)
            else:
                content = str(content)

        # Format content (simple HTML escaping/newlines)
        content_escaped = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

        # Format tool calls
        tc_html = ""
        if event.tool_calls:
            tc_html_parts = []
            for tc in event.tool_calls:
                args_json = json.dumps(tc.args, indent=2)
                tc_html_parts.append(
                    f"<li>Call <code>{tc.name}</code> with:<pre><code>{args_json}</code></pre></li>"
                )
            tc_html = f'<div class="tool-calls"><strong>Tool Calls:</strong><ul>{"".join(tc_html_parts)}</ul></div>'

        events_html.append(f"""
        <div class="event {source_class}">
            <div class="event-header">
                <strong>{source_class.upper()}</strong> {ts_str}
            </div>
            {thinking_html}
            <div class="content">{content_escaped}</div>
            {tc_html}
        </div>
        """)

    insights_section = ""
    if insights:
        insights_section = f"""
        <div class="insights">
            <h2>Insights & Reflections</h2>
            <p>{insights.replace(chr(10), "<br>")}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Session {session.session_id}</title>
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
        .user {{ border-left: 4px solid #3b82f6; }}
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
        .timestamp {{
            float: right;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <h1>Session {session.session_id}</h1>
    
    <div class="meta-box">
        <div class="meta-grid">
            <div class="meta-item"><strong>Slug</strong>{slug}</div>
            <div class="meta-item"><strong>Started At</strong>{started_at}</div>
            <div class="meta-item"><strong>Ended At</strong>{ended_at}</div>
            <div class="meta-item"><strong>User Context</strong>{str(has_user_context)}</div>
            <div class="meta-item"><strong>Project</strong>{correlation.get("project") or "N/A"}</div>
            <div class="meta-item"><strong>Task ID</strong>{correlation.get("task_id") or "N/A"}</div>
            <div class="meta-item"><strong>Tokens Used</strong>{session.tokens_used}</div>
            <div class="meta-item"><strong>Cost (USD)</strong>${session.cost_usd:.6f}</div>
        </div>
    </div>

    {insights_section}

    <h2>Timeline</h2>
    <div class="events">
        {"".join(events_html)}
    </div>
</body>
</html>
"""
    return html


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
    """Render metadata sidecar to a JSON string."""
    user_prompts = []
    for event in session.events:
        if event.source == "user" and event.type == "message" and event.content:
            user_prompts.append(
                {
                    "text": event.content,
                    "timestamp": event.timestamp,
                }
            )

    data = {
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
        "user_prompts": user_prompts,
        # For compatibility with ledger checks:
        "surface": correlation.get("project") or "cli",
        "date": started_at,
    }

    return json.dumps(data, indent=2)


def render_session_to_all_formats(
    session: NormalizedSession,
    slug: str,
    started_at: str,
    last_modified: str,
    ended_at: str,
    has_user_context: bool,
    correlation: dict[str, str | None],
    insights: str | None,
) -> tuple[str, str, str]:
    """Render a session into all three output formats: Markdown, HTML, JSON."""
    md = render_to_markdown(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    html = render_to_html(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    json_sidecar = render_to_json(
        session, slug, started_at, last_modified, ended_at, has_user_context, correlation, insights
    )
    return md, html, json_sidecar
