---
name: dashboard
description: Cognitive Load Dashboard - Live Streamlit dashboard for task visibility and session activity monitoring.
allowed-tools: Read,Bash,Skill
version: 1.0.0
permalink: skills-dashboard-skill
---

# Cognitive Load Dashboard

Single Streamlit dashboard for task visibility and session activity monitoring.

## Overview

Live web dashboard displaying high-priority tasks and Claude Code session activity across all projects. Designed for desktop monitoring and mobile/tablet access when away from desk.

**Target reliability**: 100% (vs task_view.py ~50% failure rate)

## Problems Solved

1. **Terminal indistinguishability** - Tasks buried in terminal history
2. **task_view.py unreliability** - ~50% failure rate makes it unusable
3. **No activity log** - Can't see what happened while away
4. **Static visualization** - Excalidraw dashboards don't auto-update
5. **Away-from-desk blindness** - No mobile/tablet access to task state

## When to Use

- "Check task priorities"
- "What's urgent?"
- "Show me focus tasks"
- "What happened today?"
- "What sessions are active?"

## Running

```bash
cd $AOPS && uv run streamlit run skills/dashboard/dashboard.py
```

## Access

- **Desktop**: http://localhost:8501
- **Tablet/Phone**: http://<desktop-ip>:8501

## Components

### Focus Panel (P0/P1 Tasks) ✅
Displays up to 5 highest-priority tasks with:
- Priority badge (🔴 P0, 🟡 P1, 🔵 P2, ⚪ P3)
- Task title
- Project classification
- Auto-refresh every 10s

### Activity Log ✅
Shows recent activity from ALL Claude Code sessions:
- User prompts (with preview)
- Significant tool operations (Edit, Write, Task, Bash)
- Session identification and color-coding
- No time limit - can see activity from any session

### Active Sessions ✅
Overview of all discovered sessions grouped by project, each showing:
- First user prompt (what started the session)
- Most recent user prompt (current state)
- Most recent memory server documentation write (if any)
- Time since last activity

## Architecture

Uses unified `lib/session_reader.py` module that reads:
- Claude session JSONL (`*.jsonl`)
- Agent transcripts (`agent-*.jsonl`)
- Hook logs (`*-hooks.jsonl`)

Same parser used by `/transcript` skill for markdown export.

## Technical Notes

- Uses `lib.session_reader.SessionProcessor` for parsing all session data
- Uses `lib.session_reader.find_sessions()` for session discovery
- Uses `skills.tasks.task_loader.load_focus_tasks()` for task data
- Auto-refresh every 10 seconds
- Error handling prevents crashes on parse failures
- Responsive layout works on mobile devices

---

## Planned: Cross-Machine Activity View

### Problem
Current dashboard only sees local JSONL sessions. When working across multiple machines/terminals, there's no unified view of "what am I doing everywhere?"

### Solution
Read prompts from Cloudflare R2 endpoint and use LLM to synthesize activity context.

### Data Source
- **Endpoint**: `https://prompt-logs.nicsuzor.workers.dev/read`
- **Auth**: Bearer token via `PROMPT_LOG_API_KEY`
- **Format**: JSON array of `{key, timestamp, content}` objects
- **Write hook**: UserPromptSubmit hook logs prompts to this endpoint

### LLM Synthesis
Use lightweight LLM (Haiku) to:
1. Cluster prompts by apparent session/project/task
2. Extract "what's happening" summary per cluster
3. Identify which machine/terminal each cluster is from (if metadata available)

### Display
New panel showing cross-machine activity:
- Grouped by inferred project/task
- Each group shows: machine/terminal, recent prompts summary, inferred current focus
- Updates on refresh (not real-time)

### Implementation Notes
- Add metadata to prompts: machine hostname, working directory, project name
- Dashboard fetches from R2, caches locally, runs LLM synthesis
- Consider rate limiting LLM calls (only re-synthesize when new prompts arrive)

### Dependencies
- Cloudflare worker deployed: `~/dotfiles/scripts/cloudflare-prompts/`
- Hook integration needed: modify UserPromptSubmit to log prompts

---

## Hook Integration: Prompt Logging

### Location
`hooks/user_prompt_submit.py` - existing hook that runs on every user prompt

### Current Behavior
1. Reads `userMessage` from stdin JSON
2. Logs to local activity file via `log_activity()`
3. Injects additional context from markdown

### New Behavior
Add step between 2 and 3: POST prompt + metadata to Cloudflare R2

### Payload Format
```json
{
  "prompt": "user's prompt text",
  "hostname": "machine-name",
  "cwd": "/path/to/project",
  "project": "project-name",
  "timestamp": "2024-12-24T15:30:00Z"
}
```

### Implementation
```python
def log_to_cloudflare(prompt: str, cwd: str) -> None:
    """Fire-and-forget POST to Cloudflare R2. Non-blocking, silent failure."""
    import subprocess
    import socket
    from datetime import datetime, timezone

    api_key = os.environ.get("PROMPT_LOG_API_KEY")
    if not api_key:
        return  # Skip if not configured

    payload = json.dumps({
        "prompt": prompt[:500],  # Truncate long prompts
        "hostname": socket.gethostname(),
        "cwd": cwd,
        "project": Path(cwd).name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    # Fire-and-forget with subprocess (non-blocking)
    subprocess.Popen(
        ["curl", "-s", "-X", "POST",
         "https://prompt-logs.nicsuzor.workers.dev/write",
         "-H", f"Authorization: Bearer {api_key}",
         "-H", "Content-Type: application/json",
         "-d", payload],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
```

### Cloudflare Worker Update
Update `src/index.js` to accept JSON payloads (currently accepts plain text):

```javascript
// POST /write - append a prompt
if (request.method === 'POST' && url.pathname === '/write') {
  const contentType = request.headers.get('Content-Type') || '';
  let body;

  if (contentType.includes('application/json')) {
    body = await request.text();  // Store full JSON
  } else {
    body = await request.text();  // Plain text backward compat
  }

  const key = `prompts/${Date.now()}-${crypto.randomUUID().slice(0, 8)}.json`;
  await env.LOGS.put(key, body);
  return new Response(JSON.stringify({ ok: true, key }), {
    headers: { 'Content-Type': 'application/json' }
  });
}
```

### Environment Setup
Add to `~/.env` (already done):
```bash
export PROMPT_LOG_API_KEY="<key>"
```

### Failure Mode
- Hook must NOT fail if Cloudflare is unreachable
- Use fire-and-forget subprocess, no error handling
- Local activity logging continues regardless
