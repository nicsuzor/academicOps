---
title: Agent Compliance Matrix
type: audit
status: active
tier: core
depends_on: [agent-authority]
tags: [audit, agents, compliance, governance]
created: 2026-04-21
---

# Agent Compliance Matrix

Per `specs/agent-authority.md`. Rows: every agent file in scope. Columns: spec dimensions. This file is the authoritative audit state until the lint tool (sibling task `task-8ff8dac0`) regenerates it.

**Legend**: ✅ conformant · ⚠️ conformant with noted exception · ❌ non-conformant · — n/a

## Core Agents (`aops-core/agents/`)

| Agent      | Canonical names | Schema fields | skills declared            | subagents declared | MCP scoping | Notes                                                                                         |
| ---------- | --------------- | ------------- | -------------------------- | ------------------ | ----------- | --------------------------------------------------------------------------------------------- |
| `enforcer` | ✅              | ✅            | ✅ (`[]`)                  | ✅ (`[]`)          | —           | ⚠️ **Transitional.** To become a build artifact derived from `rbg` (see spec §Derived Agents). |
| `james`    | ✅              | ✅            | ✅ (`[strategic-review]`)  | ✅ (`["*"]`)       | —           | Wildcard subagents per user decision (orchestrator gate is open).                             |
| `jr`       | ✅              | ✅            | ✅ (`["*"]`)               | ✅ (`["*"]`)       | ✅          | Intentionally underspecified — any skill / any subagent.                                      |
| `marsha`   | ✅              | ✅            | ✅ (`[qa]`)                | ✅ (`[]`)          | ✅          | —                                                                                             |
| `pauli`    | ✅              | ✅            | ✅ (`[remember, planner]`) | ✅ (`[]`)          | ✅          | Retains full frontmatter surface (permissionMode, maxTurns, effort, background, isolation).   |
| `rbg`      | ✅              | ✅            | ✅ (`[]`)                  | ✅ (`[]`)          | —           | Granted Edit+Write (may fix mechanical violations directly). Verdict-format prose removed.    |

## GitHub Action Agents (`.github/agents/`)

These grant tools via the invoking workflow's `claude_args`; the frontmatter surface is minimal by design (see spec §GitHub Action Agents). Left as-is per user decision.

| Agent         | Frontmatter present    | Notes               |
| ------------- | ---------------------- | ------------------- |
| `merge-prep`  | ✅ (name, description) | No change required. |
| `pr-reviewer` | ✅ (name, description) | No change required. |
| `qa`          | ✅ (name, description) | No change required. |

## Plugin Agents

None present in the current tree. When added, they conform to the same schema as core agents.

## Outstanding Items (feed sibling tasks)

| Item                                                                                          | Sibling task    |
| --------------------------------------------------------------------------------------------- | --------------- |
| Build-translate Claude Code → Gemini CLI tool names in `scripts/build.py`                     | `task-8ff8dac0` |
| Derive `enforcer` from `rbg` as GH-target build artifact; remove source file                  | `task-8ff8dac0` |
| Migrate enforcer gate-specific prose (watch tables, output format) to gate caller or skill    | `task-8ff8dac0` |
| Implement lint: schema conformance, canonical naming, referential integrity, prose drift warn | `task-8ff8dac0` |
| Regenerate this matrix from lint output                                                       | `task-8544ef68` |
| Wire lint into CI as blocking check                                                           | `task-95aa08f1` |
