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
allowed-tools: Bash,Read,Write,Grep,Glob,mcp__pkb__search,mcp__pkb__pkb_orphans,mcp__pkb__create_memory,mcp__pkb__list_tasks,mcp__pkb__graph_stats,mcp__pkb__get_network_metrics,mcp__pkb__update_task,mcp__pkb__get_task,mcp__pkb__task_search,mcp__pkb__pkb_context,mcp__pkb__bulk_reparent,mcp__pkb__find_duplicates,mcp__pkb__batch_merge,mcp__pkb__merge_node,mcp__pkb__complete_task,mcp__pkb__batch_reclassify,mcp__pkb__batch_archive,mcp__pkb__batch_update,mcp__pkb__create_task,mcp__pkb__update_memory,mcp__omcp__messages_search,mcp__omcp__messages_query,mcp__omcp__calendar_list_events
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
7. **Note maturity** — `seedling` (single source, provisional) → `budding` (corroborated by 2+ sources) → `evergreen` (reviewed, stable, established). Maturity progresses through evidence, not time.

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
| 1b    | Transcript Mining           | Extract unsaved insights from session transcripts       |
| 2     | Episode Replay              | Scan recent activity, identify promotion candidates     |
| 2b    | Knowledge Consolidation     | Transform episodic content into semantic knowledge      |
| 3     | Index Refresh               | Update mechanical framework indices (`SKILLS.md`, etc.) |
| 4     | Data Quality Reconciliation | Dedup, staleness verification, misclassification        |
| 5     | Staleness Sweep             | Detect orphans, stale docs, under-specified tasks       |
| 5b    | Graph Maintenance           | Densify, reparent, or connect — pick ONE strategy       |
| 5c    | PKB Quality Review          | Qualitative assessment of knowledge note quality        |
| 6     | Brain Sync                  | Commit and push `$ACA_DATA`; re-run `graph_stats`       |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics not connected to a project
- `projects_without_goal_linkage` — projects with no `goals: []` field populated
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

This is the baseline. Phase 6 re-runs graph_stats to measure what changed.

## Phase 1b: Transcript Mining

Extract insights from session transcripts that agents may not have saved during the session.

**Input**: Session transcripts in `$AOPS_SESSIONS/` (JSONL files)
**Output**: Knowledge notes created via /remember skill

### Process

1. Find transcripts not yet mined: check for `.mined` marker files or `mined_transcripts.json` manifest
2. For each unmined transcript (up to 5 per cycle):
   a. Read the transcript (use `aops-core/scripts/transcript.py` to convert if needed)
   b. Identify extractable insights: decisions made, patterns observed, facts learned, problems solved
   c. For each insight: search PKB first (`mcp__pkb__search`) to avoid duplicates
   d. Create knowledge notes via /remember skill with proper provenance:
   - `sources: ["Session transcript <session-id> <date>"]`
   - `confidence: provisional` (single source)
     e. Mark transcript as mined

### Critical Rules

- **NEVER fabricate** — only extract what is actually stated or clearly implied in the transcript
- **NEVER editorialize** — extract facts and observations, not opinions about what the user should do
- **Provenance required** — every extracted fact must cite the session it came from
- **Dedup first** — always search PKB before creating. If the insight was already saved during the session, skip it
- **Respect abstraction level** — extract generalizable patterns, not implementation minutiae (see /remember skill's Abstraction Level section)

### Environment Guard

Transcript mining requires access to `$AOPS_SESSIONS`. On GitHub Actions, this directory may be mounted or cloned separately. Skip this phase if transcripts are not accessible.

### Batch Limit

Process up to 5 transcripts per cycle. Each transcript may yield 0-10 insights. Time budget: 5 minutes.

## Phase 2b: Knowledge Consolidation

Transform episodic memory into durable semantic knowledge. This is the core of the sleep cycle's value — it mirrors the cognitive process of semanticization, where temporal memories are decontextualized into lasting understanding.

### The Consolidation Pipeline

```
Daily notes / Meeting notes / Task bodies (episodic)
        ↓ extract observations
Atomic observations with provenance
        ↓ detect patterns across 3+ observations
Synthesis notes (semantic knowledge)
        ↓ accumulate related synthesis
Maps of Content (navigational hubs)
```

### Process

1. **Identify consolidation candidates**: Find episodic content older than 7 days that hasn't been consolidated:
   - Daily notes without `consolidated: YYYY-MM-DD` in frontmatter
   - Meeting notes without `consolidated: YYYY-MM-DD`
   - Completed tasks with substantive body content

2. **Extract observations**: For each candidate (up to 10 per cycle):
   a. Read the episodic content carefully
   b. Identify atomic facts, decisions, patterns, and insights
   c. Search PKB for existing knowledge notes on the same topics
   d. Either augment existing knowledge notes or create new ones
   e. Use observation notation format (see /remember skill)
   f. Always include provenance: `sources: ["[[source-note]]"]`
   g. Mark the episodic source as `consolidated: YYYY-MM-DD` in its frontmatter (but DO NOT modify the content — episodic notes are preserved as-is)

3. **Detect synthesis opportunities**: When 3+ observations exist on the same topic:
   a. Create or update a synthesis note that integrates the observations
   b. Synthesis note frontmatter includes all source observations
   c. `confidence` level based on evidence strength:
   - `established`: 3+ independent sources agree
   - `provisional`: pattern emerging but limited evidence
   - `speculative`: single inference, needs verification

4. **Generate MOCs**: When a topic area has 5+ related knowledge notes:
   a. Check if a MOC already exists for that topic
   b. If not, create one with curated links and brief annotations
   c. If yes, update with new entries

### Critical Rules

- **Extract, don't invent** — only create knowledge that is grounded in the source material
- **Preserve episodic originals** — NEVER modify the content of daily notes, meeting notes, or task bodies. Only add `consolidated: YYYY-MM-DD` to their frontmatter.
- **Provenance chain** — every synthesized fact must trace back to specific sources
- **Abstraction ladder** — climb one rung at a time. Don't leap from a single meeting note to a broad generalization.
- **Leave editorializing to the user** — agents extract patterns and connections. Value judgments and strategic implications are the user's domain.

### Knowledge Note Deduplication

Before creating new knowledge notes, check for overlapping existing notes. When two notes cover substantially the same topic:

- Keep the stronger note (more sources, better synthesis, clearer thesis)
- Merge any unique content from the weaker note into the stronger
- Delete the weaker note
- Update any `superseded_by` or wikilink references

This is distinct from Phase 4's task dedup — it operates on `knowledge/` files by reading and comparing content qualitatively, not by title/embedding similarity.

### Bounded Effort

- Up to 10 episodic sources consolidated per cycle
- Up to 3 synthesis notes created/updated per cycle
- Up to 1 MOC created per cycle
- Time budget: 10 minutes

## Phase 4: Data Quality Reconciliation

Before structural work, fix the data. Structural metrics are meaningless when the graph is inflated with duplicates, stale items, and misclassified content. Data quality MUST run before Graph Maintenance (Phase 5b).

Three activities, run in order. Each is bounded per cycle.

### Activity 1: Deduplication (mechanical, autonomous)

1. Run `find_duplicates(mode="both")` to get clusters by title + semantic similarity.
2. For high-confidence clusters: merge autonomously via `batch_merge`. The tool selects the canonical node (most connected, most content).
3. For ambiguous clusters: log in cycle summary for human review. Don't merge.
4. Batch limit: up to 50 merges per cycle.

### Activity 2: Staleness Verification (evidence-based)

Target: active tasks with age >= 90 days.

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

**Time budget**: Phase 4 gets 10 minutes max. Exit the phase when time is up.

## Phase 5: Tools Available

The agent uses these as **signals**, not as deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

## Phase 5b: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                            | Strategy            | Planner Activity                                                              |
| ------------------------------------ | ------------------- | ----------------------------------------------------------------------------- |
| `disconnected_epics` > 10            | Connect epics       | Reparent — find project parents for disconnected epics                        |
| `projects_without_goal_linkage` > 10 | Link projects       | Add `goals: []` metadata — link projects to existing goals via metadata field |
| `flat_tasks` > 100                   | Reparent flat tasks | Reparent — find epic/project parents for orphans                              |
| `orphan_count` > 20                  | Fix orphans         | Reparent — connect or archive disconnected nodes                              |
| All metrics healthy                  | Densify edges       | Densify — use strategies to add dependency edges                              |

**Type-aware orphan detection**: `pkb_orphans` now reports both missing-parent AND wrong-type-parent orphans (e.g., a task parented directly to a project instead of an epic). Phase 5b should treat wrong-type-parent orphans the same as missing-parent orphans when selecting a reparent strategy.

See `aops-core/skills/planner/SKILL.md` → `maintain` mode for full activity reference.

**Bounded effort**: Process a configurable number of items per cycle (default 100, set via `batch_limit` workflow input). Use `mcp__pkb__bulk_reparent` for efficiency when processing multiple items with the same parent. Quality over quantity.

**Autonomous vs. flagged**:

- **Obvious**: Task title mentions the project/epic by name → reparent autonomously
- **Ambiguous**: Flag for user review in the cycle log, don't apply

**Measure after**: Re-run `graph_stats` in Phase 6 to confirm the metric improved.

## Phase 5c: Consolidation Self-Check (Lightweight)

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
2. Use the "Next" field from the last cycle to inform this cycle's Phase 5b strategy
3. After Phase 6, update the PR body with the cycle log entry

## Design Principles

1. **Smart agents, not dumb code** — tools provide signals; the agent decides
2. **Idempotent** — running twice produces the same result
3. **Incremental** — only processes what's new since last run
4. **Surfaces, doesn't decide** — flags candidates for human/supervised review
5. **No moldy docs** — never creates knowledge docs without a named consumer
6. **Agents can consolidate (hypothesis under test)** — we believe agents can perform the episodic→semantic transformation given proper value alignment, clear provenance requirements, and bounded autonomy. The `/qa` review on each consolidation PR tests this hypothesis. If quality review reveals persistent problems, escalate enforcement — don't just trust harder.

## Output: Consolidation PR

Knowledge creation (Phases 1b, 2b) produces output of uncertain quality. This output MUST go through a QA gate before reaching the main branch. The sleep cycle creates a PR — it never commits knowledge directly to main.

### Process

1. Mechanical work (Phase 0, 3, 4, 5, 5b, 6) commits directly to main — deterministic and verifiable.
2. Knowledge work (Phases 1b, 2b) commits to a branch: `sleep/consolidation-YYYY-MM-DD-HHMM`
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
