# Claude Code Best Practices for academicOps Framework

**Purpose**: Evidence-based guidance for creating effective Claude Code components (subagents, skills, commands, hooks) that are concise, performant, and maintainable.

**Last Updated**: 2025-11-02

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Context Engineering](#context-engineering)
3. [Subagents](#subagents)
4. [Skills](#skills)
5. [Slash Commands](#slash-commands)
6. [Hooks](#hooks)
7. [Tool Design](#tool-design)
8. [What to AVOID](#what-to-avoid)
9. [References](#references)

---

## Core Principles

### 1. Simplicity First

**Principle**: "Start simple. Finding the simplest solution possible, and only increasing complexity when needed."

- Use simple, composable patterns rather than complex frameworks
- Optimize single LLM calls before building multi-agent systems
- For many applications, "optimizing single LLM calls with retrieval and in-context examples is usually enough"

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)

### 2. Transparency Over Opacity

**Principle**: "Explicitly display planning steps" to users

- Make agent reasoning visible
- Show what the agent is thinking and why
- Enable debugging through transparency

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)

### 3. Context as Finite Resource

**Principle**: "Context must be treated as a finite resource" with "diminishing marginal returns"

- LLMs have an "attention budget" that depletes with excessive tokens
- Target "the smallest set of high-signal tokens that maximize the likelihood of your desired outcome"
- Even with large context windows, context pollution degrades performance

**Source**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### 4. The Goldilocks Altitude

**Principle**: Balance specificity with flexibility in instructions

- **Too Low**: Overly complex, brittle hardcoded logic
- **Too High**: Vague guidance that assumes shared context
- **Just Right**: Specific paired with flexible guidance through strong heuristics

**Source**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### 5. Examples Over Exhaustive Rules

**Principle**: "Examples are the 'pictures' worth a thousand words"

- Use diverse, canonical examples showing expected behavior
- More effective than exhaustive rule documentation
- Include challenging examples and edge cases

**Source**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Context Engineering

### Token Efficiency Strategies

**1. Curated Context, Not Comprehensive Context**

Provide minimal necessary information, not everything potentially relevant:

```markdown
❌ BAD: Include 500 lines of background, history, edge cases, FAQs

✅ GOOD: Include 50 lines of essential instructions + 2-3 examples
```

**2. Just-in-Time Retrieval**

Rather than pre-loading all data, maintain lightweight identifiers and dynamically retrieve via tools:

- Enables progressive discovery
- Mirrors human cognition
- Prevents upfront context pollution

**Source**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**3. Structured Organization**

Use XML tags or Markdown headers to delineate sections:

```markdown
<background_information>
[Essential context only]
</background_information>

<instructions>
[Clear, actionable steps]
</instructions>

<examples>
[2-3 canonical cases]
</examples>
```

**Source**: [Claude 4 Prompt Engineering Best Practices, Anthropic](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

### Context Pollution Solutions

**For Long-Horizon Tasks**:

1. **Compaction**: Summarize conversation history, preserving architectural decisions while discarding redundant outputs
2. **Structured Note-Taking**: Maintain persistent external memory (files, task database)
3. **Sub-Agent Architectures**: Specialized agents return condensed summaries (1,000-2,000 tokens) to lead agent

**Source**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Subagents

### Structure

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

**Source**: [Subagents - Claude API - Anthropic](https://docs.claude.com/en/docs/claude-code/sub-agents)

### Design Principles

**1. Mandatory Skill-First Pattern**

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

**2. Single, Clear Responsibility**

- One agent, one purpose
- Improves predictability and performance
- Simplifies debugging and iteration

**3. Start with AI-Generated Agents**

"We highly recommend generating your initial subagent with Claude and then iterating on it to make it personally yours."

**4. Write Detailed But Concise Prompts**

- Include specific instructions, constraints, and examples
- Avoid unnecessary background or FAQ content
- More focused guidance = better results

**5. Limit Tool Access Strategically**

- Grant only necessary tools for the agent's role
- Enhances security and focus
- If tools omitted, agent inherits all tools (be intentional)

**6. Encourage Proactive Use**

Use phrases like "use PROACTIVELY" or "MUST BE USED" in descriptions to trigger automatic task routing.

**Source**: [Subagents - Claude API - Anthropic](https://docs.claude.com/en/docs/claude-code/sub-agents)

### Context Preservation Benefit

Each subagent maintains its own context window, preventing main conversation pollution—this is the "core innovation" of subagents.

**Source**: [Best Practices for Claude Code Subagents, PubNub, 2025](https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/)

---

## Skills

### Skills vs Commands

**Skills**: Richer context, validation scripts, organized reference material
**Commands**: Simple prompt expansion

Use skills when:
- Complex workflows require structured guidance
- Scripts or validation logic needed
- Multiple reference documents required
- Reusable across projects

**Source**: [Claude Code Plugins, Anthropic](https://www.anthropic.com/news/claude-code-plugins)

### Skill Structure

```
skills/
  skill-name/
    skill.md          # Main prompt (YAML frontmatter + instructions)
    scripts/          # Automation/validation scripts
    references/       # Supporting documentation
```

### Design Principles

**1. Self-Contained Guidance**

Skills should provide complete, actionable instructions without requiring external knowledge.

**2. Reference Over Inline**

```markdown
❌ BAD: Include 200 lines of inline instructions

✅ GOOD: Include 50 lines of core instructions + @reference to detailed docs
```

**3. Script-Enhanced Workflows**

Use scripts for:
- Validation (checking code quality, test patterns)
- Automation (running tools, gathering context)
- Complex logic (parsing, analysis)

**4. Focused Expertise**

Each skill should represent deep expertise in one domain, not shallow coverage of many.

**5. Required Components for Skill-First Architecture**

To support the mandatory skill-first pattern, ALL skills must include:

**a) Documentation Index** - Clear references to all relevant docs:
```markdown
## References
- Core instructions: `@$ACADEMICOPS/core/_CORE.md`
- Best practices: `@$ACADEMICOPS/docs/bots/BEST-PRACTICES.md`
- Detailed guide: `@$ACADEMICOPS/references/specific-guide.md`
```

**b) Workflow Checklist** - Step-by-step process:
```markdown
## Workflow
1. [Step 1 with specifics]
2. [Step 2 with specifics]
3. [Step 3 with specifics]
```

**c) Critical Rules** - Key principles and constraints:
```markdown
## Critical Rules
**NEVER**: [List of prohibited actions]
**ALWAYS**: [List of required actions]
```

**d) Quick Reference** - Condensed lookup for experienced users:
```markdown
## Quick Reference
- Pattern A: [Brief description]
- Pattern B: [Brief description]
```

**Why Required**: These components ensure skills serve as comprehensive entry points, preventing agents from searching for context independently.

---

## Slash Commands

### Structure

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

**Source**: [Slash Commands - Claude Docs](https://docs.claude.com/en/docs/claude-code/slash-commands)

### Design Principles

**1. Mandatory Skill-First Pattern**

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

**2. Load Context Efficiently**

Commands should invoke skills or load reference docs, not duplicate content:

```markdown
❌ BAD: Repeat 500 lines of skill instructions in command

✅ GOOD: Invoke skill via Skill tool, then add specific task guidance
```

**3. Use Arguments**

Support parameterized commands with `$ARGUMENTS`:

```markdown
Usage: /command <parameter>

Task: Process $ARGUMENTS with [specific instructions]
```

**4. Keep Commands Focused**

Each command should have one clear purpose. Use multiple focused commands rather than one Swiss Army knife.

**5. Namespace for Organization**

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

**Source**: [Slash Commands - Claude Docs](https://docs.claude.com/en/docs/claude-code/slash-commands)

**6. Limit YAML Frontmatter Bloat**

Keep frontmatter minimal - only `description` required:

```markdown
❌ BAD (42 lines of extra: bloat):
---
description: "Short description"
extra: |
  ## When to Use
  [20 lines]
  ## What This Loads
  [15 lines]
  ## Related Commands
  [7 lines]
---

✅ GOOD (minimal frontmatter):
---
description: "Short description"
---

[Concise body with actual instructions]
```

**Hard limit**: `extra:` blocks >10 lines are bloat. Move content to body or delete.

**Why**: YAML frontmatter is loaded into agent context immediately. Extensive `extra:` content wastes tokens on scene-setting that doesn't affect behavior. Use body for essential instructions, reference external docs for details.

**7. Supervisor Orchestration Pattern**

When invoking supervisor agent, provide explicit checklist requirements:

```markdown
✅ CORRECT (explicit requirements):
Invoke `supervisor` agent.

Supervisor MUST create TodoWrite with:
1. ✓ Independent plan review (second agent validates)
2. ✓ Atomic TDD cycles as todo items
3. ✓ Independent final state review vs original plan
4. ✓ Commit and push all changes

❌ INCORRECT (vague delegation):
The supervisor will handle the development task and enforce TDD.
```

**Why**: Supervisor needs explicit checklist to enforce workflow gates. Vague delegation ("will handle", "will enforce") allows skipping critical reviews. Imperative requirements ("MUST create TodoWrite with...") ensure supervisor creates visible, trackable workflow.

**Pattern applies to**: Any command invoking orchestration agents (supervisor, strategist, etc.) where specific workflow steps are mandatory.

---

## Hooks

### Types

- **SessionStart**: Run when Claude Code starts (context loading)
- **PreToolUse**: Run before Claude executes any tool (validation, linting)
- **PostToolUse**: Run after successful tool completion (formatting, tests)
- **Stop**: Run when Claude Code stops (cleanup)

**Source**: [Claude Code: Advanced AI Development Platform Guide, 2025](https://www.paulmduvall.com/claude-code-advanced-tips-using-commands-configuration-and-hooks/)

### Design Principles

**1. Lightweight and Fast**

Hooks run on critical path—keep them minimal:
- Avoid expensive operations in PreToolUse
- Use PostToolUse for slower tasks (tests, linting)
- SessionStart should load only essential context

**2. Conditional Execution**

Use matchers to run hooks only when relevant:

```yaml
- name: Load project context
  when:
    - type: session_start
  command: cat project-context.md
```

**3. Fail Fast**

Hooks should surface issues immediately, not silently fail or retry.

---

## Tool Design

### Principles from Anthropic

**1. Natural Formats**

Ensure tool inputs/outputs are natural to LLMs:
- Avoid unnecessary escaping
- Use clear, readable structures
- Prefer JSON or plain text over complex formats

**2. Thinking Space**

Provide sufficient tokens for reasoning before execution in tool descriptions.

**3. Comprehensive Documentation**

Include in tool definitions:
- Examples of typical use
- Edge cases and boundaries
- Clear error handling guidance

**4. Poka-Yoke Design**

Design tool arguments to prevent mistakes:
- Use enums for constrained choices
- Validate inputs clearly
- Provide helpful error messages

**5. Token Efficiency**

Tools should:
- Return concise, high-signal information
- Avoid bloated outputs
- Minimize functionality overlap (clear single purpose per tool)

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents); [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## What to AVOID

### 1. Unnecessary Details and Bloat

**Avoid**:
- Extensive background history that doesn't affect behavior
- FAQ sections answering questions the agent hasn't asked
- Exhaustive edge case documentation
- Verbose explanations of obvious concepts

**Why**: "Including too many unnecessary details can confuse AI tools" and creates context pollution.

**Source**: [What NOT to Include in Agent Prompts, Multiple Sources, 2024]

### 2. Excessive Scene-Setting

**Avoid**:
- Long contextual narratives
- Detailed persona descriptions when unnecessary
- Motivational or philosophical preambles

**Why**: "The model doesn't need a full scene description, just enough to influence style."

**Source**: [ElevenLabs Agents Prompting Guide, 2024](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)

### 3. Over-Engineering

**Avoid**:
- Complex frameworks when simple patterns work
- Multi-agent systems before optimizing single calls
- Premature abstraction

**Why**: "Over-engineered, bloated systems deliver underwhelming results." Start simple and increase complexity only when needed.

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)

### 4. Negative Instructions

**Avoid**:
- "Don't do X" without saying what to do instead
- Focus on what not to do

**Why**: "Avoid saying what not to do but say what to do instead—this encourages more specificity."

**Source**: [11 Prompt Writing Rules for AI Agents, Datablist, 2024](https://www.datablist.com/how-to/rules-writing-prompts-ai-agents)

### 5. Vague Instructions

**Avoid**:
- "Be concise" (vague)
- "Handle edge cases" (unspecific)
- "Use best practices" (assumes shared context)

**Do Instead**:
- "Limit response to 2-3 sentences" (specific)
- "Check for null values before accessing properties" (specific)
- "Follow fail-fast principles: no .get() with defaults" (specific)

**Why**: "Being specific about your desired output can help enhance results."

**Source**: [Claude 4 Prompt Engineering Best Practices, Anthropic](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

### 6. Mixing Instructions with Context

**Avoid**:
- Long prompts where instructions are buried in context
- Interleaving background information with action items

**Do Instead**:
- Separate instructions from context using XML tags or clear headings
- Put actionable instructions in dedicated sections

**Why**: "Separate instructions from context to avoid long, messy prompts."

**Source**: [General Tips for Designing Prompts, Prompt Engineering Guide](https://www.promptingguide.ai/introduction/tips)

---

## Quick Reference: Before You Write

**Before creating any component, ask**:

1. ✅ **Is this the simplest approach?** (Can I solve this without adding complexity?)
2. ✅ **Is the context minimal and high-signal?** (Am I providing just what's needed?)
3. ✅ **Are instructions specific, not vague?** ("2-3 sentences" not "be concise")
4. ✅ **Do I use examples over exhaustive rules?** (2-3 canonical examples vs. 20 edge cases)
5. ✅ **Is the structure clear and organized?** (XML tags, headers, logical flow)
6. ✅ **Have I removed bloat?** (Background fluff, FAQs, unnecessary narratives)
7. ✅ **Is the tool/component focused on one purpose?** (Single responsibility)
8. ✅ **Will this actually improve performance?** (Evidence-based, not just comprehensive)

---

## References

### Primary Sources (Anthropic Official)

1. **Building Effective AI Agents** (Dec 2024)
   https://www.anthropic.com/engineering/building-effective-agents
   *Key workflows, simplicity principles, tool design*

2. **Effective Context Engineering for AI Agents** (2024)
   https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
   *Context pollution, token efficiency, long-horizon techniques*

3. **Subagents - Claude API - Anthropic**
   https://docs.claude.com/en/docs/claude-code/sub-agents
   *Official subagent structure and best practices*

4. **Claude 4 Prompt Engineering Best Practices**
   https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices
   *XML tags, specificity, examples, chain of thought*

5. **Slash Commands - Claude Docs**
   https://docs.claude.com/en/docs/claude-code/slash-commands
   *Official command structure and usage*

6. **Claude Code Best Practices (Anthropic Engineering)**
   https://www.anthropic.com/engineering/claude-code-best-practices
   *Comprehensive Claude Code usage guidance*

### Secondary Sources

7. **Best Practices for Claude Code Subagents** (PubNub, 2025)
   https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/
   *Context preservation, practical patterns*

8. **Prompt Engineering Guide**
   https://www.promptingguide.ai/
   *General prompt engineering techniques*

9. **ElevenLabs Agents Prompting Guide** (2024)
   https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide
   *What to avoid, conciseness principles*

10. **11 Prompt Writing Rules for AI Agents** (Datablist, 2024)
    https://www.datablist.com/how-to/rules-writing-prompts-ai-agents
    *Practical rules for agent instructions*

### Anthropic Cookbook

11. **Anthropic Agent Patterns Cookbook**
    https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents
    *Code examples for workflow patterns*

---

## Evolution of This Document

This document should evolve as we learn more about what makes Claude Code components effective. When updating:

1. **Cite sources**: Every principle should reference authoritative documentation
2. **Prefer evidence over intuition**: Include practices proven to improve performance
3. **Remove disproven patterns**: If something doesn't work, document why and remove it
4. **Keep it concise**: This document itself should follow the principles it advocates
5. **Use the aops-trainer skill**: Let the trainer refine this document based on experimentation

**Last major review**: 2025-11-02
**Next review**: When new Anthropic guidance published or after 50+ agent experiments logged
