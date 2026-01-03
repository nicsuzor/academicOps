---
title: Gemini Mining Prompt Template
type: reference
permalink: session-insights-mining-prompt
---

# Gemini Mining Prompt

Prompt for per-session learning extraction via `mcp__gemini__ask-gemini`.

## Prompt Template

```
@{transcript_path}

Analyze this Claude Code session transcript. Extract:

1. **SKILL EFFECTIVENESS** - Look for patterns like "**Skill(s)**: X" (suggested) and "🔧 Skill invoked: `Y`" (actually used)
   - Which skills were recommended by prompt hydration?
   - Were the recommended skills actually invoked?
   - When invoked, was the skill useful? Did it provide relevant context?
   - When NOT invoked, did the agent struggle without that context?

2. **CONTEXT TIMING** - Evaluate whether context arrived at the right moment
   - Was necessary context injected BEFORE it was needed?
   - Did the agent make mistakes that earlier context injection could have prevented?
   - What specific context was missing when errors occurred?

3. **USER CORRECTIONS** - where user corrected agent behavior
   - What was agent doing?
   - What did user say to correct?
   - What's the generalizable lesson?

4. **FAILURES** - mistakes requiring user intervention
   - Description of what went wrong
   - Category: navigation|verification|instruction|hallucination|skill-bypass|context-gap|other

5. **SUCCESSES** - tasks completed correctly, especially when skills were properly invoked

Return JSON:
{
  "skill_effectiveness": [
    {
      "skill_suggested": "skill name or null",
      "skill_invoked": "skill name or null",
      "followed_suggestion": true/false,
      "was_useful": true/false/null,
      "notes": "why useful or what went wrong without it"
    }
  ],
  "context_issues": [
    {
      "issue": "description of context gap or timing problem",
      "consequence": "what mistake or delay resulted",
      "missing_context": "what should have been available",
      "suggested_injection_point": "when/where context should appear"
    }
  ],
  "corrections": [
    {"action": "what agent did", "feedback": "user correction", "lesson": "generalizable principle"}
  ],
  "failures": [
    {"description": "what failed", "category": "type"}
  ],
  "successes": [
    {"description": "what worked", "skill_contributed": "skill name if relevant"}
  ]
}
```

## Post-Processing

- Skill effectiveness → Track compliance patterns, identify skills that need stronger framing
- Context issues → Improve prompt hydration timing and skill descriptions
- User corrections → `/learn` skill for intervention selection
- Other findings → `/log` skill → GitHub Issues for pattern tracking
