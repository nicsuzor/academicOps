---
title: "Subagent Design"
type: guidance
description: "Best practices for creating effective Claude Code subagents, including structure requirements, mandatory skill-first pattern, and design principles for context preservation."
tags:
  - subagent
  - agent-design
  - best-practices
  - skill-first
relations:
  - "[[docs/bots/BEST-PRACTICES]]"
  - "[[docs/bots/SKILL-DESIGN]]"
---

# Subagent Design

Best practices for creating effective Claude Code subagents.

**Source**: [Subagents - Claude API - Anthropic](https://docs.claude.com/en/docs/claude-code/sub-agents); [Best Practices for Claude Code Subagents, PubNub, 2025](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)

---

## Structure

Subagents are Markdown files with YAML frontmatter:

```yaml
---
name: agent-name
description: "Clear one-sentence purpose statement"
tools: Read, Write, Edit, Bash, Grep, Glob
model: inherit  # or sonnet, opus, haiku
---

# Agent Name

[Concise prompt following context engineering principles]
```

**Location**:
- Project: `.claude/agents/` (highest priority)
- User: `~/.claude/agents/`

---

## Design Principles

### 1. Mandatory Skill-First Pattern

**ALL subagents MUST invoke their corresponding skill FIRST before attempting work.**

This architectural pattern ensures consistency and prevents agents from improvising workflows.

**Template for Subagents**:

```yaml
---
name: agent-name
description: "Clear one-sentence purpose"
tools: [list]
---

# Agent Name

**MANDATORY FIRST STEP**: Invoke the `skill-name` skill before proceeding with any task.

## Core Responsibilities

[Agent-specific authority and orchestration - keep minimal]

## Workflow

1. Load skill-name skill (MANDATORY)
2. Follow skill instructions for [task type]
3. [Any agent-specific orchestration]

See skill-name for complete workflow details.
```

**Rationale**: Subagents should focus on orchestration and authority, delegating procedural details to skills. This keeps subagent prompts minimal and prevents duplication.

### 2. Single, Clear Responsibility

- One agent, one purpose
- Improves predictability and performance
- Simplifies debugging and iteration

### 3. Start with AI-Generated Agents

"We highly recommend generating your initial subagent with Claude and then iterating on it to make it personally yours."

### 4. Write Detailed But Concise Prompts

- Include specific instructions, constraints, and examples
- Avoid unnecessary background or FAQ content
- More focused guidance = better results

### 5. Limit Tool Access Strategically

- Grant only necessary tools for the agent's role
- Enhances security and focus
- If tools omitted, agent inherits all tools (be intentional)

### 6. Encourage Proactive Use

Use phrases like "use PROACTIVELY" or "MUST BE USED" in descriptions to trigger automatic task routing.

---

## Context Preservation Benefit

Each subagent maintains its own context window, preventing main conversation pollution—this is the "core innovation" of subagents.
