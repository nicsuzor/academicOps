---
name: test-readonly
description: Test agent with read-only tools to verify frontmatter enforcement
tools: Read, Grep, Glob
color: yellow
---

# Test Agent: Read-Only

This is a test agent to verify if Claude Code enforces the `tools` field in agent frontmatter.

## Expected Behavior

If Claude Code enforces the `tools` field:
- ✅ Should be able to use: Read, Grep, Glob
- ❌ Should be BLOCKED from: Write, Edit, Bash, TodoWrite, etc.

## Test Instructions

1. Invoke this agent: `@agent-test-readonly`
2. Try to use Write tool: "Create a file called test.txt"
3. Observe if Claude Code blocks the Write tool natively

## Expected Results

**If tools enforcement works:**
- Claude Code blocks Write tool with error message
- No need for custom hook validation

**If tools enforcement doesn't work:**
- Write tool succeeds (or hook blocks it)
- Need to parse transcript in hooks for agent detection
