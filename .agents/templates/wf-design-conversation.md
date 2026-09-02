---
alias:
- wf-design-conversation-wf-design-conversation
- wf-design-conversation
created: 2026-07-31T05:08:30.644756856+00:00
id: wf-design-conversation
last_modified: 2026-07-31T05:11:04.532989422+00:00
modified: 2026-07-31T05:11:04.532986407+00:00
permalink: wf-design-conversation
tags:
- wf-template
- workflow
- design-conversation
- iterative-artifact
- medium-agnostic
title: wf-design-conversation
type: template
---

---
requires: [wf-human-approval]
pairs-with: [wf-verification, wf-handover, wf-fact-check]
recommends: [wf-self-test]
conflicts: [wf-batch-fanout]
---

## What this process does

Iterates one artifact with the person who owns the judgment on it — a
wired-architecture map, a research methodology, a shopping list — through
repeated present → feedback → rework passes until it is right. The medium
changes; the loop does not. Distilled from `academicops-wired-map.excalidraw`
design-conversation passes ([[aops_b167d73a]], [[aops_fca30941]]) and
generalised on Nic's instruction not to overfit to diagram work: "generalised
out to everything, including potentially research methodologies and shopping
lists."

## When to route here

Route here whenever an artifact needs to converge with what is actually true
and what is actually wanted, through iteration with its owner — not a
one-shot production task (write once, done) and not many independent items
processed the same way (see `conflicts`: that is `wf-batch-fanout`'s job).

## The core loop

**1. Ground truth and claim discipline.** Before anything earns a place in the
artifact, establish what must be true for it to belong: code at a named commit
for a map, question-fit + data + literature for a methodology, actual pantry
state for a shopping list. Keep the receipts (commit SHA, dataset citation,
pantry check) — the next rework pass reuses them instead of re-establishing
ground truth from nothing.

**2. Classify the ask.** Every incoming piece of feedback is one of two jobs:
an accuracy correction (the artifact asserts something false) or a
legibility/design correction (the artifact is true but hard to read or use).
They take different fixes — don't let a design pass quietly change a claim, or
an accuracy fix hide inside a redesign. **Human decision point where the
classification isn't obvious** — ask rather than guess which job this is.

**3. Read the artifact's existing conventions before adding anything.**
Extend what is already there; never fork a second notation, a parallel
section, or a competing document sitting next to the original.

**4. Content lives in the artifact's native structure.** Not prose pasted
onto it. Declare vocabulary and notation once, in one place. Nothing gets
labelled twice.

**5. Present, expect taste feedback, treat prior work as not precious.** Put
the current state in front of the owner. Expect them to mark it up. Do not
defend the previous version — it was a step, not a commitment. **Human
decision point: the pass halts here for the owner's read**, same discipline
as `wf-human-approval`.

**6. Carry feedback into the rework brief near-verbatim.** Brief with goal +
context + constraints; leave the design decisions to whoever executes the
rework. Over-specifying method from the owner's raw feedback is the standing
failure here, not under-specifying it.

**7. The artifact rides along with the reality it describes.** Update it the
moment the underlying reality changes — it must not trail. An annotation that
lags the thing it annotates gets corrected once and then corrected again; that
is not a second bug; it is the same bug, caught late (lesson from the
architecture-map passes, where a stale annotation was fixed twice in one day
because the map wasn't updated at the moment the code changed under it).

**8. Validate artifact integrity after every edit, by the medium's own check.**
JSON validity for Excalidraw, internal consistency for a methodology, "can
someone actually shop from this" for a list. An edit that isn't validated is
not yet a finished pass.

## Gates

Steps 2 and 5 are human decision points. Step 2 halts only when the
accuracy-vs-legibility split is genuinely unclear; step 5 halts every pass —
the artifact does not advance on the agent's own read of whether it's good
enough.

## Riders

A rider states what changes for one medium. It restates nothing from the core
loop — a rider that repeats the loop instead of specialising it has failed the
test below.

### Excalidraw / diagram-iteration rider

**Before drawing**

- Read the diagram's existing legend and conventions (stroke, line weight,
  arrowhead, badge) before inventing a new one. Extend what's there; don't
  duplicate it under a different name.
- Verify every claim you're about to depict against code at a named commit —
  keep the citation (file:line @ commit) beside the working note so a later
  pass doesn't re-derive it. `git diff` the map against its last commit before
  interpreting anything on it; never read element labels and infer the rest —
  deletions, rebindings, and reroutings are structurally invisible that way.
- Confirm which job this pass is (core loop step 2): a correctness fix (the
  map stays accurate) or a readability pass (the mechanism becomes legible) —
  a stroke flip or a corrected annotation can leave a map true and still
  unreadable.

**While drawing**

- Information lives in structure — nodes, arrows, sequence — never in prose
  pasted into a box. A label that reads like a sentence is a note in disguise.
- One small visual vocabulary, declared once in a legend: shape, line weight,
  arrowhead, badge. Never overload one visual attribute for two meanings (e.g.
  dashed for "unbuilt/intent" and for "grouping box" collide) — give each
  meaning its own attribute or its own badge. A new element type earns a
  legend entry when it's introduced, not retrofitted once several exist
  undocumented.
- No label duplicated on both an arrow and the box it touches. Terse labels —
  handler/event names, not sentences.

**Mechanics**

- Files are token-heavy. Load the shipped `diagram` skill before editing, and
  transform the file with a script, keyed on element `id` — never hand-edit,
  never touch it with `sed` or a heredoc.
- Take a copy of the file before editing — in the scratch directory, never
  beside the original and never under a versioned filename. It is the
  baseline the geometry checks below are read against, and it is discarded at
  the end of the pass; git remains the only versioning.
- Pause the brain auto-sync daemon before the write, not after. `~/brain`
  runs a daemon that commits writes as they land, as `auto: sync
  <timestamp>`. Edit first and your `git commit` returns `nothing to commit,
  working tree clean` — the daemon already took your change under a message
  that says nothing about it, and there is no recovery short of amending
  someone else's commit. This is why the map's history carries no design
  rationale at all.
- After every edit, validate: well-formed JSON; `type` fields intact; no
  duplicate ids; every `containerId`, `boundElements` entry and arrow binding
  resolves; no bounding-box overlap with neighbours (boundary/zone rectangles
  excepted); the `elements` array in strict ascending `index` order (a file
  can pass every referential check and still be unopenable if array order and
  fractional indices disagree — this corrupted the map once already); bound
  text fits its container or the label renders outside the box. Verify with:

  ```
  excalidraw-view.py <file> check
  → OK: N elements, ids unique, index-sorted, all bindings resolve
  ```

  `excal-edit.py arrows` (crossing count) and `excal-edit.py overlap` catch
  geometry regressions. Read both as a delta against the pre-edit copy, never
  as an absolute number — the map has never been at zero crossings and no
  pass is expected to get it there; what matters is that your edit did not
  make it worse.
- What a clean `check` does **not** tell you, all three known and live: it
  fails only on **content** divergence between `text` and `originalText`, not
  on line-wrap divergence, and the map carries 35 wrap-only mismatches that
  pass (see [[obs_5df02f93]] for what the content case costs); it never
  inspects `startBinding`/`endBinding`, so a half-bound arrow passes silently
  ([[task_737c102e]]); `map` mode drops arrow labels entirely, so a `map`
  reading is not the whole document ([[task_3bff27d4]]) — and on this map the
  arrow labels carry open design forks.
- Git history is the only versioning: never keep a backup copy or a versioned
  filename. This has been violated at least once in practice
  (`academicops-wired-map.excalidraw.bak-20260730-reconcile`, committed
  2026-07-30) — treat that as the failure mode to avoid, not a precedent.

**Before calling a pass done**

- Re-verify "solid" (built/wired) claims against the code as actually
  shipped, not the code as understood when the element was drawn — solid can
  go stale between draw and merge; a real instance surfaced only at
  merge-time verification, not during the design pass itself.
- Annotations go stale the moment the code under them changes (core loop step
  7) — a single annotation needed correcting twice in one day in practice.
  Map corrections ride along with the code-change workflow rather than
  trailing it as a separate cleanup pass, and they get made after the code is
  verified, not before.

Concrete instantiation: [[wf-map-then-wire]] runs this rider as the mechanics
of its own step 3 ("Draw it, then halt"), as the front half of a longer
process that continues into wiring the agreed feature into code, building,
and a live test — that continuation is specific to architecture-map work and
stays in `wf-map-then-wire`, not here.

### Research-methodology rider

- **Ground truth (step 1) = question fit + data + literature.** The research
  question drives the methodology; not the data that happens to be available,
  not fashion. Receipts are citations and dataset provenance, not commit SHAs.
- **Research data is immutable.** Source datasets, ground-truth labels, and
  anything serving as evidence for a research claim are never modified,
  reformatted, or "fixed" to suit a tool — halt and report the gap instead
  (`.agents/CORE.md`, "Research Data Is Immutable"; AXIOMS P#42).
- **Methodology decisions stay with the researcher.** An agent proposes
  options and their trade-offs (step 6's rework brief); the researcher makes
  the call and owns the justification. Never silently pick a statistical
  method or a sampling frame on the researcher's behalf.
- **Native structure (step 4)** is the methodology section of the paper or
  protocol itself, not a separate design memo bolted alongside it.
- **Integrity check (step 8)** is internal consistency: do the stated method,
  the reported N, and the analysis actually match each other end to end.

### Shopping-list rider

- **Ground truth (step 1) = actual pantry/fridge state, checked, not
  assumed.**
- **Native structure (step 4)** is the list itself, grouped by aisle or store
  section — its own existing convention, if one exists.
- **Integrity check (step 8)**: can someone actually shop from this.

Nothing else changes. No wiring-into-code step, no build/install step, no
versioning discipline beyond the list itself. This rider stays this short on
purpose — it is the test that the core loop above is genuinely medium-agnostic
rather than diagram work with the word "excalidraw" filed off.

## Standing constraints

- **One feedback pass at a time.** Present, get one round of reaction, rework,
  re-present. Don't batch several rounds of guessed corrections ahead of the
  owner's actual read.
- **The current artifact is truth.** Never keep a parallel "just in case" copy
  — version control, where the medium has it, is the history; a second file
  is drift waiting to happen.
- **Steps 1–4 are the design conversation itself; nothing downstream of step 6
  starts before step 5's human read has happened.**

## Declared stakes

Where the artifact is a design record for something that will be built (a
map), a bad pass costs a wrongly-built feature downstream — the two human
gates (steps 2, 5) are what make that recoverable. Where the artifact is the
deliverable itself (a methodology section, a shopping list), a bad pass costs
the owner's trust that the artifact reflects what they actually said; the same
two gates protect that just as directly. Proportion the ceremony around the
gates to what a wrong pass would actually cost — a shopping list doesn't need
a live test; a research methodology's rework brief does need the researcher's
sign-off before it's treated as settled.
