# Interactive Follow-up Workflow

Streamlined workflow for follow-up requests within an active session.

## When to Use

Use this workflow when:
- User is continuing work within the same session
- The request is a bounded, simple follow-up (e.g., "save to daily note", "update the readme", "rename that function")
- A task is already bound and active in the session
- No major architectural or framework changes are involved

Do NOT use for:
- New features or complex bugs
- Initial task planning
- Framework governance changes ([[framework-change]])
- Multi-session goals

## Pattern

1. **Continue current task**: Do NOT claim or create a new task. Use the existing bound task.
2. **Skip Critic**: Small changes don't require full critic review.
3. **Execute immediately**: Implement the requested change.
4. **Lightweight Verification**: Use simple tests or checks.
5. **Session Persistence**: Keep working until the session goal is met.

## Triggers

- Request is continuation of prior work
- Explicitly mentions "save", "update", "move", "fix typo", etc.

## Constraints

### Core Rules

- Do NOT create a new task if one is already bound.
- Invoke the hydrator for context (paths, formats) but avoid the "ceremony" of full planning.
- Skip the `Invoke CRITIC` step in the execution plan.

## How to Check

- **Context Injection**: Still happens (e.g., finding the daily note path).
- **Ceremony Reduction**: No redundant task creation or critic invocation.
- **Speed**: Goal is to get to the action within 5-10 seconds of hydration.
