---
title: Gemini Mining Prompt Template
type: reference
permalink: session-insights-mining-prompt
---

# Gemini Mining Prompt Template

Use with `mcp__gemini__ask-gemini` for per-session learning extraction.

## Prompt Structure

```
@$TRANSCRIPT_PATH

Analyze this Claude Code session transcript for framework learnings.

## Context

### Active Experiments
$EXPERIMENT_SUMMARIES

### Known Patterns
$LEARNING_THEMES

## Extract

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

{
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
}
```

## Building Context

### Get Active Experiments

```bash
# Find experiments not marked resolved
for f in $ACA_DATA/projects/aops/experiments/2025*.md; do
  if ! grep -q "Decision.*Resolved\|completed\|closed" "$f"; then
    echo "=== $(basename $f) ==="
    head -30 "$f" | grep -A5 "Hypothesis"
  fi
done
```

### Get Learning Themes

```bash
ls $ACA_DATA/projects/aops/learning/*.md | grep -v LOG | grep -v ARCHIVE
```

## Routing Results

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
