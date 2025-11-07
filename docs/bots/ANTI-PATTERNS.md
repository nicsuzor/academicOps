---
title: "Anti-Patterns: What to AVOID"
type: guidance
description: "Common mistakes that reduce agent effectiveness, including unnecessary details, excessive scene-setting, over-engineering, negative instructions, vague instructions, and mixing instructions with context."
tags:
  - anti-patterns
  - best-practices
  - mistakes
  - agent-design
relations:
  - "[[docs/bots/BEST-PRACTICES]]"
  - "[[docs/bots/CONTEXT-ENGINEERING]]"
---

# Anti-Patterns: What to AVOID

Common mistakes that reduce agent effectiveness.

**Sources**: Multiple Anthropic and industry sources (see references below)

---

## 1. Unnecessary Details and Bloat

**Avoid**:
- Extensive background history that doesn't affect behavior
- FAQ sections answering questions the agent hasn't asked
- Exhaustive edge case documentation
- Verbose explanations of obvious concepts

**Why**: "Including too many unnecessary details can confuse AI tools" and creates context pollution.

---

## 2. Excessive Scene-Setting

**Avoid**:
- Long contextual narratives
- Detailed persona descriptions when unnecessary
- Motivational or philosophical preambles

**Why**: "The model doesn't need a full scene description, just enough to influence style."

**Source**: [ElevenLabs Agents Prompting Guide, 2024](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)

---

## 3. Over-Engineering

**Avoid**:
- Complex frameworks when simple patterns work
- Multi-agent systems before optimizing single calls
- Premature abstraction

**Why**: "Over-engineered, bloated systems deliver underwhelming results." Start simple and increase complexity only when needed.

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)

---

## 4. Negative Instructions

**Avoid**:
- "Don't do X" without saying what to do instead
- Focus on what not to do

**Why**: "Avoid saying what not to do but say what to do instead—this encourages more specificity."

**Source**: [11 Prompt Writing Rules for AI Agents, Datablist, 2024](https://www.datablist.com/how-to/rules-writing-prompts-ai-agents)

---

## 5. Vague Instructions

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

---

## 6. Mixing Instructions with Context

**Avoid**:
- Long prompts where instructions are buried in context
- Interleaving background information with action items

**Do Instead**:
- Separate instructions from context using XML tags or clear headings
- Put actionable instructions in dedicated sections

**Why**: "Separate instructions from context to avoid long, messy prompts."

**Source**: [General Tips for Designing Prompts, Prompt Engineering Guide](https://www.promptingguide.ai/introduction/tips)

---

## References

- [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents)
- [Claude 4 Prompt Engineering Best Practices, Anthropic](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- [ElevenLabs Agents Prompting Guide, 2024](https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide)
- [11 Prompt Writing Rules for AI Agents, Datablist, 2024](https://www.datablist.com/how-to/rules-writing-prompts-ai-agents)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
