---
title: State-Aware Task Selection
type: spec
category: spec
status: proposed
permalink: state-aware-task-selection
tags: [spec, tasks, adhd, state-tracking, next]
created: 2026-01-07
---

# State-Aware Task Selection

**Status**: Proposed
**Extends**: [[task-selector-skill]]

## User Story

**As** Nic (academic with ADHD whose capacity varies significantly by mood, energy, and context),
**I want** `/next` to prompt for my current state and adapt recommendations accordingly,
**So that** I get task suggestions that match what I can actually accomplish right now, not just what's due.

## Problem Statement

Current `/next` uses task metadata (deadlines, projects, effort) but ignores user state:

```
User: /next
System: Here are 3 tasks based on deadlines and variety!
User: [exhausted, picks "quick win" anyway]
System: [no learning, no adaptation]
```

Task selection should consider: Can this person do this task _right now_?

## Solution

### Phase 1: State Capture

Before generating recommendations, `/next` prompts for state:

```
Before I suggest tasks:
- Energy (1-5):
- Mood (1-5):
- Focus quality today: [great/ok/rough]
- Anything weighing on you? [optional]
```

Time budget: <30 seconds to complete.

### Phase 2: State-Adaptive Filtering

| State Signal             | Recommendation Adjustment                              |
| ------------------------ | ------------------------------------------------------ |
| Energy 1-2               | Filter to quick wins, maintenance tasks                |
| Energy 4-5               | Surface deep work, creative tasks                      |
| Mood 1-2                 | Prioritize enjoyable tasks; flag if this enables drift |
| Poor focus               | Single clear option, not 3 choices                     |
| High energy + good mood  | This is when to suggest hard writing                   |
| Framework drift detected | Explicitly name it, force writing/real-work suggestion |

### Phase 3: State Logging

Each `/next` invocation logs:

```yaml
timestamp: 2026-01-07T14:32:00
energy: 3
mood: 4
focus: ok
notes: "distracted by email"
session_project: aops
task_selected: [task-id or "none"]
```

Storage: `$ACA_DATA/state/YYYYMMDD-state.jsonl` (one file per day, append-only)

### Phase 4: Pattern Detection (Future)

After N sessions with state data:

- Correlate state → task completion
- Identify time-of-day patterns
- Surface insights: "You're most productive for writing after lunch"
- Detect drift patterns: "Low mood correlates with framework rabbit holes"

## Integration Points

### With `/q`

When `/q` captures a task during a session, it should note:

- Most recent state from `/next` check-in
- Whether capture represents drift from stated session intention

This creates feedback: "You queued 4 framework tasks during your last writing session."

### With Daily Summary

State data feeds into daily summary:

- Average energy/mood
- Focus quality distribution
- Correlation between state and accomplishments

## Acceptance Criteria

- [ ] **AC1**: `/next` prompts for energy, mood, focus before recommendations
- [ ] **AC2**: Prompts are skippable (user can say "skip" or just answer partially)
- [ ] **AC3**: State influences which tasks are recommended
- [ ] **AC4**: State is logged to JSONL file
- [ ] **AC5**: Low energy filters out deep-work tasks
- [ ] **AC6**: Framework drift warning triggers when aops-heavy + low mood

## Design Decisions

### Why Prompt, Not Infer?

We could try to infer state from session behavior, but:

1. Inference is unreliable
2. Prompting creates accountability moment
3. The act of reflecting on state is itself valuable

### Why JSONL, Not Database?

- Append-only is simpler
- Easy to query with jq
- Human-readable for debugging
- Can migrate to DB later if needed

### Why Per-Day Files?

- Natural archival boundary
- Keeps file sizes manageable
- Aligns with daily.md pattern

## Open Questions

1. **Prompt frequency**: Every `/next` call? Once per session? Once per terminal?
2. **Inference fallback**: If user skips, use last-known state or assume baseline?
3. **Drift detection threshold**: How many framework items before warning?

## Non-Goals

- Fully automated state inference (unreliable)
- Complex mood tracking app (we're not building a mood tracker)
- Gamification (no streaks, badges, etc.)
