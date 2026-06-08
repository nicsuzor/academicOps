---
name: sentinel-policy-context-destructive
title: Sentinel Gate — Context Injection for Blocked Destructive or Irreversible Op
category: template
description: |
  Context injected into agent when sentinel gate blocks a destructive or irreversible operation.
---

**SENTINEL GATE: Destructive or irreversible operation blocked.**

The operation you attempted ({tool_name}) represents a destructive or irreversible action that cannot be taken automatically as a defensible default.

**Why this matters.** Irreversible operations (such as force-reindexing a large corpus or performing major schema/data alterations) have high impact and can result in significant resource consumption, data loss, or system downtime. Under the act-don't-ask / defensible-default doctrine, operations of this class carry a strict carve-out.

**What to do instead.**
You must surface this operation to the user for ratification via `AskUserQuestion` and obtain explicit confirmation before proceeding.

**Do not bypass this block or retry the operation without explicit user confirmation.**
