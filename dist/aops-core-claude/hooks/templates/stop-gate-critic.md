# Plan Review Required

You are attempting to stop the session immediately after hydration without performing any work or review.

**Mandatory Step**: Before finishing, you MUST invoke the Critic skill to review your execution plan and ensure it aligns with the hydrated intent and acceptance criteria.

**Instruction**: Do NOT stop. Invoke:
`Task(subagent_type="critic", prompt="Review this plan: [your plan here]")`
