---
name: exit-reflection-policy-context
title: Exit-Reflection FULL-Tier Policy Context Injection
category: template
description: |
  Full context injection when the exit_reflection gate's FULL tier
  blocks/warns on Stop (task-bound session that did work this turn).
  Consolidates the former rbg-review + qa + handover Stop-gate instructions
  into one checklist (aops_4c2949d9). Variables: {temp_path}.
---

<academicOps exit-reflection>
✕ **Exit-reflection required before you stop.** This session is task-bound and did work this turn — the full checklist applies. Session record: `{temp_path}`.

1. **RBG-lens self-audit.** Check this session against the framework axioms. Any violations?
2. **Durable capture.** Confirm state, decisions, and synthesis are saved to the PKB/task — not only in this transcript, which is ephemeral. You may be interrupted at any time; anything not saved is lost work.
3. **Commit → push → PR.** Land the plane: uncommitted or unpushed work is garbage-collected.
4. **`/aops-pkb:learn`** for any bugs or friction hit this session.
5. **`/aops-pkb:remember`** for any durable lesson learned.
6. **Prose handover.** Update the PKB task with a handover that self-identifies EVERY load-bearing claim and _shows_ its justification — a command and its observed output, a `file:line` pointer, or a resolving link. A claim with no shown justification is not evidence. An honest, stated failure reason is a legal exit — exactly as legal as a verified success. What is NOT legal: restating this checklist's headings ("I self-audited", "I captured durably") without the evidence underneath — that is a self-graded ritual, not compliance, and must be rejected on re-read.

Where the harness supports it, a reflection auditor is dispatched directly on this Stop event rather than relying on you to invoke one yourself. Do the checklist anyway — the dispatched pass is a second, independent check, not a substitute for your own honesty.
</academicOps exit-reflection>
