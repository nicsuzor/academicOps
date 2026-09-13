# Knowledge Extraction and Consolidation Cycle

Consolidation synthesises episodic records into durable knowledge and maintains graph data quality.

## Safety Controls

- **Dry run by default**: Bulk operations (`batch_update`, `batch_merge`, `apply_consolidation_batch`) default to `dry_run=true`. Set `dry_run=false` only after inspecting previews.
- **Destination-first persistence**: Verify destination note writes by ID before modifying or deleting any source task body or episodic note. If the destination write fails, halt immediately.
- **Halt on tool failure**: When a tool fails, emit `HALT: <tool_name>` and report immediately; never use workarounds or perform destructive partial edits.
- **Control context volume**: Query slices by `status` or `project` rather than pulling full unindexed graphs.
- **Sub-agent tooling**: Sub-agents dispatched to `pkb:pauli` require an explicit `tools` list in the dispatch call (e.g. `mcp__plugin_pkb_services__*` -- a server-level pattern; `mcp__<server>__pkb__*` matches nothing).
- **Invocation is code-mode, not flat tools**: every `pkb.<op>(...)` call below runs inside the `services` MCP server's code-mode interface (`listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode`). There is no directly-invocable flat tool named `pkb__<op>` or `pkb-<op>`.

## Focus

A cycle may be given a focus: a keyword, a topic, or a path. With a focus:

- **Seed the working set**: Union of `pkb.search(query="<focus>")` and a literal search of the brain for the term (`grep -rli "<focus>"`) across notes, memories, tasks, and specs, plus nodes one `[[wikilink]]` hop out from any hit.
- **Scope the stages**: Run Stages 3, 4, 5, and 8 over the working set only. Skip transcript mining unless the focus names a session.
- **Establish current truth before consolidating**: For each claim in the working set, identify its source of record (the live configuration, repository, code, or spec the claim describes) and check the claim against it. A claim the source no longer supports is superseded: replace it in the canonical note; delete or archive nodes whose only content is superseded claims. Contradictions between live sources are preserved with both cited. A claim with no reachable source is marked `confidence: speculative`, never deleted on suspicion.
- **Report the working set**: The summary lists every node in the working set with its outcome (verified, superseded, merged, deleted, unverifiable).

Without a focus, stages run in order as listed below.

## Knowledge Extraction Method

1. **Cluster siblings**: Group sibling tasks under the same parent to synthesise into one canonical note.
2. **Find canonical note**: Search with `pkb.search(query="<topic>")`. Augment existing notes via `pkb.update_body` or create via `pkb.create`.
3. **Persist destination first**: Write durable content to the destination note and verify readback by ID.
4. **Rewrite source task body**: Once verified, rewrite the task body in place (<1,500 chars) to its minimal form: Goal, completed checklist, and `## Pointers` with `[[destination-id]]` and PR links. Do not alter status or graph edges.
5. **Densify links**: Add `[[wikilink]]` pointers from the destination note to peer concepts and Maps of Content.

### Content Boundaries

| Destination note                                                                               | Retained in task body                                            | Discarded                                                    |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------ |
| Models, architectures, decisions, empirical findings, API constraints, contacts, external URLs | Goal, completed checklist, PR/commit links, destination pointers | Debug traces, retry loops, terminal logs, routine timestamps |

### Extraction Verification

Evaluate extractions against four criteria:

- **Lossy (FAIL)**: Any durable fact or link in the source is missing from the destination note within one `[[wikilink]]` hop.
- **Accretive (FAIL)**: Source content pasted verbatim under dated headers or duplicated across notes.
- **Fabricated (FAIL)**: Unverified assertions not supported by source bodies or cited commits.
- **Good (PASS)**: Concise source task body pointing to a comprehensive, well-linked canonical topic note.

_Empty extraction_: If a task contains only ephemeral coordination, write nothing to the knowledge layer and rewrite the task body to its minimal state.

### Defect Checklist

Audit generated notes for:

1. Duplicate canonical/narrow pairs.
2. Title-encoded dates or session IDs (`note-2026-04-18`).
3. Missing frontmatter `sources:`.
4. Missing frontmatter `confidence:` (`established`, `provisional`, `speculative`).
5. Status or progress tables misfiled in knowledge notes.
6. Zero wikilinks to existing concepts.
7. Stagnation at `status: inbox`.

## Cycle Stages

1. **Baseline**: Run `pkb.status` and `pkb.get_stats`. Record document count and index freshness.
2. **Mine transcripts**: Process unmined transcripts (up to 15 per cycle). Synthesise durable topics, record provenance (`sources: ["Session <id> (<date>)"]`), and update frontmatter `mined: <date>`. Do not edit transcript bodies.
3. **Consolidate knowledge**: Extract durable content from daily notes, meeting notes, and closed tasks to canonical topic notes per the extraction method. Create Maps of Content (`type: moc`) for clusters of 5+ notes. Delete episodic notes once verified at destination.
4. **Reconcile data quality**:
   - _Duplicates_: Inspect candidates from `find_duplicates(mode="both")` semantically before merging.
   - _Staleness_: Delegate task staleness and closure to `/aops:reconcile`.
   - _Misclassifications_: Reclassify informational tasks to memories or invoke `/aops:q` to reposition.
5. **Sweep orphans**: Review tag-orphan notes surfaced by `pkb.get_consolidation_cluster` and tasks with no parent or project (`pkb.batch_update(orphan=true, dry_run=true)` lists them).
6. **Process refiles**: Reposition tasks flagged with `refile` using `/aops:q` and clear the flag.
7. **Maintain graph**: Run `pkb.refresh_graph`, then compare `pkb.status` against the baseline to confirm convergence.
8. **Audit output**: Verify that new or updated notes satisfy the extraction tests and defect checklist.

## Summary Report

Emit a structured summary for each cycle:

1. **Halt count**: Listed at top with phase and failure details (or `0`).
2. **Baseline and deltas**: Initial vs. final graph stats and orphan counts.
3. **Stage details**: IDs of processed, augmented, rewritten, and merged nodes.
4. **Empty extractions**: List of tasks containing no durable knowledge.
5. **Next actions**: Focus items for subsequent cycles.
