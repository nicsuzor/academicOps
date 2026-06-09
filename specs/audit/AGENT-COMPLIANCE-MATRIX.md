# Agent Compliance Matrix

Generated on Sun Jun 7 00:29:09 UTC 2026 from `scripts/audit_agent_compliance.py`.

## Agents

| Agent                               | Schema OK | Naming OK | Referential OK | Skills Declared    | Subagents Declared    | Notes                                                                                   |
| :---------------------------------- | :-------- | :-------- | :------------- | :----------------- | :-------------------- | :-------------------------------------------------------------------------------------- |
| aops-core/agents/james.md           | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |                                                                                         |
| aops-core/agents/junior.md          | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |                                                                                         |
| aops-core/agents/marsha.md          | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |                                                                                         |
| aops-core/agents/pauli.md           | ✅        | ✅        | ✅             | ❌ Missing skills: | ✅                    |                                                                                         |
| aops-core/agents/rbg.md             | ✅        | ✅        | ✅             | ✅                 | ✅                    |                                                                                         |
| .github/agents/enforcer.agent.md    | ✅        | ✅        | ✅             | ✅                 | ✅                    |                                                                                         |
| .github/agents/mechanic.agent.md    | ✅        | ✅        | ✅             | ✅                 | ✅                    | renamed from merge-prep.agent.md at Phase 5; reduced scope (no approval, no auto-merge) |
| .github/agents/pr-reviewer.agent.md | ✅        | ✅        | ✅             | ✅                 | ✅                    |                                                                                         |
| .github/agents/qa.agent.md          | ✅        | ✅        | ✅             | ✅                 | ✅                    |                                                                                         |

## Skills (allowed-tools check)

| Skill                                      | Conformance              |
| :----------------------------------------- | :----------------------- |
| aops-core/skills/aops/SKILL.md             | ❌ Missing allowed-tools |
| aops-core/skills/cowork-sync/SKILL.md      | ❌ Missing allowed-tools |
| aops-core/skills/craft/SKILL.md            | ✅                       |
| aops-core/skills/daily/SKILL.md            | ✅                       |
| aops-core/skills/design-rubric/SKILL.md    | ❌ Missing allowed-tools |
| aops-core/skills/dogfood/SKILL.md          | ✅                       |
| aops-core/skills/dump/SKILL.md             | ❌ Missing allowed-tools |
| aops-core/skills/end_session/SKILL.md      | ❌ Missing allowed-tools |
| aops-core/skills/peer-review/SKILL.md      | ✅                       |
| aops-core/skills/planner/SKILL.md          | ❌ Missing allowed-tools |
| aops-core/skills/program/SKILL.md          | ❌ Missing allowed-tools |
| aops-core/skills/project/SKILL.md          | ❌ Missing allowed-tools |
| aops-core/skills/remember/SKILL.md         | ✅                       |
| aops-core/skills/research/SKILL.md         | ✅                       |
| aops-core/skills/sleep/SKILL.md            | ✅                       |
| aops-core/skills/strategic-review/SKILL.md | ✅                       |
| aops-core/skills/supervisor/SKILL.md       | ❌ Missing allowed-tools |
| aops-core/skills/survey/SKILL.md           | ✅                       |
| aops-core/skills/verify/SKILL.md           | ✅                       |
