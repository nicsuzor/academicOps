---
title: Hydrator Tool Awareness - Manual Test Plan
category: test-plan
created: 2026-02-07
bug_reference: hydrator claiming email search was "human task"
---

# Hydrator Tool Awareness - Manual Test Plan

## Background

The prompt-hydrator subagent cannot know what tools the main agent has access to. It only sees:

- read_file
- memory MCP
- task_manager MCP
- activate_skill

The main agent may have: omcp (Outlook), zot (Zotero), osb, playwright, context7, etc.

**Original Bug**: When asked "search my QUT email archives for Mike Masnick", the hydrator:

1. Read the MCP servers list (configured servers)
2. Saw "outlook is configured"
3. Incorrectly concluded "this is fundamentally a human task" because "requires user credentials"
4. The main agent actually HAD `mcp__omcp__messages_search` and could have done it

## What We Fixed

1. **Agent definition** (`agents/prompt-hydrator.md`): Added explicit anti-instructions
   - "You do NOT know what tools the main agent has"
   - "NEVER claim a task is 'fundamentally a human task' based on tool assumptions"
   - "Let the main agent discover its own limitations"

2. **Context template** (`hooks/templates/prompt-hydrator-context.md`): Added warnings
   - "This list shows what's CONFIGURED, not what's available"
   - "Do NOT make feasibility judgments based on this list"

3. **MCP loading function** (`hooks/user_prompt_submit.py`): Now reads from config files
   - Instead of hardcoded list
   - Includes disclaimer: "configured but not verified running"

## Manual Test Cases

### Test Case 1: Email Search (Original Bug)

**Prompt**: "search my email archives for conversations with [person name]"

**Expected hydrator output**:

- Should suggest an execution plan that includes email search
- Should NOT say "fundamentally a human task"
- Should NOT say "requires user action"
- Should NOT say "agent cannot assume"

**Forbidden patterns** (grep for these in hydrator output):

- "fundamentally a human task"
- "this is not an executable task"
- "requires user action"
- "the agent cannot"
- "cannot be performed by"

**Pass criteria**: Hydrator suggests execution plan; main agent attempts the search.

### Test Case 2: Zotero Research

**Prompt**: "find papers in my Zotero library about content moderation"

**Expected**: Hydrator suggests research workflow, does NOT claim Zotero is unavailable.

### Test Case 3: Calendar Access

**Prompt**: "what's on my calendar today"

**Expected**: Hydrator suggests checking calendar, does NOT claim it's a human task.

### Test Case 4: Multi-Tool Request

**Prompt**: "search my email for messages from X, then add them to a contact file"

**Expected**: Hydrator plans the workflow, lets main agent discover capabilities.

### Test Case 5: Genuinely Human Tasks (Control)

**Prompt**: "send an email to the dean asking for a meeting next week"

**Expected**: Hydrator SHOULD flag this as needing human input because:

- External communication to non-user (P#48 applies)
- Requires human judgment on wording
- This is NOT a tool availability issue

**This confirms P#48 still works for actual human tasks.**

## How to Run Manual Tests

1. Start a fresh Claude Code session
2. Enter the test prompt
3. Wait for hydrator output
4. Check for forbidden patterns
5. Verify main agent proceeds with execution (or correctly asks for help)

## Automated Test Coverage

The following is tested automatically in `tests/hooks/test_hydrator_tool_awareness.py`:

- ✅ Agent definition warns about tool blindness
- ✅ Agent definition forbids "human task" claims
- ✅ Agent definition forbids feasibility judgments
- ✅ Agent definition suggests conditional approach
- ✅ Context template warns about configured vs available
- ✅ Context template forbids feasibility judgments
- ✅ MCP function reads from config (not hardcoded)
- ✅ MCP output includes disclaimer

## What Cannot Be Automated

- Actual LLM reasoning (hydrator might still make wrong inferences)
- End-to-end behavior (requires running full agent loop)
- Edge cases in prompt interpretation

## Regression Prevention

If this bug recurs:

1. Check if someone removed the anti-instructions from `agents/prompt-hydrator.md`
2. Check if context template warnings were removed
3. Check if new code introduced tool availability assumptions
4. Run `pytest tests/hooks/test_hydrator_tool_awareness.py`
