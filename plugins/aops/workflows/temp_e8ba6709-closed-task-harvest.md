---
alias:
- temp_e8ba6709-closed-task-harvest
- temp_e8ba6709
category: process
contributes_to:
- justification: The graveyard is exactly the accumulated terminal-task bodies this template retires; it is the only governed route from 'the graph is full of closed work nobody can read' to a graph whose closed nodes are stubs pointing at durable notes.
  stated_weight: Almost certain
  target: academicops-dfb31347
created: 2026-08-27T13:05:04.670552301+00:00
id: temp_e8ba6709
last_modified: 2026-08-28T02:52:09.893304949+00:00
modified: 2026-08-28T02:52:09.893303656+00:00
permalink: closed-task-harvest
related:
- aops_extract_inner_wf
- aops_3135feec
- aops_4bf92d6a
- kb_634e639c
- aops_f44de72e
- aops_b6376952
source: pauli 2026-08-27, reconciled against aops_f44de72e pilot rubric and kb_634e639c
tags:
- wf-template
- process
- consolidation
- pkb-hygiene
- extraction
- task-hygiene
- prune
- synthesize-not-accrete
title: closed-task-harvest
type: template
---

## What this step does

Retrospectively **harvests durable knowledge out of terminal task bodies and then retires the
bodies**, in bounded batches, over a corpus that has already accumulated. It is the backlog half of
[[kb_634e639c]] — _a task is a unit of work, not a store of knowledge_ — and it exists because
nothing in the ordinary loop collapses a body that was a working surface.

**It does not teach extraction.** The method is defined once on [[aops_extract_inner_wf]] and
executed through the `remember` skill's consolidation mode. This template states only what the
_sweep_ obliges: what may be selected, what order the phases run in, what stops it, and what each
batch leaves behind.

**Not this step:** the forward duty — extracting at the moment a task closes ([[aops_3135feec]],
fired from the closure path) is per-task, not a sweep, and is the only thing that stops this backlog
re-forming. `wf-handover`'s dangling `[[wf-memory-capture]]` names _that_ step; it stays dangling.

## Selection

- **Terminal status is the only admission criterion** — `done` or `cancelled`. The pilot
  ([[aops_f44de72e]]) drew from the closed stratum for a stated reason: a closed body is finished, so
  rewriting it cannot disturb work in flight. That is a property of state, not of age.
- **Age is a settling window, never an admission reason.** The pilot applied no age filter and none
  is evidenced. A local convention holding recently-closed work back is a _skip_ rule with no bearing
  on what qualifies; elapsed time is never evidence that a body is spent. The 2026-08-14 prune
  ([[mem_2e719040]], repair [[aops_0d8246d8]], decision [[aops_05582ad0]]) ran a pure age cutoff and
  deleted 713 live tasks — _being old is what being blocked looks like_.
- **A batch is at most 20 nodes, and 20 means 20.** The pilot's bound, verbatim: large enough that
  the clustered subset can fail visibly, small enough that a human can diff every one by hand in a
  sitting. **The budget is the safety mechanism** — if extraction is going well, stop at the bound
  anyway and report that it was going well.
- **Stratify; do not take the head of a list.** Largest bodies, modal bodies, and a thematically
  clustered set — lossiness shows up in the largest, cost in the modal, accretion only in the
  clustered.
- **Cluster siblings before extracting, never after.** One canonical note per cluster, not N per-task
  dumps: measured 50–55% cheaper than 1:1, and the 1:1 failure is the one that looks like success.
- Non-task types are **out of scope** — a `cancelled` note may carry its parent's status rather than
  its own, and that population is [[aops_4bf92d6a]]'s trichotomy, not this sweep's.

## Procedure

Phases 1–3 and 5 are **not reorderable**. Nothing is removed before a verified harvest.

1. **Baseline.** Record the store's git SHA **before the first write of the batch**, on the sweep's
   own node, and again on the receipt. Auto-sync commits interleave, so a batch is not its own commit
   and the SHA is the only recovery coordinate. **It is always obtainable and its absence is never
   acceptable.** A container with no shell cannot read it — that is a reason to take it from the host
   before dispatching, not a reason to omit it. Recovering one that was missed is trivial from the
   host: `git -C $ACA_DATA log --diff-filter=A -- <receipt path>` gives the commit that first added
   the receipt, and its parent is the pre-batch state. `pkb__status`'s `git_hash` is the **server
   binary's** build hash, not the store's commit, and is never a substitute. Serialise: one sweep at
   a time against the store.
2. **Harvest**, per node, through `remember` consolidation mode. **Default `dry_run=true`** for any
   batched pass. Destination-first: the durable content exists at a named destination id **before**
   the source body is touched. **HALT rule** — a worker that cannot write its destination stops and
   reports; it never proceeds to modify the source.
3. **Verify, per node, by recoverability.** Every fact, number, path, date, decision and supersession
   statement in the old body is reachable from the new body within **one `[[wikilink]]` hop**;
   anything that is not is **named explicitly as a loss**. _Reporting a loss is a pass; hiding one is
   the fail._ Verify by id, never by search ([[kb-487983a5]]).
   **An empty extraction yields no verdict at all.** If nothing was written to a destination there is
   nothing for recoverability to be computed against — so there is no PASS, and the node is not
   eligible for phase 5. "Nothing durable" is a legitimate finding about the _content_; it is never a
   finding that the body is safe to remove.
4. **Integrity gate. Filesystem `grep` is mandatory — a batch that cannot run it does not run.**
   Establish inbound references with `grep -rl '<id>' $ACA_DATA`, then add `pkb__search` on top. There
   is no inbound-edge tool, and even the grep count is a lower bound: frontmatter edges (`parent`,
   `depends_on`, `contributes_to`) and bare-id prose mentions are not in a wikilink count.
   **Search alone is not a lower bound, it is noise.** Batch 1 ([[revi_4808a7ce]]) ran search-only and
   reported "no clear independent inbound reference found" for a node with **40** inbound files, with
   five further undercounts of 5–15. A gate that can be off by that margin cannot license anything.
5. **Retire, to a shape that depends on terminal status.**
   - **`cancelled` — collapse to a stub**: title, terminal status, closing date, one-line reason it
     was cancelled, links to the notes that received any harvest, so the id stays resolvable. There
     is no acceptance criteria to check off against work that was abandoned.
   - **`done` — collapse to Goal / Acceptance Criteria / Receipt, not a bare stub.** The surviving
     body is exactly three parts: the goal in one or two sentences; the acceptance criteria, as a
     checklist, restated verbatim from whatever the task was actually judged against; and a receipt
     that checks off each criterion actually met, states any deviation from what was asked (in one
     line, not a narrative), and links to the PR or final artifact that is the evidence. **No
     back-and-forth, no reconciliation history, no prior positions and how they were resolved, no
     file paths or line numbers, no code.** The session transcript already holds all of that. This
     shape is denser than a `cancelled` stub because a completed task's goal, AC and outcome are
     current-state facts a future reader may genuinely need — they are not history, and collapsing a
     `done` task to the same one-liner a `cancelled` task gets would destroy that.
     **A node whose extraction was empty is left intact.** There is no stub, and no Goal/AC/Receipt, to
     write, because there is no destination to link, and either retained shape carrying no outbound
     harvest link is a deletion wearing a title.
     **Zero inbound references is the precondition for deletion**, and deletion is a separate one-way
     phase (below).
6. **Receipt, appended per node as the batch runs**, never assembled at the end — an append per node
   is the only thing distinguishing _died at node 12_ from _never started_. The batch receipt names
   the pre-batch SHA, the destination ids that received harvest, end-state counts, and everything
   skipped with its reason. **It describes every write, not the write the worker set out to make** —
   a node augmented _and_ silently amended is an undisclosed edit, and batch 1 shipped one: five
   pre-existing figures on `kb-42d2a179` were revised under a receipt line that said only "added".

## Circuit-breakers — any one halts the sweep

- **A lossy FAIL.** One node holding something unreachable from its new body halts the batch. It is a
  finding about the method, not a defect to fix quietly and continue past.
- **A body collapsed on an empty verdict.** This _is_ a lossy FAIL that was never measured, and it
  halts the batch on the same terms. Batch 1 was internally inconsistent on it inside a single run —
  `aops_8606e022` was collapsed on an empty-extraction verdict (44,574 → 1,502 chars) while
  `academicops-a12872d8` and `task_3d6d4623` were correctly left intact on the same verdict.
  Inconsistency within one batch is the tell that the rule was being applied by judgement rather than
  read off the procedure.
- **Yield disproportionate to destruction.** The specimen precedent — `nicsuzor/brain` commit
  `71516fc016` (2026-08-23; PR #48, closed unmerged) — destroyed ~81k net lines across ~300 files and
  produced 18 generic notes. A batch trending that way stops and reports; volume removed is not a
  measure of work done. Its defect fingerprints are catalogued on [[aops_extract_inner_wf]].
- **Fabrication** — a durable insight not verifiable against the source body or a cited commit.
- **A script.** _A consolidation cycle is an agent session, not a script._ Byte-identical output
  across unrelated nodes, `title or filename_stem` fallbacks, unbalanced `[[ ]]` — script artefacts,
  and the reason the specimen commit was rejected.

## What this step never does

- **Never invents a lesson to justify a write.** _"Nothing durable" is a valid and expected
  outcome_ — most terminal bodies carry only minutiae git already holds. A worker with nothing to
  extract writes **nothing**: no summary section, no generic bullet. A templated bullet is a FAIL,
  not a fallback. **And it retires nothing either** — the body stays exactly as it is (Procedure 5).
- **Never deletes a referenced node.** Breaking an inbound link to reclaim a file is a bad trade.
- **Never treats `pkb__delete` as a deletion.** It clears disk and graph and leaves the document
  **fully searchable** — unreachable by id yet still competing for retrieval, the worst state
  available. Three-step procedure and traps: [[kb-487983a5]]. Deletion is a one-way door and carries
  [[wf-human-approval]]; the harvest is two-way and does not.
- **Never rewrites a primary episodic record** — daily notes, meeting notes, evidence records — even
  when reached from a task. A task body is a checklist and may be rewritten; a primary record may not.
- **Never changes `status`, `id`, `parent`, `depends_on` or `contributes_to` on a node it harvests**,
  never picks a winner between contradicting sources, and never reverts a terminal status it believes
  is mistaken. The last two are surfaced, not resolved.

## When to include

On explicit request, or inside a scheduled consolidation cycle, when terminal bodies have accumulated
past what the graph should carry. **Skip** for a task that has just closed — that is the forward duty
[[aops_3135feec]] — and for any ask that turns out to mean live work.

**Composes with:** [[aops_extract_inner_wf]] (method), [[wf-verification]] (criteria locked before
the batch), [[wf-batch-fanout]] internal regime (chunking, in-flight receipts), [[wf-qa-verify]]
(independent verdict on the aggregate, reviewer ≠ executor), [[wf-human-approval]] (gates deletion
only), [[wf-handover]] (return).

## Exit

Every candidate sits in exactly one end state: harvested and collapsed to its retained shape (a
stub for `cancelled`, Goal/Acceptance-Criteria/Receipt for `done`), harvested and deleted (zero
inbound references, approved, three steps run), left intact with an empty-extraction finding
stated, or skipped with a stated reason. A node whose harvest was written but whose retirement did
not run is a **failure of this process, not a partial success** — and a node retired without a
verified harvest is the failure it exists to prevent.

## Relationships

- [[kb_634e639c]] — the doctrine: tasks are not knowledge stores; one correct current version per node
- [[aops_extract_inner_wf]] — the extraction method, its four tests, and its three safety controls
- [[aops_f44de72e]] — the 20-node pilot this template's selection rules and batch bound come from
- [[kb_ac17b13f]] — the pilot's measured cost, and what its self-reported 0%-loss claim does not license
- [[aops_b6376952]] / [[revi_4808a7ce]] — batch 1, the live run whose two losses are the evidence behind
  the empty-verdict rule, the mandatory-grep rule, and the SHA rule
- [[aops_3135feec]] — the forward duty at closure; the reason this sweep is finite
- [[aops_4bf92d6a]] — read-only triage of cancelled non-task documents; different corpus, different rubric
- [[kb-487983a5]] — write-to-searchable lag, and why deletion takes three steps
- [[mem_2e719040]] — the 2026-08-14 prune that used age as a proxy for obsolescence
- [[mem_pkb_serialise_writers]] — one writer per store at a time
