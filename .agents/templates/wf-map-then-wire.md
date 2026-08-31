---
alias:
- wf-map-then-wire-wf-map-then-wire
- wf-map-then-wire
created: 2026-07-29T08:41:43.273982202+00:00
id: wf-map-then-wire
last_modified: 2026-08-24T00:18:09.860495877+00:00
modified: 2026-08-24T00:18:09.860494264+00:00
permalink: wf-map-then-wire
tags:
- wf-template
- workflow
- framework
- hooks
- plugin-map
- incremental-rollout
title: wf-map-then-wire
type: template
---

---
requires: [wf-verification, wf-human-approval]
pairs-with: [wf-handover, wf-design-conversation]
recommends: [wf-self-test]
conflicts: [wf-batch-fanout]
---

## What this process does

Brings **one** capability at a time back into academicOps: agree it on the map
first, wire it in code second, prove it live third. The map is the design record
and the point of agreement; no code moves until both people have looked at the
same picture. One feature per pass, however small the feature.

## When to route here

Re-including a feature that was disabled or stripped out, or adding a new one,
during an incremental rollout where the design is still being settled visually.
Do not route here for batch work — see `conflicts`.

## The loop

**1. Re-read the ground truth.**
Read the specs that govern the area **before** forming any plan — the design
documents are authoritative and reverse-engineering from source produces
confident wrong answers. Then read the current map, and **`git diff` it against
its last commit before interpreting anything on it.** Never read the labels of
the elements you expect and infer the rest: deletions, rebindings, and
reroutings are structurally invisible that way, and a summary of what changed
states intent, not the delta.

**2. Pick one feature — the human's call.**
If a feature was named, take it. Otherwise propose **exactly one**, say in a
sentence why it is next, and **stop for confirmation**. A proposal is not
authorization; the pass does not advance on inference.

**3. Draw it, then halt.**
Put the feature on the map and stop. Review is visual — deliver the change _on
the map_, never as a chat table or a schema to read. Iterate: they mark up, you
**re-diff**, you make the next single change. [[wf-design-conversation]]'s
Excalidraw rider is this step worked out in full — legend discipline,
verify-before-draw, the taste-feedback loop, and the Excalidraw file mechanics.

Draw one concrete answer. If it is wrong, draw the next one — that is cheaper
than deliberating, and it is what the human is there for.

**4. Wire it in code.**
Move the agreed feature into the plugin it belongs to. Where the feature is a
hook, check **both** halves before believing it works: the event declared in
`hooks.template.json`, _and_ `[[shared]] from="hooks" to="hooks"` present in
`manifest/plugin.toml`. Either half missing leaves the hook silently dead with no
error surfaced to anyone — see [[mem_7b9c90b1]]. A third half exists for a _new_
event: it must appear in `CANONICAL_EVENTS` in `lib/hooks/dispatch.py`, or the
dispatcher drops it, and the per-client map in the same file decides whether it
reaches agy at all.

**5. Build and install locally.**
`make build install-dev`.

**6. Restart the session and test together.**
**State what you expect to observe before the restart**, so the test is capable of
failing. Registration is not evidence; a hook is done when its effect has been
seen live. Where the feature is an injection, confirm _which context it lands in_
rather than that it fired at all — see [[mem_fb6189a2]].

**7. Close the pass.**
Update the map's provenance line to the commit you grounded against, update the
sync-state table on [[academicops-wired-map]] to match, **re-check the stroke
style of every element this pass touched against what is now actually built**,
then record what landed,
what is now live, and the one thing worth doing next — or say plainly that there
is nothing. A map that does not state which commit it was checked against cannot
be told apart from a stale one.

## What the map may carry

The map holds the design, and nothing else.

- **No proposal notes, no OPEN boxes, no notes-for-later.** A question written on
  the map is work deferred instead of done. Ask it in conversation and draw the
  answer.
- **Boxes carry rules; edges carry flow.** An edge label says what travels and
  where it lands. An instruction written on an edge is a note in disguise — if a
  rule binds an agent, some box must hold it and some edge must inject it, or it
  does not exist.
- **Plain speech.** No mechanism codes, legends, explainer boxes, or
  abbreviations. Every hook carries a trigger-in edge and an injection-out edge;
  nothing floats unconnected.
- **Lifecycle is carried by the outline alone**, per the map key, and the three
  states are mutually exclusive: **solid** = current & live; **dashed** = built
  but currently dark / untested / broken; **dotted** = proposed and not yet
  built. Bracket tags (`[ACTIVE] [DARK] [PROPOSED]` …) are **abolished** —
  Nic, 2026-08-23, "no dumb tags please" ([[aops_8f38ffdc]]). Do not reintroduce
  them, and do not read "dotted" as retired: retired material comes off the map.
- **A stroke style is a falsifiable claim about build state, and it is the only
  such claim the map makes.** Never draw one you have not checked at a named
  ref. Three were measured wrong within two days of the v8 map becoming the
  reset reference, two of them flattering ([[aops_stroke_reconcile]]). Checking
  a stroke costs a grep; a wrong one sends someone to rebuild a working
  subsystem or to trust a dead one.

## Gates

- **Steps 2, 3 and 6 are human decision points.** The pass halts at each. None of
  them is satisfiable by the agent's own judgment.
- **Step 6 carries the acceptance evidence.** Criteria are locked at step 2 (what
  will this feature do, and how will we see it) and confirmed at step 6 against
  what was observed — not against a reinterpretation of what got built.

## Editing the Excalidraw file

Load the shipped diagram skill before editing. Transform the JSON with a script;
never hand-edit it and never touch it with `sed` or a heredoc.
[[wf-design-conversation]]'s Excalidraw rider carries the full
pre-draw/drawing/iteration checklist; the checks below are the ones referential
validation alone does not cover.

**Pause the brain auto-sync daemon before the write, not after.** `~/brain` runs
a daemon that commits writes as they land, as `auto: sync <timestamp>`. Edit
first and your `git commit` returns `nothing to commit, working tree clean` — the
daemon already took your change under a message that says nothing about it, and
there is no recovery short of amending someone else's commit. This is why the
map's history carries no design rationale at all.

**Take a copy of the file before editing** — in the scratch directory, never
beside the original and never under a versioned filename. It is the baseline the
geometry checks below are read against, and it is discarded at the end of the
pass; git remains the only versioning.

- **The `elements` array must be in strict ascending `index` order.** Excalidraw
  rejects a file whose array order and fractional indices disagree, and every
  binding can still be intact. Sort by `index` before writing. This corrupted the
  map once already: new elements were inserted mid-array carrying indices that
  sorted last.
- **Bound text must fit its container**, or the label renders outside the box.

Then verify — valid JSON; every `containerId`, `boundElements` entry and arrow
binding resolves:

```
excalidraw-view.py <file> check
→ OK: N elements, ids unique, index-sorted, all bindings resolve
```

`excal-edit.py arrows` (crossing count) and `excal-edit.py overlap` catch
geometry regressions. **Read both as a delta against the pre-edit copy, never as
an absolute number** — the map has never been at zero crossings and no pass is
expected to get it there; what matters is that your edit did not make it worse.

What a clean `check` does **not** tell you, all three known and live:

- It fails only on **content** divergence between `text` and `originalText`, not
  on line-wrap divergence. The map carries 35 wrap-only mismatches that pass.
  See [[obs_5df02f93]] for what the content case costs.
- It never inspects `startBinding`/`endBinding`, so a half-bound arrow passes
  silently ([[task_737c102e]]).
- `map` mode drops arrow labels entirely, so a `map` reading is not the whole
  document ([[task_3bff27d4]]) — and on this map the arrow labels carry open
  design forks.

## Delegating any of this

State the intent, the constraints, and what you expect back. Do not prescribe
method — the doer chooses how, and over-specification is the standing failure
here, not under-specification. Where the work needs a delegation discipline
heavier than a paragraph, invoke the process rather than hand-rolling one.

## Standing constraints

- **One feature per pass.** Never batch, never chain steps, never run ahead.
- **The map is git-backed and git history is the only versioning.** Never make a
  backup copy or a versioned filename in the repo.
- **Steps 1–3 are design.** Implementation begins at step 4.

## Declared stakes

Each pass ends in a shipped change to a live plugin, so the cost of getting it
wrong is a silently broken agent surface rather than a bad document. The two
human gates and the live test are what make that recoverable; a pass that skips
them has not run this process.
