---
name: framework
category: instruction
description: "Framework development workflows - routing to specific procedures for hooks, skills, experiments, debugging, and specs"
allowed-tools: Task, Read, Glob, Grep, Bash, Edit, Write
version: 6.0.0
permalink: skills-framework
---

# Framework Skill

Route your task to the appropriate workflow below.

## Workflow Router

| If you need to... | Use workflow |
|-------------------|--------------|
| **Add a hook, skill, command, or agent** | [01-design-new-component](workflows/01-design-new-component.md) |
| **Fix something broken in the framework** | [02-debug-framework-issue](workflows/02-debug-framework-issue.md) |
| **Test a new approach or optimization** | [03-experiment-design](workflows/03-experiment-design.md) |
| **Check for bloat or trim the framework** | [04-monitor-prevent-bloat](workflows/04-monitor-prevent-bloat.md) |
| **Build a significant new feature** | [05-feature-development](workflows/05-feature-development.md) |
| **Write or update a specification** | [06-develop-specification](workflows/06-develop-specification.md) |
| **Record a lesson or observation** | [07-learning-log](workflows/07-learning-log.md) |
| **Unstick a blocked decision** | [08-decision-briefing](workflows/08-decision-briefing.md) |

## Quick Decision Tree

```
Is this a bug or something broken?
  → YES: 02-debug-framework-issue

Is this adding a new component (hook/skill/command/agent)?
  → YES: 01-design-new-component

Is this a significant feature with multiple phases?
  → YES: 05-feature-development

Is this testing an idea before committing?
  → YES: 03-experiment-design

Is this documentation/spec work?
  → YES: 06-develop-specification

Is this cleanup/maintenance?
  → YES: 04-monitor-prevent-bloat

Is this capturing a learning?
  → YES: 07-learning-log

Is something stuck waiting for a decision?
  → YES: 08-decision-briefing
```

## Usage

1. **Identify your task** using the router above
2. **Read the workflow** - each has specific steps, templates, and checkpoints
3. **Follow it completely** - workflows are tested procedures, not suggestions

## Key Principles (from workflows)

- **Test-first**: Write integration tests before implementation
- **Hook safety**: Never delete hook scripts mid-session; use no-op stubs
- **Experiments have hypotheses**: Define success criteria upfront
- **Fail-fast**: No partial success; fix or revert
- **Single source of truth**: Reference, don't duplicate
