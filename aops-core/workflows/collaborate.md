---
id: collaborate
category: exploration
bases: [base-task-tracking]
---

# Collaborate

Open-ended interactive sessions for exploration, brainstorming, or complex debugging.

## Routing Signals

- "Let's brainstorm..."
- "I need to explore..."
- "Work with me on..."
- "Collaborate on..."

## Constraints & Output Handling

**CRITICAL**: Do NOT paste raw transcripts into task bodies.

1. **Session**: Perform the collaboration.
2. **Analysis**: Use `/session-insights` to generate a structured summary.
3. **Task Update**:
   - **Summary**: Copy from insights (max 500 chars).
   - **Learnings**: Key bullet points only.
   - **Link**: Reference the full transcript file/insights file.

## Workflow Steps

1. Create/Claim task (Type: `learn` or `task`).
2. Define session goal in task body.
3. Execute session (interactive).
4. Run `/session-insights`.
5. Update task with summary + link.
6. Complete task.
