# Knowledge Extraction and Consolidation Cycle

A consolidation cycle is an **agent session, not a script**. Tools give you
signals; you make the decisions. Work the stages in order, using judgment about
what actually needs attention this cycle, and stop when the next action would be
lower quality than the last.

Quality over coverage, everywhere. One well-sourced note beats five superficial
ones, and one surfaced ambiguity beats one confidently wrong merge.

## Invariants and Safety Controls

1. **`dry_run=true` is the default for bulk passes and mutators.**
   The bulk mutators (`batch_update`, `batch_reparent`, `batch_merge`,
   `batch_reclassify`, `batch_archive`, `merge_node`) and all batched extraction
   passes default to `dry_run=true`. A call that omits it changes nothing and
   returns a simulation. Pass `dry_run=false` only when you deliberately intend to
   commit changes — and always inspect the preview first.

2. **Destination-first is mechanised, not advised.**
   Nothing leaves a source task body until the durable knowledge has landed and
   been verified by ID in a named destination node.
   - The destination node ID must exist and be recorded **before** any source
     body is modified.
   - If the destination write fails or returns an error, the worker **HALTS
     immediately** and reports; it **never** proceeds to modify the source task.

3. **A missing tool or write failure is a halt, not a workaround.**
   A worker or delegated stage that cannot execute a required tool or write its
   destination emits `HALT:` and the specific failure/tool name rather than
   fabricating output or performing destructive partial edits. Count halts across
   the cycle and report them at the **top** of the cycle summary.

4. **Large results spill; a spill is a signal.**
   On a mature graph, `find_duplicates` and unfiltered `list_tasks` return more
   than fits in context and land in a temp file.
   - Prefer compact output: narrow by `status` or `project`, use default markdown.
   - Reach for JSON only when needed for specific fields, with tight `limit` caps.
   - **Never pull a large result into your own context.** Mechanical processing
     runs as a script over the spilled file; semantic judgment goes to a subagent
     reading in chunks.

5. **"A consolidation cycle is an agent session, not a script."**
   Script artifacts (such as identical boilerplate strings repeated across tasks,
   `title or filename_stem` fallback text, and unbalanced `[[ ]]` links) are
   strictly prohibited. Every extraction is an agent evaluation exercising semantic
   judgment.

---

## The Definitive Knowledge-Extraction Method

Tasks hold the **work record**; they are not knowledge stores (`kb_634e639c`).
Durable knowledge discovered during work must leave the closed task body and land
in the permanent PKB store.

### The Extraction Workflow Sequence (Mandatory)

1. **Scan & Cluster Siblings**:
   Before extracting, cluster sibling tasks under the same parent or topic area.
   Shared insights must be synthesised into **one canonical topic note** rather
   than generating N fragmented notes (clustering yields 50–55% token reduction
   and higher coherence).
2. **Search for Canonical Note**:
   Run `pkb__search(query="<topic>")` to check if a canonical topic note already
   exists.
   - If a canonical topic note exists: plan to **augment** it (`pkb__update_body`).
   - If no note exists: plan to **create** a new structured topic note (`pkb__create`).
3. **Execute Destination Write (Destination-First)**:
   Persist the synthesised knowledge to the destination note.
   - Strip any duplicated frontmatter blocks when doing surgical edits (`mem_189264cc`).
   - Re-read and verify the write landed by ID (`mem_pkb_serialise_writers`).
   - If write fails: **HALT and report**. Do NOT touch the source task.
4. **Rewrite Source Task Body In-Place**:
   Once (and only once) destination persistence is verified, rewrite the source
   task body in place to a concise, navigational record (<1,500 chars).
   - In-place rewrite **never** changes `status`, `id`, `parent`, `depends_on`, or
     `contributes_to`.
   - The rewritten body contains:
     - One-sentence **Goal**
     - Completed work checklist
     - Backlinks to extracted notes under `## Pointers` (e.g. `- Extracted knowledge: [[destination-node-id]]`)
     - Backlinks to PRs, commits, and parent/child tasks
5. **Densify Graph Relationships**:
   Ensure the destination note carries multiple valid `[[wikilink]]` pointers in
   prose to relevant concepts, parent topics, and Maps of Content (MOCs).

### What moves, what stays, what goes

| Move to a topic note                                                                                                                                                                  | Keep in the task body                                                                                               | Discard                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Models and formulas; architecture; behavioural invariants; empirical findings; post-mortems and generalisable lessons; infra constraints and APIs; **contacts, URLs, document links** | One-sentence Goal; completed checklist; backlinks to extracted notes; backlinks to parent/child; PR and commit URLs | Retry loops and terminal spam; intermediate debug output; routine status timestamps; raw transcripts and PIDs; retracted scratchpad proposals |

### The Four Tests — Every Extraction Passes All Four

Evaluate every extraction by **recoverability, not tidiness**: diff the old body
against the new body plus every note it points to.

1. **Lossy (FAIL)**: Any durable fact, number, path, decision, date, contact, URL,
   or supersession statement in the old body unreachable from the new body within
   **one `[[wikilink]]` hop**. Deleted prose with nowhere to land is worse than
   doing nothing.
2. **Accretive (FAIL)**: The old body pasted verbatim under a dated heading, or a
   new note created 1:1 per task where a canonical note exists. Where a canonical
   topic note exists, you must **augment and synthesise into it**.
3. **Fabricated (FAIL)**: Anything not verifiable against the source body or a
   cited commit/PR. Never invent generalisations or paste templated advice.
4. **Good (PASS)**: New task body is short and navigational (<1,500 chars); each
   durable fact sits in a topic note beside its siblings; the reader opens **one**
   note instead of walking a chain of closed tasks.

### The Seven Defect Classes (Reviewer Lint List)

Every knowledge note produced or touched must be checked against these defect classes:

1. **Duplicate canonical/narrow pairs**: Narrow observations created in parallel
   to an existing canonical note (must merge into canonical and remove duplicate).
2. **Title-encoded dates and session IDs**: Titles like `note-2026-04-18` or
   `kb-<hash>` freeze living knowledge into dated artifacts that accrete rather than
   update.
3. **Missing `sources:` in frontmatter**: Knowledge claims lacking provenance.
4. **Missing `confidence:` in frontmatter**: Missing confidence level
   (`established`, `provisional`, `speculative`).
5. **Status content misfiled as `type: knowledge`**: Phase progress tables, RFC
   status, or blocker trackers belong on tasks, not in knowledge notes that rot.
6. **Zero wikilinks despite obvious targets**: Isolated notes unreachable in graph
   traversal.
7. **Notes never advancing past `status: inbox`**: Knowledge notes stagnating at
   inbox rather than advancing through maturity stages.

### Empty Extraction is a Legal, Named Outcome

A task that contains only ephemeral coordination, routine logs, trivial status, or
scratchpad proposals contains **nothing durable**.

- In such cases, the worker writes **nothing** to the knowledge layer (no new note,
  no updated note, no `## Key Knowledge` placeholder).
- A generic or templated bullet (e.g. invented framework rules) is a **FAIL, not a
  fallback**.
- The task body is simply rewritten in place to its minimal goal + checklist + PR
  pointers.

---

## Stages of the Consolidation Cycle

### 1 — Baseline

Run `graph_stats`. Record `flat_tasks`, `disconnected_epics`,
`targets_without_contributing_edges`, `orphan_count`, `stale_count`, and
`metrics_hash`.

Measure the knowledge layer separately:

```
pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)
```

Record that total as the convergence baseline. Measure both numbers again at the
end of the cycle to report the delta.

### 2 — Mine the Transcripts

Session transcripts hold what agents did not save during sessions.
Find transcripts with no `mined: <date>` in frontmatter (up to 15 per cycle):

1. Read the transcript, identifying first-class topics, decisions, and patterns.
2. Route per the extraction method: search for canonical note, augment or create,
   record provenance (`sources: ["Session <id> (<date>)"]`, `confidence: provisional`).
3. Mark frontmatter `mined: <date>`. **Never modify transcript body content.**
4. If transcript store is unreachable, report as skipped.

### 3 — Consolidate Knowledge & Extract Closed Tasks

Find episodic content not yet consolidated (daily notes, meeting notes with no
`consolidated:` marker, and closed tasks with substantive bodies):

1. For each source, apply the **Definitive Knowledge-Extraction Method** above:
   - Identify durable facts (models, architecture, decisions, contacts, URLs).
   - If nothing durable: record empty extraction.
   - If durable: write to canonical destination note first, verify read-back by ID.
   - Rewrite source task body in-place (<1,500 chars).
   - Mark episodic notes `consolidated: <date>` and advance status.
2. Create a Map of Content (MOC, `type: moc`) only when a topic area accumulates 5+
   canonical notes and navigation is genuinely improved.

### 4 — Reconcile Data Quality

Fix data quality before structural maintenance. Three activities:

#### Duplicates

`find_duplicates(mode="both")` produces candidates, not verdicts. Always read member
titles to judge:

- Heterogeneous titles mean not a duplicate set, regardless of score.
- Merge only when members are the same work restated.
- Quarantine large/degenerate clusters.
- Always check that the survivor is the note with the most context.

#### Staleness and Closure

Staleness, unclosed merged tasks, dead claims, and artifact rot are owned by the
`reconcile` skill (`plugins/aops-core/skills/reconcile/SKILL.md`).
Delegate this stage to `/reconcile` in batch context; do not freelance separate
closure logic.

#### Misclassification

Identify captures masquerading as tasks (e.g. aged "Email:" prefixes with no
children, informational prose with no action). Archive or reclassify to memories.

### 5 — Sweep for Orphans

Run `pkb_orphans()` for actionable tasks and knowledge notes. Evaluate flagged
nodes and surface genuine candidates rather than blindly retiring them.

### 6 — Process Refiles

Process tasks flagged `refile` by inspecting task body, lineage, and context:

- Correct parentage, consequence, severity, effort, dependencies, and tags.
- Clear the `refile` flag when complete.

### 7 — Maintain the Graph

Check `metrics_hash` against baseline. If unchanged, actionable graph has
converged. Maintain knowledge layer until stable. Two consecutive no-op cycles
across both layers indicates graph stability.

### 8 — Check Your Own Output

Perform a 2-minute audit on notes produced or modified this cycle:

- Does every claim carry `sources:`?
- Does synthesis cite 2+ observations?
- Are wikilinks valid?
- Is confidence present and plausible?
- Did all extractions pass the four tests?

---

## The Cycle Summary

Every consolidation run emits a structured report:

1. **Subagent Halt Count** (at the very top, even if zero): list any `HALT:`
   occurrences with phase and missing tool/error.
2. **Baseline & Deltas**: initial vs final graph stats and knowledge orphan counts.
3. **Stage Details**: items processed, notes created/augmented, tasks rewritten,
   duplicates merged, with exact IDs named.
4. **Empty Extractions**: list of task IDs where extraction was cleanly empty.
5. **Next Actions**: concise statement of what the next cycle should pick up.
