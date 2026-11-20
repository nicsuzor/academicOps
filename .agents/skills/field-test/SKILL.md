---
name: field-test
description: Procedural guide for validating a framework change end to end -- audit the instruction surface, then prove the behaviour where it actually runs. Use when changing instructions, hooks, or execution plumbing; when certifying a release; or when a change has passed every static check and still needs to be believed. Prescribes goals and checks, not techniques -- tools drift, obligations do not.
---

# Field-Test -- Prove It Where It Runs

Each phase states an obligation and the check that settles it. Obtain current harness mechanics (flags, log locations) from tool help and [`debug`](../debug/SKILL.md).

## 0. Pre-register the claim

- Before gathering evidence, write one sentence naming what should be observably different, on which surface, for whom. Score every result against that sentence, never post-hoc.

## 1. Stand on verified ground

- Open every document your judgment relies on before citing it; a pointer or index row proves nothing by itself.
- Report missing ground-truth documents as findings that narrow your conclusion; never reconstruct missing contents.

## 2. Distrust reported absence

- Delegate searching freely, then reproduce decisive claims yourself before acting on them.
- Treat "X does not exist" as scoped to the reporter's visible layers; check every layer where a name can resolve before deleting anything.

## 3. Prove the artifact, not the source

- Build the real deployable deliverable, verify build freshness, and confirm the change exists in what ships rather than only in the edited tree.

## 4. Drive the changed path, live, on every surface

- Walk layers in order (structure, boot, trivial interaction, changed path) and stop at the first failure.
- Repeat once per client and execution environment; exercise the changed path directly rather than an arbitrary path.

## 5. Judge from authoritative records, not UIs

- Name the authoritative channel per claim (transcript, structured log, exit code) and count instrumented events directly; never infer runtime behaviour from UI rendering or source code.

## 6. Force quiet failures

- Presume degrading mechanisms off until observed working in the deployed environment and their degradation notice is confirmed read.
- Re-check boundary-crossing paths, addresses, and identities from inside the target environment.

## 7. Deletion has consumers

- After removals, sweep and repair inbound references, re-derive surviving consumer behaviour for silently empty contracts, and run at least one blind task on a contextless agent.

## 8. A tripped guard is information

- Check whether a tripped check tests live behaviour or pins a duplicate literal against source/config text; consolidate or delete literal-copy drift.
- Where a check tests real behaviour, fix either the change or the check openly -- never rephrase around a check to hide from it.

## 8b. Oddity defaults to drift

- Treat unexplained special cases or inconsistencies as stale drift; keep an exception only with stated necessity, never a post-hoc rationale.

## 9. Close the loop

- Re-run the originally failing observation in its failing environment to prove it passes, and record before/after cause and deliberate omissions where the next session starts.

## 10. Publish grades where the next round starts

- Grade each tested component: **green** (working end-to-end, efficient, useful), **amber** (works with caveats, redundant spend, or noise), or **unmarked** (not tested). Never downgrade a verified build/test-environment pass waiting for downstream user deployment.
- Append dated `✅` / `⚠` badges naming the PR onto the umbrella epic's excalidraw map with a legend, advancing index keys past max and verifying element-preserving re-parse; supersede stale badges.
- File one evidence record per finding and place the component grade table on the round's task record.

## Fitness test

A stranger holding only your report can identify which claims were observed on which authoritative channel, re-run each decisive check from your citations, and see what remains unproven.
