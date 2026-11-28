---
title: Interactive session
type: template
description: "Crew: how an interactive session is run -- the composed workflow decides task tracking, role assignment, seam checks, output placement, and handover."
tags: [workflow, interactive, in-session, delegation]
---

## What this step does

Governs a session with the user on the other end. The composed workflow decides whether and how work is tracked in a task, how roles are assigned, where outputs go, and how the session hands over; pure lookups and direct questions need no task ceremony.

## Structure

1. **Task tracking and placement**: the composed workflow decides whether an outer task is opened, who creates or claims it, where outputs are placed, and whether any work is prepared for worker containers.
2. **Role assignment**: the composed workflow decides delegation and role routing rather than fixing an internal chain.
3. **Seam review**: any inter-agent seam checks, review depth, and remediation loops run only as the composed workflow specifies.
4. **Handover**: session close and release follow the composed workflow and the session's release mechanism.

## The brief

The coordinator's brief quotes the ask verbatim with its message id and states the depth of effort it warrants. Closing reviews are included only when the composed workflow selects them. Any receiving party returns a brief that misjudges effort or distorts the ask.
