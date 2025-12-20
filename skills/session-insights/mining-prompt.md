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

1. **PROBLEMS**
   - User corrections (explicit or implicit)
   - Navigation failures (searched multiple times)
   - Verification skipped
   - Instructions ignored

2. **SUCCESSES** (especially ordinary ones)
   - Correct tool/skill usage
   - Proper instruction following
   - Hook working correctly

3. **EXPERIMENT EVIDENCE**
   - Behavior matching hypothesis
   - Even unremarkable success counts if predicted

## Output (JSON)

{
  "problems": [{
    "type": "user_correction|navigation|verification|instruction|other",
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
| Known pattern problem | `learning/[theme].md` |
| Novel problem | `LOG.md` |
| Experiment evidence | `experiments/[file].md` |
| Success with experiment match | `experiments/[file].md` |
