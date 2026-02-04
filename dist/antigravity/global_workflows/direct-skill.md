---
id: direct-skill
category: routing
bases: []
---

# Direct Skill

Request maps 1:1 to existing skill. Skills contain their own workflows.

## Routing Signals

- Explicit: "/commit", "/email", "run /daily"
- Implicit: Request matches skill description exactly

## NOT This Workflow

- Multiple skills needed → appropriate workflow
- Context composition required → [[design]]
- Ambiguous mapping → ask user

## Unique Steps

1. Invoke skill directly
2. Do NOT add unnecessary ceremony around skill invocation

## Key Rule

Skills are self-contained. Trust the skill to handle the request.
