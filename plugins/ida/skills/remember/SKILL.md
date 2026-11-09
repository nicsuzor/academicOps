---
name: remember
description: Write and maintain durable knowledge in the PKB. Capture persists facts, decisions, and constraints as they emerge; consolidation synthesises episodic records into durable topic notes and repairs drift. Does not file bugs (use GitHub) or log debug traces.
---

# Remember

Write and consolidate knowledge notes under `synthesize-not-accrete`. State current truth in synthesised prose; do not accumulate chronological history or changelogs.

## Invariants

- **Current facts only (CURRENT STATE ONLY)**: The PKB holds what is true now, one canonical note per topic. Retaining historical provenance lists (`sources:` frontmatter arrays), session references, chronological changelogs, dated layers, or citations to non-existent or prior-state material is strictly prohibited. When encountered, strip historical source lists immediately. Never accumulate historical provenance.
- **Rewrite in place**: A fact that is no longer true is deleted, not annotated. No superseded sections, changelogs, dated layers, or corrections that quote the old text.
- **Custodial curation**: Pauli exclusively curates knowledge notes per `.agents/rules/pkb.md`; other agents offer durable facts to Pauli or record them under `## Durable Facts` in task records.
- **Search before writing**: Query existing notes before creating or updating.
- **Never fabricate**: Record citable facts and direct implications; omit opinions on what should have happened.
- **Resolve contradictions**: When sources disagree, state the resolved fact and delete the losing version -- do not record the disagreement. Where a retired premise would otherwise be re-derived by the next reader, keep one forward-looking line of warning and delete the reasoning it came from. If the conflict cannot be resolved from evidence, ask; do not file both claims and move on.
- **Target and task rules**: Target nodes carry only worth ($W_t \in \mathbb{R}$ on the open continuous log scale); task bodies are work checklists, not logs.
- **Bugs on GitHub**: Report system, tool, and framework bugs on GitHub only.
- **Age is not staleness**: Do not archive or cancel notes based on age alone.

## Capture Workflow

1. **Search**: Query existing notes for the topic.
2. **Find canonical note**: Maintain one canonical note per primary topic (concept, tool, project). If a topic note exists, update it rather than creating a new one.
3. **Augment in place**: Rewrite the relevant section to reflect current state. Replace superseded facts; do not append dated entries or provenance narratives. Grounding evidence lives in its own node linked by `[[wikilink]]`.
4. **Create when novel**: Create documents (`type: knowledge`) or atomic facts (`type: memory`) only when no canonical topic matches.

### Graph Integration

- **Densify relationships**: Link notes to peer concepts and navigation nodes with `[[wikilink]]` pointers **in the prose that needs them**. A wikilink anywhere in a body is a real graph edge (not read by the flow rule, pending FQ23). Do not author a `## Relationships`, `## Related`, `## See also`, or `## References` heading -- no code path reads body headings into edges, and a link parked in a list at the foot of a note is an edge without a reason attached. Task bodies express relationships via graph edges, never in prose.
- **Frontmatter**: Set it when creating the node. Node creation accepts `title`, `type`, `tags`, `confidence` (float 0–1), and `source` (a single string); `id`, `alias`, `permalink`, `created`, and `modified` are generated. When deriving a note from a PKB artefact, pass the artefact's PKB-relative path in `source` (or parent to a node whose file lives in that sub-project directory) so home-directory placement files the note in that sub-project directory rather than defaulting to `notes/`. Afterwards metadata updates can change `title`, `type`, `tags` and the other task fields. Nothing else is writable -- unknown keys are rejected, not written. Do not add or accumulate provenance arrays or lists; facts stand on their own in synthesised prose.
- **Prohibited frontmatter (`sources:`, `synthesized:`, `last_reviewed:`, `maturity:`)**: The PKB is CURRENT STATE ONLY. Frontmatter arrays maintaining historical `sources:` or provenance lists are strictly prohibited; unknown or legacy keys must never be added, and when encountered on older nodes they must be stripped immediately. Never require or retain provenance lists in reviews.
- **Navigation nodes**: Create or update `type: index` notes when a topic accumulates five or more notes. There is no `moc` type; writes specifying one are rejected.

## Routing Emerging Work

- **Incidents and friction**: Route to `/aops:learn` for root-cause diagnosis.
- **New asks or decisions**: Route to `/ida:q` for graph positioning and valuation.
- **Fallback**: If an owning skill cannot run, create an `inbox` node noting the required skill.

## Consolidation

Consolidate episodic sources (daily notes, meeting notes, closed tasks) into canonical topic notes per `references/consolidation.md` and `references/quality.md`.

- **Synthesis over collection**: Synthesise underlying principles across sources; do not concatenate bullet lists.
- **Repair drifted tasks**: Extract durable knowledge (models, architecture, decisions) to destination notes first, then rewrite the task body to minimal goal, deliverable, scope, checklist, and pointers.
- **Retire primary records**: Decide archive versus delete and one note per subject by referencing the governing knowledge base specification rules, without restating criteria here.
