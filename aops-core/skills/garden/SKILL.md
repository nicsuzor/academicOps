---
name: garden
category: instruction
description: Incremental PKM and task graph maintenance - weeding, pruning, linking, consolidating, reparenting. Tends the knowledge base and task hierarchy bit by bit.
allowed-tools: Read,Grep,Glob,Edit,Write,Bash,Task,mcp__pkb__search,mcp__pkb__list_documents
version: 1.0.0
permalink: skills-garden
---

# Garden

Tend the personal knowledge base and task graph incrementally. Small regular attention beats massive occasional cleanups.

## Gardening Activities

| Activity       | What to Do                                          |
| -------------- | --------------------------------------------------- |
| **Lint**       | Validate frontmatter structure and YAML syntax      |
| **Weed**       | Remove dead links, outdated content, duplicates     |
| **Prune**      | Archive stale notes, trim bloated files             |
| **Compost**    | Merge fragments into richer notes                   |
| **Cultivate**  | Enrich sparse notes, add context                    |
| **Link**       | Connect orphans, add missing [[wikilinks]]          |
| **Map**        | Create/update MoCs for navigation                   |
| **DRY**        | Remove restated content, replace with links         |
| **Synthesize** | Strip deliberation artifacts from implemented specs |
| **Reparent**   | Fix orphaned tasks, enforce hierarchy rules         |
| **Hierarchy**  | Validate task→epic→project→goal structure           |
| **Stale**      | Flag tasks with stale status or inconsistencies     |
| **Dedup**      | Surface duplicate/overlapping tasks for review      |

## Modes

### lint [area]

Validate frontmatter structure and YAML validity. Uses `scripts/lint_frontmatter.py`.

```bash
uv run python $AOPS/aops-tools/skills/garden/scripts/lint_frontmatter.py <path> [--recursive] [--fix] [--errors-only]
```

**What it checks:**

| Code  | Severity | Issue                                                 |
| ----- | -------- | ----------------------------------------------------- |
| FM003 | error    | Opening `---` not on its own line (e.g., `---title:`) |
| FM005 | error    | Missing closing `---` delimiter                       |
| FM008 | error    | Invalid YAML syntax                                   |
| FM009 | warning  | Missing identifier (id/task_id/permalink)             |
| FM010 | warning  | Missing title field                                   |

**Common YAML issues requiring manual fix:**

- `title: [Learn] something` - brackets parsed as YAML array; quote the title
- `aliases: [x]` followed by `- x` - conflicting YAML syntax
- Wikilinks in values - `[[link|alias]]` can break YAML parsing

**Usage:**

```bash
# Scan for issues
uv run python lint_frontmatter.py data/tasks/ --recursive --errors-only

# Fix delimiter issues automatically
uv run python lint_frontmatter.py data/tasks/inbox/ --fix
```

### scan [area]

Health check. Count orphans, broken links, stale content, sparse notes, duplicates, orphan implementation docs.

**Orphan Implementation Doc Detection**:
Files in `experiments/` that describe features with existing specs should be synthesized, not left as separate files. Scan identifies these:

1. List files in `$AOPS/experiments/*.md`
2. For each, check title/content against `specs/` filenames and content
3. If match found → report as "orphan implementation doc - synthesize into [spec]"
4. Output: "Found N implementation docs that should be merged into specs"

Note: Per AXIOM #28, episodic observations go to tasks, not local files.

### weed [area]

Fix broken [[wikilinks]], remove dead references, flag duplicates.

### prune [area]

Archive stale sessions (>30 days), compress verbose notes, update temporal metadata.

### link [area]

Connect orphans and enforce semantic link density per [[HEURISTICS.md#H34]].

**What to check:**

1. **Zero-backlink orphans**: Files with no incoming links
2. **Semantic orphans**: Files in same folder with overlapping topics but no mutual links
3. **Hub disconnection**: Project hubs that don't link to their key content files
4. **Missing bidirectional links**: If A references B's topic, both should link

**Detection process:**

1. List files in target area
2. For each project folder, check: does hub link to substantive content (not just `[[meetings]]`)?
3. For files with overlapping tags in same folder, check: do they link to each other?
4. Use `mcp__pkb__search` on file titles - if PKB returns "related" files that don't link, flag them

**Fix process:**

- Add wikilinks IN PROSE where semantic relationships exist (per [[HEURISTICS.md#H7b]] - no "see also" sections)
- Ensure hub files link to key strategic/analysis documents
- Ensure related analyses link bidirectionally

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
- Episodic content that should be tasks, not local files

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

## Task Graph Gardening

The task graph accumulates structural debt just like the knowledge base. Task gardening maintains hierarchy integrity and priority signal quality.

### Hierarchy Rules

| Level    | Must belong to              |
| -------- | --------------------------- |
| Task     | An epic                     |
| Epic     | A project or another epic   |
| Project  | A project or a goal         |
| Goal     | Root-level (no parent required) |

**No task should be a root-level orphan.** Orphan tasks degrade graph metrics, break downstream weight calculations, and become invisible to priority-based queries.

### reparent [project]

Detect and fix orphaned tasks within a project.

**Detection:**

1. List tasks for the project: `mcp__pkb__list_tasks(project="X", status="ready")`
2. Identify root-level items (no parent) that aren't goals or projects
3. Group orphans by theme — look for natural clusters (3-8 items)

**Execution:**

1. If orphans fit an existing epic, reparent with `mcp__pkb__update_task(id, {parent: epic_id})`
2. If orphans form a new cluster, create an epic first, then reparent children to it
3. Ensure new epics themselves have a parent (project or goal) — don't create new orphans
4. Verify: no epic has excessive children (target: 5-10 per epic, max ~12)

**Batch efficiency:** Make all `update_task` calls in parallel — parent assignment has no cross-dependencies.

### hierarchy [project]

Validate the full hierarchy for a project.

1. Check all tasks have a parent epic
2. Check all epics have a parent project or goal
3. Check no epic has >12 direct children (split if needed)
4. Check no task has `type: task` but functions as an epic (has children) — fix type to `epic`
5. Report violations as a summary table

### stale [project]

Detect tasks that may need status updates.

1. `in_progress` tasks with no modification in >7 days → flag for review
2. `active` tasks with all children `done` → candidate for completion
3. Tasks marked `done` but with `active` children → inconsistency, flag

### dedup [project]

Find tasks with similar titles or overlapping scope.

1. Use `mcp__pkb__task_search` with each task's title against the project
2. Flag pairs with high similarity scores
3. Surface for human decision — don't auto-merge (requires judgment)

## Area Targeting

| Area        | Focus                      |
| ----------- | -------------------------- |
| `projects`  | Project documentation      |
| `sessions`  | Session logs               |
| `tasks`     | Task tracking              |
| `archive`   | Historical content         |
| `[project]` | Specific project subfolder |

Default: highest-activity areas (recent modifications).

## Health Metrics

| Metric                                    | Target        |
| ----------------------------------------- | ------------- |
| Frontmatter errors                        | 0             |
| Orphan rate (notes)                       | <5%           |
| Link density                              | >2 per note   |
| Broken links                              | 0             |
| MoC coverage                              | >90%          |
| DRY violations                            | 0             |
| Implemented specs with deliberation cruft | 0             |
| Orphan tasks (no parent)                  | 0             |
| Epic child count                          | 5-10 per epic |
| Hierarchy violations                      | 0             |
| Stale in_progress tasks (>7 days)         | 0             |

## Anti-Patterns

- Marathon cleanup sessions → Small, frequent instead
- Delete without extracting value → Preserve then prune
- Reorganize folder structures → Use MoCs for navigation
- Restate core docs → Link or omit entirely
- Perfectionism → Progress over perfection
- **`## Relations` or 'references' boilerplate** sections → Remove entirely

## Named Session Logs Anti-Pattern

**Problem:** Individual session files like "Framework Logger Agent - First Production Use.md" or "ZotMCP Implementation Session 2025-11-22.md" duplicating what daily logs capture.

**Why it's wrong:**

1. Daily logs are the authoritative record of what happened each day
2. Named session files fragment history across multiple locations
3. Creates maintenance burden and stale cross-references
4. Reusable patterns go to HEURISTICS.md or tasks, not session logs

**What to keep:**

- Daily logs: `YYYYMMDD-daily.md`
- Raw transcripts: `claude/*.md` (machine-generated, useful for analysis)

**What to delete:**

- Named session files: "X Implementation Session.md", "Y - First Use.md"
- Session summaries that restate daily log content
- Full transcript copies outside claude/ subdirectory

**If valuable patterns exist:** Extract to HEURISTICS.md or create a task via `mcp__pkb__create_task()`, then delete the session log.
