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
Health check. Count orphans, broken links, stale content, sparse notes, duplicates, orphan implementation docs.

**Orphan Implementation Doc Detection**:
Files in `experiments/` that describe features with existing specs should be synthesized, not left as separate files. Scan identifies these:
1. List files in `$AOPS/experiments/*.md`
2. For each, check title/content against `specs/` filenames and content
3. If match found → report as "orphan implementation doc - synthesize into [spec]"
4. Output: "Found N implementation docs that should be merged into specs"

Note: Per AXIOM #28, episodic observations go to GitHub Issues, not local files.

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
De-temporalize content: strip deliberation artifacts from specs, and delete/consolidate agent-generated temporal logs. See [[HEURISTICS.md#H23]] and [[AXIOMS.md#13]] (Trust Version Control).

**Spec Index Maintenance**:
After synthesizing any spec, ensure `specs/specs.md` is updated:
1. Check if spec is listed in the index
2. If not listed → add to appropriate category section
3. If status changed → update the index entry
4. Commit spec + index together

**What's SACRED (never touch)**:
- User-written meeting notes, file notes, journal entries
- Research records, annotations, observations
- Anything the user authored as a primary document

**What can be de-temporalized** (agent-generated cruft):
- Event logs: "X Cleanup - Month YYYY.md" where git has the commits
- Decision records after implementation: options/alternatives sections
- Temporal markers in reference docs: "as of YYYY", "TODO:", "considering"

**Detection patterns**:
- Files named with dates/months that document completed work
- Specs with `status: Implemented` containing `## Options` or `## Alternatives`
- Reference docs with temporal language that implies incompleteness
- Episodic content that should be GitHub Issues, not local files

**Workflow for specs**:
1. Scan for implemented items with deliberation cruft
2. For each: "Archive rationale to decisions/? Strip from spec?"
3. Update spec, preserving acceptance criteria and current behavior

**Workflow for temporal logs**:
1. Check: Is this user-written or agent-generated?
2. If agent-generated event record: Does git have the commits?
3. Extract any reusable heuristics → promote to HEURISTICS.md
4. Delete the temporal file (git is the archive)

**Does NOT delete user content** - only agent-generated temporal records whose value is now in version control.

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
- **`## Relations` boilerplate** → Remove entirely (see below)

## Relations Section Anti-Pattern

**Problem:** Files with `## Relations` or `## References` sections containing boilerplate like:
```markdown
## Relations
- part_of [[parent]]
- related [[sibling]]
```

**Why it's wrong:**
1. Relationships should emerge organically through in-content wikilinks
2. `part_of` is redundant - folder structure shows hierarchy
3. `related` links add no semantic value - everything is "related"
4. Creates maintenance burden when structure changes
5. MoCs exist for navigation - individual files don't need relationship metadata

**Detection:**
```bash
grep -l "^## Relations$\|^## References$" $ACA_DATA/**/*.md
grep -l "^- part_of \[\[" $ACA_DATA/**/*.md
```

**Fix - Link Migration Pattern:**

1. **Check for orphan risk**: If Relations contains the ONLY links in the file, deleting creates orphans
2. **Migrate meaningful links inline**: Convert first mention of linked entity to a wikilink in the body text
   - `- colleague [[Brian Fitzgerald]]` → find "Brian Fitzgerald" in body, make it `[[Brian Fitzgerald]]`
   - `- part_of [[QUT]]` → find "QUT" in body, make it `[[QUT]]`
3. **Delete pure boilerplate**: `part_of [[contacts]]` adds nothing - just delete
4. **Clean up merged content**: Files with "Merged from:" sections often have duplicate Relations - consolidate the file first

**Example transformation:**
```markdown
# Before
...worked with Brian Fitzgerald on CC licensing...
## Relations
- colleague [[Brian Fitzgerald]]
- part_of [[contacts]]

# After
...worked with [[Brian Fitzgerald]] on CC licensing...
```

## Named Session Logs Anti-Pattern

**Problem:** Individual session files like "Framework Logger Agent - First Production Use.md" or "ZotMCP Implementation Session 2025-11-22.md" duplicating what daily logs capture.

**Why it's wrong:**
1. Daily logs are the authoritative record of what happened each day
2. Named session files fragment history across multiple locations
3. Creates maintenance burden and stale cross-references
4. Reusable patterns go to HEURISTICS.md or GitHub Issues, not session logs

**What to keep:**
- Daily logs: `YYYYMMDD-daily.md`
- Raw transcripts: `claude/*.md` (machine-generated, useful for analysis)

**What to delete:**
- Named session files: "X Implementation Session.md", "Y - First Use.md"
- Session summaries that restate daily log content
- Full transcript copies outside claude/ subdirectory

**If valuable patterns exist:** Extract to HEURISTICS.md or create GitHub Issue, then delete the session log.
