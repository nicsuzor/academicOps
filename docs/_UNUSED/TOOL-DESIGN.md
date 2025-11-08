---
title: Tool Design
type: guidance
description: Principles for designing effective tools for AI agents, including natural
  formats, thinking space, comprehensive documentation, poka-yoke design, and token
  efficiency.
tags:
- tool
- tool-design
- best-practices
- agent-design
relations:
- '[[docs/bots/BEST-PRACTICES]]'
permalink: a-ops/docs/unused/tool-design
---

# Tool Design

Principles for designing effective tools for AI agents.

**Source**: [Building Effective AI Agents, Anthropic, Dec 2024](https://www.anthropic.com/engineering/building-effective-agents); [Effective Context Engineering for AI Agents, Anthropic, 2024](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## Principles from Anthropic

### 1. Natural Formats

Ensure tool inputs/outputs are natural to LLMs:

- Avoid unnecessary escaping
- Use clear, readable structures
- Prefer JSON or plain text over complex formats

### 2. Thinking Space

Provide sufficient tokens for reasoning before execution in tool descriptions.

### 3. Comprehensive Documentation

Include in tool definitions:

- Examples of typical use
- Edge cases and boundaries
- Clear error handling guidance

### 4. Poka-Yoke Design

Design tool arguments to prevent mistakes:

- Use enums for constrained choices
- Validate inputs clearly
- Provide helpful error messages

### 5. Token Efficiency

Tools should:

- Return concise, high-signal information
- Avoid bloated outputs
- Minimize functionality overlap (clear single purpose per tool)