---
name: learn
description: Make minor adjustments to memory/instructions for future agents
allowed-tools: Edit
permalink: commands/learn
---

# CRITICAL: The user is telling you this because you failed

If the user invokes `/learn`, it means **an agent needed this information and didn't have it**. The user had to intervene. That's a failure.

**Your job is to fix the failure, not rationalize why you don't have to.**

❌ **WRONG**: "This info exists in file X, no changes needed"
✅ **RIGHT**: "This info exists but wasn't discoverable when needed. I'll add it where agents will find it."

**Existence ≠ Discoverability.** If the user had to tell you, the current location failed.

## What to do

1. **Accept that current documentation failed** - Don't argue
2. **Figure out WHERE agents need this info** - At what point did you need it?
3. **Put it there** - Even if it means adding a cross-reference to existing docs
4. **Keep it minimal** - 1-3 sentences, not essays

## Filing locations

- **Workflow step for a skill** → That skill's `SKILL.md`
- **Project-specific context** → That project's `CLAUDE.md`
- **Tool/integration info** → Reference doc in relevant skill
- **General framework** → README or relevant skill docs

## Anti-patterns (what you just did wrong)

- "Information already exists" → **Then why didn't you find it?** Add a pointer.
- "This is too minor" → The user is telling you. It's not minor to them.
- "I'll use /log instead" → Only if it's a behavior pattern. Facts go in docs.

## NOT for behavior patterns

If the lesson is about agent behavior (e.g., "agent broke X while fixing Y"), use `/log` instead.

## Examples

- "Transcripts are in ~/.claude/projects/" → Add to commands/transcript.md intro OR CLAUDE.md where agents search for transcripts
- "Use uv run from repo root" → Add to relevant SKILL.md
- "Project X uses format Y" → Add to projects/X/CLAUDE.md
