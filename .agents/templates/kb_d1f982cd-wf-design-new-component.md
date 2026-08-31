---
alias:
- kb_d1f982cd-wf-design-new-component
- kb_d1f982cd
created: 2026-07-28T02:37:35.295841559+00:00
id: kb_d1f982cd
last_modified: 2026-07-28T03:01:21.926000443+00:00
modified: 2026-07-28T03:01:21.925998419+00:00
permalink: kb_d1f982cd
tags:
- wf-template
- workflow
- framework
- component-design
- hooks
title: wf-design-new-component
type: template
---

## What this step does

Process for adding new framework capability — a hook, skill, script, or command. Verify-first, test-first discipline: confirm the capability doesn't already exist, write the integration test before the component, then implement against it.

## Procedure

1. **Verify necessity** — search existing components for similar functionality, document why they're insufficient, confirm alignment with framework philosophy.
2. **Design the integration test FIRST** — define success criteria, write a test that validates the component end-to-end. The test must fail before the component exists (proof it's testing something real).
3. **Document in an experiment log** — hypothesis, design, expected outcomes.
4. **Implement the component** — single source of truth, reference existing documentation rather than duplicating it, minimal bounded scope. For hooks specifically, see Hook Safety below.
5. **Run the integration test** — must pass completely. No partial success within the claimed component's own surface: a narrower scope honestly disclosed as partial is legitimate, a claimed component with a red test inside its own surface is not.
6. **Update authoritative sources** — reconcile any index/registry documents against the actual structure; verify no documentation conflicts introduced.
7. **Commit only if all tests pass** — confirm single source of truth held, no bloat introduced.

## Hook Safety (normative)

Claude Code loads hook configuration at session start and cannot reload mid-session. This asymmetry between adding and removing a hook is load-bearing:

**Adding a hook is safe**: add the script, add the entry to the client settings file, commit and push — the next session picks it up automatically.

**Removing a hook needs a stub, never a straight delete**:

1. Never delete a hook script while a session referencing it might still be active.
2. Always create a no-op stub first (reads stdin if needed, prints `{}`, exits 0).
3. Remove the hook's entry from the settings file.
4. Commit the stub + settings change together.
5. Only after a session restart, delete the stub in a separate commit.

Deleting a hook script while a session is running it causes repeated errors until restart; a settings change alone doesn't take effect until the next session loads it — the stub bridges that gap.

## When to include

Any change that adds a new hook, skill, script, or command to the framework's own capability surface. Not for changes to existing components — this is specifically the "does this need to exist at all, and does it work end-to-end before it ships" gate for net-new capability.

## Source

Recovered verbatim (structure and content, condensed formatting only) from `.agents/skills/aops/workflows/01-design-new-component.md`, deleted in the v0.6 plugin reorganisation (PR #2340) with no successor found in `plugins/pkb/workflows/process/` or elsewhere in the rebuilt tree.
