---
id: live-fix-loop
type: template
kind: process
category: development
description: Fix a defect that only appears in the real runtime — drive the deployed artefact, capture verbatim failure evidence, dispatch a fixer, rebuild, re-drive, score on the machine record
requires: []
pairs-with: [investigation, wf-verification]
conflicts: []
version: 1.0.0
permalink: workflows-process-live-fix-loop
status: retired
superseded_by: aops_f74b7e6c
tags: [retired]
---

> [!IMPORTANT]
> **RETIRED**: archived off as part of the v0.9 null workflow-template set reset ([[aops_f74b7e6c]]). Do not compose.

# Process: Live Fix Loop

**When to invoke**: the defect lives in a runtime the test suite cannot reach —
a container, an installed artefact, a second client, a deployed service — and
static checks pass while the real thing is broken. Static-only work routes to
[[feature-dev]]; an unknown cause with a reachable probe routes to
[[investigation]].

Each round is one full circuit: **drive → capture → dispatch → rebuild →
re-drive → score**. A round ends in a verdict, never in a guess.

## Steps

1. **Build the artefact that will actually run.** The runtime executes what was
   packaged, not the tree you are editing, and nothing on the launch path checks
   freshness. Build, then drive. A source change tested without a rebuild proves
   nothing about either.

2. **Drive one probe that exercises every acceptance criterion in a single
   pass.** Order the criteria so each depends only on the ones before it, and
   make the first step "state your identity and list every tool you can call" —
   a capability that is missing explains every later failure at once.

3. **Instruct the worker to halt and explain, never to work around.** Spell it
   out: on failure, stop, do not try an alternative route, and name the tool
   called, the exact error text, and your diagnosis. A worker that routes around
   a broken capability converts your one clean signal into a plausible success,
   and the loop then runs on a defect you can no longer see.

4. **Capture the failure from the machine record, not the summary.** Read the
   host-side logs and the raw transcript before you read what the agent said
   about them. The record carries the error string a fixer can act on; the
   summary carries the agent's theory of it.

5. **Dispatch a fixer with evidence, criteria, and constraints — not a
   diagnosis.** Hand over: the verbatim failure text with its source path, the
   acceptance criteria in full, the leads you have with an explicit instruction
   to verify rather than assume each one, and the standing prohibitions (no
   workaround, no stub, no mock, no placeholder credential, rebuild before
   finishing, commit). A fixer given a conclusion will confirm it; a fixer given
   evidence will test it.

6. **Re-drive the same probe against the rebuilt artefact, and score it on the
   tool-call record.** A worker's own `PASS` is a claim, not a result — it can
   be produced by reading a file, by recalling the prompt, or by inferring what
   should have happened. Score the machine's record of what was invoked, and
   check the side effects landed where they were supposed to land.

7. **Repeat until every criterion passes in one run.** A fix that trades one
   failure for a different one is progress and is reported as such — the next
   round, with the new verbatim evidence.

## Critical Rules

- **Hold the probe fixed once the criteria are fixed.** Rounds are only
  comparable while the question is identical. Where the probe genuinely must
  change, say so in the report — a silently reworded probe makes a regression
  look like a fix.
- **One rebuild per round.** Fixing two things between drives leaves you unable
  to say which one moved the result.
- **A green claim is not a pass**, and a silent worker is not a finished one.
- **Report the failed rounds.** The intermediate failures are the evidence that
  the final pass is real, and each names a limit someone downstream will meet.
- **Preserve the surface in the report.** A result is only interpretable against
  the runtime that produced it — name the artefact version driven.

## NOT this template

- Reproducible in the test suite → [[feature-dev]].
- Cause unknown and no runtime needed to find it → [[investigation]].
