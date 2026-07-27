# Consolidation Cycle

A consolidation cycle is an **agent session, not a script**. Tools give you
signals; you make the decisions. Work the stages in order, using judgment about
what actually needs attention this cycle, and stop when the next action would be
lower quality than the last.

Quality over coverage, everywhere. One well-sourced note beats five superficial
ones, and one surfaced ambiguity beats one confidently wrong merge.

## Two invariants before you start

**The bulk mutators default to preview.** `batch_update`, `batch_reparent`,
`batch_merge`, `batch_reclassify`, `batch_archive`, and `merge_node` all default
to `dry_run=true`. A call that omits it changes nothing and returns a simulation.
Pass `dry_run=false` when you mean it — and read the preview first when you do
not.

**Large results spill; a spill is a signal.** On a mature graph, `find_duplicates`
and unfiltered `list_tasks` return more than fits in context and land in a temp
file instead. When that happens you have lost the turn and the data is not where
you can use it.

- Prefer compact output: `list_tasks` with a `status` or `project` filter and the
  default markdown format. Reach for JSON only when you need a specific field,
  then cap `limit` hard.
- **Never pull a large result into your own context to analyse it.** Mechanical
  work — counting, filtering, grouping, pulling fields — runs as a script over
  the spilled file. Whole-file semantic judgment — which clusters are real,
  reading prose — goes to a sub-agent that reads in chunks and returns a compact
  verdict. Either way you never load the blob.
- Do not retry the same call. The slice was too broad.

**A missing tool is a halt, not a workaround.** A delegated stage that cannot get
a tool it needs emits `HALT:` and the tool name rather than fabricating output.
Count the halts across the cycle and report the total at the **top** of the cycle
summary with the stage and the missing tool — not buried inside per-stage output.
A halt reported nowhere visible is the silent failure this rule exists to catch.

## 1 — Baseline

`graph_stats`. Record `flat_tasks`, `disconnected_epics`,
`targets_without_contributing_edges`, `orphan_count`, `stale_count`, and
`metrics_hash`.

Then measure the knowledge layer **separately** — `orphan_count` is
actionable-only and never counts `note`, `knowledge`, or `memory` nodes:

```
pkb_orphans(types=["note","knowledge","memory"], include_all=true, limit=0)
```

Record that total. It is the number the knowledge-layer work converges against;
`orphan_count` is not a proxy for it.

Orphan detection is type-aware. Actionable nodes orphan on a missing parent
alone. Knowledge and strategic nodes orphan only with **no parent and no
deliberate edge in either direction** — a body `[[wikilink]]`, an inbound link,
or a `contributes_to` all clear it; only auto-computed similarity edges do not.
So "not an orphan" means graph-reachable. It does not certify that a note carries
its own outbound wikilink, which is what the capture contract requires.

Measure the same two numbers again at the end of the cycle and report the delta.

## 2 — Mine the transcripts

Session transcripts hold what agents did not save at the time.

Find transcripts with no `mined: <date>` in frontmatter. For each, up to about
fifteen a cycle:

1. Read it, noting decisions, patterns, facts, and problems solved.
2. For each insight, identify the **first-class topic it is about** — the subject,
   not the symptom.
3. Route it per the capture discipline: augment the canonical note for that
   topic, create one with a section scaffold if the topic is first-class and has
   none, reconcile stale peers in the same write. Provenance is the session
   reference and the date; single-source additions are `confidence: provisional`.
4. Mark the transcript `mined: <date>` in frontmatter. **Never modify its
   content** — a transcript is a primary record.

Skip anything already saved during the session. Never fabricate, never
editorialise.

Transcripts live outside `$ACA_DATA`, which is why they may be edited directly at
all — and the edit is confined to that one frontmatter field.

If the transcript store is not reachable in this environment, skip this stage and
say so.

> Extracting **prompts or command invocations** — which commands were run, how
> often, which skills fired — is not a transcript-reading job. The structured
> session summaries carry `user_prompts` and typed timeline events across every
> client; read those. Raw transcripts are the fallback for what summaries do not
> hold: agent reasoning, tool calls, full context.

## 3 — Consolidate knowledge

Find episodic content not yet consolidated: daily notes and meeting notes with no
`consolidated:` frontmatter, and completed tasks with substantive bodies. Older
than about a week is the usual candidacy signal.

For each, identify the first-class topic each insight is about, and route it to
the canonical topic note per the capture discipline — that is where the _how_
lives, and this stage does not restate it. Then mark the source
`consolidated: <date>` and advance its status, leaving its content untouched.

Create a Map of Content only when a topic area has genuinely accumulated five or
more canonical notes and navigation would help. Skip it by default.

Pacing, per cycle: roughly ten episodic sources, three canonical notes created or
substantially restructured, at most one MOC.

**Age alone never justifies cancellation.** Old episodic sources get surfaced for
review, not retired.

## 4 — Reconcile data quality

Before any structural work, fix the data. Four activities, bounded.

### Duplicates

`find_duplicates(mode="both")` produces **candidates, not verdicts**. The only
reliable field is member count; every other call is made by **reading the member
titles**. The cluster score can lie — a degenerate cluster once self-reported
perfect title similarity across unrelated titles, while genuine merge pairs
routinely score low. **When the score and the titles disagree, trust the titles.**
The question is always "are these the same work item, restated?", and it is
answered by reading.

- Ignore non-clusters: fewer than two distinct members, or a canonical id that is
  also in the merge set.
- **Heterogeneous titles mean it is not a duplicate set, at any member count** —
  including three members at maximum confidence. Member count bounds blast
  radius; it does not detect degeneracy.
- Quarantine large clusters, and separate the two reasons. **Degenerate** —
  heterogeneous titles, catch-all anchored on one broad epic — is a tool artifact
  and gets one summary line. **Large but plausibly genuine** — homogeneous titles,
  too many to merge unattended — gets filed as an actual task ("Review N-way
  duplicate set: <shared title>") so it survives an unattended run.
- Disposition the rest by reading: **merge** where every member is the same work
  restated; **reject** where different people or organisations were spuriously
  matched; **flag** where the overlap is real but the scope may differ; **partial**
  where some members match and others do not — flag the coherent pairs, never
  merge the whole cluster.
- Two guards before any merge: glance at bodies for date-prefixed, section-
  numbered, "Summary", "Plan", and "Review" titles, which are false-positive
  classes; and sanity-check the canonical, which is sometimes the narrower node —
  keep the survivor with the most context.
- Every cluster lands in exactly one bucket in the cycle summary, with counts.

### Staleness

Non-terminal tasks aged past about ninety days, up to twenty a cycle. Read the
body, then look for completion evidence — sent mail, calendar entries, commits.
Evidence found means complete the task with the evidence recorded. No evidence
means **flag for human review**, never auto-cancel: age is not evidence of
irrelevance. Where the evidence tools are not available in this environment, skip
the verification and flag the candidates.

### Misclassification

Untriaged captures masquerading as tasks: an "Email:" title prefix with real age
and no children; long-aged nodes with no children and a sparse body; bodies that
are purely informational with no action in them. Clear non-tasks get archived
with a reason or reclassified to a memory; anything ambiguous is flagged. Up to
about thirty a cycle.

### Close the loop

For each closed PR since the last cursor, match it to a task by, in order: a
`pr_url` already on the task; a task id in the PR body; the PR head branch
matching the task's recorded branch; the PR title matching the task title
whole-word, ignoring conventional-commit prefixes. A reverse match on distinctive
title substrings is surfaced as _likely closed by_ and **never auto-completes**.

- **Merged** → re-read the task's acceptance criteria against the merged artifact
  before closing. Every criterion clearly met → complete it, recording the PR and
  the date. Any criterion unmet or requiring judgment → leave it and surface the
  criterion, quoted. Surface, do not block.
- **Closed without merge** → route it (below). Never re-queue automatically.
- **No match** → surface it. Never invent a task.

PRs only; no commit-log scanning. The cursor advances only after writes succeed.

Run a **cursor-independent backstop** over every task in `merge_ready` or
`review`, oldest first. These are not the same parked state. A `merge_ready` task
resolves against its PR — merged and not yet done goes through the same
criteria check; closed-without-merge routes below; **no resolvable PR at all is
anomalous** and gets surfaced, not closed. A `review` task is parked on a human
decision and is **never auto-closed**: if it carries a PR, note the PR's live
state in what you surface; if it has no PR, which is the common case, surface it
as awaiting a decision so it cannot rot silently.

Also surface: a body claiming release with no PR recorded; a worker no-op marker,
which re-queues to `inbox` with an annotation; and three or more sweep reports on
one task all reading closed-without-merge, which is strong evidence the approach
keeps failing and belongs in the routing context.

**Never force a close past open children.** When a merge is confirmed but the
close is rejected because children are open, do not cascade. Open children may be
legitimate post-merge follow-up, and cascade-closing destroys real pending work.
Surface it as merge-confirmed, close-blocked, and let it resolve when the child
does.

If the state this stage depends on is absent — as distinct from the PKB being
unreachable — say so explicitly in the summary. Do not report a stage as complete
when it never had inputs.

### Routing a PR closed without merge

Gather the context first: PR title and body, the last several reviewer comments,
the review state, labels, whether the branch was deleted, and whether the task
already carries repeated closed-without-merge reports.

Then **have an agent read it and classify**. This is a semantic judgment, not a
string match — a "wontfix" label is a signal, not the verdict. Exactly one of:

| Class                  | Signal                                                                                    | Action                                                                                                                                                             |
| ---------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **wontfix**            | Clear "do not do this", not-planned, superseded, or the reviewer rejects the goal itself. | Cancel the task, or complete it if a sibling superseded it. Record the PR and the reason in the body. File no follow-up.                                           |
| **bad-implementation** | Wrong approach, design rejected, repeated failure, "needs a rethink", or ambiguous.       | Cancel the original. File a sibling investigation task under the same parent, softly depending on the original, saying what went wrong and what must change first. |
| **retry-as-is**        | Rare. Unrelated infrastructure failure, documented in the comments. Nothing was wrong.    | Re-queue to `inbox`, with the justification written into both the task body and the cycle log.                                                                     |

Record the chosen route, the close reason, and any node created.

## 5 — Sweep for staleness

Orphans and under-specified work, as **signals** rather than verdicts. Run
`pkb_orphans()` for the actionable layer and the knowledge-layer call from stage
1 for the other. Read the flagged nodes and decide whether they genuinely need
attention. Surface candidates; do not auto-cancel on age.

**Artifact rot check.** For `ready` and `queued` tasks aged past about a
fortnight, verify that the files and symbols the task's criteria name still exist
where they claim to. Where they have rotted, demote the task to `inbox` with an
annotation saying so and re-decompose. Rot triggers demotion; age alone does not.

## 6 — Process refiles

A `refile` flag means the user spotted something structurally wrong — not only
parentage. Find flagged tasks and fix the whole weighting surface, reading the
task's own body, its lineage, and its context rather than copying fields from the
parent:

- **Parent** — find the correct lineage.
- **Consequence and severity** — on a target, match severity to the impact the
  consequence prose actually describes, and write that prose if it is missing. On
  an ordinary task, never assign non-zero severity; if it looks target-worthy,
  flag it for triage instead.
- **Priority** — never originate or adjust a band. A band that looks clearly
  wrong gets flagged for the user, not changed.
- **Due** — fix a missing or plainly wrong date; flag if unclear.
- **Effort** — estimate from actual scope. A default is usually wrong.
- **Dependencies** — wire real blockers and dependants; set `blocked` where it is.
- **Tags** — reflect the new lineage.

Clear the flag when done. Where the right answer needs the user's judgment, clear
the flag, mark it for triage, and name the specific ambiguity in the summary.

No batch limit — these are explicit user requests. Run this before the structural
stage so the metrics reflect it.

## 7 — Maintain the graph

Delegate to [`../../graph-maintenance/SKILL.md`](../../graph-maintenance/SKILL.md).
Select the strategy from this cycle's baseline; that skill executes it and owns
the triage rules.

**Convergence.** An unchanged `metrics_hash` means the _actionable_ graph has
converged — skip the actionable strategies and log it. It says nothing about the
knowledge layer, which is measured by a different call and has its own terminal
condition. Do not skip knowledge curation on an actionable-layer signal.

Two consecutive no-op cycles across **both** layers means the graph is stable and
a running loop should stop.

## 8 — Check your own output

Two minutes, on what **this cycle** produced. For each knowledge note created or
changed: does it carry `sources`? Does the synthesis cite more than one
observation? Are its wikilinks valid? Is confidence present and plausible? For
each episodic source consolidated: has its status advanced?

Log failures in the summary and flag them for review. Do not try to fix content
quality here — that is the reviewer's job.

Where the same issue appears across three or more cycles, that is a procedure
defect, not a run defect: file a task describing the pattern, cite the specific
notes where it appeared, and propose the change to this document or to
[`quality.md`](quality.md).

## The cycle summary

Every cycle emits one. Sections with nothing to report are omitted — except the
halt count, which always renders even at zero.

Lead with the halt count, then the baseline and its delta in both layers, then
one line per stage that did work: what it processed, what it changed, and what it
surfaced for a human. **Name the ids** for anything merged, archived, or
surfaced — a bare count is not reviewable. Close with a single sentence on what
the next cycle should pick up.

State it as what happened and what is now true. It is a report, not a log to
accumulate.
