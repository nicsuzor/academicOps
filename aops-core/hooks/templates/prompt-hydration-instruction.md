**Prompt hydration available.** To transform your prompt into a structured execution plan, invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

Command:

- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='Follow instructions in {temp_path}')`
- Claude: `Agent(subagent_type='aops-core:prompt-hydrator', prompt='Follow instructions in {temp_path}')`

Hydration is recommended for complex tasks but optional for simple ones.
