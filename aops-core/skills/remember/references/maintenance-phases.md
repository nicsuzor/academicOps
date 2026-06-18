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

The parent sleep orchestrator may delegate Phase 2 (Transcript Mining), Phase 4 (Knowledge Consolidation), and the PKB Quality Review to parallel `junior` sub-agents. The junior agent profile exposes the necessary filesystem and shell access to discover transcripts, mark them as mined, and inspect git state.

When dispatching, ALWAYS pass the explicit `tools` argument to ensure the sub-agent gets the exact knowledge-work toolset it needs. Example invocation:

```
Agent(
  subagent_type='junior',
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

### PKB MCP Tool Mutator Invariants (dry_run Default)

The PKB MCP bulk/merge tools (`batch_update`, `batch_reparent`, `batch_merge`, and `merge_node`) default to `dry_run=true`. To actually mutate the knowledge graph or execute the write operations, the agent MUST explicitly specify `dry_run=false` in the tool input. Calling these tools with the default parameter or omitting `dry_run` will result in a preview/simulation only and will not modify data.

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
| 8     | Refile Processing           | Re-parent and re-weight user-flagged tasks (consequence, stakeholder, deps, due), remove flag        |
| 9     | Graph Maintenance           | Densify, reparent, or connect — pick ONE strategy                                                    |
| 10    | Consolidation Self-Check    | Lightweight sanity check of this cycle's own output                                                  |
| 11    | Brain Sync                  | Commit and push `$ACA_DATA`; re-run `graph_stats`                                                    |

## Phase 0: Graph Health Baseline

Run `graph_stats` at the start of every cycle. Record:

- `flat_tasks` — tasks with no parent or children
- `disconnected_epics` — epics with no parent edge and no `contributes_to` edge to a target — i.e. genuinely unmoored from the work hierarchy
- `targets_without_contributing_edges` — target nodes with zero inbound `contributes_to`
- `orphan_count` — truly disconnected nodes
- `stale_count` — tasks not modified in 7+ days while in_progress

**Then measure the knowledge layer separately.** `graph_stats.orphan_count` is **actionable-only** — it excludes `note`/`knowledge`/`memory` nodes entirely, so a healthy-looking `orphan_count` can still hide a large disconnected knowledge population. The live number is whatever the call below returns, never a figure quoted in prose. Run:

```
pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)
```

and record `knowledge_orphan_count` — the total it reports. This is the number Phase 7's sweep and Phase 9's knowledge-layer strategy converge against; `orphan_count` alone is not a convergence signal for the knowledge layer.

> **Detector behaviour.** Orphan detection is **type-aware** (mem#425, merged 2026-06-10; SSoT `mem/specs/pkb-server-spec.md` "Orphan Detection"). Actionable types orphan on a missing/dangling `parent` alone. Knowledge types (`memory`/`note`) and out-of-tree strategic nodes (`goal`/`target`) orphan only when they have **no valid parent AND no deliberate structural edge** in either direction — a body `[[wikilink]]` (auto-extracted into a `link` edge), an inbound link, or a `contributes_to` all clear orphan status; only auto-computed `similar_to` similarity edges are excluded. So `knowledge_orphan_count` is now the genuine residual: nodes with neither a parent nor any deliberate link. "Not an orphan" means graph-reachable — it does **not** certify the `/remember` curation contract (an outbound wikilink on every note), which is what Activity K still enforces. If you see a large one-off drop right after the detector fix reindexed, that drop is detector correction, not curation progress — do not claim it in the cycle delta.

This is the baseline. Phase 11 re-runs `graph_stats` **and** `pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)` to measure what changed in both layers.

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

2. **Route observations to canonical topic notes**: For each candidate, follow [[remember]]'s Canonical Topic Notes discipline — identify the first-class topic each insight is about, update the canonical note (or create one with a scaffold if missing), reconcile stale peers in the same write. Then mark the episodic source as `consolidated: YYYY-MM-DD` and advance its `status` to `done` in its frontmatter (do NOT modify the episodic content itself).

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
2. For high-confidence clusters: merge autonomously via `batch_merge` (passing `dry_run=false` to execute).
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

- **Merged** → run the AC-verification step in [[../../verify/references/merge-close-ac-check]] before closing: re-read the task's acceptance criteria against the merged artifact, classify mechanical vs judgment-laden. Every AC clearly met → `complete_task(id, completion_evidence="PR #N merged <ISO> — <url>", pr_url=<url>)`. Any unmet or judgment-laden AC → leave the task in `merge_ready` and log it to the ambiguous queue (surfaced in next `/daily` under "Needs your call"), quoting the criterion. Surface, do not block (#1426).
- **Closed-without-merge** → apply the [close-context routing protocol](#close-context-routing-protocol) below. Never re-queue automatically.
- **Open** → no-op.
- **No match** → log to ambiguous queue in artefact, surface in next `/daily`. Never invent a task.

PRs only — **no `git log` scanning**. Idempotent. Cursor advances only after writes succeed. Phase no-ops when PKB MCP unavailable (CI guard).

Artefact written to `$ACA_DATA/state/pr-state.json`.

**Activity 4a-bis — status-drift backstop (cursor-independent).**

For every task currently in `status: merge_ready` or `status: review` (cap 50 per cycle, oldest-modified first). **`status: merge_ready` and `status: review` are not the same parked state** — see the canonical protocol in [[taxonomy#status-values-and-transitions]]: `status: merge_ready` is parked on a PR and may auto-close on merge; `status: review` is parked on a _human decision_ and is **never auto-closed by this backstop** — the most it does to a `status: review` task is surface it. Treat the two sets accordingly:

1. **PR-status reverify (`merge_ready` only).** For a `merge_ready` task with a `pr_url`, fetch the PR's current state. State `MERGED` and task not yet `done` → run the AC-verification step ([[../../verify/references/merge-close-ac-check]]) against the merged artifact first; `complete_task` only if every AC is clearly met, else leave in `merge_ready` and surface the unmet/judgment-laden criterion to the ambiguous queue. State `CLOSED` and not merged → apply the close-context routing protocol (same as Activity 4a). A `merge_ready` task with **no** resolvable PR is anomalous → surface as `merge_ready-without-PR`. Never re-queue automatically. For a `review` task, **never auto-close**: if it carries a PR, note the live PR state in the surfaced item (merged = "confirm the decision and close", evidence not authority); if it has no PR (the common case), surface it as `awaiting-decision` so it cannot silently rot in the parked set.
2. **Body-vs-frontmatter drift.** If body contains `## Release: merge_ready` but no `pr_url` exists, surface as `claim-without-pr` — do not auto-act.
3. **Worker-no-op marker.** If body contains `⚠️ Review needed (zero changes detected)` or `Worker finished without making changes`, re-queue to `inbox` with annotation.
4. **Repeated-sweep-failure marker.** If body contains ≥3 `## 🧹 Sweep Report` entries all reading `PR Closed without merge`, treat as a `bad-implementation` signal when routing: include it in the context given to the routing sub-agent as strong evidence the approach keeps failing.

Output a `status-drift` block in the cycle summary and in `pr-state.json` under `status_drift`.

Time budget: 4a-bis adds at most 5 minutes to Phase 6.

**Activity 4b — gate-1 verification audit (including lens-task resolution).**

For tasks transitioned `in_progress → done` since the last cycle (up to 20 per cycle, oldest-modified first):

1. Look up the verification subtask the planner gate created at `inbox → ready`.
2. Look up any lens-tasks (security, accessibility, etc.) created during the same decomposition.
3. Confirm all such subtasks are in a terminal state (`done` or `cancelled` with rationale).
4. If any subtask is missing or unresolved: surface in cycle summary under `Loop-close gaps`. **Do NOT auto-close or auto-fail — surface only.**

### Close-context routing protocol

Applies whenever a PR was closed without merge. The action depends on close context — never defaults to re-queue.

**Step 1 — Gather close context.** Collect: PR title and body, last 10 reviewer comments, review state (approved/changes-requested/dismissed), PR labels, whether the branch was deleted, and whether a repeated-sweep-failure marker exists in the task body (≥3 sweep reports reading "PR Closed without merge").

**Step 2 — Invoke an agent to classify the close.** Pass the gathered context to a sub-agent. The agent must choose exactly one of:

| Class                  | Signal                                                                                                                    | Action                                                                                                                                                                                                                   |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **wontfix**            | Clear "don't do this", not-planned, superseded, reviewer explicitly rejects the goal (not just implementation)            | Mark task `cancelled` (or `done` if superseded by completed sibling). Note closing PR URL + close reason in task body. Do NOT file a follow-up.                                                                          |
| **bad-implementation** | Ambiguous, wrong approach, reviewer rejection of approach/design, repeated failure, or "needs rethink" language           | Mark original task `cancelled`. File a sibling investigation task (same parent, `soft_depends_on: [<original-id>]`) summarising what went wrong and what must change before redispatching. Do NOT re-queue the original. |
| **retry-as-is**        | Rare: unrelated infrastructure failure explicitly documented in PR comments; nothing about the task or approach was wrong | Re-queue to `inbox`. Log the justification explicitly in the sleep activity log and in the task body.                                                                                                                    |

**Agent invocation, not regex** — per `judgment-non-delegable` (AXIOMS.md). The agent reads the actual PR body and comments to make a semantic judgment. Do not string-match on "wontfix" or similar labels; the label is a signal, not the verdict.

**Investigation task format (bad-implementation route):**

```
title: "Investigate: <brief description of what went wrong with <original task title>>"
type: task
parent: <same parent as original task>
soft_depends_on: [<original-task-id>]
body: |
  ## Why this investigation exists
  PR #N for <original-task-id> (<original title>) was closed without merge.
  Close context: <brief summary of close reason and key reviewer signals>

  ## What must change before redispatching
  <agent's assessment: what was wrong with the approach, what questions must be answered first>

  ## Original task
  [[<original-task-id>]] — left in cancelled state, pointer back here.
```

**Sleep activity log per task** must record: the chosen route (wontfix / bad-implementation / retry-as-is), the close reason summary, and any follow-up node created.

**Time budget**: Phase 6 gets 20 minutes max (10m baseline + 5m for Activity 4a/4b + 5m for Activity 4a-bis).

## Phase 7: Staleness Sweep

Detect orphans, stale docs, and under-specified tasks. The agent uses these as **signals**, not deterministic verdicts:

- **Actionable orphan detection**: `mcp__pkb__pkb_orphans()` (defaults to actionable-only: task/epic/project/target). Feeds Phase 9's task/epic strategies.
- **Knowledge-layer orphan detection**: `mcp__pkb__pkb_orphans(types=["note","knowledge","memory"], include_all=true)`. This is a **separate population** the default actionable call never returns. Feed it to Phase 9's knowledge-layer curation strategy. Do not let an all-green actionable `orphan_count` stand in for knowledge-layer health; they are measured by different calls.
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

Process tasks the user has explicitly flagged for refiling. The `refile` flag means "something is obviously wrong with this task" — not just parentage, but any structural or weighting problem the user spotted.

### Steps

1. **Find flagged tasks**: Search for `refile: true` across `$ACA_DATA/`
2. **Reparent**: Invoke `/planner` in `maintain` mode to find the correct parent/lineage.
3. **Evaluate weight**: For each refiled task, review and fix the full weighting surface:
   - **Severity** — severity lives on `type: target` nodes only (see [[TAXONOMY.md#severity-ladder-sev0sev4]]). For target nodes, read the `consequence` text and match severity to the actual impact described. If consequence text is missing, write it. For ordinary tasks, do NOT assign non-zero severity — it inverts the focus queue. If a refiled task seems SEV3-worthy, ensure the consequence prose is accurate and add `needs_triage: true` to flag possible reclassification as a target.
   - **Stakeholder** — if someone is waiting on this task, set `stakeholder` to their name.
   - **Priority** — `priority` is Nic's personally curated intent, never agent estimation; never originate or auto-adjust a band from severity or apparent importance (canonical rule: [[framework-conventions-summary#intent-authority]]). If a band seems clearly misaligned (e.g. high-impact task sitting at P4 with no Nic signal), do **not** change it — add `needs_triage: true` and log the discrepancy for Nic's review (surface, don't set).
   - **Due date** — check whether the due date is missing, stale (past and not overdue-by-design), or obviously wrong. Fix if possible; add `needs_triage: true` if unclear.
   - **Effort** — if missing, estimate from task scope. Default 3d is often wrong for small tasks (marking = 1d, check-in = 1h).
   - **Dependencies** — if the task is clearly blocked by something, wire `depends_on` and set status to `blocked`. If it has obvious downstream dependants, wire those too.
   - **Tags** — ensure tags reflect the new parent lineage (e.g. `qut`, `teaching`, `llb242` for a task under Teaching & Admin > LLB242).
4. **Clean up the flag**: After successful reparenting and weight evaluation, remove `refile: true` from frontmatter.
5. **Handle ambiguity**: If the planner cannot determine a parent or the weight evaluation requires user judgment (e.g. unclear consequence severity, ambiguous due date), remove `refile: true` and add `needs_triage: true`. Log the specific ambiguity in the cycle summary.

### Rules

- **No batch limit** — these are explicit user requests; process all of them.
- **Commits directly to main** — this is mechanical/autonomous work.
- **Runs before Phase 9** so graph metrics reflect the refile changes.
- **Weight evaluation uses the task's own content and context** — read the body, consequence, email thread, and parent lineage to make informed judgments. Don't just copy fields from the parent.
- **Log changes** — for each refiled task, note what changed (parent, severity, stakeholder, etc.) in the cycle summary so the user can review.

## Phase 9: Graph Maintenance

**Delegates to the Planner agent's `maintain` mode.** Sleep selects the strategy based on graph_stats; Planner executes it.

### Convergence Detection

Before doing any work, compare the current `metrics_hash` from `graph_stats` against the previous cycle's hash.

- **If `metrics_hash` is identical**: the **actionable** graph has converged. Skip the actionable strategies and log "actionable graph converged — no structural changes needed." **Do not skip Knowledge-Layer Curation on this basis** — `metrics_hash` is derived from actionable-only `graph_stats` and is blind to `knowledge_orphan_count`. Run Activity K whenever its own trigger (`knowledge_orphan_count` > 50) and terminal condition say to.
- **If 2 consecutive cycles produce no-ops**: the graph is stable. Cancel the active-loop cron if running via `/loop` — but only once **both** the actionable terminal condition **and** the knowledge-layer terminal condition (below) are met.

### Strategy Selection

Each cycle, pick ONE strategy based on what graph_stats shows needs the most attention:

| Condition                                 | Strategy               | Planner Activity                                       |
| ----------------------------------------- | ---------------------- | ------------------------------------------------------ |
| `disconnected_epics` > 10                 | Connect epics          | Reparent — find project parents for disconnected epics |
| `targets_without_contributing_edges` > 10 | Wire edges             | Wire edges via `/planner wire-edges` flow              |
| `flat_tasks` > 100                        | Reparent flat tasks    | Reparent — find epic/project parents for orphans       |
| `orphan_count` > 20                       | Fix orphans            | Reparent — connect or archive disconnected nodes       |
| `knowledge_orphan_count` > 50             | Curate knowledge layer | Knowledge-Layer Curation (below) — one bounded batch   |
| All metrics healthy                       | Densify edges          | Densify — use strategies to add dependency edges       |

**Two strategies per cycle when both layers need work.** The strategy table is "pick ONE" for the _actionable_ layer. The knowledge layer is a parallel population on a different metric (`knowledge_orphan_count`, Phase 0), so a cycle may run one actionable strategy **and** one Knowledge-Layer Curation batch. Keep each within its own bounded-effort cap; do not let knowledge curation crowd out actionable work or vice versa.

### Concrete Agent Instructions

- **Split oversized containers**: If an epic has >20 direct children, split it by theme using `batch_reparent` (passing `dry_run=false` to execute).
- **Find misparented tasks**: Use `pkb_orphans` to find wrong-type-parent orphans and reparent to an appropriate epic.
- **Nest loose tasks**: For `flat_tasks`, read the task title and body, search for related epics, and `batch_reparent` (passing `dry_run=false` to execute) to the best match. If no match, check if 3+ loose tasks share a theme — if so, create an epic.
- **Connect disconnected epics**: The parent for an orphan is an `epic` (or a root-level `epic` if it's a top-level area). The `frontmatter.project` field is a polecat slug — use it only to discover _which repo_ the work belongs to for context, not as a parent ID.

### Knowledge-Layer Curation (Activity K)

Triggered when `knowledge_orphan_count` (Phase 0) > 50. This is the knowledge-layer analogue of the task/epic reparenting above, enforcing the [[remember]] / pauli **Relational Integrity** rule ("never allow orphan nodes or unlinked knowledge to persist"; "every note weaves into the graph with back-references") that previously had no repair loop. It carries the **same surface-don't-decide discipline as Phase 8/9**: mechanical, unambiguous dispositions execute autonomously; anything requiring judgment is flagged for human review, never guessed.

**Input.** The knowledge-orphan list from Phase 7: `pkb_orphans(types=["note","knowledge","memory"], include_all=true)`.

**Per-orphan triage — assign exactly one disposition.** Read the node (title, tags, `created`/`modified`, body). Do not act on title/tag keywords alone (same rule as task reparenting). Classify:

| Disposition       | Signal                                                                                                                                                             | Action                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **link/reparent** | Active knowledge whose parent concept clearly exists in the graph (a canonical topic note, MOC, or epic).                                                          | Add the structured edge to that parent (`batch_reparent`/`batch_update`, `dry_run=false`). For memories (no `parent` param at capture), a body `[[wikilink]]` to a live hub is the preferred, lighter-weight connection — under the type-aware detector (Phase 0 note) a deliberate wikilink in either direction clears orphan status for knowledge types just as a structured parent does. Either way, connect to a node that is itself graph-reachable, not to another orphan. |
| **MOC**           | A cluster of 5+ orphans on one first-class topic, no hub note exists.                                                                                              | Create/extend a Map of Content per [[remember]] Maps-of-Content guidance and wire the cluster under it. MOCs are earned, not scheduled — only when the cluster is real.                                                                                                                                                                                                                                                                                                          |
| **merge**         | Duplicate / near-duplicate of an existing canonical note (confirm via `find_duplicates` or `search`).                                                              | `merge_node`/`batch_merge` (`dry_run=false`) into the canonical note, preserving provenance.                                                                                                                                                                                                                                                                                                                                                                                     |
| **archive**       | Legacy import or superseded episodic record with no live consumer — e.g. `career-planning-*` / OneNote imports from 2016–19, `status: done`, no current relevance. | **Verify by observation first**: confirm zero inbound references (`pkb_context` backlinks / `search`) — "no live consumer" must be observed, never assumed from title or age. Any inbound reference or doubt → SURFACE instead. Then `batch_archive` with reason. Per P#123 **age alone is not the trigger** — archive only when irrelevance is established by content, not date. Reversible (archive ≠ delete).                                                                 |
| **SURFACE**       | Ambiguous parent, possible-but-unconfirmed duplicate, or anything where the right home needs human judgment.                                                       | Flag in the cycle summary's knowledge-orphan block with the node ID and the specific ambiguity. **Do not guess a parent.**                                                                                                                                                                                                                                                                                                                                                       |

**Bounded effort.** Process up to 100 knowledge orphans per cycle (shares the `batch_limit` cap with the actionable strategy; split the budget — do not let either starve the other). Quality over coverage: a wrong reparent is worse than a surfaced one.

**What NOT to do.** All Phase 9 "What NOT to Do" rules apply, plus: don't reparent a knowledge node to a task; don't create MOCs speculatively (5+ real cluster members, not 2); don't archive on age alone (P#123); don't archive without the inbound-reference check — an unread consumer is exactly what "reversible" does not protect against; don't fabricate a parent to clear the count — an unsurfaced wrong home is the failure this activity exists to prevent.

**Terminal condition (knowledge layer).** Independent of the actionable-layer terminal condition. Knowledge curation is complete for the loop when EITHER `knowledge_orphan_count` is unchanged for 2 consecutive cycles (the residual is the genuinely-SURFACE population awaiting human calls), OR two consecutive cycles process zero non-SURFACE dispositions. Track the per-cycle `knowledge_orphan_count` delta in the summary so the downward trend (or its stall) is visible — a flat count with a growing SURFACE queue means the loop has done its mechanical share and the remainder needs Nic.

### Known Metric Limitations

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

Process up to 100 items per cycle (configurable via `batch_limit` workflow input). Use `mcp__pkb__batch_reparent` (passing `dry_run=false` to execute) for efficiency.

### Terminal Condition

Graph maintenance is complete when EITHER of:

1. `metrics_hash` unchanged for 2 consecutive cycles.
2. Two cycles in a row where Phase 9 processed zero items.

When terminal condition is met during an active loop: cancel the cron/loop and log the final `graph_stats` snapshot.

## Phase 10: Consolidation Self-Check (Lightweight)

A 2-minute sanity check of THIS cycle's own output.

For each knowledge note created or modified in this cycle:

- Does it have `sources:` in frontmatter?
- Does synthesis cite 2+ observations?
- Are wikilinks valid (not broken)?
- Is confidence level present and reasonable?

For each episodic source consolidated in this cycle:

- Is its `status` advanced from `inbox` (e.g., to `done`)?

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

<baseline metrics_hash, key actionable counts; knowledge_orphan_count (this cycle) vs. previous cycle — render the delta, e.g. "knowledge_orphan_count: 84 (was 100, −16)">

## Phase 2 — Transcript Mining

<N transcripts processed, M canonical notes touched>

## Phase 4 — Knowledge Consolidation

<N episodic sources consolidated, M canonical notes created/restructured>

## Phase 6 — Data Quality Reconciliation

- Activity 1 (dedup): <N merges, M ambiguous>
- Activity 2 (staleness): <N completed via evidence, M flagged for review, K skipped (CI guard)>
- Activity 3 (misclassification): <N archived/reclassified, M flagged>
- Activity 4a (PR-state sweep): <N merged→closed; for closed-without-merge: X wontfix-cancelled, Y bad-impl-investigation-filed (list task IDs), Z retry-requeued (list task IDs + justification), K ambiguous>
- Activity 4b (gate-1 verification audit): see Loop-close gaps below

## Phase 7 — Staleness Sweep

<actionable orphan/stale candidates flagged; gate-1 artifact rot demotions: N; knowledge-layer orphans detected: N (from the types=["note","knowledge","memory"] call)>

## Phase 9 — Graph Maintenance

<actionable strategy chosen, N items processed, metrics_hash delta>

### Knowledge-Layer Curation (Activity K)

<knowledge_orphan_count start → end (delta); dispositions: X linked/reparented, Y MOC'd, Z merged, W archived, S surfaced-for-review. List node IDs (with one-line reason) for every **archived** and **merged** node — a bare count is not reviewable — plus IDs of surfaced + any ambiguous. "skipped — under trigger" or "converged — count stable 2 cycles" when not run.>

## Phase 10 — Self-check

<pass/fail per check; flags for QA reviewer>

## Loop-close gaps

<tasks transitioned in_progress → done in this cycle whose verification subtask or lens-tasks are missing or unresolved; one bullet per task with task ID + reason. "none" if clean.>

## Next

<single-sentence forward note for the next cycle's Phase 9 strategy or unresolved threads>
```

## Output: Consolidation PR

Knowledge creation (Phases 2, 4) produces output of uncertain quality. This output MUST go through a QA gate before reaching the main branch.

### Process & Environment Policy

**Policy Decision on Auto-commits:** We accept that **local sleep cycles commit directly to the active branch (intended to be main)**. The PKB MCP tool is a long-running process that auto-commits all writes; toggling this per-session is fragile. Because local cycles are manually triggered and supervised, bypassing the PR/QA gate is acceptable. The graduation path (PR → QA → Auto-merge) applies strictly to remote GitHub Actions runs, where the MCP server is absent and the agent uses standard git branching.

1. Mechanical work (Phases 0, 1, 3, 5, 6, 7, 8, 9, 10, 11) commits directly to the active branch.
2. Knowledge work (Phases 2, 4) requires review.
   - **Local Environment**: Due to PKB MCP auto-commits, all writes go directly to the active branch. Do not attempt to branch or stash.
   - **CI Environment (Full-session)**: fresh branch `sleep/consolidation-YYYY-MM-DD-HHMM` per cycle, one PR per cycle.
   - **CI Environment (Short-loop)**: persistent daily branch `sleep/consolidation-YYYY-MM-DD`, one PR per day that accumulates commits from every cycle.
3. On CI, create the PR against main on first use of the branch; subsequent short-loop cycles push to the existing PR.
4. On CI, the `/qa` skill reviews the PR for fitness-for-purpose.
5. On CI, merge only after QA passes. On the brain repo, enable `gh pr merge --auto --squash` after Phase 10 passes.

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
