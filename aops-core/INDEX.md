---
name: index
title: Framework Index
type: index
category: framework
description: |
  Master index pointing to all sub-indices.
permalink: index
tags: [framework, index, routing]
---

# Framework Index

Master index for aops-core. Sub-indices provide focused context for different concerns.

## Sub-Indices

| Index                  | Purpose                                 | When to Load                     |
| ---------------------- | --------------------------------------- | -------------------------------- |
| [[SKILLS.md]]          | Skill invocation patterns and triggers  | Skill-related prompts, routing   |
| [[CORE.md]]            | Framework tool inventory and workflows  | SessionStart (Tier 1)            |
| [[WORKFLOWS.md]]       | Workflow decision tree (Global + Local) | All prompts (workflow selection) |
| [[.agents/workflows/]] | Project-specific procedures             | Project-scoped work              |
| [[indices/FILES.md]]   | Key files by category                   | File discovery, navigation       |
| [[RULES.md]]           | AXIOMS and HEURISTICS quick reference   | Governance, principle lookup     |
| [[indices/PATHS.md]]   | Resolved framework paths                | Path resolution                  |

## Maintenance

Indices are maintained by:

- `/audit` skill - validates completeness, updates FILES.md
- Manual updates when adding new components
