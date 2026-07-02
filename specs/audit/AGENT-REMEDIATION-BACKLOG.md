# Agent Compliance Remediation Backlog

This backlog lists the actions required to bring all agents and skills into full compliance with the `Agent Authority` spec.

## Core Agents

| Agent       | Priority | Required Action                                        |
| :---------- | :------- | :----------------------------------------------------- |
| `james.md`  | P1       | Add `skills:` and `subagents:` allowlists.             |
| `marsha.md` | P1       | Add `skills:` and `subagents:` allowlists.             |
| `pauli.md`  | P1       | Add `skills:` allowlist.                               |
| `rbg.md`    | P2       | Add `skills: []` and `subagents: []` for explicitness. |

## Skills

| Skill                  | Required Action                           |
| :--------------------- | :---------------------------------------- |
| `aops/SKILL.md`        | Add `allowed-tools` block to frontmatter. |
| `end_session/SKILL.md` | Add `allowed-tools` block to frontmatter. |
| `planner/SKILL.md`     | Add `allowed-tools` block to frontmatter. |
| `project/SKILL.md`     | Add `allowed-tools` block to frontmatter. |
| `supervisor/SKILL.md`  | Add `allowed-tools` block to frontmatter. |

## Tool Authority (Drift Remediation)

Based on `specs/audit/AGENT-TOOLS.md`:

- **Edit Tool**: `ida.md` now shares `Edit` with `rbg.md` (flagged `❌ Drifted` in the matrix) — confirm this is intentional or narrow `ida`'s tool grant.
