# Prompt Hydration Instruction (Gemini)

Gemini-specific instruction injected by BeforeAgent hook.
Since Gemini CLI doesn't support Task() subagents, the agent reads the hydration context directly.

Variables:

- `{prompt_preview}` - First 80 chars of user prompt
- `{temp_path}` - Path to temp file with full context

---

## Direct Questions: Answer and STOP

**If the user prompt is a pure information request** (e.g., "what is X?", "how does Y work?", "where is Z?"):

1. **Answer the question directly** - no hydration needed
2. **STOP and wait for further direction** - do NOT:
   - Suggest related tasks
   - Offer to implement anything
   - Chain into execution
   - Ask follow-up questions about next steps

The user asked a question. Answer it. Then wait. Nothing more.

---

## All Other Prompts: Hydrate First

**MANDATORY**: Read the hydration context file and apply its guidance:

```
Read {temp_path}
```

The file contains:
- User's original prompt
- Session context (recent conversation history)
- Framework workflows and skills index
- Applicable principles/heuristics
- Active and ready tasks

**After reading**, use the context to:
1. Identify the appropriate workflow for this prompt
2. Check if there's an existing task to claim or if a new task is needed
3. Apply relevant principles from the heuristics section
4. Execute the workflow guidance

**CRITICAL - Distinguishing Questions from Directives:**
- **Pure information requests** ("what is X?", "how does Y work?") -> Answer directly, then STOP
- **Imperatives disguised as questions** ("allow X to do Y", "make it so X works") -> These are DIRECTIVES, hydrate them
- **Discussion of feature design** ("should we add X?") followed by agreement -> This is a DIRECTIVE, hydrate it
- **When in doubt**: If there's ANY implementation intent, hydrate. If it's purely "tell me about X", answer and stop.
