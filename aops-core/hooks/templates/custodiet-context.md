---
name: custodiet-context
title: Custodiet Context Template
category: template
description: |
  Template written to temp file for rbg compliance subagent.
  Variables: {session_context} (chronological session record),
             {tool_name} (tool that triggered compliance check),
             {active_skill} (current active skill if any; "none" if no skill),
             {skill_scope} (authorized scope description for the active skill, empty if none)
---

# Workflow Enforcement Audit Request

Check if the session is maintaining high workflow integrity and staying within the requested scope.

## Trigger

Workflow check triggered after tool: **{tool_name}**

## Session Narrative

The following is a chronological record of the entire session. Use this to detect workflow anti-patterns grounded in what actually happened.

{session_context}

## Active Skill Context

**Active skill**: {active_skill}

{skill_scope}

If an active skill is shown above (not "none"), the agent has implicit authority for actions that skill requires. Evaluate violations in the context of this skill's authorized scope — actions within scope are NOT violations.

## Your Assessment

Review the session narrative against your axioms and workflow anti-patterns. Cite violations by principle number with evidence from the narrative.

### Context for Avoiding False Positives

- **Skill authority**: When `{active_skill}` is not "none", the Active Skill Context section above describes what that skill authorizes. Do NOT flag actions that fall within this authorized scope.
- **User-directed actions**: If the session narrative shows the USER invoked a skill (via `/skillname` or `Skill(skill=...)`), subsequent actions required by that skill are user-directed, not agent-initiated scope expansion.
- **Session continuations**: If the narrative contains a compaction summary from a prior session, previous custodiet blocks are RESOLVED. Focus on current activity, not historical events.
- **User overrides**: If the user explicitly directed the agent to do something, that direction takes precedence over principles like P#5 (Do One Thing) for that specific action.

Return your assessment in the specified format (OK, WARN, BLOCK, or error).
