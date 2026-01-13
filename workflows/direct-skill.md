---
id: direct-skill
title: Direct Skill/Command Invocation
type: workflow
category: routing
dependencies: []
steps:
  - id: identify-skill
    name: Identify matching skill or command
    workflow: null
    description: Match user prompt to exact skill/command
  - id: invoke
    name: Invoke the skill/command directly without wrapping in TodoWrite
    workflow: null
    description: Execute the skill with appropriate arguments
---

# Direct Skill/Command Invocation

## Overview

Minimal routing workflow for requests that map 1:1 to an existing skill or command. Skills already contain their own workflows, so wrapping them adds no value.

## When to Use

ONLY use when ALL of these are true:
- User prompt is a 1:1 match for an existing skill or command
- No additional planning or steps needed
- Skill/command handles the entire request
- No context composition required beyond skill itself

## When NOT to Use

Use a different workflow if:
- Request requires multiple skills in sequence
- Additional planning or coordination needed
- Request is more complex than single skill can handle
- Context from multiple sources must be composed

## Identification Signals

### Explicit Skill/Command Requests

User explicitly names a skill or command:
- "/commit"
- "/session-insights"
- "run /commit"
- "use the commit skill"

### Implicit Skill Matches

User request matches skill description exactly:
- "generate transcript for today" → session-insights skill
- "commit my changes" → commit skill
- "create session insights" → session-insights skill
- "review this PR" → review-pr skill

## Steps

### 1. Identify matching skill or command

Match user prompt to available skills:

**Check for exact matches:**
- Skill name mentioned explicitly?
- Request matches skill description exactly?
- Single skill handles entire request?

**Available skills to check:**
- See Skill tool documentation for current skill list
- Use `/help skills` to list available skills

### 2. Invoke the skill/command directly

Execute the skill without additional ceremony:

```javascript
Skill(skill="skill-name", args="[any arguments if needed]")
```

**Do NOT:**
- Wrap in TodoWrite
- Add additional planning steps
- Compose additional context (beyond what skill does)
- Add pre/post processing (unless skill requires it)

**Why direct invocation:**
- Skills already contain complete workflows
- TodoWrite adds no value
- Faster execution
- Cleaner transcript

## Examples

### Example 1: Explicit Command

**User:** "/commit"

**Action:**
```javascript
Skill(skill="commit")
```

**Not this:**
```javascript
// ❌ Don't do this
TodoWrite(todos=[
  {content: "Run commit skill", status: "pending", ...}
])
Skill(skill="commit")
```

### Example 2: Implicit Skill Match

**User:** "generate transcript for today"

**Action:**
```javascript
Skill(skill="session-insights")
```

### Example 3: Skill with Arguments

**User:** "commit with message 'feat: add new feature'"

**Action:**
```javascript
Skill(skill="commit", args="-m 'feat: add new feature'")
```

## Non-Examples (Wrong Workflow)

### Multi-Step Request

**User:** "commit my changes and push to remote"

**Wrong:** Direct skill invocation (needs multiple steps)

**Right:** Use appropriate workflow:
```javascript
TodoWrite(todos=[
  {content: "Commit changes", status: "pending", ...},
  {content: "Push to remote", status: "pending", ...}
])
```

### Request Requiring Context

**User:** "commit my work on the feature"

**Wrong:** Direct skill invocation (needs context about what feature work was done)

**Right:** Gather context first, then use skill:
```javascript
// First understand what was worked on
Task(subagent_type="general-purpose", prompt="Identify files changed for feature work")

// Then commit with appropriate message
Skill(skill="commit", args="-m 'feat: [description from context]'")
```

### Ambiguous Request

**User:** "review my code"

**Wrong:** Guess which skill (could be review-pr, could be critic, could be QA)

**Right:** Ask for clarification:
```
What kind of review would you like?
1. Pull request review (review-pr skill)
2. Critical feedback on design (critic agent)
3. QA verification of implementation (qa-verifier agent)
```

## Decision Tree

```
User request
    │
    ├─ Explicit skill mentioned? ──────────────────────> Direct invocation
    │
    ├─ 1:1 match to skill description? ────────────────> Direct invocation
    │
    ├─ Requires multiple skills? ──────────────────────> Use appropriate workflow
    │
    ├─ Needs context composition? ─────────────────────> Use appropriate workflow
    │
    └─ Ambiguous? ─────────────────────────────────────> Ask for clarification
```

## Success Metrics

- [ ] Skill invoked matches user intent exactly
- [ ] No unnecessary TodoWrite wrapping
- [ ] No missing context that skill needs
- [ ] Skill completes request fully
- [ ] Clean, minimal transcript
