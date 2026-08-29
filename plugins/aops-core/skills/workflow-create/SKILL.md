---
name: workflow-create
description: Turn a process the user has just been through and approved into a reusable workflow template saved in the template library. Use when the user says "make this a workflow", "template this", "capture what we just did so we can repeat it", or approves a process and wants it repeatable. Not for hypothetical or unapproved processes.
---

# workflow-create: from an approved process to a library template

Input: a recently completed process the user APPROVED — transcript, tasks, artifacts, the user's
comments, and your own reflections. Output: one workflow template saved into the template library.
Nothing else changes.

## Rules

1. **Sources are read-only.** Mine the transcript, tasks, and artifacts for evidence; never modify
   them. You were asked to capture the process, not to touch its records.
2. **Sort the evidence by approval grade** before writing a line:
   - **Approved verbatim** — what the user accepted as-is. Encode as the template's obligations.
   - **Corrected** — the highest-value signal. Encode the corrected form; never the first attempt.
   - **Improvised without ruling** — what the agent chose and the user never judged. Encode as
     defeasible defaults, marked as such — never as doctrine.
3. **Extract the pattern, not the story.** Capture the structural architecture that made the
   process work — independent blind parallel executors, synthesis that traces divergence rather
   than averaging, validation by a non-author, delivery in place, or whatever the evidence shows.
   Never a replay of what happened: if a line only makes sense to someone who was there, it is
   wrong.
4. **Brief future executors with purpose, audience, and strategic context — never method.** The
   executor is at least as capable as the dispatcher; method prescribed from outside the work is
   on average worse than the executor's own choice.
5. **Scope guard is mandatory.** The template states when to select it and when not to.

## Validate before delivering

- **Replay test:** followed cold, would the draft have reproduced the approved process — including
  the user's corrections?
- **Generality test:** instantiate it mentally against one unrelated domain. Any step that breaks
  is over-fit; lift it one level of abstraction.
- **Library check:** enumerate the template library for prior coverage and slug collision. Extend
  an existing template rather than duplicating it.

## Deliver in place

Save the template into the workflow template library per its conventions (tier, frontmatter shape,
no registry entry). The deliverable is the saved template at its library location — never a
proposal, a draft beside it, or a description of one.

## Fitness

This skill and every template it produces obey every rule they impose: one screen, purpose over
method, scope-guarded, validated. Report the template's id/path and which approval grade each
obligation came from.
