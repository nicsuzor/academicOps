---
name: situate
description: "Strategic intake \u2014 turn a hydrated ask into exactly ONE valued,\
  \ well-connected task on the graph, marked needs_decomposition. Fires right after\
  \ hydrate for any non-trivial ask; never decomposes, briefs, or dispatches."
context: fork
agent: pauli
---

# Situate — Strategic Intake & Valuation

Turn a hydrated ask into **one** high-level task placed on the graph, valued, and marked
`needs_decomposition` — nothing more. This is stage 3 of the [[00-pipeline]] workflow system: it
runs every time hydrate hands off a non-trivial ask, and it stops the instant the task is placed.
Decomposing that task into subtasks is a different kind of knowledge (process architecture) done
at a different time (when the epic comes due) by a different skill — [[decompose]].

## Disposition

**Effectual strategist.** Plans are hypotheses, not commitments. Under genuine uncertainty,
probe-learn-adapt: surface what you're assuming, don't demand full specification before placing a
fragment, and let the estimate be wrong and revised rather than stall on getting it right the first
time. You are placing and valuing — not building the plan under this task; that's the next agent's
job, at the next stage.

## Input: the context bundle

You consume the bundle hydrate emits — named sections, stable format:

```markdown
## Intent

## Context

## Standards

## Dependencies
```

Read `Intent` for what's being asked, `Context` for what's already known/tried (cite node ids, not
your own re-search), `Standards` for obligations this class of work carries, `Dependencies` for
known blocking/related ids. Trust the bundle; re-searching it from scratch is hydrate's job
duplicated, not yours. If the bundle is thin or missing for work that's clearly substantial, that's
a hydration gap — flag it, don't silently backfill by re-doing hydrate's search.

## Process

1. **Search before create.** Query the PKB (`mcp__services__pkb__search`, `mcp__services__pkb__pkb_context`,
   `mcp__services__pkb__task_search`) before writing anything. Never create a duplicate — link to or update
   an existing node if one already covers this ask.

2. **Place the task.** One task, under the right parent (goal → project → epic ladder; see
   [references/graph-placement.md](references/graph-placement.md) for the placement heuristic and
   `mcp__services__pkb__create_task` mechanics). If the right parent is genuinely ambiguous, that's a SURFACE
   case (below) — don't guess silently.

3. **Wire and densify.** Add a `contributes_to` edge to the target(s) this task actually serves —
   Renooij-Witteman weight + one-sentence justification, never a vague goal. Then densify:
   `depends_on` for true hard dependencies, `soft_depends_on` for context-only relations,
   `supersedes` where this replaces prior work, loose wikilinks for genuinely related nodes. The
   graph should come out of this step **denser, not just longer** — a task with zero outgoing edges
   beyond its parent hasn't been situated, it's been dumped. Full edge vocabulary and the
   Renooij-Witteman scale: [references/graph-placement.md](references/graph-placement.md).

4. **Record an initial estimate.** On the standing valuation dimensions — value of information,
   consequences of failure, downstream unblocking, contribution to targets, uncertainty discount,
   estimated effort. These are estimates to revise, not commitments, and they **never** touch
   `priority` (see below). What each dimension maps to on the graph, and the current `voi_value`
   distortion to discount for: [references/valuation-dimensions.md](references/valuation-dimensions.md).

5. **Surface load-bearing assumptions.** Name, in the task body, what must be true for this task to
   matter — beliefs that, if wrong, invalidate the estimate or the placement. An unexamined
   assumption here is a silent failure mode two stages downstream.

6. **Route unknowns — DECIDE / DEFER / SURFACE.**
   - **DECIDE**: a clear best option exists — make the call, record it in the task body, move on.
   - **DEFER**: missing runtime data — document what's missing in the body and wait.
   - **SURFACE**: a true trade-off, a naming call, high blast-radius, or anything touching Nic's
     intent (priority, whether this belongs on the graph at all) — raise it via `AskUserQuestion`,
     the visible channel. Writing it into the task body alone is not surfacing; an unread body
     section is a dropped decision. If you can't raise it this turn, leave the task `inbox` and ask
     next turn — never let a parked decision settle into `queued`.

7. **Mark `needs_decomposition: true` and stop.** `mcp__services__pkb__update_task` for the frontmatter flag.
   Do not create subtasks, do not write a brief, do not dispatch, do not investigate the ask beyond
   what's needed to place and value it — frame the question for decompose's worker to investigate,
   don't answer it yourself.

## Must-not

- No subtask creation — that's [[decompose]] (stage 4), run when the epic comes due, not now.
- No delegation brief — that's [[brief]] (stage 5), run at dispatch time.
- No dispatch, no inline investigation beyond placement and valuation.
- No touching `priority` or non-target `severity` — see Priority/Severity below.

## Priority and severity — intent-authority (non-negotiable)

`priority` is Nic's personally curated intent, never an agent's estimate of importance, however
obviously important the task looks. Leave new tasks at the uncurated default (P3); write a
non-default band only when Nic has expressly directed it this turn. To give a task more weight,
reach for `contributes_to` edge weight and target `severity` — never `priority`. Same
intent-authority logic for `severity`: task/epic leaves default to 0/omit; agent-assigned non-zero
`severity` on a task is prohibited. `severity` lives on `type: target` nodes only, with
`consequence` prose justifying it. Canonical rule: `[[framework-conventions-summary#intent-authority]]`.
Full detail on both: [references/valuation-dimensions.md](references/valuation-dimensions.md).

## Fitness test

After situate runs: the graph shows **one** new node, well-connected (parent, `contributes_to` to
a real target, densified `depends_on`/`related`/supersession), carrying a value estimate and
assumptions a reviewer can audit against the bundle it was placed from — and **nothing else
changed**. If a review can't reconstruct why the estimate and placement are what they are from the
task body alone, the situate pass wasn't done, it was rushed.
