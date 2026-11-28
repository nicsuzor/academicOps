---
title: Dispatch
type: template
description: "Crew: hand a reified task to the dispatcher to run in a worker container, with no child tasks and no claim or release ceremony."
tags: [workflow, dispatch, worker, fast-path]
---

## What this step does

Sends existing work to a worker container. The worker has no plugins and no PKB access; the reified task is its whole prompt, and its final message is written back to the task by the dispatch service.

## Requirements

1. The custodian (`pauli`) reifies the task (`/reify`) just before dispatch, so it is complete without PKB knowledge.
2. The dispatcher starts the worker against the existing task; no child tasks are minted.
3. No one runs `/pull`, `/dump`, claim or release for it, the worker included.
4. Report the dispatch outcome.
