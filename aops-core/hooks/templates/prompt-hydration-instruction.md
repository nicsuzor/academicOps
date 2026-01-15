# Prompt Hydration Instruction Template

Short instruction injected by UserPromptSubmit hook.
Tells main agent to spawn prompt-hydrator with temp file path (hydrator reads the file, not main agent).

Variables:

- `{prompt_preview}` - First 80 chars of user prompt
- `{temp_path}` - Path to temp file with full context

---

**MANDATORY**: Spawn prompt-hydrator (do NOT read the temp file yourself):

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Read {temp_path} and provide workflow guidance.")
```

**After receiving the plan**, invoke critic to review BEFORE executing:

```
Task(subagent_type="critic", model="opus",
     description="Review hydrated plan",
     prompt="Review this plan for errors, hidden assumptions, and missing verification:

[PASTE THE HYDRATOR'S EXECUTION PLAN HERE]

Return: PROCEED (execute as planned) | REVISE (list specific changes) | HALT (stop, explain why)")
```

- **PROCEED**: Call TodoWrite with the plan and execute
- **REVISE**: Update the plan per critic feedback, then execute
- **HALT**: Stop immediately, present the issue to user

**Why always invoke hydrator?** Hydration is fast (haiku model), costless, and can only improve outcomes. Even "simple" tasks benefit from context enrichment.

**Why critic review?** Plans reviewed before execution catch errors early. Critic uses opus for rigorous analysis.
