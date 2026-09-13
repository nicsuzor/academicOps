---
name: remember
description: Write and maintain durable knowledge in the PKB. Capture persists facts, decisions, and constraints as they emerge; consolidation synthesises episodic records into durable topic notes and repairs drift. Does not file bugs (use GitHub) or log debug traces.
---

# Remember

Write and consolidate knowledge notes under `synthesize-not-accrete`. State current truth in synthesised prose; do not accumulate chronological history or changelogs.

## Invariants

- **Search before writing**: Query existing notes before creating or updating.
- **Never fabricate**: Record citable facts and direct implications; omit opinions on what should have happened.
- **Preserve contradictions**: Record conflicting claims with their respective sources; do not pick winners silently.
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

- **Densify relationships**: Link notes to peer concepts and Maps of Content with `[[wikilink]]` pointers in prose.
- **Typed relationships**: Record related nodes under `## Relationships` on notes (`- [related] [[id]] -- reason`). Task bodies express relationships via graph edges, never in prose.
- **Frontmatter**: Notes of `type: knowledge` include `sources`, `synthesized`, `last_reviewed`, `confidence`, and `maturity: seedling|budding|evergreen`.
- **Maps of Content**: Create or update `type: moc` notes when a topic accumulates five or more notes.

## Routing Emerging Work

- **Incidents and friction**: Route to `/aops:learn` for root-cause diagnosis.
- **New asks or decisions**: Route to `/aops:q` for graph positioning and weighting.
- **Fallback**: If an owning skill cannot run, create an `inbox` node noting the required skill.

## Consolidation

Consolidate episodic sources (daily notes, meeting notes, closed tasks) into canonical topic notes per `references/consolidation.md` and `references/quality.md`.

- **Synthesis over collection**: Synthesise underlying principles across sources; do not concatenate bullet lists.
- **Repair drifted tasks**: Extract durable knowledge (models, architecture, decisions) to destination notes first, verify readback, then rewrite the task body to minimal goal, deliverable, scope, checklist, and pointers.
- **Retire primary records**: Delete or archive episodic notes and replaced memories only after verified arrival at the destination node.
