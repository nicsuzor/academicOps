# Experiment: Task-Manager Skill Delegation and MCP Access

## Metadata
- Date: 2025-11-04
- Issue: #181
- Commit: adf0caca482b4aaed39e5bdb00507cec998268fc
- Model: claude-sonnet-4-5-20250929

## Hypothesis

**Problem 1**: task-manager loads strategic context via direct bash commands instead of delegating to tasks skill (violates Axiom #14: skills are authoritative).

**Problem 2**: task-manager cannot access MCP outlook tools despite needing them for email operations.

**Expected outcome**:
1. Removing bash command examples and strengthening skill delegation will reduce bloat and enforce skill authority
2. Adding explicit `tools:` field to agent frontmatter will grant MCP tool access to subagent

## Changes Made

### 1. commands/email.md
- BEFORE: Instructed to "Load strategic context: Silently read the user's personal database"
- AFTER: Simplified to invoke task-manager without procedural detail, delegate to skills

### 2. agents/task-manager.md frontmatter
- BEFORE: No `tools:` field (inheritance not working for MCP tools)
- AFTER: Added explicit `tools: Skill, Bash, mcp__outlook__messages_index, mcp__outlook__messages_list_recent, mcp__outlook__messages_get, mcp__outlook__messages_query`

### 3. agents/task-manager.md section "Strategic Alignment"
- BEFORE: Lines 92-98 provided bash commands to load context
- AFTER: Removed bash examples, replaced with reference to tasks skill

## Success Criteria

1. `/email` command successfully invokes task-manager agent
2. task-manager can access MCP outlook tools (no "No such tool available" errors)
3. task-manager invokes tasks skill for context loading (observed in logs - no direct bash to data/)
4. Email processing workflow completes successfully
5. Net line reduction (bloat removal, not addition)

## Results

[To be filled after testing]

**Test 1: Basic invocation**
- Command: `/email`
- Expected: task-manager launches, no tool errors
- Actual: [TBD]

**Test 2: MCP tool access**
- Expected: Successfully calls mcp__outlook__messages_list_recent
- Actual: [TBD]

**Test 3: Skill delegation**
- Expected: Invokes Skill(command="tasks") and Skill(command="email")
- Actual: [TBD]

**Test 4: Context loading**
- Expected: No direct bash commands to $ACADEMICOPS_PERSONAL/data/*
- Actual: [TBD]

## Outcome

[Success/Failure/Partial - to be filled]

## Findings

[What we learned - to be filled]

## Token Count Analysis

- BEFORE: commands/email.md (24 lines) + agents/task-manager.md (296 lines) = 320 lines
- AFTER: commands/email.md (15 lines) + agents/task-manager.md (289 lines) = 304 lines
- NET CHANGE: -16 lines (-5% reduction)

Bloat removed:
- 9 lines from commands/email.md (procedural detail now in agent)
- 7 lines from agents/task-manager.md (bash examples replaced with skill reference)
- +1 line for tools field in frontmatter
