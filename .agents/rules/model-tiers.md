---
trigger: always_on
description: Name models only by capability tier (flagship, mid-tier, or fast) in instructions, workflows, skills, agent definitions, and specs; concrete models are named only at polecat launch.
---

## Name model tiers, not model names

Name models only by capability tier -- `flagship` (highest-capability reasoning and synthesis), `mid-tier` (general tasks and subagent coordination), or `fast` (lightweight or high-volume steps) -- never by concrete model name, family, or version.

- **Polecat-launch exception**: A polecat launch is the only place a concrete model must be named.
