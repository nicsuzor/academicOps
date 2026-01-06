---
name: prompt-hydration-instruction
title: Prompt Hydration Instruction
category: template
---

# Prompt Hydration Instruction Template

Short instruction injected by UserPromptSubmit hook.
Tells main agent to spawn prompt-hydrator with temp file path (hydrator reads the file, not main agent).

Variables:

- `{prompt_preview}` - First 80 chars of user prompt
- `{temp_path}` - Path to temp file with full context

**MANDATORY**: Spawn prompt-hydrator (do NOT read the temp file yourself):

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Read {temp_path} and provide workflow guidance.")
```

Follow the hydrator's workflow guidance before proceeding.

**CRITICAL - User Intervention Priority**: If this prompt is a correction, suggestion, or redirection from the user while you were working on something else: **HALT your current work immediately**. Do NOT continue your previous plan. Focus EXCLUSIVELY on what the user is now asking. The user's intervention takes absolute priority over any in-progress work.

**Why always invoke?** Hydration is fast (haiku model), costless, and can only improve outcomes. Even "simple" tasks benefit from context enrichment - agents cannot reliably judge task complexity upfront. Never skip.
