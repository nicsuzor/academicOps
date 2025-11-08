---
title: Claude Code Best Practices for academicOps Framework
type: guidance-index
description: Evidence-based guidance for creating effective Claude Code components
  (subagents, skills, commands, hooks) that are concise, performant, and maintainable.
  Index file referencing modular topic chunks.
tags:
  - best-practices
  - agent-design
  - framework
  - index
relations:
  - "[[docs/bots/CONTEXT-ENGINEERING]]"
  - "[[docs/bots/SUBAGENT-DESIGN]]"
  - "[[docs/bots/SKILL-DESIGN]]"
  - "[[docs/bots/COMMAND-DESIGN]]"
  - "[[docs/bots/HOOK-DESIGN]]"
  - "[[docs/bots/TOOL-DESIGN]]"
  - "[[docs/bots/ANTI-PATTERNS]]"
permalink: a-ops/docs/unused/best-practices
---

# Claude Code Best Practices for academicOps Framework

**Purpose**: Evidence-based guidance for creating effective Claude Code components (subagents, skills, commands, hooks) that are concise, performant, and maintainable.

**Last Updated**: 2025-11-07

---

## Core Guidance

All guidance has been modularized into focused topic files. Load what you need:

### Context Engineering

@CONTEXT-ENGINEERING.md

Core principles for effective context management:

- Simplicity first, transparency over opacity
- Context as finite resource, the Goldilocks altitude
- Examples over exhaustive rules
- Token efficiency strategies
- Context pollution solutions

### Component Design

**Subagents**: @SUBAGENT-DESIGN.md

- Structure and frontmatter
- Mandatory skill-first pattern
- Design principles (single responsibility, tool access, proactive use)
- Context preservation benefit

**Skills**: @SKILL-DESIGN.md

- Skills vs commands decision
- Structure (skill.md, scripts/, references/)
- Required components for skill-first architecture
- Self-contained guidance principles

**Slash Commands**: @COMMAND-DESIGN.md

- Structure and frontmatter
- Mandatory skill-first pattern
- Context efficiency, arguments, focus
- Namespace organization, frontmatter limits
- Supervisor orchestration pattern

**Hooks**: @HOOK-DESIGN.md

- Types (SessionStart, PreToolUse, PostToolUse, Stop)
- Lightweight and fast principles
- Conditional execution, fail-fast

**Tools**: @TOOL-DESIGN.md

- Natural formats, thinking space
- Comprehensive documentation
- Poka-yoke design, token efficiency

### What to AVOID

@ANTI-PATTERNS.md

Common mistakes that reduce agent effectiveness:

- Unnecessary details and bloat
- Excessive scene-setting
- Over-engineering
- Negative instructions
- Vague instructions
- Mixing instructions with context

---

## Quick Reference

**Before creating any component, ask**:

1. ✅ **Is this the simplest approach?**
2. ✅ **Is the context minimal and high-signal?**
3. ✅ **Are instructions specific, not vague?**
4. ✅ **Do I use examples over exhaustive rules?**
5. ✅ **Is the structure clear and organized?**
6. ✅ **Have I removed bloat?**
7. ✅ **Is the component focused on one purpose?**
8. ✅ **Will this actually improve performance?**

---

## Complete References

### Primary Sources (Anthropic Official)

1. **Building Effective AI Agents** (Dec 2024) https://www.anthropic.com/engineering/building-effective-agents

2. **Effective Context Engineering for AI Agents** (2024) https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

3. **Subagents - Claude API** https://docs.claude.com/en/docs/claude-code/sub-agents

4. **Claude 4 Prompt Engineering Best Practices** https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices

5. **Slash Commands - Claude Docs** https://docs.claude.com/en/docs/claude-code/slash-commands

6. **Claude Code Best Practices** (Anthropic Engineering) https://www.anthropic.com/engineering/claude-code-best-practices

### Secondary Sources

7. **Best Practices for Claude Code Subagents** (PubNub, 2025) https://www.pubnub.com/blog/best-practices-for-claude-code-sub-agents/

8. **Prompt Engineering Guide** https://www.promptingguide.ai/

9. **ElevenLabs Agents Prompting Guide** (2024) https://elevenlabs.io/docs/agents-platform/best-practices/prompting-guide

10. **11 Prompt Writing Rules for AI Agents** (Datablist, 2024) https://www.datablist.com/how-to/rules-writing-prompts-ai-agents

### Anthropic Cookbook

11. **Anthropic Agent Patterns Cookbook** https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents

---

## Evolution of This Document

This document should evolve as we learn more about what makes Claude Code components effective. When updating:

1. **Cite sources**: Every principle should reference authoritative documentation
2. **Prefer evidence over intuition**: Include practices proven to improve performance
3. **Remove disproven patterns**: If something doesn't work, document why and remove it
4. **Keep it concise**: This document itself should follow the principles it advocates
5. **Use the aops-trainer skill**: Let the trainer refine this document based on experimentation
6. **Chunk everything**: Keep topic files focused (<200 lines), reference via @notation

**Last major review**: 2025-11-07 (modularized into topic chunks) **Next review**: When new Anthropic guidance published or after 50+ agent experiments logged
