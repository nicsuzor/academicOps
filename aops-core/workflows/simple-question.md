# Simple Question Workflow

Answer and HALT. No modifications.

## When to Use

Use this workflow when:

- "What is...", "How does...", "Where is..."
- Pure information request
- No actions are required

Do NOT use for:

- "Can you...", "Please...", "Fix..." (action is required)
- Questions that lead to investigation (use debugging)
- Requests that need file modifications (use design)

## Fast-Track Detection

The `user_prompt_submit` hook automatically detects pure questions and routes them
to this workflow without full hydration. This saves tokens and latency.

### Examples: Pure Questions (fast-tracked)

These prompts skip full hydration and route directly here:

1. "What is the hydrator?" - Information request, no action keywords
2. "How does the task system work?" - Explanation request
3. "Where are errors handled?" - Location inquiry
4. "Explain the architecture" - Description request
5. "Is the memory server running?" - Status inquiry

### Examples: NOT Pure Questions (full hydration)

These contain action keywords and need full hydration:

1. "What should I add to fix this?" - Contains "add", "fix"
2. "Can you create a new file?" - Contains "can you", "create"
3. "How do I run the tests?" - Contains "run" as action verb
4. "Please explain and then update it" - Contains "please", "update"
5. "Help me implement this feature" - Contains "help me", "implement"

## Constraints

### Core Rules

- Answer clearly and concisely
- After answering, **HALT** and await the user's next instruction

### Critical Prohibition

**No unsolicited actions.** Answer the question, then stop.

### Never Do

- Never take unsolicited actions
- Never modify files
- Never create tasks
- Never suggest next steps or offer to do additional work

## Triggers

- When question is received → answer it
- When answer is given → halt

## How to Check

- Answer clearly: response directly addresses the question asked
- Halt: agent stops and awaits next user instruction
- Unsolicited actions: any action not directly requested by user
- File modifications: any Write, Edit, or NotebookEdit tool use
- Task creation: any create_task MCP call
- Suggest next steps: offering to do additional work
