---
title: Authoring a durable document
type: template
kind: process
category: meta
description: Write or revise a document that agents load repeatedly — a spec, skill, template, agent file, README or MoC. Enforces the length budget and strips provenance, history and datestamps. Not for task bodies, reports or PR descriptions
tags: [authoring, spec, instructions, concision, meta]
requires: [task-tracking]
pairs-with: [wf-verification]
---

# Authoring a durable document

## When to select this

The deliverable is a document something will **load again and again** — a spec, a
skill, a workflow template, an agent definition, a README, a Map of Content.
Compose it onto whatever spine is doing the work; it constrains how the document
is written, not what it says.

**Not this** for a task body, a review, a report, a PR description or a handover.
Those are written once, read once, and may carry all the provenance they like.

## What this process obliges

**1. One document, one job, stated in one line.** If the opening line needs an
"and", it is two documents. Say what the reader can do after reading it.

**2. Hold the length budget.** Measured across this repo: specs run to a median
of 186 lines, agent files 37–119, workflow templates a median of 46. Those are
the budget, not the floor.

- Over budget → the excess is detail that belongs in the thing that *executes*,
  not the thing that *describes*. Move it there and link, or split the document.
- A template orchestrates; a skill executes. A spec states the contract; the
  implementation holds the mechanics.

**3. Nothing datestamped, ever.** No "as of 2026-08-24", no "corrected on", no
"v0.7-era", no incident IDs, no session references, no "was X, now Y". A durable
document states what is true **now**. Why it is true belongs in git, the PR, or
memory — the three places that are actually built to hold history.

**4. No authoring scaffolding in the artifact.** Acceptance-criteria
cross-references, fork numbers, review-round output blocks, sign-off gate
records, and validation tables are all working notes from the document's own
construction. They are worthless to every future reader. Cut them on sight.

**5. Agent instruction files have a harder boundary** — identity, behavioural
rules, output schema, routing table, and nothing else. `craft` owns that rule
set; invoke it rather than restating it here.

**6. Separate what is measured from what is intended.** State facts about the
corpus only after checking the corpus. Write targets in the imperative so a
reader can tell them apart. A target written in the present tense is a document
lying about the system it describes, and the reader cannot detect it.

**7. Delete outdated material; never retire it in place.** No superseded
banners, no tombstone sections, no rows recording what something used to be.
Repoint inbound links, then delete.

## Exit criterion

Read the finished document and ask of each passage: **if this were removed,
would anyone behave differently?** No → cut it. Report the before/after line
count, and name what you moved rather than deleted.
