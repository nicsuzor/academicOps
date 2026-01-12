---
name: framework
category: instruction
description: "[DEPRECATED] Use framework-executor agent instead. This skill redirects to the agent."
allowed-tools: Task
version: 5.0.0
permalink: skills-framework
deprecated: true
---

# Framework Skill (Deprecated)

**This skill has been replaced by the `framework-executor` agent.**

The agent provides:

- All categorical conventions from this skill
- Full task lifecycle (bd logging, status tracking, QA verification)
- Skill orchestration and explicit access to all framework skills
- Commit, push, and knowledge persistence

## Migration

Instead of:

```
Skill(skill="framework")
```

Use:

```
Task(subagent_type="framework-executor", prompt="[your task]")
```

## For Quick Convention Lookup

If you just need to check a convention without executing a full task lifecycle, the conventions are documented in:

- `$AOPS/agents/framework-executor.md` - Core conventions
- `$AOPS/AXIOMS.md` - Inviolable principles
- `$AOPS/HEURISTICS.md` - Empirically validated guidance

## Why This Changed

The framework skill provided instructions but couldn't enforce the full lifecycle:

- No bd integration for task tracking
- No QA verification built-in
- No commit/push enforcement

The framework-executor agent handles everything end-to-end, ensuring work is actually completed (not just started).
