---
id: simple-question
title: Simple Question Workflow
type: workflow
category: information
dependencies: []
steps:
  - id: answer
    name: Answer the user's question
    workflow: null
    description: Provide clear, direct answer to the question
  - id: halt
    name: HALT after answering and await further instructions
    workflow: null
    description: Don't take additional actions unless asked
---

# Simple Question Workflow

## Overview

Minimal workflow for answering simple informational questions that don't require modifying data or files.

## When to Use

ONLY use when ALL of these are true:
- Question can be answered directly
- No file modifications needed
- No data changes needed
- No actions required
- Pure information request

## When NOT to Use

Use a different workflow if:
- Question leads to action (use appropriate workflow)
- Files need to be read/modified (use feature-dev or minor-edit)
- Data needs to be changed (use appropriate workflow)
- Question is exploratory (might need Explore agent)

## Steps

### 1. Answer the user's question

Provide a clear, direct answer:

**Be concise:**
- Answer the specific question asked
- Don't elaborate unnecessarily
- Use examples if helpful

**Be accurate:**
- Cite sources if relevant (file paths, line numbers)
- Admit uncertainty if unsure
- Offer to investigate if needed

**Be helpful:**
- Anticipate follow-up questions
- Provide context if useful
- Offer next steps if appropriate

### 2. HALT after answering and await further instructions

**Critical: Do NOT:**
- Make changes without being asked
- Start working on related tasks
- Proactively "fix" things you noticed
- Take any actions beyond answering

**Instead:**
- Wait for user response
- Let user decide next steps
- Be ready to act if asked

## Examples

### Good: Simple Question

**User:** "What does the git status command do?"

**Response:**
```
The git status command shows the current state of your working directory
and staging area. It displays:

- Which branch you're on
- Changes staged for commit (green)
- Changes not staged (red)
- Untracked files

It's useful for seeing what will be included in your next commit.
```

**Then:** HALT and await further instructions.

### Good: Code Reference Question

**User:** "Where are errors from the client handled?"

**Response:**
```
Clients are marked as failed in the `connectToServer` function
in src/services/process.ts:712.

The relevant code catches connection errors and updates the client
status accordingly.
```

**Then:** HALT and await further instructions.

### Bad: Acting Beyond Question

**User:** "What does the git status command do?"

**Bad Response:**
```
The git status command shows... [answer]

I notice you have uncommitted changes. Let me commit those for you.
[proceeds to make commits without being asked]
```

**Why bad:** User asked a question, not for action. Taking unsolicited action violates user autonomy.

## Edge Cases

### Question Requires Investigation

If you need to search/explore to answer:

```
I'll need to search the codebase to answer that. Let me use the
Explore agent to find where [X] is handled.
```

Then use appropriate tools/agents to investigate.

### Question is Ambiguous

If the question is unclear:

```
I need clarification:
- Did you mean [interpretation A] or [interpretation B]?
- Are you asking about [specific aspect]?
```

Don't guess - ask for clarification.

### Question Leads to Action

If answering reveals work needed:

```
[Answer to question]

I noticed [issue/opportunity]. Would you like me to:
1. [Option A]
2. [Option B]
3. Leave it as-is
```

Let user decide next steps.

## Success Metrics

- [ ] Question answered clearly and correctly
- [ ] No unsolicited actions taken
- [ ] No file modifications made
- [ ] Awaiting user's next instruction
