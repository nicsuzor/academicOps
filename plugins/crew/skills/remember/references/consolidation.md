# Knowledge Extraction and Consolidation Cycle

Consolidation synthesises episodic records into durable knowledge under custodian curation (`ida:remember`), preserving offered/filed/retired PKB facts and maintaining graph data quality.

## Safety Controls

- **Dry run by default**: Bulk operations (`batch_update`, `batch_merge`, `apply_consolidation_batch`) default to `dry_run=true`. Set `dry_run=false` only after inspecting previews.
- **Destination-first persistence**: Write the destination note before modifying or deleting any source task body or episodic note. If the destination write fails, halt immediately.
- **Halt on tool failure**: When a tool fails, emit `HALT: <tool_name>` and report immediately; never use workarounds or destructive partial edits.
- **Control context volume**: Query slices by `status` or `project` rather than pulling full unindexed graphs.

## Focus

When given a focus (keyword, topic, or path):

- **Seed the working set**: Union of PKB search for the focus term and literal search across notes, memories, and tasks, plus nodes one `[[wikilink]]` hop out.
- **Scope stages**: Run Stages 3, 4, 5, and 8 over the working set only; skip transcript mining unless the focus names a session.
- **Verify current truth**: Check each claim against its source of record (live config, repo, code, or spec). Replace superseded claims in the canonical note and delete or archive nodes holding only superseded claims; resolve contradicting live sources into the settled fact (or ask if unresolvable); retain unreachable-source claims with low `confidence:` rather than deleting on suspicion.
- **Report the working set**: List every working-set node with its outcome (verified, superseded, merged, deleted, unverifiable).

Without a focus, run stages in order below.

## Knowledge Extraction Method

1. **Cluster siblings**: Group sibling tasks under the same parent to synthesise into one canonical note. When clustering 3+ siblings under a component or initiative epic, hoist the full holistic `serves -> target` weight onto the parent epic (never priced as a remainder) and strip direct `serves` edges from clustered child tasks.
2. **Find canonical note**: Search existing topic notes; update an existing note or create a new one.
3. **Persist destination first**: Write durable content to the destination note before touching source records.
4. **Rewrite source task body**: Once the destination write succeeds, slim the task body in place (<1,500 chars) to Goal, completed checklist, and `## Pointers` with `[[destination-id]]` and PR links (leave status and graph edges unchanged).
5. **Densify links**: Add `[[wikilink]]` pointers in prose to peer concepts and index notes.

### Content Boundaries

| Destination note | Retained in task body | Discarded |
| - | - | - |
| Models, architectures, decisions, empirical findings, API constraints, contacts, external URLs | Goal, completed checklist, PR/commit links, destination pointers | Debug traces, retry loops, terminal logs, routine timestamps |

### Extraction Verification

- **Lossy (FAIL)**: Any durable fact or link in the source is missing from the destination note within one `[[wikilink]]` hop.
- **Accretive (FAIL)**: Source content pasted verbatim under dated headers or duplicated across notes.
- **Fabricated (FAIL)**: Unverified assertions not supported by source bodies or cited commits.
- **Good (PASS)**: Concise source task body pointing to a well-linked canonical topic note.

_Empty extraction_: If a task holds only ephemeral coordination, write nothing to the knowledge layer and slim the task body.

### Defect Checklist

Audit generated notes for: (1) duplicate canonical/narrow pairs, (2) title-encoded dates or session IDs, (3) historical provenance lists (`sources:` arrays) or prior-state narration (prune on sight, preserving active citations inline or in `source` per `cite-sources`), (4) missing frontmatter `confidence:` float, (5) status/progress tables misfiled in knowledge notes, (6) zero wikilinks to existing concepts, and (7) stagnation at `status: inbox`.

## Cycle Stages

1. **Baseline**: Run `pkb.status` and `pkb.get_stats`; record document count and index freshness.
2. **Mine transcripts**: Process unmined transcripts (up to 15 per cycle) into current-state topic notes without modifying transcript bodies or recording `sources:` / `mined:` provenance arrays.
3. **Consolidate knowledge**: Extract durable content from daily notes, meeting notes, and closed tasks into canonical topic notes per the extraction method. Create `type: index` navigation notes for clusters of 5+ notes (no `moc` type); delete episodic notes once persisted at the destination.
4. **Reconcile data quality**: Inspect `find_duplicates(mode="both")` candidates semantically before merging; delegate staleness sweeps to `/reconcile`; reclassify informational tasks or reposition via `/q`.
5. **Sweep orphans**: Review tag-orphan notes via `pkb.get_consolidation_cluster` and parentless/projectless tasks via `pkb.batch_update(orphan=true, dry_run=true)`.
6. **Process refiles**: Reposition `refile`-flagged tasks via `/q` under their governing epic with zero leaf `serves` edges, then clear the flag.
7. **Maintain graph**: Run `pkb.refresh_graph` and compare `pkb.status` against baseline.
8. **Calibrate graph edges (weekly)**: Review Strategic Value Carriers ordered by reach and draft holistic `serves -> target` link proposals; hoist any residual leaf `serves` edges onto parent component epics and strip `serves` from child tasks.
9. **Audit output**: Confirm all new or updated notes satisfy extraction checks and the defect checklist.

## Summary Report

Emit a structured cycle summary with: (1) **Halt count** (with phase and failure details, or `0`), (2) **Baseline and deltas** (graph stats and orphan counts), (3) **Stage details** (processed, augmented, rewritten, and merged node IDs), (4) **Empty extractions**, and (5) **Next actions**.
