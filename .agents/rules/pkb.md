---
trigger: always_on
description: Ruling on PKB write authority and basic PKB usage conventions.
---

## PKB writes and usage

- **Who writes knowledge**: Pauli exclusively curates, updates, and prunes knowledge notes (`note`, `knowledge`, `memory`, `target`) and planning graph structure. Other agents never mutate knowledge notes directly; offer durable facts to Pauli in-session or record under `## Durable Facts` in task records for custodian collection.
- **Who writes task lifecycle**: Workers claim (`pkb_claim_task`) and release (`pkb_release_task`) their own assigned tasks directly, recording completion evidence under `## Report`. Sessions running `/dump` create retroactive tasks for unparented edits and operational recoveries.
- **Basic usage**:
  - Pass `_session: {session_id: "..."}` on every PKB and services MCP tool call.
  - Search before creating; use `metadata` or `summary` for broad scans, reserving `full` for target bodies.
  - Links are strictly one-way: tasks link upward to parent project or epic; tasks never link to indexes or MoCs.
  - Current state only (`synthesize-not-accrete`): The PKB is CURRENT STATE ONLY. Rewrite notes in place; delete superseded facts and obsolete material immediately. Never add, retain, or accumulate historical provenance lists (such as `sources:` frontmatter arrays), session references, changelogs, or citations to non-existent prior-state memories. Task bodies hold only goal, scope, checklist, and pointers; bugs go to GitHub only.
