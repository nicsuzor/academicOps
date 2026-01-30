# Hydrate Before Acting

**Preliminary Step**: Invoke the **prompt-hydrator** skill to gather context using this EXACT command:

`activate_skill(name="prompt-hydrator", prompt="Analyze context in {temp_path}")`

**IMMEDIATE ACTION REQUIRED**:
Once the hydrator returns the plan, you **MUST IMMEDIATELY PROCEED** to execute it (e.g. claim task, invoke critic).
**DO NOT STOP** after hydration. This is just a context-loading step.
