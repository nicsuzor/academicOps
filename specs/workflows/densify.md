---
id: workflows-0210e04c
title: Densify Workflow — Progressive Wikilinking of the Knowledge Graph
type: spec
status: inbox
tier: workflow
depends_on: [sleep-cycle, planner, pkb-server-spec]
tags: [spec, workflow, knowledge-graph, wikilinks, consolidation, densification]
created: 2026-04-28
---

# Densify Workflow — Progressive Wikilinking of the Knowledge Graph

## Problem

The PKB is supposed to be a dense knowledge graph — atomic notes joined by `[[wikilinks]]` such that any concept is reachable by following two or three edges. The actual graph is sparse:

- Bulk imports (consolidations like the spec migration of 2026-04-28, retrospective backfills, transcript mining) drop in dozens of files at once. Bodies retain whatever cross-references the source had — usually path-based, often to files that no longer exist. The set is a connected subgraph internally; it is essentially disconnected from the rest of the PKB.
- Newly authored notes link to things the author was thinking about at write time, not to everything they're conceptually adjacent to. Densification by sole author drift is slow.
- Path-based wikilinks (`[[specs/foo.md]]`) survive a layout reorg as orphan references because Obsidian resolves by basename.
- Existing `pkb` tooling has the raw materials (`pkb_search`, `pkb_context`, `find_duplicates`, `pkb_orphans`) but nothing routes them into a workflow that adds edges.

The [[sleep-cycle]]'s Phase 9 picks "densify edges" as a strategy when other graph metrics are healthy, and delegates to [[pauli|planner]]'s `maintain` mode. But that branch is about **task-graph edges** — `DependsOn` / `SoftDependsOn` between work items. There is no equivalent for **knowledge-graph edges** — `[[wikilinks]]` between concepts, specs, references, knowledge notes.

This spec defines the **densify** workflow that fills that gap.

## Giving Effect

- [[sleep-cycle]] — densify will plug in as one of sleep's Phase 9 strategies (alongside today's task-graph variant)
- [[pauli]] — densify can be invoked in planner's `maintain` mode
- [[pkb-server-spec]] — uses `pkb_search`, `pkb_context`, `pkb_orphans`, `find_duplicates`, document CRUD
- [[batch-graph-operations]] — bulk frontmatter / append operations
- [[remember]] (skill) — densify defers to remember for the mechanics of writing wikilinks (where in the body, what alias text)
- [[conceptual-review-workflow]] — output goes through conceptual review on PR before merge

## Two Modes — Knowledge vs. Task

The verb "densify" already overloads. Be explicit:

| Mode                  | Edge type                       | Owner          | Scope                                                                       |
| --------------------- | ------------------------------- | -------------- | --------------------------------------------------------------------------- |
| `densify --tasks`     | `DependsOn`, `SoftDependsOn`    | [[planner]]    | Existing Phase 9 strategy. Adds dependency edges between work items.        |
| `densify --knowledge` | `[[wikilinks]]`, related-blocks | densify itself | **NEW.** Adds wikilinks between concept/spec/reference/knowledge documents. |

This spec is principally about `--knowledge`. The two modes share scaffolding (candidate selection, batching, convergence detection, PR gate) but diverge in the per-document operation.

## Values

These are the same values as [[sleep-cycle]] — densify is a peer process under the same discipline.

1. **Never fabricate** — only suggest a wikilink between two documents when the relationship is grounded in their actual content. "These had similar embeddings" is not enough; an agent that has read both must be able to articulate the relationship in one sentence.
2. **Always track provenance** — every added wikilink carries an explanation. A bare `[[Foo]]` at the end of a file is worse than no link.
3. **Preserve content** — densify only adds edges. It does not rewrite paragraphs, retitle sections, or reword the body. Adds to a `## Related` block at the foot, or inserts wikilinks at carefully chosen anchor points (see Anchor Discipline below).
4. **Leave editorialising to the user** — densify does not assert "X is more important than Y" or restructure the conceptual hierarchy. It connects what's already there.
5. **Respect uncertainty** — confidence in a suggested edge falls into three buckets: high (clear conceptual overlap, both docs reference the same primary subject), medium (plausible relationship), low (semantic match without obvious conceptual link). High goes through autonomously; medium is suggested and surfaced; low is dropped.
6. **Quality over quantity** — one well-grounded edge beats ten mechanically-derived ones. Bounded effort per cycle, terminal condition when the graph stops changing.
7. **Defer to remember** — the discipline of how a wikilink lives in a note (alias usage, "See:" footer convention, related-block format) lives in `/remember`. Densify does not duplicate or contradict those rules.
8. **Judgment over procedure (pauli)** — pauli (or the agent acting in the pauli role) decides when a suggested edge is worth adding. Heuristics surface candidates; the agent makes the call.

## How It Works

Densify is an **agent session**, not a script. Like [[sleep-cycle]], it is launched periodically (cron or via `/densify`) with a consolidation prompt. Tools provide signals; the agent decides.

```bash
# Manual invocation
/densify

# Focus on a specific subset
/densify --scope=knowledge --target=projects/aops/specs/

# As a sleep phase
/sleep --phase=9 --strategy=densify-knowledge
```

## Phases

| Phase | Name                        | What it does                                                               |
| ----- | --------------------------- | -------------------------------------------------------------------------- |
| 0     | Baseline                    | Run `graph_stats`; record per-doc wikilink density distribution            |
| 1     | Candidate Selection         | Pick a bounded set of documents with low link density                      |
| 2     | Path Wikilink Normalisation | Mechanical: `[[specs/foo.md]]` → `[[foo]]` across the candidate set        |
| 3     | Backlink Discovery          | For each candidate, query `pkb_context` and `pkb_search` for neighbours    |
| 4     | Suggestion Generation       | Per (candidate, neighbour) pair, agent reads both and proposes a wikilink  |
| 5     | Triage                      | Each suggestion classified high / medium / low confidence                  |
| 6     | Application                 | High-confidence: append to `## Related`. Medium: surface in PR description |
| 7     | Convergence Self-Check      | Did density actually improve? Are there spurious edges?                    |
| 8     | Output PR + QA Gate         | Branch `densify/YYYY-MM-DD-HHMM`, PR for [[conceptual-review-workflow]]    |

## Phase 1: Candidate Selection

Pick a bounded set per cycle (default 20 docs). Strategies, in priority order:

1. **Newly imported, never densified.** Frontmatter has no `densified:` marker. Bulk imports surface here.
2. **Lowest density first.** Compute `outgoing_wikilinks / body_word_count`. Bottom decile.
3. **Recently modified, drifted from the graph.** Modified in the last 30 days, with `outgoing_wikilinks - prior_outgoing_wikilinks <= 0`. The note moved but its connections didn't.
4. **Hub gaps.** Run `pkb_orphans` — any node not reachable from a hub MOC is a candidate.

Record the strategy used in the cycle log so the dashboard can show what densify is currently working on.

## Phase 2: Path Wikilink Normalisation (mechanical, autonomous)

Across every candidate document, rewrite path-style wikilinks to basename-only:

| Source                      | Becomes                                                                              |
| --------------------------- | ------------------------------------------------------------------------------------ |
| `[[specs/foo.md]]`          | `[[foo]]`                                                                            |
| `[[foo.md]]`                | `[[foo]]`                                                                            |
| `[[specs/foo.md\|alias]]`   | `[[foo\|alias]]`                                                                     |
| `[[path/to/dir/]]` (no .md) | `` `path/to/dir/` `` (downgrade to inline code — this is a path, not a concept link) |

Pure regex on body, masked-out fenced and inline code. Idempotent. This pass is autonomous — no judgment required.

## Phase 3: Backlink Discovery

For each candidate doc D:

1. `pkb_context(D, hops=2)` — current 2-hop neighbourhood
2. `pkb_search(D.title + D.first_paragraph, k=20)` — semantically related docs
3. `find_duplicates(D)` — flag near-duplicates for separate handling (densify is not the right tool for merges)

Difference set = `search_results − current_neighbours − dupes`. This is the candidate edge set.

## Phase 4: Suggestion Generation

This is the expensive phase. For each (D, candidate-neighbour) pair, the agent:

1. Reads D and the neighbour in full.
2. Asks itself: **what is the conceptual relationship in one sentence?** If the answer is "they both contain similar words" or "I'm not sure", the pair is dropped.
3. If the relationship is real, drafts a one-line context note in the form:
   `- [[Neighbour]] — <one-line explanation of how the two relate>`
4. Records the suggestion with confidence (high / medium / low).

This step deliberately blocks on agent reading. Mechanical similarity scores produce noise; reading produces signal. The bounded effort budget (15 minutes / cycle as a default) limits how many pairs get this treatment.

## Phase 5: Triage

Per suggestion, confidence is assigned by these signals:

- **High** — D and neighbour share a primary subject; one cites the other in body text; one is a logical successor (e.g., a follow-up spec to a vision doc).
- **Medium** — Plausible relationship but not central. The link makes the graph richer but isn't load-bearing.
- **Low** — Vague semantic similarity. Drop.

## Phase 6: Application

- **High confidence** — append to `## Related` block at the foot of D. Create the block if absent. Per `/remember` discipline, the block lists wikilinks with one-line context.
- **Medium confidence** — surface in the PR description as a "review-and-decide" block. Do not write to D.
- **Low** — dropped, not surfaced.

The frontmatter gets a `densified: YYYY-MM-DD` marker. Not `modified:` — that field has its own meaning (see [[issue-taxonomy-gap-A]]).

## Phase 7: Convergence Self-Check

Re-run Phase 0 metrics. Compare per-doc density delta. Sanity check:

- Did at least one document's density actually increase?
- Are there suspected spurious edges (e.g., the same `## Related` block on too many docs — signal of a too-permissive search threshold)?
- Did any document end up with > N wikilinks in `## Related`? (likely a sign of over-application; trim or split)

If two consecutive cycles produce no high-confidence edges across the entire candidate set, **terminal condition**: the graph is densified to the threshold of the available signals. Cancel the loop and log "densify converged."

## Phase 8: Output PR + QA Gate

Same as [[sleep-cycle]]'s Phase 11. Knowledge work — even at this conservative grain — must go through a review gate.

- Branch `densify/YYYY-MM-DD-HHMM`
- PR description includes:
  - Strategy used
  - Candidate set (count + sample titles)
  - High-confidence edges added (full list)
  - Medium-confidence edges flagged for human review (full list, with one-line context)
  - Density delta per doc
- [[conceptual-review-workflow]] runs on the PR; reviewer can accept, reject, or restructure
- Merge only after review passes

## Anchor Discipline

When applying a wikilink inside a body paragraph (rare — the default is the `## Related` footer), choose anchors carefully:

- **Prefer first-mention.** If a paragraph mentions Foo and we're linking Foo, link the first occurrence.
- **Don't double-link.** One wikilink per (doc, target) pair. If `[[Foo]]` already appears elsewhere, the related-block entry is sufficient.
- **Don't link in code.** Anchors inside code fences or inline code stay literal.
- **Don't link in the title.** The title is the wikilink target; linking it from inside the doc is circular.

## Bounded Effort

Per-cycle defaults (override via `--budget`):

- 20 candidate docs
- 30 minute soft time cap on Phase 4 (the expensive one)
- Up to 10 high-confidence edges added per doc
- One PR per cycle

## Idempotence

- `densified: YYYY-MM-DD` frontmatter marker — Phase 1 candidate selection skips docs marked within the last 30 days (configurable)
- High-confidence edges already present in `## Related` are no-ops
- The same suggestion run twice produces the same suggestion

## Convergence

Two terminal conditions, either fires:

1. Two consecutive cycles add zero high-confidence edges across the candidate set
2. Mean per-doc density across the PKB stabilises within ±1% across two cycles

When terminal condition is met during an active loop, cancel the cron and log the final density distribution. Do not keep cycling.

## What Densify Does NOT Do

- **Does not merge near-duplicates.** That's `find_duplicates` + `merge_node` (a different operation).
- **Does not rewrite bodies.** Read-only on existing prose. Only appends to `## Related` and rewrites path-style wikilinks (Phase 2).
- **Does not change frontmatter beyond `densified:`.** The linter owns id/type/etc.
- **Does not assert dependency edges between tasks.** That's `densify --tasks` via planner.
- **Does not create new documents.** No new MOCs, no new concept notes. Hub creation is `/remember`'s job.

## Architecture

```
templates/github-workflows/densify.yml         ← workflow template (in $AOPS, parallel to sleep-cycle.yml)
$ACA_DATA/.github/workflows/densify.yml        ← installed copy (runs the agent)
aops-core/skills/densify/SKILL.md              ← skill itself
aops-core/skills/densify/procedures/           ← procedures (Phase 4 prompt, anchor discipline rules)
```

The skill follows the same install path as [[sleep-cycle]]. Most logic lives in the SKILL.md and procedures; the workflow YAML just dispatches the agent.

## User Expectations

### What densify is for

Users expect densify to **make the PKB feel connected**. Today, opening a recently-imported doc shows zero backlinks. After densify has passed, opening the same doc shows a `## Related` block with three to ten meaningful wikilinks, each with a one-line explanation that helps the user decide whether to follow the link.

### What densify is not for

Densify does not write knowledge. It does not synthesise. It does not produce understanding. It surfaces existing relationships. If two docs have no real relationship, densify leaves them alone.

### Quality bar

A user reading the `## Related` block should never think "why is X linked here?" If they ever do, the cycle's QA gate is failing — surface that pattern back into procedure improvements via the [[feedback-loops]] mechanism.

## Acceptance Criteria

1. Running `/densify` on a set of newly imported docs produces a PR with a `## Related` block on each, populated with one to ten high-confidence wikilinks.
2. Each wikilink in the `## Related` block has a one-line context note.
3. No path-style wikilinks remain in the candidate set after Phase 2.
4. Frontmatter has `densified: YYYY-MM-DD` on every document touched.
5. The PR description lists medium-confidence suggestions for human review.
6. Re-running densify on the same set within 30 days is a no-op.
7. The density metric (mean wikilinks per doc) increases monotonically across cycles until convergence.

## Risks

- **Spurious linking.** Semantic similarity can find shallow matches. Mitigated by Phase 4's "agent reads both docs" requirement and Phase 5's confidence triage.
- **Over-application.** A single doc accumulating too many `## Related` entries hides signal in noise. Mitigated by per-doc cap (10 high-confidence per cycle) and Phase 7's spurious-edge check.
- **Cost.** Phase 4 is expensive — every (D, neighbour) pair is an LLM read. Mitigated by bounded candidate set and time-cap.
- **Compounds with bad imports.** A bulk import with bad source content gets densified and the bad content propagates as suggestions. Mitigated by the QA gate on the densify PR.

## Out of Scope

- Densifying the task graph (that's `densify --tasks` via [[planner]] / Phase 9 of [[sleep-cycle]]; existing).
- Auto-generating MOCs from clusters (that's `/remember` when a cluster grows past 5 docs).
- Reconciling duplicate docs (that's `find_duplicates` + `merge_node`).
- Auto-resolving contradictions across docs (that's a future spec; densify only adds edges, never reconciles content).

## Open Questions

- Should densify surface _missing_ docs? E.g., when 3+ candidates all share a concept that has no canonical note, suggest creating one. (Lean: no — that's `/remember`'s job, surface as a flag instead.)
- How does densify interact with `Supersedes` edges? When A supersedes B, should A inherit B's incoming wikilinks? (Lean: no — supersession is content-level, wikilinks are concept-level. Leave alone.)
- What about `[[Foo|alias text]]` — do we ever rewrite the alias? (Lean: never. Aliases carry author intent.)

## See also

- [[sleep-cycle]] — the parent consolidation workflow
- [[pauli]] — owns `densify --tasks`
- [[remember]] (skill) — wikilink discipline
- [[conceptual-review-workflow]] — the QA gate
- [[batch-graph-operations]] — append-to-document and frontmatter ops
- [[pkb-server-spec]] — the tools densify uses
