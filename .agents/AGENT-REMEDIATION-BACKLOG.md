# Agent Compliance Remediation Backlog

This backlog lists the actions required to bring all agents and skills into full compliance with the `Agent Authority` spec.

## Core Agents

| Agent       | Priority | Required Action                                        |
| :---------- | :------- | :----------------------------------------------------- |
| `james.md`  | P1       | Add `skills:` and `subagents:` allowlists.             |
| `junior.md` | P1       | Add `skills:` and `subagents:` allowlists.             |
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

Based on `.agents/AGENT-TOOLS.md`:

- **Exclusivity Enforcement (PKB destructive tools — BLOCKED, needs ownership decision)**: `EXCLUSIVE_INTENT` in `scripts/audit_agent_compliance.py` marks `bulk_reparent`, `batch_archive`, and `merge_node` as pauli-exclusive. However:
  - `tests/test_junior_tools.py` is an explicit regression test asserting junior MUST hold these three tools (added by merged PR #758).
  - `aops-core/skills/planner/SKILL.md`, `remember/SKILL.md`, and `sleep/SKILL.md` all list these tools in their `allowed-tools`; junior drives these skills.
  - Stripping the tools from junior breaks the planner/remember/sleep workflows.

  **Decision needed (assignee: nic):** either (a) accept these are shared between pauli + junior and update `EXCLUSIVE_INTENT` to remove the exclusivity claim, (b) move the destructive operations into a sub-skill that only pauli drives and update planner/remember/sleep to dispatch instead of call directly, or (c) some other reorganisation.
- **Edit Tool**: `EXCLUSIVE_INTENT` marks `Edit` as rbg-exclusive but junior also holds it. The intent's own comment says "we just track the tool for now"; this row is aspirational, not enforced.
