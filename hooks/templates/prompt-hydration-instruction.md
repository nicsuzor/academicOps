# Prompt Hydration Instruction Template

Short instruction injected by UserPromptSubmit hook.
Tells main agent to spawn prompt-hydrator with temp file path.

Variables:
- `{prompt_preview}` - First 80 chars of user prompt
- `{temp_path}` - Path to temp file with full context

---
**MANDATORY**: Use the Read tool to read `{temp_path}`, then spawn prompt-hydrator:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="[contents of temp file]")
```

Follow the hydrator's workflow guidance before proceeding.

**Why always invoke?** Hydration is fast (haiku model), costless, and can only improve outcomes. Even "simple" tasks benefit from context enrichment - agents cannot reliably judge task complexity upfront. Never skip.
