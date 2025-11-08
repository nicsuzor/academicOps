---
title: Hook Design
type: guidance
description: Best practices for creating effective Claude Code hooks, including SessionStart,
  PreToolUse, PostToolUse, and Stop hooks with lightweight design principles.
tags:
  - hook
  - hook-design
  - best-practices
  - automation
relations:
  - "[[docs/bots/BEST-PRACTICES]]"
permalink: a-ops/docs/unused/hook-design
---

# Hook Design

Best practices for creating effective Claude Code hooks.

**Source**: [Claude Code: Advanced AI Development Platform Guide, 2025](https://www.paulmduvall.com/claude-code-advanced-tips-using-commands-configuration-and-hooks/)

---

## Types

- **SessionStart**: Run when Claude Code starts (context loading)
- **PreToolUse**: Run before Claude executes any tool (validation, linting)
- **PostToolUse**: Run after successful tool completion (formatting, tests)
- **Stop**: Run when Claude Code stops (cleanup)

---

## Design Principles

### 1. Lightweight and Fast

Hooks run on critical path—keep them minimal:

- Avoid expensive operations in PreToolUse
- Use PostToolUse for slower tasks (tests, linting)
- SessionStart should load only essential context

### 2. Conditional Execution

Use matchers to run hooks only when relevant:

```yaml
- name: Load project context
  when:
    - type: session_start
  command: cat project-context.md
```

### 3. Fail Fast

Hooks should surface issues immediately, not silently fail or retry.
