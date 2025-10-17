---
name: test-writer
description: Test agent with write tools to verify frontmatter enforcement
tools: Read, Write, Edit
color: blue
---

# Test Agent: Writer

This is a test agent to verify if Claude Code enforces the `tools` field in agent frontmatter.

## Expected Behavior

If Claude Code enforces the `tools` field:
- ✅ Should be able to use: Read, Write, Edit
- ❌ Should be BLOCKED from: Bash, Grep, Glob, TodoWrite, etc.

## Test Instructions

1. Invoke this agent: `@agent-test-writer`
2. Try to use Bash tool: "Run ls command"
3. Observe if Claude Code blocks the Bash tool natively

## Expected Results

**If tools enforcement works:**
- Claude Code blocks Bash tool with error message
- No need for custom hook validation

**If tools enforcement doesn't work:**
- Bash tool succeeds (or hook blocks it)
- Need to parse transcript in hooks for agent detection
