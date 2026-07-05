---
id: TBD
title: In-Session Enforcement — The Work-Unit Contract (Layer 2)
type: spec
status: draft
tags: [enforcement, framework-architecture, verification]
---

# In-Session Enforcement — The Work-Unit Contract (Layer 2)

## aops-pkb — Work-unit loop (the task contract)

Operative from PKB `claim_task` → `release_task`. That pair is the contract for a
single agent session's single unit of work: one claimed unit, released under
contract.

**aops-pkb is the sole owner of the verification invariant.** The `release_task` /
`complete_task` call is the authoritative completion claim — the task graph is the
single source of truth, and a prose "done" that never moves task state is cheap
talk. Enforcement binds to the claim act, not to the session, so it holds
regardless of session class.

**Completion is not a claim — it is a claim carrying verification.** The release
must carry independent-verification evidence bound to the artifact state of the
work.

### Mechanisms

- **Premise gate** — at `claim_task`; refuses a task with no genuine premise
  assessment before compute is spent.
- **Freshness gate** — at `claim_task`; path-resolution and supersession checks.
- **Evidence contract** — at `release_task` / `complete_task`; the completion
  claim must carry independent-verification evidence bound to artifact state.
  This is the single runtime enforcer of the invariant. Its floor is the `mem`
  MCP server predicate — the contract is only as strong as that floor.
