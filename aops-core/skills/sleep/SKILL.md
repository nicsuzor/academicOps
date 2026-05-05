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

> **Taxonomy note**: This skill orchestrates periodic offline consolidation — transforming write-optimised storage (tasks, session logs) into read-optimised knowledge that agents actually use. Full design rationale lives in the brain PKB (project: aops, topic: sleep-cycle).

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

### Sub-Agent Dispatch (Phases 2, 4, and Quality Review)

The parent sleep orchestrator may delegate Phase 2 (Transcript Mining), Phase 4 (Knowledge Consolidation), and the PKB Quality Review to parallel `aops-core:pauli` sub-agents. Pauli's default profile only exposes a narrow Read/Skill/PKB-MCP toolset because pauli is also used in non-sleep contexts where Bash/Edit are inappropriate. **Sleep dispatch is the exception**: the consolidation phases need filesystem and shell access to discover transcripts, mark them as mined, and inspect git state.

When dispatching, ALWAYS pass the explicit `tools` argument so the sub-agent inherits the knowledge-work toolset rather than the lean default. Example invocation:

```
Agent(
  subagent_type='aops-core:pauli',
  prompt='Execute Phase 2 (Transcript Mining) per aops-core/skills/sleep/SKILL.md. Process up to 15 unmined transcripts under $AOPS_SESSIONS. Report HALT explicitly if any required tool is missing.',
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

**Edit scope**: `Edit` is granted ONLY to mark transcripts as `mined: YYYY-MM-DD` in their frontmatter. Transcripts live OUTSIDE `$ACA_DATA` (typically `/Users/suzor/.aops/sessions/transcripts/*.md` or `$AOPS_SESSIONS/**/*.md`), which is the explicit exception carved out by the [[remember]] skill's hard rules. Sub-agents must NOT use `Edit` to modify anything inside `$ACA_DATA` — knowledge writes go through PKB MCP tools.

**CI environment**: when running on GitHub Actions, the PKB MCP server is unavailable (see "CI-Specific Rules" in the workflow prompts). In that environment the sub-agents work directly against markdown files via `Bash`/`Glob`/`Edit`/`Write` and the dispatch can omit the `mcp__plugin_aops-core_pkb__*` entries. The parent must surface this clearly in the dispatched prompt so the sub-agent knows which channel is live.

**Do NOT add these tools to pauli's default profile** (`aops-core/agents/pauli.md`). The toolset is dispatch-context-specific; pauli is also invoked by James, Marsha, and during interactive `/planner` work where Bash/Edit are inappropriate.

### Halt Surfacing (Anti-Silent-Failure)

Sub-agents are instructed to emit a literal `HALT:` line and the missing tool name when a required tool is unavailable, rather than fabricating output. The parent orchestrator MUST:

1. Parse each sub-agent return for any of the markers `HALT:`, `HALTED`, `tool gap`, `tool not available`, or `cannot proceed: missing tool`.
2. Maintain a halt counter across all dispatched sub-agents in the cycle.
3. Surface the count in the final cycle report (and in `$GITHUB_STEP_SUMMARY` on CI), with the affected phase names and missing tools listed. Example summary line: `Sub-agent halts: 2 (Phase 2 — missing Bash; Phase 4 — missing mcp__plugin_aops-core_pkb__append)`.
4. If the halt count is non-zero, the cycle exit code/PR description must call this out at the TOP — not buried inside per-phase output. This closes the silent-failure mode where halts were only visible inside individual sub-agent returns.

```bash
# Trigger via GitHub Actions (runs in $ACA_DATA repo)
gh workflow run sleep-cycle -R nicsuzor/brain

# Manual invocation as a skill
/sleep

# Focus on a specific area
gh workflow run sleep-cycle -R nicsuzor/brain -f focus="staleness only"
```

## Pacing & Mode

The skill runs in two modes with different output cadences. **Detect the mode at the start of every cycle** and pick the matching output strategy. This is the fix for #712 — under `/loop` short intervals the per-cycle PR-and-QA gate is too heavy and Phases 2/4 get skipped, defeating the purpose of the cycle.

### Mode detection

Pick the first signal that matches:

1. **Explicit flag**: `SLEEP_MODE=short-loop` or `SLEEP_MODE=full-session` in the environment overrides everything.
2. **Loop interval**: if `LOOP_INTERVAL_MINUTES` (or `CLAUDE_LOOP_INTERVAL_MINUTES`) is set and `<= 30`, mode is `short-loop`.
3. **Loop context**: if the invocation prompt or transcript shows the skill was launched by `/loop` (e.g., recurring `/sleep` invocations within the same session) and prior cycles in this session exist, treat as `short-loop`.
4. **Default**: `full-session` (manual `/sleep` and GHA cron).

Log the detected mode and the signal that determined it in the cycle summary.

### Short-loop mode (interval <= 30m, in-session)

- **Always run Phases 2 and 4.** They are the highest-value work; never skip them because the output gate feels heavy. If the gate is the obstacle, change the gate (below), not the work.
- **Persistent branch per day**: use `sleep/consolidation-YYYY-MM-DD` (no `-HHMM` suffix). Reuse it across every cycle in the day. Create on first cycle, fast-forward / rebase from main on later cycles.
- **Accumulate commits**: each cycle adds commits to the same branch — one commit per phase that produced output is fine.
- **No PR per cycle.** Open the PR on the _first_ cycle of the day if it doesn't exist; subsequent cycles push to the same branch and the PR updates automatically.
- **QA runs once per day** (or on demand), not per cycle. The PR description should note "short-loop accumulation; QA on close" so reviewers know not to expect a per-cycle gate.
- **Time budget per cycle**: keep Phase 4 to ~5 minutes and Phase 2 to ~5 minutes when interval is 20m or less. Quality over coverage — better one well-sourced note than five superficial ones.

### Full-session mode (manual `/sleep`, GHA cron)

Existing behaviour, unchanged:

- Branch: `sleep/consolidation-YYYY-MM-DD-HHMM` (timestamped, fresh per invocation).
- One PR per cycle.
- `/qa` review per PR before merge.
- Time budgets per phase as documented in each phase below.

### Brain repo auto-merge

On the **brain repo only** (`$ACA_DATA`, currently `nicsuzor/brain`), and ONLY after Phase 10 self-check passes, enable auto-merge on the consolidation PR:

```bash
gh pr merge --auto --squash -R nicsuzor/brain <pr-number>
```

The branch acts as recovery/audit trail, not a blocking gate — brain consolidation is low-blast-radius (knowledge notes, not code) and the per-cycle review backlog is the bigger risk. Per #448 graduated-trust rules:

- Auto-merge is enabled ONLY on the brain repo. Never on `academicOps` or any other repo.
- Auto-merge requires Phase 10 self-check to have **passed** (no failures logged). On any Phase 10 failure, do NOT enable auto-merge — leave the PR open for human review.
- This applies in both modes. In short-loop mode this means the daily branch auto-merges once it's green; in full-session mode each per-cycle PR auto-merges once green.

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

### Garden Pass Discipline (P#123)

Per [[../../HEURISTICS.md#P123|P#123 — Age Is Not A Staleness Signal]]: when this phase encounters old episodic sources, do NOT recommend cancellation based on age alone. Only relevance — not age — justifies cancellation. Garden passes here surface candidates for human review; they do not recommend cancellation.

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
   - Deadline >90d past + zero evidence of any activity → flag in cycle summary for human review (per [P#123](../../HEURISTICS.md#P123), age alone does not establish irrelevance)
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

### Activity 4: Loop-close (PR-state sweep + gate-1 verification audit)

Two checks added to Phase 6 — not new phases. Per `spec-7715b135` §4.

> **Planning note**: Putting Activity 4a (PR-state sweep) under Phase 6 alongside Activity 4b (gate-1 verification audit) is a planning choice for grouping data-quality-class loop-close work, not a spec mandate. Future readers may re-litigate placement if Phase 6 starts feeling overloaded.

**Activity 4a — PR-state sweep.**

For each tracked repo (`$ACA_DATA/state/tracked-repos.json`, initial `["nicsuzor/academicOps", "nicsuzor/brain"]`), for each PR closed since the cursor at `$ACA_DATA/state/close-loop-cursor.json`:

Match PR → task by precedence:

1. `pr_url` already on the task
2. `task-XXXXXXXX` ID found in PR body
3. PR `headRefName` matches the task's recorded branch
4. PR title matches task title (whole-word, ignoring `feat()` / `fix()` / `chore()` prefixes)

Resolution:

- **Merged** → `complete_task(id, completion_evidence="PR #N merged <ISO> — <url>", pr_url=<url>)`.
- **Closed-without-merge** → re-queue to `inbox` (always; see Re-queue policy below); append reviewer comments via `mcp__pkb__append`.
- **Open** → no-op (optional `pr_url` annotation if missing).
- **No match** → log to ambiguous queue in artefact, surface in next `/daily`. Never invent a task.

PRs only — **no `git log` scanning**. Idempotent. Cursor advances only after writes succeed. Phase no-ops when PKB MCP unavailable (CI guard per `.agents/CAPABILITIES.md`).

Artefact written to `$ACA_DATA/state/pr-state.json` for `/daily` and dashboard consumers (single producer / two consumers).

**Activity 4b — gate-1 verification audit.**

For tasks transitioned `in_progress → done` since the last cycle, look up the verification subtask the planner gate (`spec-64352eac`) created at `inbox → ready`. Confirm terminal state (`done` or `cancelled` with rationale). If missing or unresolved, surface in the cycle summary under `Loop-close gaps`. **Do NOT auto-close or auto-fail — surface only.**

> **Planner-gate discoverability gap (open)**: `spec-64352eac` requires planners to emit a verification subtask but does not yet mandate a tag, title prefix, or `kind: verification` frontmatter field that makes that subtask programmatically discoverable. Activity 4b currently relies on heuristics (subtasks of the just-completed task whose title contains "verify" / "verification" / "QA" or whose body cites the parent's AC). When the convention is firmed up in `spec-64352eac`, replace the heuristic with the explicit signal and tighten the audit. Until then, false negatives are expected and `Loop-close gaps` surfacing is conservative.

### Re-queue policy (closed-without-merge): always to `inbox`

Closed-without-merge PRs carry new counter-evidence (review comments, surfaced bugs). The planner gate (`spec-64352eac`) exists precisely to re-decompose: AC, named file/symbol, verification subtask, lens subtasks. Bypassing it would let stale assumptions ride. Reviewer comments are appended to the task body either way, preserving visibility. Cost is one extra trip through the planner gate — that is the design intent.

**Time budget**: Phase 6 gets 15 minutes max (10m baseline + 5m for Activity 4). Exit the phase when time is up.

## Phase 7: Staleness Sweep

Detect orphans, stale docs, and under-specified tasks. The agent uses these as **signals**, not as deterministic verdicts:

- **PKB orphan detection**: `mcp__pkb__pkb_orphans()`
- **Git log**: Recent commits, task changes since last cycle
- **Own judgment**: The agent reads flagged tasks and decides whether they genuinely need attention.

**Per [HEURISTICS P#123](../../HEURISTICS.md#P123) — age is not staleness.** Surface candidates for human review; do not auto-cancel based on age. Cancellation requires evidence the work has become irrelevant, not just that it is old.

### Gate-1 artifact rot check

For each task in `ready` or `queued` whose age is ≥ 14 days: read the planner-gate outputs recorded on the task (acceptance criteria, named file/symbol, target repo); verify the named file/symbol still exists in the named repo (same grep mechanic Part A row 2 uses for supervisor pre-flight). If rotted (file deleted, symbol renamed, repo no longer contains it), demote to `inbox` with an annotation appended to the body:

```
# Demoted by /sleep YYYY-MM-DD: gate-1 artifacts no longer present (file deleted / symbol renamed). Re-decompose.
```

Per `spec-7715b135` §4: surface, don't decide — the demotion is mechanical (artifacts no longer exist), not editorial. Per P#123: age alone is not staleness — only artifact rot triggers demotion. A 14-day-old `ready` task whose artifacts still exist is left alone.

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

**Find misparented tasks**: Use `pkb_orphans` to find wrong-type-parent orphans (e.g., a task parented directly to a project instead of an epic). For each, find an appropriate epic under the same project (use `list_tasks(type="epic", project="<project-id>")` to enumerate candidates rather than walking the parent chain) and reparent. If no suitable epic exists, create one.

**Nest loose tasks**: For `flat_tasks` (tasks with no parent), read the task title and body, search for related epics/projects via `search`, and `bulk_reparent` to the best match. If no match exists, check if 3+ loose tasks share a theme — if so, create an epic to contain them.

**Connect disconnected epics**: For each disconnected epic, prefer the epic's `frontmatter.project` slug and resolve the matching project directly. If `project` is missing, read the title and children, search for matching projects via `search`, and reparent. Do not infer project membership from task ID prefixes or by walking unrelated parent chains. If no project matches, flag for human review.

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

1. Detect mode per "Pacing & Mode" — `/loop` invocations with interval <= 30m are `short-loop`.
2. Read the DRAFT PR body for prior cycle learnings.
3. Use the "Next" field from the last cycle to inform this cycle's Phase 9 strategy.
4. After Phase 11, update the PR body with the cycle log entry.
5. In short-loop mode, push to the persistent daily branch and let the existing PR auto-update — do NOT open a new PR per cycle. Phases 2 and 4 must run every cycle (#712).

## Design Principles

1. **Smart agents, not dumb code** — tools provide signals; the agent decides
2. **Idempotent** — running twice produces the same result
3. **Incremental** — only processes what's new since last run
4. **Surfaces, doesn't decide** — flags candidates for human/supervised review
5. **No moldy docs** — never creates knowledge docs without a named consumer
6. **Agents can consolidate (hypothesis under test)** — we believe agents can perform the episodic→semantic transformation given proper value alignment, clear provenance requirements, and bounded autonomy. The `/qa` review on each consolidation PR tests this hypothesis. If quality review reveals persistent problems, escalate enforcement — don't just trust harder.

## Cycle Summary Template

Every cycle emits a summary written to the PR body (or `$GITHUB_STEP_SUMMARY` on CI). Sections appear in this order; sections with no content are omitted (except `Sub-agent halts` which always renders, even at zero, as the silent-failure anti-pattern guard).

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

<tasks transitioned in_progress → done in this cycle whose verification subtask is missing or unresolved; one bullet per task with task ID + reason. "none" if clean.>

## Next

<single-sentence forward note for the next cycle's Phase 9 strategy or unresolved threads>
```

The `Loop-close gaps` section is the dedicated surface for Activity 4b output. It is **information for review** — never converted to an automatic action by the cycle itself. The section is omitted when empty.

## Output: Consolidation PR

Knowledge creation (Phases 2, 4) produces output of uncertain quality. This output MUST go through a QA gate before reaching the main branch. The sleep cycle creates a PR — it never commits knowledge directly to main.

### Process

1. Mechanical work (Phases 0, 1, 3, 5, 6, 7, 8, 9, 10, 11) commits directly to main — deterministic and verifiable.
2. Knowledge work (Phases 2, 4) commits to a branch — naming and PR cadence depend on the mode (see "Pacing & Mode" above):
   - **Full-session**: fresh branch `sleep/consolidation-YYYY-MM-DD-HHMM` per cycle, one PR per cycle.
   - **Short-loop**: persistent daily branch `sleep/consolidation-YYYY-MM-DD`, one PR per day that accumulates commits from every cycle.
3. Create the PR against main on first use of the branch; subsequent short-loop cycles push to the existing PR.
4. The `/qa` skill reviews the PR for fitness-for-purpose. In short-loop mode, QA runs once per day (or on demand) on the accumulated branch, not per cycle.
5. Merge only after QA passes. On the brain repo, enable `gh pr merge --auto --squash` after Phase 10 passes (see "Brain repo auto-merge" above). During supervised phase on other repos, human reviews the QA decision.

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
