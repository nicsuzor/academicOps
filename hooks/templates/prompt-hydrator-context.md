---
name: prompt-hydrator-context
title: Prompt Hydrator Context Template
category: template
description: Template written to temp file by UserPromptSubmit hook for prompt-hydrator subagent.
---

# Prompt Hydrator Context Template

This template is written to a temp file by the UserPromptSubmit hook.
The prompt-hydrator subagent reads this file to get full context.

Variables:
- `{prompt}` - Full user prompt
- `{session_context}` - Recent prompts, active skill, TodoWrite state

---
# Prompt Hydration Request

Analyze this user prompt and return workflow guidance for the main agent.

## User Prompt

{prompt}
{session_context}

## Your Task

1. **Classify the prompt** - What type of work is this?
2. **Select workflow dimensions**:
   - Gate: `plan-mode` (needs user approval) or `none`
   - Pre-work: `verify-first`, `research-first`, or `none`
   - Approach: `tdd`, `direct`, or `none` (if just a question)
3. **Identify skill(s)** - Which skill(s) should be invoked?
4. **Select guardrails** - What constraints apply?

## Return Format

Return a structured response the main agent can follow:

```markdown
## Prompt Hydration

**Workflow**: gate=[X] pre-work=[X] approach=[X]
**Skill(s)**: [skill name(s) or "none"]
**Guardrails**: [list]

### Guidance
[Specific instructions for the main agent based on workflow selection]
```
