---
title: Gemini Mining Prompt Template
type: reference
permalink: session-insights-mining-prompt
---

# Gemini Mining Prompt

Simple prompt for per-session learning extraction via `mcp__gemini__ask-gemini`.

## Prompt Template

```
@{transcript_path}

Analyze this Claude Code session. Extract:

1. **USER CORRECTIONS** - where user corrected agent behavior
   - What was agent doing?
   - What did user say to correct?
   - What's the generalizable lesson?

2. **FAILURES** - mistakes requiring user intervention
   - Description of what went wrong
   - Category: navigation|verification|instruction|hallucination|other

3. **SUCCESSES** - tasks completed correctly

Return JSON:
{
  "corrections": [
    {"action": "what agent did", "feedback": "user correction", "lesson": "generalizable principle"}
  ],
  "failures": [
    {"description": "what failed", "category": "type"}
  ],
  "successes": [
    {"description": "what worked"}
  ]
}
```

## Post-Processing

User corrections → `/learn` skill for intervention selection.
Other findings → LOG.md for pattern tracking.
