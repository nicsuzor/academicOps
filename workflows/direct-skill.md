---
id: direct-skill
category: routing
---

# Direct Skill/Command Invocation

Minimal routing for requests that map 1:1 to an existing skill. Skills contain their own workflows.

## When to Use

ONLY when ALL true:
- User prompt matches an existing skill/command exactly
- No additional planning needed
- Skill handles the entire request
- No context composition required

## When NOT to Use

- Request requires multiple skills in sequence
- Additional planning or coordination needed
- Request more complex than single skill can handle
- Context from multiple sources must be composed

## Identification Signals

**Explicit**: "/commit", "/session-insights", "run /commit"

**Implicit**: Request matches skill description exactly
- "commit my changes" → commit skill
- "generate transcript for today" → session-insights skill

## Key Rule

Invoke skill directly. Do NOT wrap in TodoWrite or add ceremony.

## Decision Tree

```
Explicit skill mentioned? → Direct invocation
1:1 match to skill description? → Direct invocation
Requires multiple skills? → Use appropriate workflow
Needs context composition? → Use appropriate workflow
Ambiguous? → Ask for clarification
```

## Quality Gates

- Skill invoked matches user intent exactly
- No unnecessary wrapping
- No missing context that skill needs
- Skill completes request fully
