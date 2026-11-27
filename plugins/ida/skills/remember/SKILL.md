---
name: remember
description: Write and maintain durable knowledge in the PKB. Capture persists facts, decisions, and constraints as they emerge; consolidation synthesises episodic records into durable topic notes and repairs drift. Does not file bugs (use GitHub) or log debug traces.
---

# Remember

Write and consolidate knowledge notes under `synthesize-not-accrete`: state current truth in synthesised prose with one canonical note per topic, without changelogs or dated layers.

## Invariants

- **Custodial curation**: The PKB custodian (Pauli) exclusively curates knowledge notes; other agents offer settled durable facts to the custodian or record them under `## Durable Facts` in task records and handover summaries.
- **Current state only**: Hold what is true now; never fabricate, record opinions on what should have happened, or keep retrospective provenance lists (`sources:`, `synthesized:`, `last_reviewed:`, `maturity:` frontmatter keys) or dead citations. Cite non-trivial claims inline via `[[wikilink]]` or the single `source` string per `cite-sources`, preserving active citations when stripping legacy `sources:` arrays.
- **Rewrite in place & concision (30-80 lines)**: Delete obsolete facts outright rather than annotating or quoting old text. Capture durable principles, architectural decisions, invariants, and verified findings (<1,500 chars per note so notes can be rewritten whole), stripping execution trivia, line numbers, and transient timestamps.
- **Search before writing & one note per subject**: Query existing notes before creating or updating. Decide one note per subject and archive-versus-delete strictly by the governing PKB specification without restating its criteria here.
- **Four-category retirement on sight**: Resolve, merge, correct, or delete immediately on discovery without deferring or filing maintenance tickets:
  - _Conflicting_: State the resolved current fact and delete the losing version (keep one forward-looking warning line if the retired premise would otherwise be re-derived; if unresolvable from evidence, ask rather than filing both).
  - _Unnecessary_: Merge duplicates, overlapping fragments, or scraps into the canonical topic note and delete the redundant note.
  - _Demonstrably false_: Delete or correct claims contradicting verified live state or primary sources.
  - _Stale_: Apply the governing PKB specification's archive-versus-delete rules (never archive or cancel by age alone).
- **Targets, tasks, and bugs**: Target nodes carry only worth ($W_t \in \mathbb{R}$); task bodies are work checklists, not logs. System/framework bugs never belong in knowledge notes -- route faults to `/learn`, which queues `type: task` issue payloads for GitHub.

## Capture & Graph Integration

1. **Search**: Query existing topic notes and scan closed tasks or handover summaries for unfiled `## Durable Facts`.
2. **Augment canonical note or create**: Update the matching topic note in place within 30-80 lines and mark incorporated task facts; create `type: knowledge` or atomic `type: memory` nodes only when no canonical topic exists. Grounding evidence lives in its own node linked by `[[wikilink]]`.
3. **Destination-first persistence**: Write the destination knowledge note before rewriting or deleting any source record.
4. **Densify inline**: Place `[[wikilink]]` edges inside the prose that needs them; never add trailing `## Relationships`, `## Related`, `## See also`, or `## References` lists. Express task relationships via graph edges, never prose.
5. **Frontmatter & parent**: Node creation accepts `title`, `type`, `tags`, `confidence` (float 0-1), and `source` (single string). Set `parent` only to a project or index node to file into a sub-project directory, or pass a PKB-relative artefact path in `source`; reserve task `parent` exclusively for direct child task steps.
6. **Re-parenting & navigation**: Re-parent any note found under a task in the same turn to a project or index node (or fold it into the canonical topic note if redundant) and link it to the task via `[[wikilink]]` or `source` so the task stays unblocked. Maintain `type: index` navigation notes for clusters of 5+ notes (never `type: moc`).

## Routing & Consolidation

- **Routing**: Route incidents and friction to `/learn` (`ida:learn`), new asks or decisions to `/q`, or an `inbox` node when an owning skill cannot run.
- **Consolidation**: Read [consolidation.md](references/consolidation.md) and [quality.md](references/quality.md) before running a consolidation cycle. Synthesise underlying principles across sources rather than concatenating bullets, and repair drifted tasks by persisting durable facts to destination notes first before slimming the task body.
