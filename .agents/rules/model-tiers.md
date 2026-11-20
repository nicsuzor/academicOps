---
trigger: always_on
description: Name models only by capability tier (flagship, mid-tier, or fast) in instructions, workflows, skills, agent definitions, and specs; concrete models are named only at polecat launch.
---

## Name model tiers, not model names

Instructions, workflows, skills, agent definitions, rules, and specs name a model only by capability tier — `flagship`, `mid-tier`, or `fast` — never by concrete model name, family, or version, so authored text does not go stale when models change.

- **Three tiers**: Use `flagship` for highest-capability reasoning and synthesis, `mid-tier` for general tasks and subagent coordination, and `fast` for lightweight or high-volume steps.
- **Polecat-launch exception**: A polecat launch is the only place a concrete model must be named.
