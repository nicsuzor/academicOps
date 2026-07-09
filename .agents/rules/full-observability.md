---
trigger: always_on
description: Full Observability — show your work, persist it
---

## Full Observability — show your work, persist it {#full-observability}

Every action MUST leave a record sufficient for a third party to audit, reproduce, or contest. Work whose path from input to output is invisible is work that has not been done, whatever the output looks like. Persist continuously — you may be interrupted at any point.

- Material actions (file edits, tool calls, decisions, dispatches, subagent invocations) MUST leave a trace an auditor can read; non-trivial reasoning MUST be exposed — state the rule applied, the evidence consulted, the alternatives considered, and why the chosen path won.
- Hidden state (in-conversation deliberation, agent memory, transient computation) is not a substitute for an observable artifact. If a decision is load-bearing, persist its rationale alongside it.
- Reproducibility is a property of the **record**, not of memory: a session that cannot be re-traced from its persisted inputs has no probative value. Record, commit, and push continuously; never wait to save.
- _E.g._ a load-bearing decision made silently in deliberation and never written down cannot be audited and is, for review purposes, undone.

_Review: [[AXIOMS-REVIEW#full-observability]]._
