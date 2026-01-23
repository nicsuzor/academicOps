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
- Requests that need file modifications (use minor-edit or design)

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
