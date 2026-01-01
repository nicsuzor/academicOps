# Prompt Hydration Instruction Template

This template is injected by the UserPromptSubmit hook. Edit here to change what the main agent sees.

**Placeholders** (substituted by hook):
- `{prompt_preview}` - First 80 chars of user prompt
- `{escaped_prompt}` - Full prompt (escaped for embedding)
- `{session_context}` - Recent prompts, active skill, TodoWrite state

---

**FIRST**: Before responding to this prompt, invoke the prompt-hydrator agent to get workflow guidance:

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Analyze and hydrate this user prompt:\n\n{escaped_prompt}{session_context}")
```

Wait for hydrator output, then follow the workflow guidance it returns. The hydrator will tell you:
- Which workflow dimensions apply (gate, pre-work, approach)
- Which skill(s) to invoke
- Which guardrails are active
- Relevant context from memory and codebase

**Do NOT skip this step.** The hydrator ensures you have the right context and approach before starting work.
