# Prompt Hydration Instruction Template

Short instruction injected by UserPromptSubmit hook.
Tells main agent to spawn prompt-hydrator with temp file path (hydrator reads the file, not main agent).

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

**MANDATORY**: Spawn prompt-hydrator (do NOT read the temp file yourself):

```
Task(subagent_type="prompt-hydrator", model="haiku",
     description="Hydrate: {prompt_preview}",
     prompt="Read {temp_path} and provide workflow guidance.")
```

**After receiving the plan**, check if critic review is needed:

**SKIP critic review for**:
- `simple-question` workflow (no execution, just answering)
- Direct skill routes (hydrator output says "No bd task needed" and references a skill)
- Trivial single-step tasks

**INVOKE critic review for**:
- Multi-step execution plans
- Plans creating/modifying files
- Plans with architectural decisions or tradeoffs

```
Task(subagent_type="critic", model="opus",
     description="Review hydrated plan",
     prompt="Review this plan for errors, hidden assumptions, and missing verification:

[PASTE THE HYDRATOR'S EXECUTION PLAN HERE]

Return: PROCEED (execute as planned) | REVISE (list specific changes) | HALT (stop, explain why)")
```

- **PROCEED**: Call TodoWrite with the plan and execute
- **REVISE**: Call TodoWrite with the REVISED plan (incorporating critic feedback), then execute
  - **For idea capture / exploratory tasks**: Apply critic's revisions autonomously and create the task. Do NOT ask user clarifying questions - that violates zero-friction capture. User will correct if needed after seeing the captured idea.
- **HALT**: Stop immediately, present the issue to user

**CRITICAL**: Both PROCEED and REVISE require TodoWrite BEFORE execution. Never start executing without tracked todos.

**Why hydrator for tasks?** Hydration is fast (haiku model), costless, improves outcomes. Even "simple" tasks benefit from context enrichment.

**Why conditional critic?** Critic (opus) is expensive. Simple skill routes have well-defined workflows that don't benefit from review. Complex plans catch errors early with rigorous analysis.

**CRITICAL - Distinguishing Questions from Directives:**
- **Pure information requests** ("what is X?", "how does Y work?") → Answer directly, then STOP
- **Imperatives disguised as questions** ("allow X to do Y", "make it so X works") → These are DIRECTIVES, hydrate them
- **Discussion of feature design** ("should we add X?") followed by agreement → This is a DIRECTIVE, hydrate it
- **When in doubt**: If there's ANY implementation intent, hydrate. If it's purely "tell me about X", answer and stop.
