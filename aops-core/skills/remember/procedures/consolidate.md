---
title: Consolidation Procedure
type: automation
category: instruction
permalink: consolidation-procedure
tags: [memory, workflow, consolidation]
---

# Consolidation Procedure

Transform episodic memory into durable semantic knowledge. Mirrors the cognitive process of semanticization — retrieval and reprocessing drive the transformation, not passive storage.

## Pipeline

Episodic sources (daily notes, meeting notes, task bodies) → observation extraction → pattern detection (3+ sources) → synthesis notes → Maps of Content (5+ notes on a topic).

## When to Consolidate

- Episodic content older than 7 days
- Completed tasks with substantive bodies
- Pattern detected across 3+ sources
- Topic area feels like a jumble (create a MOC)

## Steps

### 1. Read and identify extractable knowledge

Read the full source. Ask: "What would help a future agent or user, independent of the date?"

**Extract**: decisions + rationale, cross-source patterns, facts about systems/people/processes, techniques, strategic insights.
**Skip**: implementation details (git history), routine updates, debugging steps (unless generalizable), opinions.

### 2. Search PKB, then create or augment

**Always search first** (`mcp__pkb__search`). If a match exists, **augment it**. If no match, create new note with provenance:

```yaml
---
title: Descriptive title encoding the insight
type: knowledge
topic: relevant-topic
tags: [relevant, tags]
sources:
  - "[[daily/20260401-daily]]"
  - "Session transcript abc123 (2026-04-01)"
synthesized: 2026-04-03
confidence: provisional
last_reviewed: 2026-04-03
---
```

Use observation notation for atomic facts:

```markdown
> [!observation] Specific claim extracted from source
> Source: [[daily/20260401-daily]]
> Confidence: provisional
```

### 3. Mark source as consolidated

Add `consolidated: YYYY-MM-DD` to the episodic source's frontmatter (date enables re-consolidation if quality review later flags problems). **Never modify the source's content** — episodic notes are primary records.

### 4. Update or create MOC if needed

If the topic area now has 5+ related knowledge notes and no MOC exists, create one.

## Anti-Patterns

- **Fabrication**: Asserting facts not in source material
- **Editorializing**: Adding value judgments the user hasn't made
- **Over-abstraction**: Leaping from one source to a universal principle
- **Under-attribution**: Synthesis without citing sources
- **Content modification**: Changing episodic note text (only add frontmatter)
- **Duplicate creation**: Not searching PKB first
- **Premature synthesis**: Knowledge notes from a single weak source

## Quality Check

- [ ] Every new knowledge note has `sources:` in frontmatter
- [ ] Confidence level matches evidence strength
- [ ] Wikilinks connect to related concepts
- [ ] Content understandable without reading source
- [ ] Source episodic notes marked `consolidated: YYYY-MM-DD` but content unchanged
