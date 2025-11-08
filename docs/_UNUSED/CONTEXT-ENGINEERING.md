---
title: Context Engineering for AI Agents
type: guidance
description: Evidence-based principles for effective context management in Claude
  Code components, including token efficiency strategies, curated context patterns,
  and context pollution solutions.
tags:
  - context-engineering
  - best-practices
  - token-efficiency
  - agent-design
relations:
  - "[[docs/bots/BEST-PRACTICES]]"
  - "[[docs/bots/ANTI-PATTERNS]]"
permalink: a-ops/docs/unused/context-engineering
---

# Context Engineering for AI Agents

Evidence-based principles for effective context management in Claude Code components.

**Sources**: [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents); [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)

---

## Core Principles

### 1. Simplicity First

**Principle**: "Start simple. Finding the simplest solution possible, and only increasing complexity when needed."

- Use simple, composable patterns rather than complex frameworks
- Optimize single LLM calls before building multi-agent systems
- For many applications, "optimizing single LLM calls with retrieval and in-context examples is usually enough"

### 2. Transparency Over Opacity

**Principle**: "Explicitly display planning steps" to users

- Make agent reasoning visible
- Show what the agent is thinking and why
- Enable debugging through transparency

### 3. Context as Finite Resource

**Principle**: "Context must be treated as a finite resource" with "diminishing marginal returns"

- LLMs have an "attention budget" that depletes with excessive tokens
- Target "the smallest set of high-signal tokens that maximize the likelihood of your desired outcome"
- Even with large context windows, context pollution degrades performance

### 4. The Goldilocks Altitude

**Principle**: Balance specificity with flexibility in instructions

- **Too Low**: Overly complex, brittle hardcoded logic
- **Too High**: Vague guidance that assumes shared context
- **Just Right**: Specific paired with flexible guidance through strong heuristics

### 5. Examples Over Exhaustive Rules

**Principle**: "Examples are the 'pictures' worth a thousand words"

- Use diverse, canonical examples showing expected behavior
- More effective than exhaustive rule documentation
- Include challenging examples and edge cases

---

## Token Efficiency Strategies

### 1. Curated Context, Not Comprehensive Context

Provide minimal necessary information, not everything potentially relevant:

```markdown
❌ BAD: Include 500 lines of background, history, edge cases, FAQs

✅ GOOD: Include 50 lines of essential instructions + 2-3 examples
```

### 2. Just-in-Time Retrieval

Rather than pre-loading all data, maintain lightweight identifiers and dynamically retrieve via tools:

- Enables progressive discovery
- Mirrors human cognition
- Prevents upfront context pollution

### 3. Structured Organization

Use XML tags or Markdown headers to delineate sections:

```markdown
<background_information> [Essential context only] </background_information>

<instructions>
[Clear, actionable steps]
</instructions>

<examples>
[2-3 canonical cases]
</examples>
```

**Source**: [Claude 4 Prompt Engineering Best Practices, Anthropic](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

---

## Context Pollution Solutions

### For Long-Horizon Tasks

1. **Compaction**: Summarize conversation history, preserving architectural decisions while discarding redundant outputs
2. **Structured Note-Taking**: Maintain persistent external memory (files, task database)
3. **Sub-Agent Architectures**: Specialized agents return condensed summaries (1,000-2,000 tokens) to lead agent

---

## Quick Reference

**Before creating any component, ask**:

1. ✅ **Is this the simplest approach?**
2. ✅ **Is the context minimal and high-signal?**
3. ✅ **Are instructions specific, not vague?** ("2-3 sentences" not "be concise")
4. ✅ **Do I use examples over exhaustive rules?** (2-3 canonical vs. 20 edge cases)
5. ✅ **Is the structure clear and organized?** (XML tags, headers, logical flow)
6. ✅ **Have I removed bloat?** (Background fluff, FAQs, unnecessary narratives)
7. ✅ **Is the component focused on one purpose?** (Single responsibility)
8. ✅ **Will this actually improve performance?** (Evidence-based, not just comprehensive)
