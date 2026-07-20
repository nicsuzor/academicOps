import json

import yaml

from transcripts.domain.classification import has_user_context
from transcripts.domain.correlation import infer_correlations
from transcripts.domain.reflection import extract_insights
from transcripts.domain.slug import get_session_slug
from transcripts.domain.timestamps import get_session_timestamps
from transcripts.model import NormalizedSession


def render_json_sidecar(session: NormalizedSession) -> str:
    """Render the JSON metadata sidecar for the session."""
    started_at, last_modified, ended_at = get_session_timestamps(session)
    corr = infer_correlations(session)
    insights = extract_insights(session)

    data = {
        "session_id": session.session_id,
        "slug": get_session_slug(session.session_id),
        "started_at": started_at,
        "last_modified": last_modified,
        "ended_at": ended_at,
        "has_user_context": has_user_context(session),
        "prs": corr["prs"],
        "tasks": corr["tasks"],
        "projects": corr["projects"],
        "accomplishments": insights["accomplishments"],
        "decisions": insights["decisions"],
        "tool_counts": insights["tool_counts"],
    }
    return json.dumps(data, indent=2)


def render_markdown(session: NormalizedSession) -> str:
    """Render the markdown transcript with YAML front-matter."""
    started_at, last_modified, ended_at = get_session_timestamps(session)
    corr = infer_correlations(session)
    slug = get_session_slug(session.session_id)

    frontmatter = {
        "session_id": session.session_id,
        "slug": slug,
        "started_at": started_at,
        "last_modified": last_modified,
        "ended_at": ended_at,
        "has_user_context": has_user_context(session),
        "prs": corr["prs"],
        "tasks": corr["tasks"],
        "projects": corr["projects"],
    }

    yaml_block = yaml.dump(frontmatter, sort_keys=False, default_flow_style=False)
    lines = [f"---\n{yaml_block}---", ""]

    lines.append(f"# Session Transcript: {slug}")
    lines.append("")

    for event in session.events:
        ts_str = f" [{event.timestamp}]" if event.timestamp else ""
        if event.source == "user":
            lines.append(f"### 👤 User{ts_str}")
            lines.append(event.content.strip())
            lines.append("")
        elif event.source == "model":
            lines.append(f"### 🤖 Assistant{ts_str}")
            if event.thinking:
                lines.append("<details>")
                lines.append("<summary>Thinking Process</summary>")
                lines.append("")
                lines.append(event.thinking.strip())
                lines.append("</details>")
                lines.append("")
            lines.append(event.content.strip())
            lines.append("")
            if event.tool_calls:
                lines.append("**Tool Calls:**")
                for tc in event.tool_calls:
                    lines.append(f"- `{tc.name}({tc.args})`")
                lines.append("")
        elif event.source == "tool":
            lines.append(f"#### 🛠️ Tool Output: {event.meta.get('tool_name', 'tool')}{ts_str}")
            lines.append("```")
            lines.append(event.content.strip())
            lines.append("```")
            lines.append("")
        elif event.source == "system":
            lines.append(f"#### ⚙️ System Event{ts_str}")
            lines.append(event.content.strip())
            lines.append("")

    return "\n".join(lines)


def render_html(session: NormalizedSession) -> str:
    """Render a standalone clean HTML transcript."""
    started_at, last_modified, ended_at = get_session_timestamps(session)
    corr = infer_correlations(session)
    slug = get_session_slug(session.session_id)

    events_html = []
    for event in session.events:
        ts_str = f"<span class='timestamp'>{event.timestamp}</span>" if event.timestamp else ""
        if event.source == "user":
            events_html.append(f"""
            <div class='event event-user'>
                <h3>👤 User {ts_str}</h3>
                <div class='content'>{event.content.strip()}</div>
            </div>
            """)
        elif event.source == "model":
            thinking_html = ""
            if event.thinking:
                thinking_html = f"""
                <details>
                    <summary>Thinking Process</summary>
                    <pre class='thinking'>{event.thinking.strip()}</pre>
                </details>
                """
            tc_html = ""
            if event.tool_calls:
                tc_items = []
                for tc in event.tool_calls:
                    tc_items.append(f"<li><code>{tc.name}({tc.args})</code></li>")
                tc_html = f"<div class='tool-calls'><strong>Tool Calls:</strong><ul>{''.join(tc_items)}</ul></div>"

            events_html.append(f"""
            <div class='event event-model'>
                <h3>🤖 Assistant {ts_str}</h3>
                {thinking_html}
                <div class='content'>{event.content.strip()}</div>
                {tc_html}
            </div>
            """)
        elif event.source == "tool":
            tool_name = event.meta.get("tool_name", "tool")
            events_html.append(f"""
            <div class='event event-tool'>
                <h4>🛠️ Tool Output: {tool_name} {ts_str}</h4>
                <pre class='stdout'>{event.content.strip()}</pre>
            </div>
            """)
        elif event.source == "system":
            events_html.append(f"""
            <div class='event event-system'>
                <h4>⚙️ System Event {ts_str}</h4>
                <div class='content'>{event.content.strip()}</div>
            </div>
            """)

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Session Transcript: {slug}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; background: #fafafa; }}
        h1, h2, h3, h4 {{ color: #111; }}
        .meta-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; background: #fff; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; }}
        .meta-table th, .meta-table td {{ text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }}
        .meta-table th {{ background: #f5f5f5; width: 30%; }}
        .event {{ margin-bottom: 24px; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .event-user {{ border-left: 4px solid #0076ff; }}
        .event-model {{ border-left: 4px solid #30d158; }}
        .event-tool {{ border-left: 4px solid #ff9500; background: #fbfbfb; }}
        .event-system {{ border-left: 4px solid #8e8e93; background: #f5f5f5; }}
        pre {{ background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; font-family: monospace; font-size: 14px; white-space: pre-wrap; }}
        details {{ margin: 8px 0; padding: 8px; background: #f9f9f9; border-radius: 4px; border: 1px solid #e0e0e0; }}
        .timestamp {{ font-size: 12px; color: #888; font-weight: normal; margin-left: 8px; }}
        .content {{ white-space: pre-wrap; }}
        .tool-calls {{ margin-top: 12px; padding: 8px; background: #f0f3f6; border-radius: 4px; }}
        .tool-calls ul {{ margin: 4px 0 0 0; padding-left: 20px; }}
    </style>
</head>
<body>
    <h1>Session Transcript: {slug}</h1>
    <table class="meta-table">
        <tr><th>Session ID</th><td>{session.session_id}</td></tr>
        <tr><th>Slug</th><td>{slug}</td></tr>
        <tr><th>Started At</th><td>{started_at or "Unknown"}</td></tr>
        <tr><th>Last Modified</th><td>{last_modified or "Unknown"}</td></tr>
        <tr><th>Ended At</th><td>{ended_at or "Unknown"}</td></tr>
        <tr><th>Interactive User Context</th><td>{"Yes" if has_user_context(session) else "No"}</td></tr>
        <tr><th>PRs</th><td>{", ".join(corr["prs"]) or "None"}</td></tr>
        <tr><th>Tasks</th><td>{", ".join(corr["tasks"]) or "None"}</td></tr>
        <tr><th>Projects</th><td>{", ".join(corr["projects"]) or "None"}</td></tr>
    </table>
    
    <h2>Events</h2>
    <div class="events">
        {"".join(events_html)}
    </div>
</body>
</html>
"""
    return html_template
