---
title: Dispatch
type: template
description: "Crew: dispatch a prepared task to run in a worker container under the composed workflow, with no child tasks."
tags: [workflow, dispatch, worker, fast-path]
---

## What this step does

Sends existing work to a worker container. The worker has no plugins and no PKB access; the prepared task is its whole prompt, and its final message is written back to the task by the dispatch service.

## Requirements

1. The task carries standalone instructions prepared per the composed workflow just before dispatch, so it is complete without PKB access.
2. Start the worker against the existing task; no child tasks are minted.
3. Claim and release follow the framework's release boundary, with no separate claim or release ceremony inside the worker.
4. Report the dispatch outcome.
