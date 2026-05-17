---
title: Maintenance Mode — Phase Instructions
type: procedure
category: instruction
permalink: maintenance-phases
tags: [memory, consolidation, sleep, maintenance, phases]
---

# Maintenance Mode: Phase-by-Phase Instructions

Full instructions for the `/sleep` and GHA cron maintenance mode of the [[remember]] skill. See [[remember]] for the mode overview, values, and mode detection.

## How It Works

The maintenance cycle is an **agent session**, not a script. A Claude agent is launched (via GitHub Actions cron or manually) with a consolidation prompt. The agent works through phases using judgment, calling tools as signals — not deterministic code that makes the decisions.

### Sub-Agent Dispatch (Phases 2, 4, and Quality Review)

The parent sleep orchestrator may delegate Phase 2 (Transcript Mining), Phase 4 (Knowledge Consolidation), and the PKB Quality Review to parallel `aops-core:pauli` sub-agents. Pauli's default profile only exposes a narrow Read/Skill/PKB-MCP toolset because pauli is also used in non-sleep contexts where Bash/Edit are inappropriate. **Sleep dispatch is the exception**: the consolidation phases need filesystem and shell access to discover transcripts, mark them as mined, and inspect git state.

When dispatching, ALWAYS pass the explicit `tools` argument so the sub-agent inherits the knowledge-work toolset rather than the lean default. Example invocation:

```
Agent(
  subagent_type='aops-core:pauli',
  prompt='Execute Phase 2 (Transcript Mining) per aops-core/skills/remember/references/maintenance-phases.md. Process up to 15 unmined transcripts under $AOPS_SESSIONS. Report HALT explicitly if any required tool is missing.',
  tools=[
    # PKB MCP — read
    'mcp__plugin_aops-core_pkb__search',
    'mcp__plugin_aops-core_pkb__task_search',
    'mcp__plugin_aops-core_pkb__get_document',
    'mcp__plugin_aops-core_pkb__pkb_context',
    # PKB MCP — write
    'mcp__plugin_aops-core_pkb__append',
    'mcp__plugin_aops-core_pkb__create',
    'mcp__plugin_aops-core_pkb__create_memory',
    # Filesystem / shell
    'Bash',                # transcript listing, git status
    'Glob',                # transcript discovery
    'Grep',                # transcript content search
    'Edit',                # transcript frontmatter only — see scope below
    'Read',
    'Skill',
  ],
)
```

**Edit scope**: `Edit` is granted ONLY to mark transcripts as `mined: YYYY-MM-DD` in their frontmatter. Transcripts live OUTSIDE `$ACA_DATA` (typically `$AOPS_SESSIONS/**/*.md`), which is the explicit exception to the [[remember]] skill's hard rules. Sub-agents must NOT use `Edit` to modify anything inside `$ACA_DATA` — knowledge writes go through PKB MCP tools.

**CI environment**: when running on GitHub Actions, the PKB MCP server is unavailable. In that environment sub-agents work directly against markdown files via `Bash`/`Glob`/`Edit`/`Write` and the dispatch can omit the `mcp__plugin_aops-core_pkb__*` entries. The parent must surface this clearly in the dispatched prompt so the sub-agent knows which channel is live.

**Do NOT add these tools to pauli's default profile** (`aops-core/agents/pauli.md`). The toolset is dispatch-context-specific; pauli is also invoked by James, Marsha, and during interactive `/planner` work where Bash/Edit are inappropriate.

### Halt Surfacing (Anti-Silent-Failure)

Sub-agents are instructed to emit a literal `HALT:` line and the missing tool name when a required tool is unavailable, rather than fabricating output. The parent orchestrator MUST:

1. Parse each sub-agent return for any of the markers `HALT:`, `HALTED`, `tool gap`, `tool not available`, or `cannot proceed: missing tool`.
2. Maintain a halt counter across all dispatched sub-agents in the cycle.
3. Surface the count in the final cycle report (and in `$GITHUB_STEP_SUMMARY` on CI), with the affected phase names and missing tools listed. Example summary line: `Sub-agent halts: 2 (Phase 2 — missing Bash; Phase 4 — missing mcp__plugin_aops-core_pkb__append)`.
4. If the halt count is non-zero, the cycle exit code/PR description must call this out at the TOP — not buried inside per-phase output. This closes the silent-failure mode where halts were only visible inside individual sub-agent returns.

## Pacing & Mode

The skill runs in two modes with different output cadences. **Detect the mode at the start of every cycle** per the Mode Detection rules in [[remember]] and pick the matching output strategy.

### Short-loop mode (interval <= 30m, in-session)

- **Always run Phases 2 and 4.** They are the highest-value work; never skip them because the output gate feels heavy.
- **Persistent branch per day**: use `sleep/consolidation-YYYY-MM-DD` (no `-HHMM` suffix). Reuse it across every cycle in the day. Create on first cycle, fast-forward / rebase from main on later cycles.
- **Accumulate commits**: each cycle adds commits to the same branch — one commit per phase that produced output is fine.
- **No PR per cycle.** Open the PR on the _first_ cycle of the day if it doesn't exist; subsequent cycles push to the same branch and the PR updates automatically.
- **QA runs once per day** (or on demand), not per cycle. The PR description should note "short-loop accumulation; QA on close" so reviewers know not to expect a per-cycle gate.
- **Time budget per cycle**: keep Phase 4 to ~5 minutes and Phase 2 to ~5 minutes when interval is 20m or less. Quality over coverage — better one well-sourced note than five superficial ones.

### Full-session mode (manual `/sleep`, GHA cron)

- Branch: `sleep/consolidation-YYYY-MM-DD-HHMM` (timestamped, fresh per invocation).
- One PR per cycle.
- `/qa` review per PR before merge.
- Time budgets per phase as documented in each phase below.

### Brain repo auto-merge

On the **brain repo only** (`$ACA_DATA`, currently `nicsuzor/brain`), and ONLY after Phase 10 self-check passes, enable auto-merge on the consolidation PR:

```bash
gh pr merge --auto --squash -R nicsuzor/brain <pr-number>
```

- Auto-merge is enabled ONLY on the brain repo. Never on `academicOps` or any other repo.
- Auto-merge requires Phase 10 self-check to have **passed** (no failures logged). On any Phase 10 failure, do NOT enable auto-merge — leave the PR open for human review.
- This applies in both modes.

## Phases

The agent works through these in order, using judgment about what needs attention:

| Phase | Name                        | What it does                                                                                         |
| ----- | --------------------------- | ---------------------------------------------------------------------------------------------------- |
| 0     | Graph Health                | Run `graph_stats` — baseline measurement for this cycle                                              |
| 1     | Session Backfill            | Run `aops-core/scripts/transcript.py` for pending transcripts (Stop hook + cron usually handle this) |
| 2     | Transcript Mining           | Extract unsaved insights from session transcripts                                                    |
| 3     | Episode Replay              | Scan recent activity, identify promotion candidates                                                  |
| 4     | Knowledge Consolidation     | Transform episodic content into semantic knowledge                                                   |
| 5     | Index Refresh               | Update mechanical framework indices (`SKILLS.md`, etc.)                                              |
| 6     | Data Quality Reconciliation | Dedup, staleness verification, misclassification                                                     |
| 7     | Staleness Sweep             | Detect orphans, stale docs, under-specified tasks                                                    |
| 8     | Refile Processing           | Re-parent user-flagged tasks via /planner, remove flag                                               |
| 9     | Graph Maintenance           | Densify, reparent, or connect — pick ONE strategy                                                    |
| 10    | Consolidation Self-Check    | Lightweight sanity check of this cycle's own output                                                  |
| 11    | Brain Sync                  | Commit and push `$ACA_DATA`; re-run `graph_stats`                                                    |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics not connected to a project
- `projects_without_goal_linkage` — projects with no `goals: []` field populated
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

**Convergence Check:**
Maintain a persistent cycle log at `$ACA_DATA/state/sleep-convergence.json` (or track in the active PR body) to compare cycles.

1. Compare current metrics (`flat_tasks`, `disconnected_epics`, `projects_without_goal_linkage`, `orphan_count`) to the previous cycle's baseline.
2. If all key metrics are unchanged, increment the `no_op_count`. If any changed, reset `no_op_count` to 0.
3. Save the new metrics and `no_op_count` to the persistent log.
4. **Halt Rule**: If `no_op_count >= 2` (two consecutive no-op cycles), report convergence, cancel the active `/loop` cron, and exit the cycle early.

This is the baseline. Phase 11 re-runs graph_stats to measure what changed.

## Phase 2: Transcript Mining

Extract insights from session transcripts that agents may not have saved during the session.

**Input**: Session transcripts in `$AOPS_SESSIONS/` (Markdown files), including synced GHA sessions in `$AOPS_SESSIONS/github/`.
**Output**: Updates to canonical topic notes (preferred); new canonical notes where the topic lacks one; rarely, a linked narrow note for genuinely topic-less observations.

### Process

1. **Sync GHA sessions**: Run `aops-core/scripts/sync_gha_sessions.py` to fetch new transcripts from GitHub Actions artifacts into `$AOPS_SESSIONS/github/`.
2. Find transcripts not yet mined: check for `mined: YYYY-MM-DD` in frontmatter across all session directories.
3. For each unmined transcript (up to 15 per cycle):
   a. Read the transcript carefully, noting decisions, patterns, facts, and problems.
   b. Identify extractable insights: decisions made, patterns observed, facts learned, problems solved.
   c. For each insight, identify the **first-class topic** it is about — not the symptom, the subject.
   d. Route the insight per [[remember]]'s Canonical Topic Notes discipline: update the canonical note if it exists, create one with a section scaffold if the topic is first-class and missing, reconcile stale peers as part of the same write. Provenance: `sources: ["Session transcript <session-id> <date>"]`, `confidence: provisional` for single-source additions.
   e. Mark transcript as mined: add `mined: YYYY-MM-DD` to frontmatter (but DO NOT modify the content — transcripts are preserved as-is).

### Critical Rules

- **NEVER fabricate** — only extract what is actually stated or clearly implied in the transcript.
- **NEVER editorialize** — extract facts and observations, not opinions about what the user should do.
- **Skip duplicates** — if the insight was already saved during the session, skip it.
- All writes follow [[remember]] (provenance, abstraction level, canonical topic notes, reconciliation).

### Environment Guard

Transcript mining requires access to `$AOPS_SESSIONS`. On GitHub Actions, this directory may be mounted or cloned separately. Skip this phase if transcripts are not accessible.

### Batch Limit

Process up to 15 transcripts per cycle.

## Phase 4: Knowledge Consolidation

Transform episodic memory into durable semantic knowledge. This mirrors the cognitive process of semanticization, where temporal memories are decontextualized into lasting understanding.

### The Consolidation Pipeline

```
Daily notes / Meeting notes / Task bodies / Transcripts (episodic)
        ↓ identify the first-class topic each insight is *about*
Canonical topic notes (enduring memory, stable sections)
        ↓ accumulate related topics
Maps of Content (navigational hubs)
```

### Defer to Immediate Mode

The HOW of writing and organising semantic knowledge — canonical topic notes, stable section scaffolds, the routing decision, mandatory reconciliation, maturity levels, observation notation, provenance, abstraction level, MOC creation, wikilink conventions — all lives in [[remember]] under **Immediate Mode**. Read it and apply it. This phase does not restate those rules.

What this phase adds on top is: _which_ episodic material to mine (candidacy + freshness), _when_ MOCs are warranted for the current graph state, and pacing.

### Process

1. **Identify consolidation candidates**: Find episodic content older than 7 days that hasn't been consolidated:
   - Daily notes without `consolidated: YYYY-MM-DD` in frontmatter
   - Meeting notes without `consolidated: YYYY-MM-DD`
   - Completed tasks with substantive body content

2. **Route observations to canonical topic notes**: For each candidate, follow [[remember]]'s Canonical Topic Notes discipline — identify the first-class topic each insight is about, update the canonical note (or create one with a scaffold if missing), reconcile stale peers in the same write. Then mark the episodic source as `consolidated: YYYY-MM-DD` in its frontmatter (do NOT modify the episodic content itself).

3. **Create MOCs only when warranted**: When a topic area has accumulated 5+ canonical notes and would benefit from navigation, create or update a MOC per [[remember]]'s Maps of Content guidance. Skip this step by default — MOCs are earned, not scheduled.

### Garden Pass Discipline (P#123)

Per P#123 — Age Is Not A Staleness Signal: when this phase encounters old episodic sources, do NOT recommend cancellation based on age alone. Only relevance — not age — justifies cancellation. Garden passes here surface candidates for human review; they do not recommend cancellation.

### Pacing

Pauli paces the work. Defaults are guide-rails, not hard limits.

- ~10 episodic sources consolidated per cycle
- ~3 canonical topic notes created or significantly restructured per cycle
- ~1 MOC created per cycle when earned
- Time budget ~10 minutes; stop when the next action would be lower-quality than the last

## Phase 6: Data Quality Reconciliation

Before structural work, fix the data. Three activities, run in order. Each is bounded per cycle.

### Activity 1: Deduplication (mechanical, autonomous)

1. Run `find_duplicates(mode="both")` to get clusters by title + semantic similarity.
2. For high-confidence clusters: merge autonomously via `batch_merge`.
3. For ambiguous clusters: log in cycle summary for human review. Don't merge.
4. Batch limit: up to 50 merges per cycle.

### Activity 2: Staleness Verification (evidence-based)

Target: non-terminal tasks (inbox/ready/queued/in_progress/merge_ready/review/blocked) with age >= 90 days.

For each candidate (up to 20 per cycle):

1. Read the task body for context.
2. Search for completion evidence: sent email, calendar events, git commits.
3. Decision:
   - Evidence of completion found → `complete_task` with note explaining evidence.
   - Deadline >90d past + zero evidence → flag in cycle summary for human review (age alone does not establish irrelevance, per P#123).
   - Ambiguous → flag in cycle summary.

**Environment guard**: Email/calendar tools require local MCP servers (not available on GitHub Actions). When running on CI, skip evidence-based verification entirely — only flag candidates.

### Activity 3: Misclassification Detection (pattern-based)

Target patterns:

- Tasks with "Email:" title prefix + age >60d + no children → likely untriaged email captures
- Tasks age >180d + no children + sparse body → likely fragments never triaged
- Tasks whose body is purely informational (no action items)

For matches:

- Clear non-tasks → `batch_archive` with reason, or `batch_reclassify` to "memory"
- Ambiguous → flag in cycle summary
- Batch limit: up to 30 per cycle.

### Activity 4: Loop-close (PR-state sweep + gate-1 verification audit)

**Activity 4a — PR-state sweep.**

For each tracked repo (`$ACA_DATA/state/tracked-repos.json`), for each PR closed since the cursor at `$ACA_DATA/state/close-loop-cursor.json`:

Match PR → task by precedence:

1. `pr_url` already on the task
2. `task-XXXXXXXX` ID found in PR body
3. PR `headRefName` matches the task's recorded branch
4. PR title matches task title (whole-word, ignoring `feat()` / `fix()` / `chore()` prefixes)
5. Reverse-match for session-release adhoc tasks: extract distinctive component substrings from the title and search PR bodies. Surface as `likely-closed-by` — **never auto-complete on this signal alone**.

Resolution:

- **Merged** → `complete_task(id, completion_evidence="PR #N merged <ISO> — <url>", pr_url=<url>)`.
- **Closed-without-merge** → re-queue to `inbox`; append reviewer comments via `mcp__pkb__append`.
- **Open** → no-op.
- **No match** → log to ambiguous queue in artefact, surface in next `/daily`. Never invent a task.

PRs only — **no `git log` scanning**. Idempotent. Cursor advances only after writes succeed. Phase no-ops when PKB MCP unavailable (CI guard).

Artefact written to `$ACA_DATA/state/pr-state.json`.

**Activity 4a-bis — status-drift backstop (cursor-independent).**

For every task currently in `merge_ready` or `review` (cap 50 per cycle, oldest-modified first):

1. **PR-status reverify.** If frontmatter has a `pr_url`, fetch the PR's current state. State `MERGED` and task not yet `done` → `complete_task`. State `CLOSED` and not merged → re-queue to `inbox`.
2. **Body-vs-frontmatter drift.** If body contains `## Release: merge_ready` but no `pr_url` exists, surface as `claim-without-pr` — do not auto-act.
3. **Worker-no-op marker.** If body contains `⚠️ Review needed (zero changes detected)` or `Worker finished without making changes`, re-queue to `inbox` with annotation.
4. **Repeated-sweep-failure marker.** If body contains ≥3 `## 🧹 Sweep Report` entries all reading `PR Closed without merge`, re-queue to `inbox`.

Output a `status-drift` block in the cycle summary and in `pr-state.json` under `status_drift`.

Time budget: 4a-bis adds at most 5 minutes to Phase 6.

**Activity 4b — gate-1 verification audit (including lens-task resolution).**

For tasks transitioned `in_progress → done` since the last cycle (up to 20 per cycle, oldest-modified first):

1. Look up the verification subtask the planner gate created at `inbox → ready`.
2. Look up any lens-tasks (security, accessibility, etc.) created during the same decomposition.
3. Confirm all such subtasks are in a terminal state (`done` or `cancelled` with rationale).
4. If any subtask is missing or unresolved: surface in cycle summary under `Loop-close gaps`. **Do NOT auto-close or auto-fail — surface only.**

### Re-queue policy (closed-without-merge): always to `inbox`

Closed-without-merge PRs carry new counter-evidence. The planner gate exists to re-decompose: AC, named file/symbol, verification subtask, lens subtasks. Bypassing it lets stale assumptions ride.

**Time budget**: Phase 6 gets 20 minutes max (10m baseline + 5m for Activity 4a/4b + 5m for Activity 4a-bis).

## Phase 7: Staleness Sweep

Detect orphans, stale docs, and under-specified tasks. The agent uses these as **signals**, not deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

**Per P#123 — age is not staleness.** Surface candidates for human review; do not auto-cancel based on age.

### Gate-1 artifact rot check

For each task in `ready` or `queued` whose age is ≥ 14 days (up to 20 per cycle, oldest-modified first):

1. Read the planner-gate outputs: AC bullets, named file/symbol, target repo.
2. Verify the named file/symbol still exists in the named repo (one-shot grep, like supervisor pre-flight does).
3. If artifacts have rotted: demote the task to `inbox` with an annotation:

```
# Demoted by /sleep YYYY-MM-DD: gate-1 artifacts no longer present (file deleted / symbol renamed). Re-decompose.
```

Age alone is not staleness — only artifact rot triggers demotion.

## Phase 8: Refile Processing

Process tasks the user has explicitly flagged for refiling via the dashboard's REFILE button.

1. **Find flagged tasks**: Grep for `refile: true` across `$ACA_DATA/tasks/`
2. **Reparent each task**: Invoke `/planner` in `maintain` mode for each flagged task.
3. **Clean up the flag**: After successful reparenting, remove the `refile` key from frontmatter.
4. **Handle ambiguity**: If the planner cannot determine a parent, flag in cycle summary. Remove `refile: true` and add `needs_triage: true`.

Rules:

- **No batch limit** — these are explicit user requests; process all of them.
- **Commits directly to main** — this is mechanical/autonomous work.
- **Runs before Phase 9** so graph metrics reflect the refile changes.

## Phase 9: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

### Convergence Detection

Before doing any work, compare the current `metrics_hash` from `graph_stats` against the previous cycle's hash.

- **If `metrics_hash` is identical**: the graph has converged. Skip Phase 9 entirely and log "graph converged — no structural changes needed."

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

- **Split oversized containers**: If an epic has >20 direct children, split it by theme using `bulk_reparent`.
- **Find misparented tasks**: Use `pkb_orphans` to find wrong-type-parent orphans and reparent to an appropriate epic.
- **Nest loose tasks**: For `flat_tasks`, read the task title and body, search for related epics/projects, and `bulk_reparent` to the best match. If no match, check if 3+ loose tasks share a theme — if so, create an epic.
- **Connect disconnected epics**: Prefer the epic's `frontmatter.project` slug. If missing, read title and children, search for matching projects. Do not infer project membership from task ID prefixes.

### Known Metric Limitations

- **`disconnected_epics`**: Only counts epics with no parent. Does NOT detect epics parented to the wrong project.
- **`flat_tasks`**: Tasks parented to a catch-all "misc" epic show as connected even if meaningless.
- **`orphan_count`**: Does not catch tasks parented to archived/cancelled containers.
- **`metrics_hash`**: Use for convergence detection — unchanged hash means metrics have stabilized.

Don't treat all-green metrics as "done." Spot-check qualitatively.

### What NOT to Do

- Don't reorganize for aesthetics. If a task is correctly parented but the grouping isn't pretty, leave it alone.
- Don't create epics speculatively. Only create when you have 3+ tasks that clearly belong together.
- Don't reparent based on keyword matching alone. Read the body to understand context.
- Don't split epics that are actively being worked. Flag for the next quiet period.
- Don't undo prior human decisions.

### Bounded Effort

Process up to 100 items per cycle (configurable via `batch_limit` workflow input). Use `mcp__pkb__bulk_reparent` for efficiency.

## Phase 10: Consolidation Self-Check (Lightweight)

A 2-minute sanity check of THIS cycle's own output.

For each knowledge note created or modified in this cycle:

- Does it have `sources:` in frontmatter?
- Does synthesis cite 2+ observations?
- Are wikilinks valid (not broken)?
- Is confidence level present and reasonable?

**On Failure**: log the issue in the cycle summary and flag it in the PR description. Do not try to fix content quality problems — that's the QA reviewer's job.

**Evaluation Feedback Loop**: When a pattern of quality issues is detected (same issue appearing across 3+ cycles):

1. Create a task describing the recurring quality pattern.
2. Link to examples — cite the specific notes/PRs where the issue appeared.
3. Propose a procedure update to `consolidate.md` or `quality-exemplars.md`.

Time budget: 2 minutes. Only check notes created/modified in THIS cycle.

## Active Loop Integration

When running via `/loop` or `/active-loop`:

1. Detect mode per [[remember]] Mode Detection rules.
2. Read the DRAFT PR body for prior cycle learnings.
3. Use the "Next" field from the last cycle to inform this cycle's Phase 9 strategy.
4. After Phase 11, update the PR body with the cycle log entry.
5. In short-loop mode, push to the persistent daily branch — do NOT open a new PR per cycle. Phases 2 and 4 must run every cycle.

## Design Principles

1. **Smart agents, not dumb code** — tools provide signals; the agent decides.
2. **Idempotent** — running twice produces the same result.
3. **Incremental** — only processes what's new since last run.
4. **Surfaces, doesn't decide** — flags candidates for human/supervised review.
5. **No moldy docs** — never creates knowledge docs without a named consumer.

## Cycle Summary Template

Every cycle emits a summary written to the PR body (or `$GITHUB_STEP_SUMMARY` on CI). Sections with no content are omitted (except `Sub-agent halts` which always renders, even at zero, as the silent-failure anti-pattern guard).

```markdown
# Sleep cycle summary — YYYY-MM-DD HH:MM (mode: <short-loop|full-session>; trigger: <signal>)

## Sub-agent halts

<count + per-phase tool gaps; or "none">

## Phase 0 — Graph Health

<baseline metrics_hash, key counts>

## Phase 2 — Transcript Mining

<N transcripts processed, M canonical notes touched>

## Phase 4 — Knowledge Consolidation

<N episodic sources consolidated, M canonical notes created/restructured>

## Phase 6 — Data Quality Reconciliation

- Activity 1 (dedup): <N merges, M ambiguous>
- Activity 2 (staleness): <N completed via evidence, M flagged for review, K skipped (CI guard)>
- Activity 3 (misclassification): <N archived/reclassified, M flagged>
- Activity 4a (PR-state sweep): <N closed by sweep, M re-queued to inbox, K ambiguous>
- Activity 4b (gate-1 verification audit): see Loop-close gaps below

## Phase 7 — Staleness Sweep

<orphan/stale candidates flagged; gate-1 artifact rot demotions: N>

## Phase 9 — Graph Maintenance

<strategy chosen, N items processed, metrics_hash delta>

## Phase 10 — Self-check

<pass/fail per check; flags for QA reviewer>

## Loop-close gaps

<tasks transitioned in_progress → done in this cycle whose verification subtask or lens-tasks are missing or unresolved; one bullet per task with task ID + reason. "none" if clean.>

## Next

<single-sentence forward note for the next cycle's Phase 9 strategy or unresolved threads>
```

## Output: Consolidation PR

Knowledge creation (Phases 2, 4) produces output of uncertain quality. This output MUST go through a QA gate before reaching the main branch.

### Process

1. Mechanical work (Phases 0, 1, 3, 5, 6, 7, 8, 9, 10, 11) commits directly to main.
2. Knowledge work (Phases 2, 4) commits to a branch — naming and PR cadence depend on the mode:
   - **Full-session**: fresh branch `sleep/consolidation-YYYY-MM-DD-HHMM` per cycle, one PR per cycle.
   - **Short-loop**: persistent daily branch `sleep/consolidation-YYYY-MM-DD`, one PR per day that accumulates commits from every cycle.
3. Create the PR against main on first use of the branch; subsequent short-loop cycles push to the existing PR.
4. The `/qa` skill reviews the PR for fitness-for-purpose.
5. Merge only after QA passes. On the brain repo, enable `gh pr merge --auto --squash` after Phase 10 passes.

### Graduation Path

- **Current**: Human reviews every consolidation PR.
- **Next**: `/qa` agent reviews, human reviews QA decisions.
- **Future**: `/qa` auto-approves, human reviews only rejections.
- **Autonomous**: Full auto-merge after sustained evidence of quality.

Each transition requires evidence from the previous level (P#22 corollary on graduated trust).

## Architecture

```
templates/github-workflows/sleep-cycle.yml   ← workflow template (maintained in $AOPS)
$ACA_DATA/.github/workflows/sleep-cycle.yml  ← installed copy (runs the agent)
```

Install via: `scripts/install-brain-workflows.sh <brain-repo-path>`

The workflow uses `anthropics/claude-code-action` to launch an agent with a consolidation prompt. The agent has access to the brain repo and academicOps tools. In CI, the agent works directly with markdown files — no PKB MCP server is available. Changes sync to PKB consumers via git push.
