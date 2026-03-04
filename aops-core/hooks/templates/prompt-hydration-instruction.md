**CRITICAL: Prompt hydration required.** To align with project workflows and axioms, you MUST transform your prompt into a structured execution plan. Invoke the **prompt-hydrator** subagent with the file path argument: `{temp_path}`

Command:

- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

**Hydration Policy**:

- **MANDATORY** for all **imperative directives** (e.g., "add", "fix", "implement", "create", "allow", "update", "refactor", "change"). If the user is asking you to _perform an action_ or _modify the system_, you MUST hydrate first.
- **OPTIONAL** only for **pure information requests** (e.g., "how do I...", "where is...", "what is...").

**DO NOT answer directives directly.** You must spawn the hydrator to ensure compliance with framework standards.
