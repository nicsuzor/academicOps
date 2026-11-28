---
title: Interactive session
type: template
description: "Crew: how an interactive session is run -- one outer task, delegation to internal delegates, checked seams, and one handover."
tags: [workflow, interactive, in-session, delegation]
---

## What this step does

Governs a session with the user on the other end. Pure lookups, graph operations and direct questions are answered without a task or `/dump`.

## Structure

1. **One outer task** for the topic, placed and claimed via `/q` by the internal delegate before substantial work starts. The user-facing coordinator creates no tasks; downstream agents create none for the session's work. Work leaving for worker containers is placed via `/q`, reified by the custodian just before dispatch, and dispatched via `/dispatch`.
2. **Delegation**: the user-facing coordinator delegates to an internal delegate, which routes to the custodian, a reviewer or the dispatcher as the work needs.
3. **Checked seams**: inter-agent messages use prose Argdown and undergo judicial review on the message alone per `premise-check` (zero outside substantive checks; proportionate depth, accept unambiguous fixes with `AMENDED`, material remands only); any remaining material `REVISE` is fixed and re-checked before it moves on.
4. **One handover**: only the user-facing coordinator runs `/dump`, when the outer task is complete.

## The brief

The coordinator's brief quotes the ask verbatim with its message id and states the depth of effort it warrants. Closing reviews are named in the brief only when the stakes warrant them. The delegate returns a brief that misjudges effort or distorts the ask.
