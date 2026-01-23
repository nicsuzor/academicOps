# Direct Skill Workflow

Request maps 1:1 to an existing skill. Skills contain their own workflows.

## When to Use

Use this workflow when:
- Explicit skill invocation: "/commit", "/email", "run /daily"
- Implicit match: request matches a skill description exactly

Do NOT use for:
- Multiple skills needed (use appropriate workflow)
- Context composition required (use design)
- Ambiguous mapping (ask user)

## Constraints

### Core Rules

- Invoke the skill directly without wrapping
- Trust the skill to handle the request—skills are self-contained

### Never Do

- Never wrap skill invocation in TodoWrite
- Never add ceremony around skill invocation
- Never intercept or override the skill's internal workflow

## Triggers

- When explicit skill invocation detected → invoke skill directly
- When implicit skill match detected → invoke skill directly

## How to Check

- Invoke directly: skill invoked without wrapper or preprocessing
- Trust skill: skill's internal workflow followed without override
- TodoWrite wrapping: skill invocation wrapped in TodoWrite tracking
- Added ceremony: extra steps added around skill invocation
- Intercept skill workflow: overriding or modifying skill's internal behavior
- Explicit skill invocation: user message starts with "/" or says "run /<skill>"
- Implicit skill match: request matches exactly one skill's description
