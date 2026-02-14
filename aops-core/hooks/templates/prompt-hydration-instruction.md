**Hydrate ALL prompts** (even simple ones!): invoke the **prompt-hydrator** agent before proceeding.

- Do NOT read the temp file yourself
- The Hydrator will provide missing context to help you understand and execute the instruction.
- Use your subagent tool or Task tool to call "prompt-hydrator" (or "aops-core:prompt-hydrator") with this exact query:

> `Transform user prompt using context in {temp_path}`
