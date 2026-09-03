---
id: wf-supervised-delegation
title: "wf-supervised-delegation"
type: template
category: process
description: Run a supervised chunk of work by cutting it into units, dispatching every substantive act to the cheaper `agy` executor, and verifying what returns against criteria written before dispatch. Select when the principal is present, the work decomposes into units a cold executor can be judged on, and the saving is real. Not for unattended runs, personal-knowledge-base reads or writes, security-sensitive changes, final artifacts the principal will sign, or asks that cost more to brief than to do.
tags:
  - wf-template
  - process
  - delegation
  - cost
  - aops
---

## What this covers

Delegating substantive execution from Claude-side supervisors to the Gemini harness
under strict, tiered acceptance criteria. Flagship-model tokens are spent only on
supervision and judgment, which is a thin layer; the bulk of execution tokens
land on the cheaper Gemini harness. Supervision quality survives because
principal -> Ida -> James -> agy places a different class of check at each level.

## The three roles

1. **Ida** -- the only agent the principal talks to. Holds the standard, sets
   the objective and the acceptance criteria, interrogates what comes back, and
   reports once. Performs no substantive work and never invokes `agy` herself.

2. **James** -- organises. Receives one mid-sized chunk of work from Ida, cuts
   it into dispatchable units, writes the acceptance criteria each unit will be
   judged against, dispatches them, reconciles results, and returns one verified
   report with evidence attached. Performs no unit work in his own context.

3. **agy** -- the executor. Dispatched for all substantive work (reads, writes,
   edits, builds, searches, drafting) as:
   `agy --agent james --prompt '<instructions>'`

## Obligations

- **Read the status field, never the exit code.** `agy` exits 0 even on failure.
  Any run whose status is not `SUCCESS`, or whose response is empty, is a failed
  run and must be reported as such. Never silently retry a failure into a story
  of success.
- **Instruct in plain English.** Use plain English names and descriptions. Never
  use Claude-side plugin, skill, server, or function names in an `agy` prompt.
  Skills expand in print mode only under the plugin-prefixed slash form (e.g.
  `/aops:hydrate`, not `/hydrate`).
- **Never sleep, poll, or loop.** Either run `agy` in the foreground and block,
  or run it in the background and act on the harness completion notification.
- **Take `agy` output whole.** Redirect it to a file or read it directly. Stream
  filters (`tail`, `head`, `grep`) buffer it.
- **Write the criteria before dispatch, and reject hearsay.** Each unit carries
  acceptance criteria written before dispatch. James verifies the returned
  artifact against those criteria and rejects hearsay: a claim with no evidence
  goes back to its author.
- **Tune timeouts and model tiers explicitly.** Raise `--print-timeout` for long
  units (the default is 5 minutes; an overrun returns status `ERROR` with an
  empty response). Use `--model gemini-3.1-pro-high` only for genuinely complex
  units.
- **Escalate off `agy`.** Send the unit back to a Claude-side agent when it needs
  a tool `agy` lacks, or when it is a judgment call rather than execution.

## Not for

- Unattended or released runs with the principal absent -- use the `sara` route.
- Reads and writes to the personal knowledge base -- route to `pauli`, the sole
  knowledge-base writer.
- Work where cheap execution is false economy: security-sensitive changes,
  authoring a final artifact the principal will sign, and anything where one
  rejected round costs more than the tokens saved.
- Trivial one-shot asks that cost more to brief than to do.
