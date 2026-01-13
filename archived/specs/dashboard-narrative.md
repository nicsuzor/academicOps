---
title: Dashboard Narrative Synthesis
status: draft
type: spec
category: spec
created: 2026-01-01
---

# Dashboard Narrative Synthesis

## Problem

The dashboard shows mechanical lists (tasks, sessions, accomplishments) but doesn't tell the story of the day. Users with ADHD need a quick, contextually-aware summary to regain orientation.

## Solution

Add a `narrative` field to `synthesis.json` containing 3-5 bullet points that tell the day's story.

## Output Format

```json
{
  "narrative": [
    "Started the morning reviewing HDR extension request",
    "Got pulled into dashboard debugging around 10am",
    "HDR admin tasks still waiting, plus OSB review from yesterday"
  ]
  // ... existing fields unchanged
}
```

**Design principle**: Bullets not prose blocks. Give the LLM room to interpret - don't over-structure.

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: TRANSCRIPT GENERATION (/session-insights)                           │
│                                                                              │
│ NOTE: This stage must extract NARRATIVE SIGNAL, not just accomplishments.   │
│ The daily note needs enough context for Stage 2 to tell the day's story.    │
└──────────────────────────────────────────────────────────────────────────────┘

~/.claude/projects/           scripts/                    $ACA_DATA/sessions/
┌─────────────────┐         ┌────────────────┐         ┌────────────────────┐
│ Raw Session     │────────▶│ find_sessions  │────────▶│ Markdown           │
│ JSONLs          │         │ .py            │         │ Transcripts        │
│ (conversations) │         └────────────────┘         │ (abridged + full)  │
└─────────────────┘                │                   └────────────────────┘
                                   ▼                            │
                          ┌────────────────┐                    │
                          │ claude_        │                    │
                          │ transcript.py  │                    │
                          └────────────────┘                    │
                                                               ▼
                                                    ┌────────────────────┐
                                                    │ Daily Note         │
                                                    │ YYYYMMDD-daily.md  │
                                                    │ • Session Log table│
                                                    │ • Accomplishments  │
                                                    │ • Session Context  │ NEW
                                                    │ • Abandoned Todos  │ NEW
                                                    └────────────────────┘

### Stage 1 Data Requirements

For narrative synthesis to work, /session-insights must extract:

| Signal | Source | Daily Note Section |
|--------|--------|-------------------|
| What was started | First user prompts, TodoWrite initial state | Session Context |
| Context switches | Project changes mid-session, topic pivots | Session Context |
| Abandoned work | TodoWrite items left unchecked at session end | Abandoned Todos |
| Accomplishments | Checked items, successful outcomes | Accomplishments (existing) |

**Current gap**: Session Log table only captures `| session_id | project | 3-word summary |`.
This loses the narrative signal needed for Stage 2.

┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: NARRATIVE SYNTHESIS (synthesize_dashboard.py)                       │
└──────────────────────────────────────────────────────────────────────────────┘

DATA SOURCES                    SYNTHESIS                    OUTPUT
┌─────────────────┐         ┌────────────────┐         ┌────────────────────┐
│ Daily Note      │────────▶│                │         │ synthesis.json     │
│ (today)         │         │ Format data    │         │ {                  │
├─────────────────┤         │ for LLM        │────────▶│   "narrative": [], │
│ Daily Note      │────────▶│      │         │         │   "next_action":{},│
│ (yesterday)     │  NEW    │      ▼         │         │   ...              │
├─────────────────┤         │ ┌──────────┐   │         │ }                  │
│ Task Index      │────────▶│ │ Claude   │   │         └────────────────────┘
├─────────────────┤         │ │ headless │   │
│ R2 Prompts      │────────▶│ └──────────┘   │
│ (cross-machine) │         └────────────────┘
└─────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: DISPLAY (dashboard.py)                                              │
└──────────────────────────────────────────────────────────────────────────────┘

synthesis.json ─────▶ Streamlit Dashboard
                      ┌─────────────────────────────────┐
                      │ 📖 TODAY'S NARRATIVE            │
                      │ • Started on HDR extension...   │
                      │ • Got pulled into debugging...  │
                      │ • Still pending: OSB review...  │
                      ├─────────────────────────────────┤
                      │ Existing panels (tasks, etc.)   │
                      └─────────────────────────────────┘
```

## Implementation Changes

### 0. `/session-insights` skill (PREREQUISITE)

Update the session-insights skill to extract narrative signal from abridged transcripts:

**New sections in daily note**:

```markdown
## Session Context

- 10:23 AM: Started on prompt hydrator context improvements
- 11:45 AM: Switched to dashboard synthesis investigation
- 2:30 PM: Back to prompt hydrator, abandoned for SNSF review

## Abandoned Todos

- [ ] Fix prompt enricher test coverage (from session 549f8f32)
- [ ] Document new hook architecture (from session df28e52b)
```

**Extraction logic**: The Gemini agent processing transcripts should:

1. Capture first user prompts per session (intent)
2. Detect project/topic changes (context switches)
3. Extract unchecked TodoWrite items at session end (abandoned)

This is a **separate change** to the session-insights skill. The dashboard narrative feature depends on it.

### 1. `synthesize_dashboard.py`

**Add**: Load yesterday's daily log for carryover detection

```python
def load_yesterday_log(data_dir: Path) -> dict:
    """Load yesterday's daily log for carryover items."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    # Return unchecked items from yesterday
```

**Modify**: Add narrative section to prompt

```python
NARRATIVE_PROMPT_ADDITION = """
Also generate a "narrative" field: a list of 3-5 bullet points that tell today's story.
Each bullet should be one short sentence (under 80 chars).
Cover:
- What work started today (morning intentions vs actual)
- Where context switches or distractions occurred
- What remains undone from today AND yesterday

Output as: "narrative": ["bullet 1", "bullet 2", ...]
"""
```

### 2. `dashboard.py`

**Add**: Narrative panel at top of dashboard

```python
def render_narrative_panel(synthesis: dict) -> None:
    """Render narrative bullets prominently."""
    narrative = synthesis.get("narrative", [])
    if narrative:
        st.markdown("### 📖 TODAY'S NARRATIVE")
        for bullet in narrative:
            st.markdown(f"• {bullet}")
```

### 3. Files Modified

| File                              | Change                              |
| --------------------------------- | ----------------------------------- |
| `scripts/synthesize_dashboard.py` | Add yesterday loader, modify prompt |
| `skills/dashboard/dashboard.py`   | Add narrative panel render          |

## Acceptance Criteria

### Stage 1: /session-insights (PREREQUISITE)

- [ ] Daily note includes Session Context section with timestamps
- [ ] Daily note includes Abandoned Todos section
- [ ] Context switches detected across project boundaries

### Stage 2: synthesize_dashboard.py

- [ ] Synthesis generates 3-5 narrative bullets
- [ ] Bullets are concise (< 80 chars each)
- [ ] Yesterday's undone items appear in narrative

### Stage 3: dashboard.py

- [ ] Dashboard displays narrative panel above existing content
- [ ] Works when narrative is empty (graceful fallback)
