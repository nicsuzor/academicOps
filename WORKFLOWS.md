---
name: workflows
title: Workflow Reference for Hydrator
type: instruction
category: instruction
description: What the hydrator tells the main agent for each workflow type
permalink: workflows
tags: [framework, routing, workflows]
---

# Workflow Reference

All work MUST follow one ofhe workflows in this file. No exceptions.


## TodoWrite Structure by Workflow

### Direct Skill/Command Invocation:
ONLY follow when the prompt is a 1:1 match for an existing skill or command:
- **Signals**: "generate transcript for today", "commit", "create session insights"
- **Action**: Invoke the skill/command directly without wrapping in TodoWrite
- **Example**: "generate transcript for today" → `Task(subagent_type="framework", prompt="Generate transcript for today's date")`
- **Why**: Skills already contain their own workflows; wrapping adds no value

### Simple question:
ONLY follow when the prompt is a simple question that can be answered directly WITHOUT modifying any data or files:
```
1. Answer the user's question: 
2. HALT after answering and await further instructions.
```

### Minor edit:

```
1. Fetch or create `bd` issue, mark as in-progress
2. Invoke `ttd` to create a failing test
3. Invoke `python-dev` to [change]
4. CHECKPOINT: Verify change works
5. Commit and push
```

### Development work:

Full TTD is required for all development work. 

```
0. Fetch or create `bd` issue, mark as in-progress
1. Articulate clear acceptance criteria
2. Create a plan, save to `bd` issue
3. Get critic review
4. Execute plan steps:
  - **Red**: Write failing test for [criterion]
  - **Green**: Minimal implementation to pass
  - **Evidence**: `uv run pytest -v` output
  - **Commit**: Descriptive message with phase reference
  - Repeat
6. CHECKPOINT: All tests pass
7. Invoke QA agent to validate against acceptance criteria
8. Commit, push, update `bd` issue
```

### Debugging:

```
0. Fetch or create `bd` issue, mark as in-progress
1. Articulate clear acceptance criteria
2. Use python-dev skill to design a durable test for success
3. Report findings and save to `bd` issue
4. Commit and push
```

### Batch processing:

```
0. Fetch or create `bd` issue, mark as in-progress
1. Identify scope of work and create plan for concurrent execution
2. Spawn parallel subagents for items 1-N (use run_in_background=true)
3. Monitor progress and spawn additional agents when needed
4. CHECKPOINT: All items processed successfully
5. Commit, push, update `bd` issue
```


## QA Verification Step

**CRITICAL**: Before completing work, the main agent MUST spawn qa-verifier:

```javascript
Task(subagent_type="qa-verifier", model="opus", prompt=`
Verify the work is complete.

**Original request**: [hydrated prompt/intent]

**Acceptance criteria**:
1. [criterion from plan]
2. [criterion from plan]

**Work completed**:
- [files changed]
- [todos marked complete]

Check all three dimensions and produce verdict.
`)
```

**If VERIFIED**: Proceed to commit and push
**If ISSUES**: Fix the issues, then re-verify before completing

## Beads (bd) Workflow - Issue Tracking

ALWAYS use `bd` to plan and track work and issues.

### Essential bd Commands

**Finding work:**
- `bd ready` - Show issues ready to work (no blockers)
- `bd list --status=open` - All open issues
- `bd show <id>` - Detailed issue view with dependencies

**Creating & updating:**
- `bd create --title="..." --type=task|bug|feature --priority=2` - New issue
  - Priority: 0-4 or P0-P4 (0=critical, 2=medium, 4=backlog)
- `bd update <id> --status=in_progress` - Claim work
- `bd close <id>` - Mark complete
- `bd close <id1> <id2> ...` - Close multiple (more efficient)

**Dependencies:**
- `bd dep add <issue> <depends-on>` - Add dependency (issue depends on depends-on)
- `bd blocked` - Show all blocked issues

**Sync:**
- `bd sync` - Sync with git remote (run at session end)

### bd Workflow Integration

When hydrator identifies work that should be tracked as a bd issue:
1. Check if related issue exists: `bd ready` or `bd list --status=open`
2. If creating new issues for multi-step work, recommend parallel creation
3. Include bd issue IDs in "Relevant Context" section
4. For session completion, remind: `bd sync` before `git push`
