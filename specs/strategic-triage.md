---
title: "Strategic Triage: Scheduled Effectual Planning"
type: spec
status: draft
tier: workflow
created: 2026-03-09
depends_on:
  - effectual-planning-agent
  - sleep-cycle
tags:
  - spec
  - planning
  - scheduling
  - prioritisation
---

# Strategic Triage: Scheduled Effectual Planning

## Giving Effect

_No implementation yet. This spec defines a scheduled agent that detects structural patterns in the task graph — blocking chains, convergence points, last-domino situations — and surfaces 3-5 strategic recommendations per cycle. It operationalises the effectual planner's Mode 3 (Prioritisation), with the structural analysis done unsupervised and qualitative judgment (assumption testing, information value) applied in evaluation._

- [[specs/effectual-planning-agent.md]] — upstream: strategic planning philosophy, information-value prioritisation
- [[specs/sleep-cycle.md]] — sibling: runs on the same cron infrastructure, consolidates knowledge (this spec consolidates _intent_)
- [[aops-core/workflows/decompose.md]] — downstream: when a ripe epic needs breaking down
- [[specs/research-decomposition.md]] — downstream: domain-specific decomposition for research tasks

## Problem

The task graph has 700+ nodes. ~580 are leaves. Most have no dependency edges, so `downstream_weight` — the strongest priority signal — is zero for the vast majority of tasks. The effectual planner spec describes information-value prioritisation beautifully, but nothing runs it. The user opens `/daily` and gets a firehose of "ready" tasks with no strategic lens applied.

The result: the user becomes the bottleneck. They hold the strategic context in their head, manually decide what matters, and agents wait for instructions. This is the opposite of what the framework promises — externalising cognitive load.

### What's missing

The sleep cycle consolidates knowledge. Densify adds graph edges. But no agent asks the strategic question: **"Given what we know right now, what are the 3-5 highest-information-value things to work on next?"**

### Critical upstream dependency: graph density

Triage quality depends directly on graph edge density. In dogfooding (2026-03-10), only ~20 of 600 ready tasks had any `downstream_weight` at all — the rest were invisible to structural analysis. **Densify must run before triage** in the scheduled cycle to maximise the signal available. The sleep cycle should incorporate a densification pass as a precursor to triage, not just knowledge consolidation.

Without edges, triage degrades to sorting by priority — which `/daily` already does. The value proposition depends on having enough graph structure to detect blocking chains, convergence points, and last-domino situations.

### What triage requires judgment for

This question is not a sort operation. It requires understanding:

- What gets _unblocked_ if this succeeds? (downstream weight, blocking chains)
- Where do multiple threads converge? (convergence points)
- What would we _learn_ from doing this? (information value — assessed qualitatively, not from topology)
- Is this _ready_ to be worked on, or does it need decomposition first? (maturity)
- Is this the right _time_ for this? (context: what's active, what's blocked, what just completed)

## Design Principles

1. **Selectivity is the product.** The graph has hundreds of candidates. The agent's value is in surfacing 3-5, not 50. If it recommends more than 5 things, it has failed. The user is overwhelmed, not under-informed.

2. **Information value over urgency.** Prioritise by what you'd learn, not what's overdue. A spike that tests a load-bearing assumption outranks a routine task that's been "ready" for weeks. This is the effectual planner's core insight (§ Information Value Prioritisation).

3. **Satisficing, not optimising.** Don't try to find the globally optimal set. Find a _good enough_ set that balances learning, unblocking, and feasibility. Bounded rationality (Simon) — the search itself has a cost.

4. **Maturity-aware.** Not everything that's important is ready. A vague epic needs a seedling sketch, not a task assignment. A mature epic with clear acceptance criteria is ready for `/pull`. The agent must distinguish between "this matters" and "this is actionable right now."

5. **Unsupervised scan, supervised decision.** Like the sleep cycle's Principle 5: the agent does the legwork (graph scan, evaluation, draft decompositions) and stages recommendations. The user or `/daily` makes the final call. The triage agent never assigns work to other agents directly.

6. **Cumulative, not repetitive.** Each cycle builds on the last. If a recommendation was surfaced and the user deferred it, don't re-surface it the next cycle. Track what's been presented and what decision was made (or not made).

## User Expectations

### Current State (Design & Dogfooding)

The system is currently in the **design phase**. There is no automated cron job running this logic. Users should expect:

- **No automatic recommendations** in the daily note.
- **Manual validation only**: Triage logic is currently verified through manual walkthroughs (see Dogfooding Results) to tune the selection heuristics.
- **Implementation Pending**: The `triage` skill and its integration into the `sleep-cycle` are scheduled for the next development burst.

### Target State (Implemented)

Once the triage agent is operational, a user should be able to verify its performance against these criteria:

1. **Extreme Selectivity**: The `## Strategic Triage` section in the daily note contains exactly 3–5 recommendations. If the agent surfaces more than 5 or fewer than 3 (given a pool of at least 10 candidates), it is failing its primary mandate of noise reduction.
2. **Structural Justification**: Every recommendation must include a "Why Now" argument that references at least one structural signal (e.g., "High downstream weight," "Last domino," or "Convergence point"). It must not rely solely on existing P-levels.
3. **Maturity Routing**: Recommendations must be explicitly categorized by readiness:
   - **Ready for `/pull`**: Actionable in a single session with clear AC.
   - **Needs Decomposition**: High strategic value but requires a supervised planning session first.
   - **Seedling**: Requires qualitative sketching before structural commitment.
4. **Information Value Priority**: At least one recommendation per cycle should be a "spike" or "learn" type task that tests a load-bearing assumption, even if its structural weight is lower than routine tasks.
5. **Persistence and Deferral**: The agent must respect prior user decisions. A deferred recommendation should not reappear in the next cycle unless a significant change has occurred in the task's dependency neighbourhood (e.g., a prerequisite was completed or a new dependent was added).
6. **Densify Pre-requisite**: Triage quality is a function of graph density. Triage must be preceded by a `densify` pass in the same scheduled cycle; if densification fails, triage should be aborted to prevent low-signal recommendations.

## Architecture

### Schedule

Runs as a phase within the sleep cycle's scheduled invocation (on github)

**Execution order within the sleep cycle**: (1) knowledge consolidation, (2) **densification** (add missing dependency edges), (3) **triage** (scan enriched graph, stage recommendations). Densify must run before triage — triage quality depends directly on edge density.

### Cycle

One cycle, time-bounded (~15 min). Three phases, run sequentially.

#### Phase 1: Graph Scan (5 min)

**Purpose**: Build a picture of the graph's current state and identify candidate nodes.

The agent uses PKB graph tools to gather structural signals:

```
get_network_metrics()          → downstream_weight, PageRank, centrality
list_tasks(status="ready")     → the ready queue
list_tasks(status="blocked")   → what's waiting
get_dependency_tree(id)        → for high-weight nodes: what do they unblock?
pkb_orphans()                  → disconnected nodes that may be forgotten priorities
pkb_context(id, hops=2)        → neighbourhood of promising candidates
```

**From structural signals, identify candidates using two lenses:**

| Lens            | Question                                                    | Signal                                                                                                                                        |
| --------------- | ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Unblocking**  | What, if completed, would unblock the most downstream work? | High `downstream_weight`, tasks with dependents in `blocked` status, "last domino" situations (all other blockers already resolved)           |
| **Convergence** | Where do multiple threads meet?                             | Follow dependency trees from high-weight nodes; when two independent ready tasks unblock the same downstream node, that's a convergence point |

**Note on convergence detection**: `get_network_metrics` requires a specific node ID — there is no bulk "top N highest-centrality nodes" query. In practice, convergence is discovered by following dependency trees from high-weight candidates and noticing when they meet. This is accidental rather than systematic; a future bulk centrality endpoint would improve Phase 1 significantly.

**Note on assumption testing**: The original design placed "assumption testing" as a Phase 1 scan lens. Dogfooding showed this doesn't work — graph topology doesn't encode assumption criticality. Whether a task tests a load-bearing hypothesis requires reading the task body and understanding the project context. Assumption testing is a **Phase 2 evaluation criterion**, not a Phase 1 structural signal.

**Candidate pool**: ~10-15 nodes. This is the long list, not the recommendation.

#### Phase 2: Evaluate and Select (5 min)

**Purpose**: From the candidate pool, select 3-5 recommendations using qualitative judgment.

For each candidate, the agent evaluates:

1. **Information value and assumption testing**: What would completing this teach us? Does it test an assumption? Does it resolve uncertainty that's blocking planning elsewhere? A task that produces _knowledge_ (spike, lit-review, pilot) ranks higher than one that produces _output_ (writing, data-collection) when both are available — because knowledge reshapes the plan. This is where spikes and learn-type tasks get elevated — not from topology, but from reading the task body and understanding what's at stake.

2. **Readiness**: Is this actionable right now?
   - **Ready for `/pull`**: Clear scope, acceptance criteria, single-session deliverable. An agent could pick this up.
   - **Needs decomposition**: Important but too big or vague for a single agent. Recommend decomposition first.
   - **Seedling**: Important but immature. Recommend a seedling-mode sketch (effectual planner or research decomposition) before committing structure.

3. **Context fit**: What just happened? What's active? Completing a spike is higher value if the parent project has momentum. Starting a new thread when 3 are already active may increase cognitive load rather than reduce it.

4. **Staleness risk**: Has this been recommended before and deferred? If so, note it — but don't automatically re-recommend. Respect the user's prior decision unless circumstances changed.

5. **Multi-project balance**: If all 3-5 recommendations come from a single project, flag this explicitly. Consider whether at least one cross-project recommendation is warranted. Pure information-value ranking tends to favour whichever project has the richest graph structure — which may be the framework itself, not the user's research.

6. **P0 floor**: Existing P0 designations represent user judgment about importance. P0 tasks are always candidates. The triage agent's value-add is in selecting _among_ P0s and in surfacing non-P0 tasks that have high structural leverage.

**Output**: 3-5 ranked recommendations, each with:

- The task/epic and its graph context (what it connects to)
- Why now: the information-value argument in 1-2 sentences
- Readiness assessment: ready / needs decomposition / seedling
- If needs decomposition: a draft decomposition outline (not full task creation — that's the user's call)

#### Phase 3: Stage Recommendations (5 min)

**Purpose**: Make the recommendations available to the user and downstream skills.

**Output target**: A `## Strategic Triage` section in the current daily note, consumed by `/daily` and `/briefing-bundle`.

The daily note is the single output. Previous daily notes serve as the longitudinal record — no separate triage log or task annotations needed. This avoids creating new artifacts to maintain and keeps the reasoning where the decision happens.

For each recommendation, the section includes: the task ID and title, what it connects to (blocking chain / convergence), a 1-2 sentence "why now" argument, and a readiness assessment.

### What This Does NOT Do

- **Does not create tasks.** Decomposition drafts are recommendations, not commitments. Task creation requires user approval or a supervised session (`/pull`, `/daily`).
- **Does not assign work.** It surfaces what's valuable; it doesn't dispatch agents. The polecat/swarm infrastructure handles dispatch.
- **Does not replace `/daily`.** The daily skill handles human-facing briefing, email, focus. Triage provides a strategic input _to_ daily, not a replacement.
- **Does not replace the effectual planner.** The planner is an interactive thinking partner. Triage is its unsupervised batch-mode complement — it pre-digests the graph so the planner (or the user) can make faster decisions.
- **Does not prioritise everything.** If a task isn't in the top 5, it's not mentioned. Silence is a signal: "not this cycle."

## Relationship to Existing Components

| Component                  | Relationship                                                                                                                                                                                                                                                                                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Effectual planner**      | Triage operationalises Mode 3 (Prioritisation). The planner's information-value heuristic (`downstream_weight × assumption_criticality`) is the core selection criterion.                                                                                                                            |
| **Sleep cycle**            | Sibling scheduled agent. Sleep consolidates knowledge (write → read). Triage consolidates intent (graph → recommendations). They share infrastructure but don't overlap in function.                                                                                                                 |
| **Densify**                | **Critical upstream.** Densify enriches graph edges; triage reads those edges to compute downstream weight. Without densification, most tasks have zero weight and triage degrades to priority sorting. Densify should run as part of the sleep cycle, before triage, on every scheduled invocation. |
| **`/daily`**               | Downstream consumer. Triage outputs feed into daily note recommendations. Today, `/daily` uses operational heuristics (SHOULD/DEEP/ENJOY/QUICK/UNBLOCK). Triage adds a strategic layer.                                                                                                              |
| **`/pull`**                | Downstream. Tasks that triage marks "ready for `/pull`" are the highest-value items for agents to claim.                                                                                                                                                                                             |
| **Decompose workflow**     | Invoked when triage identifies an epic that "needs decomposition." Triage drafts the outline; the user or a supervised agent runs the full decomposition.                                                                                                                                            |
| **Research decomposition** | Specialisation. When the epic needing decomposition is a research project, the research decomposition spec provides domain-specific primitives.                                                                                                                                                      |

## Worked Example

The graph contains 650 ready tasks. The triage agent scans and finds:

**Candidate pool (12 nodes):**

- 3 high-downstream-weight tasks (each blocks 4+ downstream tasks)
- 2 convergence points (reachable from 3 active projects each)
- 4 spikes testing assumptions in active projects
- 3 orphans that might be forgotten priorities

**Evaluation narrows to 4 recommendations:**

1. **`spike: validate ethics board timeline` (ready for /pull)**
   _Why now_: Blocks the entire governance study data-collection phase. The assumption "ethics approval takes 4-6 weeks" is load-bearing and untested. Completing this spike (1 session) would either unblock data-collection or force an early pivot. Information value: very high.

2. **`epic: platform API access feasibility` (needs decomposition)**
   _Why now_: Three separate projects assume API access to the same platform. This convergence point affects all three. But the epic is vague — "check if we can get API access" isn't actionable. Recommend decomposition into: (a) identify API terms of service, (b) check rate limits against data needs, (c) draft data management plan for ethics.

3. **`learn: survey comparable governance frameworks` (ready for /pull)**
   _Why now_: Literature review that would inform methodology for 2 active projects. Downstream weight is moderate but the cross-project synergy makes it high-leverage. A single agent session could produce a structured summary.

4. **`task: update dashboard focus scoring weights` (ready for /pull)**
   _Why now_: The current scoring weights don't reflect the recent densify work — `downstream_weight` is now meaningful for more tasks but the dashboard still weights it at 25%. A quick calibration session would improve every subsequent triage cycle. Self-improving.

**Not recommended (deferred with reasoning in triage log):**

- 8 other candidates: individually valuable but lower information-value or no urgency this cycle.

## Anti-Patterns

- **Recommending more than 5 items.** The whole point is selectivity. More than 5 means the agent isn't making judgment calls — it's making lists.
- **Ranking by age or status alone.** "This has been ready for 3 weeks" is not an information-value argument. Old tasks may be old for good reasons.
- **Re-surfacing deferred items without new evidence.** If the user said "not now" last cycle, respect that unless the graph has changed (new dependency, blocked task, completed prerequisite).
- **Creating tasks without user approval.** Decomposition drafts are proposals. The triage agent does not write to the task graph.
- **Trying to be comprehensive.** The triage agent does not audit the whole graph. It samples strategically, evaluates qualitatively, and recommends sparingly.

## Open Questions

1. **Deferred item tracking.** How does the agent know what was already recommended and deferred? Current answer: previous daily notes serve as the record. This may be insufficient if the agent doesn't read prior daily notes before each cycle. May need a lightweight `triage_last_recommended` date in task frontmatter, but that adds process overhead.

2. **Integration with `/daily` task recommendations.** Resolved: augment, not replace. Operational heuristics handle "what can I do in 25 minutes between meetings." Triage handles "what's strategically most important this week."

3. **Decomposition depth.** When triage identifies an epic that needs decomposition, how much decomposition should it draft? Proposed: outline only (3-5 bullet points with dependency sketch). Full decomposition is a supervised activity.

4. **Feedback loop.** How do we learn whether triage recommendations were good? If the user consistently ignores certain types of recommendations, the selection criteria should adapt. Session insights could track "triage recommendation → was it acted on?" but this requires instrumentation.

5. **Bulk centrality query.** Convergence detection currently requires following dependency chains and noticing when they meet. A PKB endpoint that returns the top-N highest-centrality or highest-downstream-weight nodes would make Phase 1 systematic rather than accidental.

## Assumptions About This Spec

| #  | Assumption                                                           | Confidence | Validation                                                                                                                                                                                                                                                                     | If wrong                                                                                             |
| -- | -------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| T1 | 3-5 recommendations is the right selectivity level                   | Medium     | Track whether users act on recommendations; too many = reduce, too few = increase                                                                                                                                                                                              | Adjust the cap based on observed behaviour                                                           |
| T2 | Information value is a better selection criterion than urgency       | Medium     | Compare triage recommendations against what users actually choose to work on                                                                                                                                                                                                   | May need a blended criterion that includes urgency for deadline-sensitive work                       |
| T3 | Graph metrics provide sufficient signal for candidate identification | Low        | Dogfooding (2026-03-10): only ~20/600 ready tasks had any downstream_weight. Structural signals alone identify unblocking and convergence candidates but miss assumption-testing value entirely. Densify-before-triage is a mitigation; text-based search may still be needed. | Supplement with text-based search (task body content, not just topology); increase densify frequency |
| T4 | 4-hour cadence is appropriate                                        | Low        | Attached to sleep cycle for now. Track whether recommendations are stale by the time the user sees them; natural trigger may be before `/daily` rather than on a fixed schedule                                                                                                | Adjust cadence; may decouple from sleep cycle if on-demand proves more useful                        |
| T5 | Unsupervised scan + supervised decision is the right boundary        | High       | Core framework principle (sleep cycle P5); validate that staged recommendations are actionable without re-scanning                                                                                                                                                             | If recommendations need too much context to act on, the triage output format needs enrichment        |

## Dogfooding Results (2026-03-10)

The spec's Phase 1–2 cycle was run against the live task graph (600 ready, 37 blocked, 16 orphans). Results:

**What the spec actually operationalises**: structural pattern detection — last dominoes (all other blockers resolved, one task remaining), convergence points (independent ready tasks feeding the same downstream node), and blocking chain depth. This is narrower than "information-value prioritisation" but useful and not currently done by anything else.

**What it doesn't operationalise**: assumption criticality. The heuristic `information_value ≈ downstream_weight × assumption_criticality` is half-computable. The downstream_weight half works from topology. The assumption_criticality half requires qualitative judgment in Phase 2.

**Four recommendations produced**: (1) assignee field policy spec — highest weight, unblocks 4-task chain; (2) create_task path bug — converges on same downstream node as #1; (3) profile mapping probe — P0 gate-opener for research strategy; (4) OSB methodology audit — last domino, one session to unblock publication. The set was defensible and cross-project (2 framework, 1 research, 1 OSB).

**Key finding**: graph density is the binding constraint. Only ~20 of 600 ready tasks had any downstream_weight. Densify must run before triage.

## Implementation Sketch

```
specs/strategic-triage.md           ← this spec
aops-core/skills/triage/            ← skill definition
aops-core/scripts/triage.py         ← orchestrator (3 phases, time-bounded)
scripts/repo-sync-cron.sh           ← add `triage` function alongside transcript/sync/viz
```

Phase 1 implementation: manual invocation only (`/triage`). Validate the selection quality before scheduling.

## Related

- [[specs/effectual-planning-agent.md]] — upstream: strategic planning philosophy
- [[specs/sleep-cycle.md]] — sibling scheduled agent (knowledge consolidation)
- [[specs/research-decomposition.md]] — domain-specific decomposition
- [[aops-core/workflows/decompose.md]] — general decomposition workflow
- [[specs/task-focus-scoring.md]] — current scoring system; triage provides a strategic overlay
