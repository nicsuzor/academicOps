# Knowledge Extraction and Consolidation Cycle

A consolidation cycle is an agent session, not a script: tools give you signals,
you make the decisions. Work the stages in order, judging what actually needs
attention this cycle, and stop when the next action would be lower quality than
the last. Quality over coverage everywhere -- one well-sourced note beats five
superficial ones, and one surfaced ambiguity beats one confidently wrong merge.

## Invariants and safety controls

1. **`dry_run=true` is the default for bulk passes and mutators.** The bulk
   mutators (`batch_update`, `batch_reparent`, `batch_merge`, `batch_reclassify`,
   `batch_archive`, `merge_node`) and all batched extraction passes default to
   `dry_run=true`; a call that omits it changes nothing and returns a simulation.
   Pass `dry_run=false` only when you deliberately intend to commit changes, and
   always inspect the preview first.
2. **Destination-first is mechanised, not advised.** Nothing leaves a source task
   body until the durable knowledge has landed and been verified by ID in a named
   destination node. The destination node ID exists and is recorded **before** any
   source body is modified. If the destination write fails or returns an error,
   halt immediately and report; never proceed to modify the source task.
3. **A missing tool or write failure is a halt, not a workaround.** A worker or
   delegated stage that cannot execute a required tool or write its destination
   emits `HALT:` with the specific failure and tool name, rather than fabricating
   output or performing destructive partial edits. Count halts across the cycle
   and report them at the **top** of the cycle summary.
4. **Large results spill, and a spill is a signal.** On a mature graph,
   `find_duplicates` and unfiltered `list_tasks` return more than fits in context
   and land in a temp file. Narrow by `status` or `project` and prefer default
   markdown; reach for JSON only when you need specific fields, with tight `limit`
   caps. Never pull a large result into your own context: mechanical processing
   runs as a script over the spilled file, and semantic judgment goes to a
   subagent reading in chunks.
5. **Every extraction is an agent evaluation exercising semantic judgment.**
   Script artifacts are prohibited -- identical boilerplate strings repeated across
   tasks, `title or filename_stem` fallback text, unbalanced `[[ ]]` links.

## The knowledge-extraction method

Tasks hold the **work record**; they are not knowledge stores (`kb_634e639c`).
Durable knowledge discovered during work leaves the closed task body and lands in
the permanent PKB store.

### The sequence, in order

1. **Scan and cluster siblings.** Cluster sibling tasks under the same parent or
   topic area before extracting. Shared insights synthesise into **one canonical
   topic note**, never N fragmented notes: clustering measures 50–55% cheaper in
   tokens and yields higher coherence.
2. **Search for the canonical note.** Run `pkb__search(query="<topic>")`. If a
   canonical topic note exists, plan to augment it (`pkb__update_body`); if none
   exists, plan a new structured topic note (`pkb__create`).
3. **Execute the destination write first.** Persist the synthesised knowledge to
   the destination note, stripping any duplicated frontmatter blocks when doing
   surgical edits. Re-read and verify the write landed by ID. If the write fails,
   **halt and report** -- do not touch the source task.
4. **Rewrite the source task body in place**, once and only once destination
   persistence is verified. The rewrite never changes `status`, `id`, `parent`,
   `depends_on`, or `contributes_to`. The rewritten body stays under 1,500
   characters and contains a one-sentence **Goal**, a completed-work checklist,
   backlinks to the extracted notes under `## Pointers`
   (e.g. `- Extracted knowledge: [[destination-node-id]]`), and backlinks to PRs,
   commits, and parent/child tasks.
5. **Densify graph relationships.** The destination note carries multiple valid
   `[[wikilink]]` pointers in prose to relevant concepts, parent topics, and Maps
   of Content.

### What moves, what stays, what goes

| Move to a topic note                                                                                                                                                                  | Keep in the task body                                                                                               | Discard                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Models and formulas; architecture; behavioural invariants; empirical findings; post-mortems and generalisable lessons; infra constraints and APIs; **contacts, URLs, document links** | One-sentence Goal; completed checklist; backlinks to extracted notes; backlinks to parent/child; PR and commit URLs | Retry loops and terminal spam; intermediate debug output; routine status timestamps; raw transcripts and PIDs; retracted scratchpad proposals |

### The four tests -- every extraction passes all four

Evaluate by **recoverability, not tidiness**: diff the old body against the new
body plus every note it points to.

1. **Lossy (FAIL)** -- any durable fact, number, path, decision, date, contact,
   URL, or supersession statement in the old body unreachable from the new body
   within **one `[[wikilink]]` hop**. Deleted prose with nowhere to land is worse
   than doing nothing.
2. **Accretive (FAIL)** -- the old body pasted verbatim under a dated heading, or a
   new note created 1:1 per task where a canonical note already exists. Where a
   canonical note exists, augment and synthesise into it.
3. **Fabricated (FAIL)** -- anything not verifiable against the source body or a
   cited commit/PR. Never invent generalisations or paste templated advice.
4. **Good (PASS)** -- the new task body is short and navigational (<1,500
   characters), each durable fact sits in a topic note beside its siblings, and
   the reader opens **one** note instead of walking a chain of closed tasks.

### The seven defect classes

Check every knowledge note produced or touched against all seven:

1. **Duplicate canonical/narrow pairs** -- a narrow observation created in parallel
   to an existing canonical note. Merge into the canonical and remove the
   duplicate.
2. **Title-encoded dates and session IDs** -- `note-2026-04-18`, `kb-<hash>`. These
   freeze living knowledge into dated artifacts that accrete rather than update.
3. **Missing `sources:` in frontmatter** -- a knowledge claim with no provenance.
4. **Missing `confidence:` in frontmatter** -- `established`, `provisional`, or
   `speculative`.
5. **Status content misfiled as `type: knowledge`** -- phase progress tables, RFC
   status, blocker trackers. Those belong on tasks, not in knowledge notes that
   rot.
6. **Zero wikilinks despite obvious targets** -- the note is unreachable in graph
   traversal.
7. **Never advancing past `status: inbox`** -- the note stagnates instead of
   advancing through maturity stages.

### Empty extraction is a legal, named outcome

A task holding only ephemeral coordination, routine logs, trivial status, or
scratchpad proposals contains nothing durable. Write **nothing** to the knowledge
layer: no new note, no updated note, no `## Key Knowledge` placeholder. A generic
or templated bullet is a **FAIL, not a fallback**. Rewrite the task body in place
to its minimal goal, checklist, and PR pointers.

## Stages of the cycle

### 1 -- Baseline

Run `graph_stats` and record `flat_tasks`, `disconnected_epics`,
`targets_without_contributing_edges`, `orphan_count`, `stale_count`, and
`metrics_hash`. Measure the knowledge layer separately:

```
pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)
```

Record that total as the convergence baseline. Measure both numbers again at the
end of the cycle and report the delta.

### 2 -- Mine the transcripts

Session transcripts hold what agents did not save during sessions. Find
transcripts with no `mined: <date>` in frontmatter, up to 15 per cycle:

1. Read the transcript, identifying first-class topics, decisions, and patterns.
2. Route per the extraction method -- search for the canonical note, augment or
   create, record provenance (`sources: ["Session <id> (<date>)"]`,
   `confidence: provisional`).
3. Mark frontmatter `mined: <date>`. **Never modify transcript body content.**
4. If the transcript store is unreachable, report it as skipped.

### 3 -- Consolidate knowledge and extract closed tasks

Find episodic content not yet consolidated: daily notes, meeting notes, and
closed tasks with substantive bodies. For each source, apply the extraction
method above -- identify durable facts (models, architecture, decisions,
contacts, URLs); record an empty extraction if nothing is durable; otherwise
write to the canonical destination note first, verify read-back by ID, then
rewrite the source task body in place under 1,500 characters, or delete the
source daily note or meeting note once its knowledge is verified at the
destination.

Create a Map of Content (`type: moc`) only when a topic area accumulates 5+
canonical notes and navigation is genuinely improved.

### 4 -- Reconcile data quality

Fix data quality before structural maintenance.

**Duplicates.** `find_duplicates(mode="both")` produces candidates, not verdicts.
Read member titles to judge: heterogeneous titles mean it is not a duplicate set
regardless of score; merge only when members are the same work restated;
quarantine large or degenerate clusters; always check that the survivor is the
note with the most context.

**Staleness and closure.** Staleness, unclosed merged tasks, dead claims, and
artifact rot are owned by the `reconcile` skill
(`plugins/aops/skills/reconcile/SKILL.md`). Delegate this to `/reconcile` in
batch context; do not freelance separate closure logic.

**Misclassification.** Identify captures masquerading as tasks -- aged "Email:"
prefixes with no children, informational prose with no action. Archive them or
reclassify them to memories.

### 5 -- Sweep for orphans

Run `pkb_orphans()` for actionable tasks and knowledge notes. Evaluate flagged
nodes and surface genuine candidates rather than blindly retiring them.

### 6 -- Process refiles

Process tasks flagged `refile` by inspecting task body, lineage, and context:
correct parentage, consequence, severity, effort, dependencies, and tags, then
clear the `refile` flag.

### 7 -- Maintain the graph

Check `metrics_hash` against baseline. If it is unchanged, the actionable graph
has converged; maintain the knowledge layer until it is stable. Two consecutive
no-op cycles across both layers indicates graph stability.

### 8 -- Check your own output

Audit the notes produced or modified this cycle: does every claim carry
`sources:`, does each synthesis cite 2+ observations, are the wikilinks valid, is
`confidence` present and plausible, and did every extraction pass the four tests?

## The cycle summary

Every consolidation run emits a structured report:

1. **Subagent halt count**, at the very top even if zero: every `HALT:`
   occurrence with its phase and missing tool or error.
2. **Baseline and deltas**: initial versus final graph stats and knowledge orphan
   counts.
3. **Stage details**: items processed, notes created and augmented, tasks
   rewritten, duplicates merged -- with exact IDs named.
4. **Empty extractions**: the task IDs where extraction was cleanly empty.
5. **Next actions**: what the next cycle should pick up.
