---
title: Gemini Mining Prompt Template
type: reference
permalink: session-insights-mining-prompt
---

# Gemini Mining Prompt

Prompt for per-session learning extraction via `mcp__gemini__ask-gemini`.

## Required Session Metadata

Before calling Gemini, the agent must provide these values (extracted from session path/context):
- `session_id`: Full UUID from session filename
- `date`: YYYYMMDD format
- `project`: Project name from session path

## Prompt Template

```
@{transcript_path}

Analyze this Claude Code session transcript. Extract the following information.

SESSION METADATA (you must include these in your response):
- session_id: {session_id}
- date: {date}
- project: {project}

EXTRACTION TASKS:

1. **SUMMARY** - One sentence describing what was worked on in this session

2. **ACCOMPLISHMENTS** - List of completed items (things marked done, features implemented, bugs fixed)

3. **SKILL EFFECTIVENESS** - Look for patterns like "**Skill(s)**: X" (suggested) and "🔧 Skill invoked: `Y`" (actually used)
   - Which skills were recommended by prompt hydration?
   - Were the recommended skills actually invoked?
   - When invoked, was the skill useful?
   - When NOT invoked, did the agent struggle without that context?

4. **CONTEXT TIMING** - Evaluate whether context arrived at the right moment
   - Was necessary context injected BEFORE it was needed?
   - Did the agent make mistakes that earlier context injection could have prevented?
   - What specific context was missing when errors occurred?

5. **USER CORRECTIONS** - where user corrected agent behavior
   - What was agent doing?
   - What did user say to correct?
   - What's the generalizable lesson?
   - Which heuristic from HEURISTICS.md relates to this? (H2=Skill-First, H3=Verification, H4=Explicit Instructions, H22=Indices First, etc.)

6. **FAILURES** - mistakes requiring user intervention
   - Description of what went wrong
   - Category: navigation|verification|instruction|hallucination|skill-bypass|context-gap|other
   - Related heuristic if applicable

7. **SUCCESSES** - tasks completed correctly, especially when skills were properly invoked

Return JSON with this EXACT structure:
{
  "session_id": "{session_id}",
  "date": "{date}",
  "project": "{project}",
  "summary": "one sentence description of session work",
  "accomplishments": ["completed item 1", "completed item 2"],
  "learning_observations": [
    {
      "category": "user_correction|skill_bypass|verification_skip|instruction_ignore|context_gap|success",
      "evidence": "quoted text from transcript",
      "context": "description of what happened",
      "heuristic": "H[n] or null",
      "suggested_evidence": "YYYY-MM-DD: observation text for HEURISTICS.md"
    }
  ],
  "skill_compliance": {
    "suggested": ["skill1", "skill2"],
    "invoked": ["skill1"],
    "compliance_rate": 0.5
  },
  "context_gaps": ["gap description 1", "gap description 2"]
}
```

## Output Location

Each session's JSON is saved to:
```
$ACA_DATA/dashboard/sessions/{session_id}.json
```

## Post-Processing

- Accomplishments → Grouped by project in daily.md
- Learning observations → `/log` skill → GitHub Issues for pattern tracking
- Skill compliance → Aggregated in synthesis.json for dashboard
- Context gaps → Inform prompt hydration improvements
