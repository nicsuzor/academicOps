# Hydrate Before Acting

**Preliminary Step**: invoke the **aops-core:prompt-hydrator** agent or skill to gather context using the EXACT command for your client:

- For Claude Code: `activate_skill(name="aops-core:prompt-hydrator", prompt="Analyze context in {temp_path}")`
- For Gemini CLI: `activate_skill(name="prompt-hydrator", prompt="Analyze context in {temp_path}")`

**IMMEDIATE ACTION REQUIRED**:
Once the hydrator returns the plan, you **MUST IMMEDIATELY PROCEED** to execute it (e.g. claim task, invoke critic).
**DO NOT STOP** after hydration. This is just a context-loading step.
