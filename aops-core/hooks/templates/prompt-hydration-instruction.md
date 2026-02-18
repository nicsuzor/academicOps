**User prompt hydration required.** Invoke the **prompt-hydrator** agent with the file path argument: `{temp_path}`

Run the hydrator with this command:
- Gemini: `delegate_to_agent(name='aops-core:prompt-hydrator', query='{temp_path}')`
- Claude: `Task(subagent_type='aops-core:prompt-hydrator', prompt='{temp_path}')`

Pass the file path directly to the agent — it will read the file and perform the hydration.

This is a technical requirement. Status: currently BLOCKED, but clearing this is quick and easy -- just execute the command!
