**Prompt hydration available.** To enrich your task with execution context, invoke the **task-hydrator** agent with the file path argument: `{temp_path}`

Command:

- Gemini: `aops_core_task_hydrator(message='{temp_path}')`
- Claude: `Agent(subagent_type='aops-core:task-hydrator', prompt='{temp_path}')`

Hydration is recommended for complex tasks but optional for simple ones.
