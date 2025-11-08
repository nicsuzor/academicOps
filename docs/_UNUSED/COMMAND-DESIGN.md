---
title: Slash Command Design
type: guidance
description: Best practices for creating effective Claude Code slash commands, including
  mandatory skill-first pattern, context efficiency, and supervisor orchestration
  patterns.
tags:
- command
- slash-command
- best-practices
- skill-first
relations:
- '[[docs/bots/BEST-PRACTICES]]'
- '[[docs/bots/SKILL-DESIGN]]'
permalink: a-ops/docs/unused/command-design
---

# Slash Command Design

Best practices for creating effective Claude Code slash commands.

**Source**: [Slash Commands - Claude Docs](https://docs.claude.com/en/docs/claude-code/slash-commands)

---

## Structure

Commands are Markdown files with optional YAML frontmatter:

```yaml
---
description: "One-line description for command list"
---

[Concise prompt following context engineering principles]
```

**Location**:

- Project: `.claude/commands/` (highest priority, version controlled)
- User: `~/.claude/commands/` (personal commands)

---

## Design Principles

### 1. Mandatory Skill-First Pattern

**ALL slash commands and subagents MUST invoke their corresponding skill FIRST before attempting work.**

This pattern solves two critical problems:

- Prevents agents from "figuring out" instructions independently (wastes tokens, creates inconsistency)
- Provides single entry point for documentation discovery (skills contain references, checklists, workflows)

**Template for Slash Commands**:

```markdown
---
description: "One-line description"
---

**MANDATORY FIRST STEP**: Invoke the `skill-name` skill IMMEDIATELY. The skill provides all context, workflows, and documentation needed for [task type].

**DO NOT**:

- Attempt to figure out instructions on your own
- Search for documentation manually
- Start work before loading the skill

The skill-name skill contains:

- [Key capability 1]
- [Key capability 2]
- [Key capability 3]

After the skill loads, follow its instructions precisely.

ARGUMENTS: $ARGUMENTS
```

**Benefits**:

- Context efficiency: Skills have built-in context loaded once
- Consistency: Same workflow every time
- Prevents improvisation and guessing
- Token efficiency: Consolidated vs scattered instructions

### 2. Load Context Efficiently

Commands should invoke skills or load reference docs, not duplicate content:

```markdown
❌ BAD: Repeat 500 lines of skill instructions in command

✅ GOOD: Invoke skill via Skill tool, then add specific task guidance
```

### 3. Use Arguments

Support parameterized commands with `$ARGUMENTS`:

```markdown
Usage: /command <parameter>

Task: Process $ARGUMENTS with [specific instructions]
```

### 4. Keep Commands Focused

Each command should have one clear purpose. Use multiple focused commands rather than one Swiss Army knife.

### 5. Namespace for Organization

Use directory structure for grouping:

```
.claude/commands/
  git/
    commit.md
    review.md
  test/
    run.md
    write.md
```

### 6. Limit YAML Frontmatter Bloat

Keep frontmatter minimal - only `description` required:

```markdown
## ❌ BAD (42 lines of bloat):

description: "Short description" extra: |

## When to Use

[20 lines]

## What This Loads

[15 lines]

## Related Commands

## [7 lines]

## ✅ GOOD (minimal frontmatter):

## description: "Short description"

[Concise body with actual instructions]
```

**Hard limit**: `extra:` blocks >10 lines are bloat. Move content to body or delete.

**Why**: YAML frontmatter is loaded into agent context immediately. Extensive `extra:` content wastes tokens on scene-setting that doesn't affect behavior. Use body for essential instructions, reference external docs for details.

### 7. Supervisor Orchestration Pattern

When invoking supervisor agent, provide explicit checklist requirements:

```markdown
✅ CORRECT (explicit requirements): Invoke `supervisor` agent.

Supervisor MUST create TodoWrite with:

1. ✓ Independent plan review (second agent validates)
2. ✓ Atomic TDD cycles as todo items
3. ✓ Independent final state review vs original plan
4. ✓ Commit and push all changes

❌ INCORRECT (vague delegation): The supervisor will handle the development task and enforce TDD.
```

**Why**: Supervisor needs explicit checklist to enforce workflow gates. Vague delegation ("will handle", "will enforce") allows skipping critical reviews. Imperative requirements ("MUST create TodoWrite with...") ensure supervisor creates visible, trackable workflow.

**Pattern applies to**: Any command invoking orchestration agents (supervisor, strategist, etc.) where specific workflow steps are mandatory.