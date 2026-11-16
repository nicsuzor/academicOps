---
name: remember
description: Write and maintain durable knowledge in the PKB. Capture persists facts, decisions, and constraints as they emerge; consolidation synthesises episodic records into durable topic notes and repairs drift. Does not file bugs (use GitHub) or log debug traces.
---

# Remember

Write and consolidate knowledge notes under `synthesize-not-accrete`. State current truth in synthesised prose; do not accumulate chronological history or changelogs.

## Invariants

- **Current facts only (CURRENT STATE ONLY)**: The PKB holds what is true now, one canonical note per topic. Retaining historical provenance lists (`sources:` frontmatter arrays), session references, chronological changelogs, dated layers, or citations to non-existent or prior-state material is strictly prohibited. When encountered, strip historical source lists immediately. Never accumulate historical provenance.
- **Rewrite in place & concision (30–80 lines)**: A fact that is no longer true is deleted, not annotated. No superseded sections, changelogs, dated layers, or corrections that quote the old text. Capture durable principles, architectural decisions (that are not PKB rules), invariants, and verified current-state findings while stripping execution trivia, line numbers, and transient timestamps, keeping note bodies within 30–80 lines (<1,500 characters) so notes can be read and rewritten whole.
- **Custodial curation**: Pauli exclusively curates knowledge notes per `.agents/rules/pkb.md`; other agents offer settled durable facts to Pauli or record them under `## Durable Facts` in task records and handover summaries.
- **Search before writing**: Query existing notes before creating or updating.
- **One note per subject and archive vs delete by PKB specification reference**: Decide one note per subject (co-locating substantive rulings and their operational or enforcement state in a single canonical topic note) and archive versus delete strictly by referencing the rules in the governing knowledge base specification, stating neither rule's operational test or criteria a second time.
- **Unified four-category retirement on sight**: When encountering conflicting, unnecessary, demonstrably false, or stale content in the knowledge base, resolve, merge, correct, or retire it immediately on sight without deferring to a later pass, filing a maintenance ticket, or reserving it as the user's call:
  - _Conflicting_: When sources disagree or contradict verified live state, state the resolved current fact and delete the losing version outright without recording the disagreement (where a retired premise would otherwise be re-derived by the next reader, keep one forward-looking line of warning and delete the reasoning it came from; if unresolvable from evidence, ask rather than filing both).
  - _Unnecessary_: Merge duplicate notes, overlapping topic fragments, or observation scraps into the single canonical topic note and delete the redundant note immediately.
  - _Demonstrably false_: Delete or correct claims contradicting verified live state or primary sources immediately on sight.
  - _Stale_: Decide archive versus delete strictly by the governing knowledge base specification rules without restating them here. Do not archive or cancel notes based on age alone.
- **Never fabricate**: Record citable facts and direct implications; omit opinions on what should have happened.
- **Target and task rules**: Target nodes carry only worth ($W_t \in \mathbb{R}$ on the open continuous log scale); task bodies are work checklists, not logs.
- **Bugs on GitHub (never in knowledge notes)**: Report system, tool, and framework bugs on GitHub only; faults diagnosed under `/learn` route to queued task nodes (`type: task`) on the PKB graph carrying the formatted issue payload, never to knowledge notes.

## Capture Workflow

1. **Search**: Query existing notes for the topic and scan completed task records or handover summaries for unfiled `## Durable Facts`.
2. **Find canonical note**: Maintain one canonical note per primary topic (concept, tool, project) per the governing knowledge base specification. If a topic note exists, update it rather than creating a new one, and mark collected task facts incorporated.
3. **Augment in place**: Rewrite the relevant section to reflect current state within the 30–80 line concision budget. Replace superseded facts; do not append dated entries or provenance narratives. Grounding evidence lives in its own node linked by `[[wikilink]]`.
4. **Create when novel**: Create documents (`type: knowledge`) or atomic facts (`type: memory`) only when no canonical topic matches.

### Graph Integration

- **Densify relationships**: Link notes to peer concepts and navigation nodes with `[[wikilink]]` pointers **in the prose that needs them**. A wikilink anywhere in a body is a real graph edge. Do not author a `## Relationships`, `## Related`, `## See also`, or `## References` heading; a link parked in a list at the foot of a note is an edge without a reason attached. Task bodies express relationships via graph edges, never in prose.
- **Frontmatter**: Set it when creating the node. Node creation accepts `title`, `type`, `tags`, `confidence` (float 0-1), and `source` (a single string); `id`, `alias`, `permalink`, `created`, and `modified` are generated. When deriving a note from a PKB artefact, pass the artefact's PKB-relative path in `source` (or parent to a node whose file lives in that sub-project directory) so home-directory placement files the note in that sub-project directory rather than defaulting to `notes/`. Afterwards metadata updates can change `title`, `type`, `tags` and the other task fields. Nothing else is writable -- unknown keys are rejected, not written. Do not add or accumulate historical provenance arrays or lists; cite non-trivial claims directly in prose via inline `[[wikilink]]` pointers or the `source` field per `cite-sources`.
- **Prohibited frontmatter (`sources:`, `synthesized:`, `last_reviewed:`, `maturity:`)**: The PKB is CURRENT STATE ONLY. Frontmatter arrays maintaining historical `sources:` or retrospective accretion lists are strictly prohibited; unknown or legacy keys must never be added. When updating nodes carrying legacy `sources:` arrays, ensure any load-bearing source citations are preserved inline or in `source` per `cite-sources` rather than leaving unreferenced assertions. Never require or retain retrospective provenance lists in reviews.
- **Navigation nodes**: Create or update `type: index` notes when a topic accumulates five or more notes. There is no `moc` type; writes specifying one are rejected.

## Routing Emerging Work

- **Incidents and friction**: Route to `/learn` (`ida:learn`) for root-cause diagnosis, which files diagnosed tool and framework faults as queued task nodes (`type: task`) on the PKB graph rather than knowledge notes.
- **New asks or decisions**: Route to `/ida:q` for graph positioning and valuation.
- **Fallback**: If an owning skill cannot run, create an `inbox` node noting the required skill.

## Consolidation

Consolidate episodic sources (daily notes, meeting notes, closed tasks) into canonical topic notes per `references/consolidation.md` and `references/quality.md`.

- **Synthesis over collection**: Synthesise underlying principles across sources; do not concatenate bullet lists.
- **Repair drifted tasks**: Extract durable knowledge (models, architecture, decisions) to destination notes first, then rewrite the task body to minimal goal, deliverable, scope, checklist, and pointers.
- **Retire primary records**: Decide archive versus delete and one note per subject by referencing the governing knowledge base specification rules, without restating criteria here.
