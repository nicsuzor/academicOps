# Agent Compliance Matrix

Generated on Mon May 11 00:29:32 UTC 2026 from `scripts/audit_agent_compliance.py`.

## Agents

| Agent                               | Schema OK | Naming OK | Referential OK | Skills Declared    | Subagents Declared    | Notes |
| :---------------------------------- | :-------- | :-------- | :------------- | :----------------- | :-------------------- | :---- |
| aops-core/agents/james.md           | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |       |
| aops-core/agents/junior.md          | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |       |
| aops-core/agents/marsha.md          | ✅        | ✅        | ✅             | ❌ Missing skills: | ❌ Missing subagents: |       |
| aops-core/agents/pauli.md           | ✅        | ✅        | ✅             | ❌ Missing skills: | ✅                    |       |
| aops-core/agents/rbg.md             | ✅        | ✅        | ✅             | ✅                 | ✅                    |       |
| .github/agents/merge-prep.agent.md  | ✅        | ✅        | ✅             | ✅                 | ✅                    |       |
| .github/agents/pr-reviewer.agent.md | ✅        | ✅        | ✅             | ✅                 | ✅                    |       |
| .github/agents/qa.agent.md          | ✅        | ✅        | ✅             | ✅                 | ✅                    |       |

## Skills (allowed-tools check)

| Skill                                      | Conformance              |
| :----------------------------------------- | :----------------------- |
| aops-core/skills/aops/SKILL.md             | ❌ Missing allowed-tools |
| aops-core/skills/daily/SKILL.md            | ✅                       |
| aops-core/skills/dogfood/SKILL.md          | ✅                       |
| aops-core/skills/end_session/SKILL.md      | ❌ Missing allowed-tools |
| aops-core/skills/planner/SKILL.md          | ❌ Missing allowed-tools |
| aops-core/skills/project/SKILL.md          | ❌ Missing allowed-tools |
| aops-core/skills/verify/SKILL.md           | ✅                       |
| aops-core/skills/remember/SKILL.md         | ✅                       |
| aops-core/skills/research/SKILL.md         | ✅                       |
| aops-core/skills/sleep/SKILL.md            | ✅                       |
| aops-core/skills/strategic-review/SKILL.md | ✅                       |
| aops-core/skills/supervisor/SKILL.md       | ❌ Missing allowed-tools |
