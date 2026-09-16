---
name: remember
description: Write and maintain durable knowledge in the PKB. Capture persists facts, decisions, and constraints as they emerge; consolidation synthesises episodic records into durable topic notes and repairs drift. Does not file bugs (use GitHub) or log debug traces.
---

# Remember

Write and consolidate knowledge notes under `synthesize-not-accrete`. State current truth in synthesised prose; do not accumulate chronological history or changelogs.

Two PKB nodes are the single source of truth for note standards, and this skill is the operating procedure for them. Read them when a rule here is ambiguous, and correct them rather than this file when the standard itself changes:

- **`kb_634e639c`** -- doctrine: what the PKB may contain, how a node is rewritten, and whose duty extraction is.
- **`inde_pkb_node_linking`** -- mechanics: valid node types, which fields are real graph edges, and what frontmatter the tools accept. Node-type semantics live in `pkb-type-taxonomy`.

A rule stated in only one of those two is not in conflict with the other; a rule restated here that contradicts either is a defect in this file.

## Invariants

- **Search before writing**: Query existing notes before creating or updating.
- **Never fabricate**: Record citable facts and direct implications; omit opinions on what should have happened.
- **Resolve contradictions**: When sources disagree, state the resolved fact and delete the losing version -- do not record the disagreement. Where a retired premise would otherwise be re-derived by the next reader, keep one forward-looking line of warning and delete the reasoning it came from. If the conflict cannot be resolved from evidence, ask; do not file both claims and move on.
- **Target and task rules**: Target nodes carry only graph weights and severity; task bodies are work checklists, not logs.
- **Bugs on GitHub**: Report system, tool, and framework bugs on GitHub only.
- **Age is not staleness**: Do not archive or cancel notes based on age alone.

## Capture Workflow

1. **Search**: Run `pkb.search(query="<topic>")`.
2. **Find canonical note**: Maintain one canonical note per primary topic (concept, tool, project). If a topic note exists, update it rather than creating a new one.
3. **Augment in place**: Rewrite the relevant section to reflect current state via `pkb.update_body`. Replace superseded facts; do not append dated entries or provenance narratives. Grounding evidence lives in its own node linked by `[[wikilink]]`.
4. **Create when novel**: Use `pkb.create(type="knowledge", ...)` for documents or `pkb.create(type="memory", ...)` for atomic facts only when no canonical topic matches.

All PKB calls above go through the `services` MCP server's code-mode interface: `listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode` running the `pkb.<op>(...)` call. There is no directly-invocable flat tool named `pkb__<op>` or `pkb-<op>`.

### Graph Integration

- **Densify relationships**: Link notes to peer concepts and navigation nodes with `[[wikilink]]` pointers **in the prose that needs them**. A wikilink anywhere in a body is a real graph edge. Do not author a `## Relationships`, `## Related`, `## See also`, or `## References` heading -- no code path reads body headings into edges, and a link parked in a list at the foot of a note is an edge without a reason attached. Task bodies express relationships via graph edges, never in prose.
- **Frontmatter**: Set it when creating the node. `pkb.create` accepts `title`, `type`, `tags`, `confidence` (float 0–1), and `source` (a single string); `id`, `alias`, `permalink`, `created`, and `modified` are generated. Afterwards `batch_update` can change `title`, `type`, `tags` and the other task fields. Nothing else is writable -- unknown keys are rejected, not written -- so provenance beyond the one `source` string belongs in the body as a `[[wikilink]]` to its evidence node.
- **Legacy frontmatter**: a few older hand-written nodes carry `sources:`, `synthesized:`, `last_reviewed:`, or `maturity:`. These are unreachable through the current tools and no code reads them. Do not add them, do not treat their absence as a defect, and do not require them in a review.
- **Navigation nodes**: Create or update `type: index` notes when a topic accumulates five or more notes. There is no `moc` type; writes specifying one are rejected.

## Routing Emerging Work

- **Incidents and friction**: Route to `/aops:learn` for root-cause diagnosis.
- **New asks or decisions**: Route to `/pkb:q` for graph positioning and weighting.
- **Fallback**: If an owning skill cannot run, create an `inbox` node noting the required skill.

## Consolidation

Consolidate episodic sources (daily notes, meeting notes, closed tasks) into canonical topic notes per `references/consolidation.md` and `references/quality.md`.

- **Synthesis over collection**: Synthesise underlying principles across sources; do not concatenate bullet lists.
- **Repair drifted tasks**: Extract durable knowledge (models, architecture, decisions) to destination notes first, verify readback, then rewrite the task body to minimal goal, deliverable, scope, checklist, and pointers.
- **Retire primary records**: Delete episodic notes and replaced memories once arrival at the destination node is verified by reading it back by id. Delete outright -- no tombstone, no `status: archived`, no archive copy. Git, session transcripts, and audit logs hold the history, and none of them is loaded on every retrieval.
