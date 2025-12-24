---
title: Gemini Mining Prompt Template
type: reference
permalink: session-insights-mining-prompt
---

# Gemini Mining Prompt Template

Use with `mcp__gemini__ask-gemini` for per-session learning extraction.

## Current Approach: Organic Discovery

Simple prompt without framework-specific context. Let Gemini discover patterns naturally.

See `specs/session-insights-mining.md` for rationale and future Option B (guided extraction).

## Prompt

```
@$TRANSCRIPT_PATH

Analyze this Claude Code session transcript. This is a conversation between a user and an AI coding assistant.

Identify:

1. **FAILURES** - Where did the agent fail, make mistakes, or frustrate the user?
   - Errors that required user correction
   - Wrong assumptions or hallucinations
   - Tasks that weren't completed properly
   - User had to repeat themselves or redirect

2. **SUCCESSES** - What worked well?
   - Tasks completed correctly
   - Good problem-solving approach
   - Proper handling of errors or uncertainty

3. **IMPROVEMENTS** - Signs the agent learned or adapted?
   - Corrected behavior after feedback
   - Better approach on retry

<<<<<<< Updated upstream
1. **USER CORRECTIONS** (highest priority)
   Look for: tool rejections, explicit corrections, "no, I meant...", redirections, user doing it themselves after agent failed.

   For EACH correction, capture:
   - What the agent was trying to do
   - What file/component was being modified (if applicable)
   - What the user said to correct
   - What the generalizable lesson is

   Example: Agent updates OBSERVABILITY.md with intent-router-specific details.
   User says: "that should be in the intent router's spec if it's unique to intent router"
   Lesson: Component-specific info belongs in component spec, not general docs.

2. **OTHER PROBLEMS**
   - Navigation failures (searched multiple times)
   - Verification skipped
   - Instructions ignored

3. **SUCCESSES** (especially ordinary ones)
   - Correct tool/skill usage
   - Proper instruction following
   - Hook working correctly

4. **EXPERIMENT EVIDENCE**
   - Behavior matching hypothesis
   - Even unremarkable success counts if predicted

## Output (JSON)
=======
4. **CONCERNS** - Patterns that might cause future problems?
   - Workarounds instead of proper fixes
   - Skipped verification steps
   - Assumptions not validated

For each finding, provide RICH CONTEXT:
- **description**: What happened
- **evidence**: Direct quote from transcript
- **trigger**: What prompt/situation triggered this (user request, tool output, etc.)
- **severity**: low/medium/high/critical
- **category**: One of: missing_context, undocumented_command, hallucination, verification_skip, user_correction, self_correction, good_practice, axiom_violation, skill_gap, other
- **actionable**: What could prevent this in future (missing docs, skill update, prompt improvement, etc.)
>>>>>>> Stashed changes

Output as JSON:
{
<<<<<<< Updated upstream
  "user_corrections": [{
    "agent_action": "What the agent was doing/attempting (REQUIRED)",
    "target": "File or component being modified (null if N/A)",
    "user_feedback": "Exact or paraphrased user correction (REQUIRED)",
    "lesson": "Generalizable principle (best effort - /learn will refine)",
    "evidence": "Quote from transcript showing the exchange (REQUIRED)"
  }],
  "problems": [{
    "type": "navigation|verification|instruction|other",
    "description": "what happened",
    "evidence": "quote from transcript",
    "route_to": "learning/file.md or LOG.md"
  }],
  "successes": [{
    "description": "what worked",
    "evidence": "quote",
    "experiment_match": "filename or null"
  }],
  "experiment_evidence": [{
    "experiment": "filename",
    "observation": "what was observed",
    "supports_hypothesis": true|false,
    "evidence": "quote"
  }]
=======
  "failures": [{"description": "...", "evidence": "...", "trigger": "...", "severity": "...", "category": "...", "actionable": "..."}],
  "successes": [{"description": "...", "evidence": "...", "trigger": "...", "category": "...", "actionable": "..."}],
  "improvements": [{"description": "...", "evidence": "...", "trigger": "...", "severity": "...", "category": "...", "actionable": "..."}],
  "concerns": [{"description": "...", "evidence": "...", "trigger": "...", "severity": "...", "category": "...", "actionable": "..."}]
>>>>>>> Stashed changes
}
```

## Post-Processing

Pass Gemini's JSON output to the `/log` skill for routing:

```
Skill(skill="log", args="session-mining: {gemini_json}")
```

The log skill will:
1. Parse each finding
2. Route by category to appropriate learning files
3. Create new files for novel patterns
4. Update existing thematic files

## Future: Option B

If organic discovery proves valuable but imprecise, switch to guided extraction with:
- Category definitions
- Active experiment hypotheses
- Explicit routing rules

<<<<<<< Updated upstream
| Result Type | Destination |
|-------------|-------------|
| **User correction** | `/learn` skill with full context |
| Known pattern problem | `learning/[theme].md` |
| Novel problem | `LOG.md` |
| Experiment evidence | `experiments/[file].md` |
| Success with experiment match | `experiments/[file].md` |

### User Correction → /learn Workflow

Each `user_corrections` item should be passed to `/learn` with context:

```
Skill(skill="learn", args="
User correction detected in session:

**Agent action**: [agent_action]
**Target**: [target]
**User feedback**: [user_feedback]
**Suggested lesson**: [lesson]

Evidence:
[evidence]
")
```

The `/learn` skill will:
1. Check for prior occurrences of similar corrections
2. Choose minimal intervention level
3. Create/update experiment to track effectiveness

### Handling Incomplete Extractions

If Gemini can't extract all fields:
- **Missing agent_action or user_feedback**: Skip this correction (can't route without core context)
- **Missing target**: Set to null, still route to /learn
- **Missing/weak lesson**: Still route - /learn will synthesize the generalizable principle
=======
See spec for details.
>>>>>>> Stashed changes
