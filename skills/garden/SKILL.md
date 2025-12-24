---
name: garden
description: Incremental PKM maintenance - weeding, pruning, linking, consolidating. Tends the knowledge base bit by bit.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Task,mcp__memory__*
version: 1.0.0
permalink: skills-garden
---

# Garden

Tend the personal knowledge base incrementally. Small regular attention beats massive occasional cleanups.

## Gardening Activities

| Activity | What to Do |
|----------|-----------|
| **Weed** | Remove dead links, outdated content, duplicates |
| **Prune** | Archive stale notes, trim bloated files |
| **Compost** | Merge fragments into richer notes |
| **Cultivate** | Enrich sparse notes, add context |
| **Link** | Connect orphans, add missing [[wikilinks]] |
| **Map** | Create/update MoCs for navigation |
| **DRY** | Remove restated content, replace with links |
| **Synthesize** | Strip deliberation artifacts from implemented specs |

## Modes

### scan [area]
Health check. Count orphans, broken links, stale content, sparse notes, duplicates.

### weed [area]
Fix broken [[wikilinks]], remove dead references, flag duplicates.

### prune [area]
Archive stale sessions (>30 days), compress verbose notes, update temporal metadata.

### link [area]
Connect orphans (zero backlinks), suggest missing links, ensure every note has ≥1 outgoing link.

### cultivate [area]
Add missing frontmatter, expand sparse notes, improve titles for searchability.

### consolidate [topic]
Merge notes on same topic, extract patterns from logs into learning files.

### map [folder]
Create missing folder/folder.md MoCs, update stale MoCs.

### dry [area]
Find restated content that should be links. See DRY Enforcement below.

### synthesize [area]
Strip deliberation artifacts from implemented specs. See [[HEURISTICS.md#H23]] for rationale.

**Detection patterns**:
- Specs with `status: Implemented` containing `## Options` or `## Alternatives`
- Reference docs with "as of YYYY", "TODO:", "considering", "we might"
- Specs >30 days since implementation with deliberation artifacts

**Workflow**:
1. Scan specs/ for implemented items with deliberation cruft
2. For each finding, show the artifact and ask:
   - "Archive rationale to decisions/? [y/n]"
   - "Strip from spec? [y/n]"
3. Update spec, preserving acceptance criteria and current behavior
4. Commit changes

**Does NOT delete specs** - synthesizes them from deliberation mode to reference mode.

## DRY Enforcement (Critical)

**Problem:** Content copied from core docs (AXIOMS, ACCOMMODATIONS, HEURISTICS) into other files instead of linking. Creates maintenance burden and drift.

**Detect restated content:**
1. Look for sections labeled "from [[X]]" or "per [[X]]" - these restate instead of link
2. Find multi-line quotes from core framework docs
3. Detect duplicate bullet points across files

**Example violation** (from a spec file):
```markdown
**Communication Guidelines** (from [[ACCOMMODATIONS.md]]):
- Match user's preparation level...
- Proactive action: Don't ask permission...
```

**Fix:** Remove the restated content entirely. The framework already loads ACCOMMODATIONS.md via hooks - no need to repeat or even link unless critically specific to this context.

**Rule:** Core docs (AXIOMS, ACCOMMODATIONS, HEURISTICS, RULES) apply everywhere implicitly. Don't restate. Don't even link unless the specific section is uniquely relevant.

## Workflow

1. **Ask** what area to tend (or pick based on recent activity)
2. **Scan** to assess health
3. **Pick mode** based on findings
4. **Work small batches** - 3-5 notes at a time
5. **Surface decisions** - confirm before deletions
6. **Commit frequently** - logical chunks

**Session length:** 15-30 minutes max. Gardening is sustainable when light.

## Area Targeting

| Area | Focus |
|------|-------|
| `projects` | Project documentation |
| `sessions` | Session logs |
| `tasks` | Task tracking |
| `archive` | Historical content |
| `[project]` | Specific project subfolder |

Default: highest-activity areas (recent modifications).

## Health Metrics

| Metric | Target |
|--------|--------|
| Orphan rate | <5% |
| Link density | >2 per note |
| Broken links | 0 |
| MoC coverage | >90% |
| DRY violations | 0 |
| Implemented specs with deliberation cruft | 0 |

## Anti-Patterns

- Marathon cleanup sessions → Small, frequent instead
- Delete without extracting value → Preserve then prune
- Reorganize folder structures → Use MoCs for navigation
- Restate core docs → Link or omit entirely
- Perfectionism → Progress over perfection

## References

- [[knowledge-management-philosophy]]
- [[knowledge-base-consolidation]]
- [[knowledge base]]
