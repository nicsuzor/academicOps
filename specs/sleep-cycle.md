---
title: "Sleep Cycle: Periodic Consolidation Agent"
type: spec
status: draft
created: 2026-03-09
task: aops-6e05d69a
tags:
  - memory
  - consolidation
  - architecture
---

# Sleep Cycle: Periodic Consolidation Agent

## Problem

We have write-optimised storage (tasks, session logs, daily notes) that captures observations well but is terrible for retrieval. When an agent needs to answer "how does X work?", it finds 5 scattered task bodies but no synthesised answer. The agent either reconstructs the answer from fragments (slow, error-prone) or doesn't find it at all.

The gap is not capture — capture works. The gap is **consolidation**: transforming accumulated episodes into retrievable, current-state knowledge that agents actually use.

### Why not just synthesise eagerly?

Most captured knowledge is never retrieved. Synthesising everything upfront creates "moldy" documents — permanent notes without a reader that drift out of date silently. We need a model where promotion is **use-case-driven**: we only promote when there's a named consumer for the knowledge.

## Design Principles

1. **Dynamic over static.** Knowledge docs must have a reader or they rot. Every promoted document must name its consumer.
2. **Consolidation, not synthesis.** We're not writing essays. We're updating current-state docs that agents read at session start, search results that agents retrieve, and framework files that govern behaviour.
3. **Offline batch processing.** Like neural sleep consolidation: replay recent episodes, extract patterns, update long-term stores. Don't interrupt active work.
4. **Use-case-driven promotion.** An observation gets promoted when it would meaningfully improve a named consumer's experience. The agent evaluates: Would this help an agent starting a fresh session? Does it answer a question that keeps being reconstructed? Does it update, contradict, or extend existing knowledge in a way that matters? There is no numeric bar — the question is always whether promotion would help a specific reader.
5. **Unsupervised execution, supervised judgment.** The sleep cycle runs on a cron job — unsupervised by design. It executes mechanical work autonomously (session backfill, index refresh, brain sync) and _stages_ promotion candidates for the next supervised session. The cycle does the legwork; the human or supervised agent (`/daily`, `/pull`) makes the final call.
6. **Idempotent and incremental.** Running the sleep cycle twice produces the same result. Each run processes only what's new since the last run.
7. **Single cycle, time-bounded.** One cycle runs every ~4 hours and does what it can within its time budget. No separate "nap" vs "deep" modes — the agent works through phases in order and exits cleanly when time runs out. Simpler scheduling, simpler reasoning.
8. **Agents do their jobs.** The sleep cycle orchestrates — it doesn't micromanage. Each phase delegates to existing tools and skills. Less planning, more execution.

## Named Consumers (Promotion Targets)

Promotion is only justified when there is a **named consumer** — a specific place where the knowledge will be read:

| Consumer            | What it reads                             | Update trigger                               |
| ------------------- | ----------------------------------------- | -------------------------------------------- |
| **Session start**   | `MEMORY.md`, `CLAUDE.md`, env vars        | Agent behaviour patterns, conventions        |
| **PKB search**      | `knowledge/`, `memories/`                 | Recurring questions without good answers     |
| **Framework files** | `aops-core/` index files, specs, axioms   | Framework behaviour changes                  |
| **Daily note**      | Focus section, task tree, recommendations | Task status changes, project progress        |
| **Task graph**      | Task frontmatter, dependencies            | Status updates, completion, blocking changes |

If an insight doesn't map to one of these consumers, it stays in its episode (task body, session log). That's fine — git history preserves it.

## Architecture

### Schedule

The sleep cycle runs as a **GitHub Actions scheduled workflow** in the `$ACA_DATA` (brain) repository, every ~4 hours. The code lives in `$AOPS` (academicOps) but executes against brain data.

```yaml
# $ACA_DATA/.github/workflows/sleep-cycle.yml
on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:
```

The workflow checks out both repos: the brain repo (data) and academicOps (code). The orchestrator script runs from academicOps with `ACA_DATA` pointing at the brain checkout.

Manual invocation: `gh workflow run sleep-cycle` or `/sleep` skill in a session.

The cycle works through phases in order. Each phase is independent and idempotent — if the cycle is interrupted or times out, the next run picks up where it left off. There is no distinction between a "light" and "heavy" run; the agent does what it can each time.

### Phases

Phases run sequentially. Each phase checks whether there's work to do and skips if not.

#### Phase 1: Session Backfill

**Consumer**: PKB search, daily note

Run `/session-insights batch` for any sessions with transcripts but no insights. This is already implemented — the sleep cycle just schedules it.

**Input**: Session transcripts without corresponding insight JSONs.
**Output**: `$ACA_SESSIONS/summaries/YYYYMMDD-{id}.json` + PKB memories.
**Skip condition**: No pending sessions.

#### Phase 2: Episode Replay

**Consumer**: PKB search, knowledge docs

Scan recent activity (since last sleep cycle) and identify **promotion candidates**:

1. **Load recent episodes**:
   - Session insight JSONs from the period
   - Tasks created/updated in the period
   - Daily note sections (accomplishments, dropped threads)
   - Git log across tracked repos (commit messages, PR titles)

2. **Evaluate for promotion** (qualitative judgment delegated to the agent — P#115/P#116):
   Ask: Is there knowledge here that would meaningfully improve a named consumer's experience? The agent considers:
   - **Retrieval value**: Would an agent starting a fresh session benefit from having this consolidated? Is there a real retrieval problem this solves, or just a frequently-mentioned detail?
   - **Knowledge ownership**: Does this belong in MEMORY.md (agent convention), PKB (durable personal knowledge), or framework files (operational behaviour)? Each tier has different implications for oversight.
   - **Relevance to existing knowledge**: Does this update, contradict, or extend an existing doc in a way that matters?

   There is no numeric threshold. One retrieval failure — an agent needed this knowledge and couldn't find it — is more signal than ten routine mentions.

3. **Check existing coverage**:
   - For each candidate, search PKB: `mcp__pkb__search(query=candidate_topic)`
   - If a knowledge doc already exists and is current → skip
   - If a knowledge doc exists but is stale → flag for update
   - If no knowledge doc exists → flag for creation

4. **Act on candidates** (unsupervised/supervised split):
   - **Execute (unsupervised)**: Mechanical updates to existing docs — status corrections, new links, corrected facts. Safe to do autonomously.
   - **Stage for supervised review**: New knowledge docs, significant rewrites, or any uncertainty about tier ownership → annotate as promotion candidates for the next supervised session (`/daily` or `/pull`). The `/briefing-bundle` and `/process-bundle` skills already support the annotation→decision pipeline. Don't auto-generate knowledge docs from unverified fragments.

**Skip condition**: No new activity since last run.

#### Phase 3: Framework Index Refresh

**Consumer**: Framework files (agents read these)

Run the audit skill's structure check for mechanical indices. This keeps `SKILLS.md` and `INDEX.md` current without manual invocation. Governance documents (`AXIOMS.md`, `HEURISTICS.md`, `VISION.md`) are never auto-updated — if they appear out of sync, flag them via PR with a description of what changed and why it matters, so the human can make a qualitative decision (P#84).

**Input**: Filesystem state of `aops-core/`.
**Output**: Updated mechanical index files, committed and pushed. PR for governance docs if stale.
**Skip condition**: No files changed in `aops-core/` since last run.

#### Phase 4: Staleness Sweep

**Consumer**: PKB search quality, task graph actionability

Identify knowledge docs and memories that may be stale, and tasks that are under-specified:

1. **Orphan detection**: `mcp__pkb__pkb_orphans()` — docs with no graph connections
2. **Contradiction detection**: Compare knowledge doc claims against recent task/session evidence
3. **Age heuristic**: Knowledge docs not modified in 60+ days with no inbound links
4. **Task quality triage**: Detect under-specified tasks using `triage_tasks.py`

##### Task Quality Triage

Many tasks have been decomposed with titles but no actionable body content. The triage script (`aops-core/skills/garden/scripts/triage_tasks.py`) classifies active tasks by checking meaningful body content — stripping boilerplate (headings that repeat the title, `## Relationships` sections, parent/child links, `Project: [[x]]` lines). It also handles escaped `\n` in YAML scalars to avoid false positives.

**Classification rules:**

| Body content | Title quality          | Verdict               | Action                     |
| ------------ | ---------------------- | --------------------- | -------------------------- |
| ≥100 chars   | any                    | `ok`                  | Skip                       |
| <100 chars   | self-explanatory†      | `ok`                  | Skip — title is sufficient |
| <100 chars   | reasonable but unclear | `needs-decomposition` | Flag for decomposition     |
| <100 chars   | vague‡                 | `needs-deletion`      | Flag for deletion          |

† Self-explanatory: "X should Y", "Fix/Add/Implement + specific object (15+ chars)", "Respond to X"
‡ Vague: single word, <15 chars, pure noun phrase with no verb

**Output**: Candidates staged as a report for `/daily` or `/garden` to process. The sleep cycle does NOT auto-delete or auto-modify tasks — it surfaces them.

**Skip condition**: Sweep ran within the last 24 hours (no need to run every 4h).

#### Phase 5: Brain Sync

**Consumer**: All (infrastructure)

Ensure `$ACA_DATA` is committed, pushed, and remote is pulled. This is already handled by `repo-sync-cron.sh` but making it explicit as the final phase ensures the sleep cycle's outputs are durable.

**Skip condition**: Never — always runs.

## Relationship to Existing Skills

| Skill               | Current role                     | Sleep cycle relationship                                                                                                                                                                         |
| ------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/daily`            | Morning briefing + progress sync | **Complementary.** Daily handles the human-facing briefing (email, focus, recommendations). Sleep cycle handles the machine-facing consolidation (episode replay, index refresh, staleness).     |
| `/session-insights` | Per-session analysis             | **Building block.** Sleep cycle Phase 1 calls session-insights batch.                                                                                                                            |
| `/audit`            | Framework index curation         | **Scheduled.** Sleep cycle Phase 3 runs audit Phases 1-2 on a schedule. Full audit remains manual.                                                                                               |
| `/garden`           | Incremental PKB maintenance      | **Downstream.** Sleep cycle Phase 4 produces staleness candidates that garden processes.                                                                                                         |
| `/remember`         | Manual knowledge capture         | **Upstream.** Inline promotion during sessions. Sleep cycle catches what /remember missed.                                                                                                       |
| `densify`           | Task graph edge enrichment       | **Complementary.** Sleep cycle consolidates episodic knowledge; densify enriches task graph structure (dependency edges). Phase 2 may surface tasks that should be linked — hand off to densify. |

## What This Does NOT Replace

- **`/daily`**: Still needed for human-facing morning briefing, email triage, focus recommendations.
- **`/remember`**: Still needed for inline, immediate knowledge capture during sessions.
- **Manual synthesis**: Some knowledge requires human judgment. Sleep cycle flags these, doesn't auto-generate.

## Anti-Patterns to Avoid

- **Over-promotion**: Creating knowledge docs for every observation. The question is always whether a named consumer would benefit — routine details that don't improve retrieval don't need promotion.
- **Moldy docs**: Creating docs without a maintenance path. Every promoted doc must be re-checkable by the staleness sweep.
- **Synthesis without verification**: Auto-generating knowledge docs from fragments. LLM synthesis of unverified claims violates epistemic honesty (P#2). Flag for human review instead.
- **Scope creep into `/daily`**: The sleep cycle is not a briefing. It doesn't present information to the user. It updates stores that other tools read.
- **Two-mode complexity**: Don't split into "light" and "heavy" runs. One cycle, one schedule, phases skip when there's nothing to do.

## Implementation Sketch

```
specs/sleep-cycle.md                              ← this spec
aops-core/skills/sleep/SKILL.md                   ← skill definition (manual invocation)
aops-core/skills/garden/scripts/triage_tasks.py   ← task quality detection (tool for Phase 4)
templates/github-workflows/sleep-cycle.yml        ← GH Actions workflow template
$ACA_DATA/.github/workflows/sleep-cycle.yml       ← installed workflow (copy from template)
```

There is no Python orchestrator. The workflow launches a **Claude agent** (`anthropics/claude-code-action`) with a consolidation prompt. The agent works through phases using judgment, calling tools like `triage_tasks.py` as signals — not deterministic scripts that make the decisions. Smart agents, not dumb code.

## User Expectations

The sleep cycle is the framework's "maintenance" layer. Users (human or agent) can expect the following behaviors:

1. **Autonomous Maintenance**: The cycle runs every 4 hours via GitHub Actions. It should complete without intervention and stay within its 20-minute time budget.
2. **Zero-Orphan Sessions**: Every session transcript eventually receives a corresponding summary JSON and PKB memory. Users shouldn't need to manually run `/session-insights` in bulk.
3. **Self-Cleaning Task Graph**: Under-specified tasks (vague titles, empty bodies) are automatically flagged. The task graph stays actionable without manual pruning of dead ends.
4. **Living Framework Indices**: Mechanical framework files (`SKILLS.md`, `INDEX.md`) stay synchronized with the filesystem. New skills or commands appear in indices within 4 hours of being merged.
5. **Staged Knowledge Promotion**: Significant patterns from recent sessions or tasks are surfaced as candidates for `MEMORY.md` or PKB. The system identifies _what_ is worth remembering, even if the human didn't manually invoke `/remember`.
6. **Remote Consistency**: The brain repo (`$ACA_DATA`) is kept synchronized across devices through periodic commits and pushes.

### Testable Criteria (Pass/Fail)

- [ ] **Backfill**: Given a session transcript without a summary, running the sleep cycle (Phase 1) generates the corresponding summary JSON.
- [ ] **Triage**: Given an active task with a vague title (e.g., "Stuff") and no body, the sleep cycle (Phase 4) flags it as `needs-deletion` or `needs-decomposition`.
- [ ] **Index Refresh**: After adding a new skill file to `aops-core/skills/`, the sleep cycle (Phase 3) updates `aops-core/SKILLS.md` to include the new skill.
- [ ] **Governance Protection**: Changes to governance documents (`VISION.md`, `AXIOMS.md`) are flagged via Pull Request rather than being auto-committed.
- [ ] **Sync Integrity**: Every successful cycle concludes with a commit to the brain repo using the standard message `sleep: periodic consolidation`.
- [ ] **Time Management**: The agent exits cleanly and records a summary to `$GITHUB_STEP_SUMMARY` within the 20-minute timeout.

## Open Questions

1. **Human review interface**: How do staged promotion candidates reach the human most effectively? The `/briefing-bundle` and `/process-bundle` skills support the annotation→decision pipeline — should candidates flow through that, or through a daily note section?
2. **Retrieval instrumentation**: How do we detect retrieval failures — the strongest signal for promotion? Session insights are one source, but they require post-session processing.
3. **Staleness vs. archival**: When a knowledge doc is stale, should it be updated, archived, or deleted?
4. **Time budget**: What's a reasonable max duration for the cycle? 10 minutes? 15? Should it hard-exit or just skip remaining phases?
