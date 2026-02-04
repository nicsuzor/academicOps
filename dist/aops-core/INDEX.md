---
name: index
title: Framework Index
type: index
category: framework
description: |
  Master index pointing to all sub-indices. Hydrator loads this to discover
  available indices, then selects relevant sub-indices based on prompt context.
permalink: index
tags: [framework, index, routing]
---

# Framework Index

Master index for aops-core. Sub-indices provide focused context for different concerns.

## Sub-Indices

| Index | Purpose | When to Load |
|-------|---------|--------------|
| [[SKILLS.md]] | Skill invocation patterns and triggers | Skill-related prompts, routing |
| [[WORKFLOWS.md]] | Workflow decision tree and routing | All prompts (workflow selection) |
| [[indices/FILES.md]] | Key files by category | File discovery, navigation |
| [[RULES.md]] | AXIOMS and HEURISTICS quick reference | Governance, principle lookup |
| [[indices/PATHS.md]] | Resolved framework paths | Path resolution |

## Index Loading Protocol

The hydrator **always** receives:
- WORKFLOWS.md (workflow selection)
- SKILLS.md (skill recognition)
- AXIOMS.md (principles - full content)
- HEURISTICS.md (guidelines - full content)

Additional indices are loaded based on prompt keywords:
- File/path questions → FILES.md, PATHS.md
- Governance/rule questions → RULES.md

## Index Schema

Each index MUST have:

```yaml
---
name: <identifier>
title: <human title>
type: index
category: framework
description: <what this index contains>
---
```

Each index SHOULD contain:
- Purpose statement
- Table of contents or lookup table
- Cross-references to related indices

## Maintenance

Indices are maintained by:
- `/audit` skill - validates completeness, updates FILES.md
- Manual updates when adding new components

See [[specs/prompt-hydration.md]] for hydrator architecture.
