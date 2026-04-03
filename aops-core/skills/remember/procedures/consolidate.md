---
title: Consolidation Procedure
type: automation
category: instruction
permalink: consolidation-procedure
tags: [memory, workflow, consolidation]
---

# Consolidation Procedure

Transform episodic memory into durable semantic knowledge. Mirrors the cognitive process of semanticization — retrieval and reprocessing drive the transformation, not passive storage.

For concrete examples of good and bad consolidation output, see [[quality-exemplars]].

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

### 3. Delete or mark superseded sources

If the new knowledge note **fully replaces** an episodic memory or older knowledge note, **delete** the old file (`git rm`). Trust git — the history preserves it. Do NOT leave superseded files with `superseded_by:` pointers; that creates duplication and confusion.

If the source is a primary episodic record (daily note, meeting note, task body), add `consolidated: YYYY-MM-DD` to its frontmatter instead — episodic notes are primary records and should not be deleted. But memories (`mem-*.md`) that have been fully consolidated into knowledge notes should be deleted.

### 4. File in the right location

The PKB has directory structure for a reason. Choosing the right directory is part of the consolidation work:

- **Project-specific insights** → the project's directory (e.g., `osb/`, `buttermilk/`, `hdr/`)
- **Generic domain knowledge** → `knowledge/<domain>/` (e.g., `knowledge/tech/`, `knowledge/cyberlaw/`)
- **Agent conventions and patterns** → `memories/` (only if truly generalizable across projects)

Don't dump project-specific insights into `knowledge/` or `memories/` to avoid thinking about where they go. If a note is about OSB benchmarking, it belongs in `osb-benchmarking/`, not `knowledge/tech/`.

### 5. Update or create MOC if needed

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
- [ ] Superseded memories deleted (not left with `superseded_by:` pointers)
- [ ] Source episodic notes marked `consolidated: YYYY-MM-DD` but content unchanged
- [ ] Notes filed in the right directory (project-specific → project dir, not generic)
