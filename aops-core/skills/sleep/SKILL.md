---
name: sleep
type: skill
category: operations
description: "Periodic consolidation agent — session backfill, transcript mining, knowledge consolidation, quality review, staleness sweep, brain sync. Runs on GitHub Actions cron or manually via /sleep."
triggers:
  - "sleep cycle"
  - "consolidation"
  - "brain maintenance"
modifies_files: true
needs_task: false
mode: execution
domain:
  - operations
allowed-tools: Bash,Read,Write,Grep,Glob,Skill,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task,mcp__pkb__update_memory,mcp__omcp__messages_search,mcp__omcp__messages_query,mcp__omcp__calendar_list_events
owner: pauli
version: 0.1.0
tags:
  - consolidation
  - memory
  - cron
---

# Sleep Cycle: Periodic Consolidation

> **Taxonomy note**: This skill orchestrates periodic offline consolidation — transforming write-optimised storage (tasks, session logs) into read-optimised knowledge that agents actually use. See `specs/sleep-cycle.md` for full design rationale.

## Why This Works (Cognitive Science)

The sleep cycle mirrors biological memory consolidation. Complementary Learning Systems theory (McClelland et al. 1995) shows that the hippocampus rapidly stores episodes while the neocortex gradually extracts patterns through offline replay during sleep. Semanticization (Baddeley 1988) confirms that episodic memories lose temporal context through repeated retrieval and integration, becoming decontextualized semantic knowledge. This is a feature, not a bug — decontextualized knowledge is more retrievable.

**Implications for this system:**

- **Offline batch processing**: Consolidation runs offline (cron), not during active work — mirroring neural sleep replay.
- **Flag contradictions, never auto-resolve**: Schema-inconsistent information must be integrated gradually or it causes catastrophic forgetting. When two sources disagree, surface both with provenance. Resolution is human judgment.
- **Just-in-time over bulk**: Promotion is triggered by retrieval need (a named consumer), not by schedule. This prevents "moldy docs" — notes nobody reads.
- **The review IS the consolidation**: Active retrieval and reprocessing drive the transformation. Passively copying information between stores does not produce understanding.

## Values

These principles govern all consolidation work — manual `/sleep` invocations and CI workflows alike.

1. **Never fabricate** — only extract what is grounded in source material. If you can't cite it, don't assert it.
2. **Always track provenance** — every synthesized fact must cite its source. The chain from claim → source must be traversable.
3. **Preserve episodic originals** — never modify the content of daily notes, meeting notes, or task bodies. Only add `consolidated: YYYY-MM-DD` to their frontmatter.
4. **Leave editorializing to the user** — agents extract patterns and connections. Value judgments and strategic implications are the user's domain.
5. **Respect uncertainty** — use confidence levels honestly. Don't upgrade `provisional` to `established` without additional evidence from independent sources.
6. **Quality over quantity** — one well-sourced synthesis note is worth more than ten unsourced assertions. Bounded effort per cycle prevents bulk low-quality output.
7. **Note maturity, MOCs, observation notation, provenance, abstraction level** — governed by [[remember]]. This skill defers to `/remember` for the mechanics of writing and organising semantic knowledge (canonical topic notes, reconciliation, maturity levels, MOC creation, provenance chains). Do not duplicate or contradict those rules here.
8. **Judgment over procedure (pauli)** — the memory agent owns synthesis. Where this skill or `/remember` offers a heuristic, treat it as a starting point. Pauli may deviate — merge differently, rescope a topic note, collapse parallel notes, restructure a section scaffold — when the material warrants it, provided Values 1-6 still hold. Pauli is trusted to decide what endures.

## How It Works

The sleep cycle is an **agent session**, not a script. A Claude agent is launched (via GitHub Actions cron or manually) with a consolidation prompt. The agent works through phases using judgment, calling tools as signals — not deterministic code that makes the decisions.

```bash
# Trigger via GitHub Actions (runs in $ACA_DATA repo)
gh workflow run sleep-cycle -R nicsuzor/brain

# Manual invocation as a skill
/sleep

# Focus on a specific area
gh workflow run sleep-cycle -R nicsuzor/brain -f focus="staleness only"
```

## Phases

The agent works through these in order, using judgment about what needs attention:

| Phase | Name                        | What it does                                            |
| ----- | --------------------------- | ------------------------------------------------------- |
| 0     | Graph Health                | Run `graph_stats` — baseline measurement for this cycle |
| 1     | Session Backfill            | Run `/session-insights batch` for pending transcripts   |
| 2     | Transcript Mining           | Extract unsaved insights from session transcripts       |
| 3     | Episode Replay              | Scan recent activity, identify promotion candidates     |
| 4     | Knowledge Consolidation     | Transform episodic content into semantic knowledge      |
| 5     | Index Refresh               | Update mechanical framework indices (`SKILLS.md`, etc.) |
| 6     | Data Quality Reconciliation | Dedup, staleness verification, misclassification        |
| 7     | Staleness Sweep             | Detect orphans, stale docs, under-specified tasks       |
| 8     | Refile Processing           | Re-parent user-flagged tasks via /planner, remove flag  |
| 9     | Graph Maintenance           | Densify, reparent, or connect — pick ONE strategy       |
| 10    | Consolidation Self-Check    | Lightweight sanity check of this cycle's own output     |
| 11    | Brain Sync                  | Commit and push `$ACA_DATA`; re-run `graph_stats`       |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics not connected to a project
- `projects_without_goal_linkage` — projects with no `goals: []` field populated
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

This is the baseline. Phase 11 re-runs graph_stats to measure what changed.

## Phase 2: Transcript Mining

Extract insights from session transcripts that agents may not have saved during the session.

**Input**: Session transcripts in `$AOPS_SESSIONS/` (Markdown files), including synced GHA sessions in `$AOPS_SESSIONS/github/`.
**Output**: Updates to canonical topic notes (preferred); new canonical notes where the topic lacks one; rarely, a linked narrow note for genuinely topic-less observations.

### Process

1. **Sync GHA sessions**: Run `aops-core/scripts/sync_gha_sessions.py` to fetch new transcripts from GitHub Actions artifacts into `$AOPS_SESSIONS/github/`.
2. Find transcripts not yet mined: check for `mined: YYYY-MM-DD` in frontmatter across all session directories.
3. For each unmined transcript (up to 15 per cycle):
   a. Read the transcript carefully, noting decisions, patterns, facts, and problems. Look for things that are worth remembering but didn't make it into tasks or notes during the session. This is the agent's judgment call — not every detail needs to be saved, but important insights should be.
   b. Identify extractable insights: decisions made, patterns observed, facts learned, problems solved
   c. For each insight, identify the **first-class topic** it is about — not the symptom, the subject. "cargo build failed for mem MCP server" is about `mem` the tool, and the lesson lives in its `Installation` section.
   d. Route the insight per [[remember]]'s **Canonical Topic Notes** discipline: update the canonical note if it exists, create one with a section scaffold if the topic is first-class and missing, reconcile stale peers as part of the same write. Provenance: `sources: ["Session transcript <session-id> <date>"]`, `confidence: provisional` for single-source additions.
   e. Mark transcript as mined: add `mined: YYYY-MM-DD` to frontmatter (but DO NOT modify the content — transcripts are preserved as-is)

### Critical Rules

- **NEVER fabricate** — only extract what is actually stated or clearly implied in the transcript
- **NEVER editorialize** — extract facts and observations, not opinions about what the user should do
- **Skip duplicates** — if the insight was already saved during the session (canonical note already contains the same knowledge), skip it
- All writes follow [[remember]] (provenance, abstraction level, canonical topic notes, reconciliation)

### Environment Guard

Transcript mining requires access to `$AOPS_SESSIONS`. On GitHub Actions, this directory may be mounted or cloned separately. Skip this phase if transcripts are not accessible.

### Batch Limit

Process up to 15 transcripts per cycle.

## Phase 4: Knowledge Consolidation

Transform episodic memory into durable semantic knowledge. This is the core of the sleep cycle's value — it mirrors the cognitive process of semanticization, where temporal memories are decontextualized into lasting understanding.

### The Consolidation Pipeline

```
Daily notes / Meeting notes / Task bodies / Transcripts (episodic)
        ↓ identify the first-class topic each insight is *about*
Canonical topic notes (enduring memory, stable sections)
        ↓ accumulate related topics
Maps of Content (navigational hubs)
```

### Defer to /remember

The HOW of writing and organising semantic knowledge — canonical topic notes, stable section scaffolds, the routing decision, mandatory reconciliation, maturity levels, observation notation, provenance, abstraction level, MOC creation, wikilink conventions — all lives in [[remember]]. Read it and apply it. This phase does not restate those rules.

What this phase adds on top is: _which_ episodic material to mine (candidacy + freshness), _when_ MOCs are warranted for the current graph state, and pacing.

### Process

1. **Identify consolidation candidates**: Find episodic content older than 7 days that hasn't been consolidated:
   - Daily notes without `consolidated: YYYY-MM-DD` in frontmatter
   - Meeting notes without `consolidated: YYYY-MM-DD`
   - Completed tasks with substantive body content

2. **Route observations to canonical topic notes**: For each candidate, follow [[remember]]'s Canonical Topic Notes discipline — identify the first-class topic each insight is about, update the canonical note (or create one with a scaffold if missing), reconcile stale peers in the same write. Then mark the episodic source as `consolidated: YYYY-MM-DD` in its frontmatter (do NOT modify the episodic content itself).

3. **Create MOCs only when warranted**: When a topic area has accumulated 5+ canonical notes and would benefit from navigation, create or update a MOC per [[remember]]'s Maps of Content guidance. Skip this step by default — MOCs are earned, not scheduled.

### Pacing

Pauli paces the work. Defaults are guide-rails, not hard limits — deviate when the material warrants (e.g., a topic with many scattered peers that should be collapsed in one pass justifies more work than usual).

- ~10 episodic sources consolidated per cycle
- ~3 canonical topic notes created or significantly restructured per cycle
- ~1 MOC created per cycle when earned
- Time budget ~10 minutes; stop when the next action would be lower-quality than the last

## Phase 6: Data Quality Reconciliation

Before structural work, fix the data. Structural metrics are meaningless when the graph is inflated with duplicates, stale items, and misclassified content. Data quality MUST run before Graph Maintenance (Phase 9).

Three activities, run in order. Each is bounded per cycle.

### Activity 1: Deduplication (mechanical, autonomous)

1. Run `find_duplicates(mode="both")` to get clusters by title + semantic similarity.
2. For high-confidence clusters: merge autonomously via `batch_merge`. The tool selects the canonical node (most connected, most content).
3. For ambiguous clusters: log in cycle summary for human review. Don't merge.
4. Batch limit: up to 50 merges per cycle.

### Activity 2: Staleness Verification (evidence-based)

Target: non-terminal tasks (inbox/ready/queued/in_progress/merge_ready/review/blocked) with age >= 90 days.

For each candidate (up to 20 per cycle):

1. Read the task body for context (action required, deadline, email reference).
2. Search for completion evidence:
   - Sent email matching task subject/keywords (`messages_search`)
   - Calendar events matching task context (`calendar_list_events`)
   - Git commits referencing the task
3. Decision:
   - Evidence of completion found → `complete_task` with note explaining evidence
   - Deadline >90d past + zero evidence of any activity → `complete_task` with "auto-closed: no activity, deadline long past"
   - Genuinely ambiguous (some activity but unclear completion) → flag in cycle summary

**Environment guard**: Email/calendar tools require local MCP servers (not available on GitHub Actions). When running on CI, skip evidence-based verification entirely — only flag candidates. Staleness verification only runs effectively during manual `/sleep` invocations on the Mac.

### Activity 3: Misclassification Detection (pattern-based)

Target patterns:

- Tasks with "Email:" title prefix + age >60d + no children → likely untriaged email captures
- Tasks age >180d + no children + sparse body → likely fragments never triaged
- Tasks whose body is purely informational (no action items)

For matches:

- Clear non-tasks → `batch_archive` with reason, or `batch_reclassify` to "memory"
- Ambiguous → flag in cycle summary
- Batch limit: up to 30 per cycle.

**Time budget**: Phase 6 gets 10 minutes max. Exit the phase when time is up.

## Phase 7: Staleness Sweep

Detect orphans, stale docs, and under-specified tasks. The agent uses these as **signals**, not as deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

## Phase 8: Refile Processing

Process tasks the user has explicitly flagged for refiling via the dashboard's REFILE button. These are user-initiated reparent requests and take priority over automated graph maintenance.

### Process

1. **Find flagged tasks**: Grep for `refile: true` across `$ACA_DATA/tasks/`
2. **Reparent each task**: Invoke `/planner` in `maintain` mode (reparent activity) for each flagged task — the planner reads the task's context and finds an appropriate parent
3. **Clean up the flag**: After successful reparenting, remove the `refile` key from the task's YAML frontmatter
4. **Handle ambiguity**: If the planner cannot determine a parent, flag in cycle summary for human review. Remove `refile: true` and add `needs_triage: true` to prevent re-processing

### Rules

- **No batch limit** — these are explicit user requests; process all of them
- **Commits directly to main** — this is mechanical/autonomous work, not knowledge creation
- **Runs before Phase 9** so graph metrics reflect the refile changes

## Phase 9: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

### Convergence Detection

Before doing any work, compare the current `metrics_hash` from `graph_stats` against the previous cycle's hash (recorded in Phase 0 or the prior cycle's Phase 11 output).

- **If `metrics_hash` is identical to the last cycle**: the graph has converged. Skip Phase 9 entirely and log "graph converged — no structural changes needed."
- **If 2 consecutive cycles produce no-ops** (no items processed because all metrics are below thresholds AND `metrics_hash` unchanged): the graph is stable. Cancel the active-loop cron if running via `/loop`, and log "terminal condition: 2 consecutive no-ops, graph maintenance complete."

This prevents infinite reorganization cycles when the graph is already healthy.

### Strategy Selection

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                            | Strategy            | Planner Activity                                                              |
| ------------------------------------ | ------------------- | ----------------------------------------------------------------------------- |
| `disconnected_epics` > 10            | Connect epics       | Reparent — find project parents for disconnected epics                        |
| `projects_without_goal_linkage` > 10 | Link projects       | Add `goals: []` metadata — link projects to existing goals via metadata field |
| `flat_tasks` > 100                   | Reparent flat tasks | Reparent — find epic/project parents for orphans                              |
| `orphan_count` > 20                  | Fix orphans         | Reparent — connect or archive disconnected nodes                              |
| All metrics healthy                  | Densify edges       | Densify — use strategies to add dependency edges                              |

### Concrete Agent Instructions

When a strategy is selected, the agent should execute these specific actions:

**Split oversized containers**: If an epic has >20 direct children, split it. Read the children, group by theme, create sub-epics, and `bulk_reparent` children into the new sub-epics. An epic with 40 tasks about "infrastructure" might split into "CI/CD", "monitoring", and "deployment" sub-epics.

**Find misparented tasks**: Use `pkb_orphans` to find wrong-type-parent orphans (e.g., a task parented directly to a project instead of an epic). For each, find an appropriate epic under the same project and reparent. If no suitable epic exists, create one.

**Nest loose tasks**: For `flat_tasks` (tasks with no parent), read the task title and body, search for related epics/projects via `search`, and `bulk_reparent` to the best match. If no match exists, check if 3+ loose tasks share a theme — if so, create an epic to contain them.

**Connect disconnected epics**: For each disconnected epic, read its title and children to infer which project it belongs to. Search for matching projects and reparent. If no project matches, flag for human review.

### Known Metric Limitations

The `graph_stats` metrics have known blind spots. The agent must understand these to avoid wasted effort:

- **`disconnected_epics`**: Only counts epics with no parent at all. It does NOT detect epics parented to the wrong project. A well-connected but misplaced epic reads as healthy.
- **`flat_tasks`**: Counts tasks with neither parent nor children. Tasks parented to a catch-all "misc" epic show as connected even if the grouping is meaningless. Low `flat_tasks` does not mean the graph is well-organized.
- **`max_depth`**: Reports the deepest nesting level but says nothing about whether depth is appropriate. A chain of goal → project → epic → task → subtask (depth 5) is healthy; a chain of epic → epic → epic → epic → task (depth 5) from over-splitting is not.
- **`orphan_count`**: Includes wrong-type-parent orphans (good), but does not catch tasks parented to archived/cancelled containers. A task under a cancelled epic is effectively orphaned but won't appear here.
- **`metrics_hash`**: A hash of all metric values. Use this for convergence detection — if the hash is unchanged between cycles, the graph metrics have stabilized.

**Implication**: Don't treat all-green metrics as "done." Use metrics to prioritize, but spot-check qualitatively. Read a sample of supposedly-healthy subtrees to verify the structure makes sense.

### What NOT to Do

- **Don't reorganize for aesthetics.** If a task is correctly parented but the grouping isn't pretty, leave it alone. The goal is actionability, not taxonomy.
- **Don't create epics speculatively.** Only create a new epic when you have 3+ tasks that clearly belong together. A single orphan task doesn't justify a new container.
- **Don't reparent based on keyword matching alone.** A task titled "Review API docs" doesn't necessarily belong under an "API" epic — read the body to understand context.
- **Don't split epics that are actively being worked.** If an oversized epic has many `in_progress` tasks, splitting it mid-flight creates confusion. Flag it for the next quiet period.
- **Don't chase `projects_without_goals` mechanically.** Many projects legitimately don't map to a formal goal. Only link when the relationship is genuine and clear.
- **Don't undo prior human decisions.** If a task was manually reparented or an epic was manually structured, respect that structure even if your heuristics disagree.

### Type-Aware Orphan Detection

`pkb_orphans` reports both missing-parent AND wrong-type-parent orphans (e.g., a task parented directly to a project instead of an epic). Phase 9 should treat wrong-type-parent orphans the same as missing-parent orphans when selecting a reparent strategy.

See `aops-core/skills/planner/SKILL.md` → `maintain` mode for full activity reference.

### Bounded Effort

Process a configurable number of items per cycle (default 100, set via `batch_limit` workflow input). Use `mcp__pkb__bulk_reparent` for efficiency when processing multiple items with the same parent. Quality over quantity.

### Autonomous vs. Flagged

- **Obvious**: Task title mentions the project/epic by name → reparent autonomously
- **Ambiguous**: Flag for user review in the cycle log, don't apply

### Terminal Condition

Graph maintenance is complete when EITHER of:

1. **Convergence**: `metrics_hash` unchanged for 2 consecutive cycles (see Convergence Detection above)
2. **Two consecutive no-ops**: Two cycles in a row where Phase 9 processed zero items

Note: when all structural metrics are healthy, the strategy table selects "Densify edges". Densify runs normally; if it produces no structural changes, `metrics_hash` converges and condition 1 fires. Do not short-circuit before densify has a chance to run.

When terminal condition is met during an active loop: cancel the cron/loop and log the final `graph_stats` snapshot. Do not keep cycling — diminishing returns waste compute.

**Measure after**: Re-run `graph_stats` in Phase 11 to confirm the metric improved.

## Phase 10: Consolidation Self-Check (Lightweight)

A 2-minute sanity check of THIS cycle's own output. This is NOT a quality review — the real quality gate is the `/qa` review on the consolidation PR (see "Output" section below).

### Check

For each knowledge note created or modified in this cycle:

- Does it have `sources:` in frontmatter?
- Does synthesis cite 2+ observations?
- Are wikilinks valid (not broken)?
- Is confidence level present and reasonable?

### On Failure

If any check fails: log the issue in the cycle summary and flag it in the PR description. Do not try to fix content quality problems — that's the QA reviewer's job.

### Evaluation Feedback Loop

Quality findings from this cycle and from /qa reviews should feed back into improving the consolidation process. When a pattern of quality issues is detected (same issue appearing across 3+ cycles):

1. **Create a task** describing the recurring quality pattern (via `mcp__pkb__create_task` or `gh issue create`)
2. **Link to examples** — cite the specific notes/PRs where the issue appeared
3. **Propose a procedure update** — suggest what change to `consolidate.md` or `quality-exemplars.md` would prevent recurrence
4. The task is then triaged normally — human decides whether to update procedures

This closes the loop: consolidation → QA review → quality findings → procedure improvements → better consolidation.

### Bounded Effort

- Only check notes created/modified in THIS cycle
- Time budget: 2 minutes

## Active Loop Integration

When running via `/loop` or `/active-loop`, the sleep cycle follows the active-loop protocol:

1. Read the DRAFT PR body for prior cycle learnings
2. Use the "Next" field from the last cycle to inform this cycle's Phase 9 strategy
3. After Phase 11, update the PR body with the cycle log entry

## Design Principles

1. **Smart agents, not dumb code** — tools provide signals; the agent decides
2. **Idempotent** — running twice produces the same result
3. **Incremental** — only processes what's new since last run
4. **Surfaces, doesn't decide** — flags candidates for human/supervised review
5. **No moldy docs** — never creates knowledge docs without a named consumer
6. **Agents can consolidate (hypothesis under test)** — we believe agents can perform the episodic→semantic transformation given proper value alignment, clear provenance requirements, and bounded autonomy. The `/qa` review on each consolidation PR tests this hypothesis. If quality review reveals persistent problems, escalate enforcement — don't just trust harder.

## Output: Consolidation PR

Knowledge creation (Phases 2, 4) produces output of uncertain quality. This output MUST go through a QA gate before reaching the main branch. The sleep cycle creates a PR — it never commits knowledge directly to main.

### Process

1. Mechanical work (Phases 0, 1, 3, 5, 6, 7, 8, 9, 10, 11) commits directly to main — deterministic and verifiable.
2. Knowledge work (Phases 2, 4) commits to a branch: `sleep/consolidation-YYYY-MM-DD-HHMM`
3. At the end of the cycle, create a PR from the branch against main.
4. The `/qa` skill reviews the PR for fitness-for-purpose (triggered by PR creation or manual invocation).
5. Merge only after QA passes. During supervised phase, human reviews the QA decision.

### Graduation Path

- **Current**: Human reviews every consolidation PR
- **Next**: `/qa` agent reviews, human reviews QA decisions
- **Future**: `/qa` auto-approves, human reviews only rejections
- **Autonomous**: Full auto-merge after sustained evidence of quality

Each transition requires evidence from the previous level (P#22 corollary on graduated trust).

## Architecture

```
templates/github-workflows/sleep-cycle.yml   ← workflow template (maintained in $AOPS)
$ACA_DATA/.github/workflows/sleep-cycle.yml  ← installed copy (runs the agent)
```

Install via: `scripts/install-brain-workflows.sh <brain-repo-path>`

The workflow uses `anthropics/claude-code-action` to launch an agent with a consolidation prompt. The agent has access to the brain repo and academicOps tools. In CI, the agent works directly with markdown files — no PKB MCP server is available. Changes sync to PKB consumers via git push.
