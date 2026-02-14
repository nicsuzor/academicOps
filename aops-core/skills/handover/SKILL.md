---
name: handover
category: instruction
description: Session handover - commit changes, output Framework Reflection, clear stop gate
allowed-tools: Bash, Read
version: 1.0.0
permalink: skills-handover
---

# /handover Command Skill

Required session-end handover procedure. Invoked when stop hook blocks session.

## Purpose

The handover skill ensures clean session closure by:

1. Verifying uncommitted changes are handled
2. Outputting structured Framework Reflection
3. Clearing the stop gate to allow session to end

## Usage

```
/handover
```

This skill is **mandatory** before session end. The stop hook blocks until `/handover` is invoked.

## Execution

### Step 1: Commit All Work (MANDATORY)

```bash
git status --porcelain
```

**You MUST commit all your work before ending the session.** This is non-negotiable per P#24 (No Commit Hesitation).

- **Staged changes**: Commit immediately with descriptive message
- **Unstaged changes**: Stage and commit ALL relevant files
- **No exceptions**: Work that isn't committed is lost

> **CRITICAL**: Do not proceed to Step 1.5 until ALL changes are committed. The only acceptable reason to skip committing is if you made NO file changes this session.

### Step 1.5: Capture Outstanding Work

Before ending the session, create follow-up tasks for ANY outstanding work:

1. **Revealed errors/warnings** - Problems discovered but not fixed (e.g., lint errors, CI failures, deprecation warnings)
2. **Incomplete work** - Planned steps that weren't completed
3. **Deferred decisions** - Items marked for later or needing user input
4. **Verification gaps** - Tests that should be run, reviews that should happen

**For each item, create a task**:

```
create_task(title="[Category] Brief description", project="[relevant-project]", priority=3)
```

**Note task IDs** in your reflection under "Next step".

> **Why**: P#30 (Nothing Is Someone Else's Responsibility) - anything discovered or deferred is your responsibility to track. Work that isn't captured in the task system is lost.

### Step 2: Output Framework Reflection

Output the following structure **exactly** (the stop hook validates this format):

```markdown
## Framework Reflection

**Outcome**: success|partial|failure
**Accomplishments**: [What was completed this session]
**Friction points**: [Issues encountered, or "none"]
**Next step**: [Task IDs for follow-up work, or "none"]
```

**Field definitions**:

- **Outcome**:
  - `success` - All planned work completed
  - `partial` - Some work completed, some deferred
  - `failure` - Unable to complete primary objective
- **Accomplishments**: Brief bullet points of what was done
- **Friction points**: Framework issues, tool problems, blockers, or "none"
- **Next step**: Task IDs from Step 1.5 (e.g., `aops-abc123`), or "none" if no follow-up needed

### Step 3: Confirm Handover Complete

After outputting the reflection, state:

```
Handover complete. Session may now end.
```

This confirms to the user and the stop hook that the handover procedure completed.

## Why This Skill Exists

Previously, the stop hook required inline Framework Reflection in any assistant message. This caused issues:

- Agents would forget the exact format
- The error message was verbose and noisy
- No structured procedure ensured commits happened before reflection

The handover skill:

- Encapsulates all session-end requirements in one place
- Ensures commits happen before reflection
- Provides clear, auditable session closure
- Allows the stop hook to be minimal ("invoke /handover")

## Integration

- **Stop hook**: Blocks session end until this skill is invoked
- **PostToolUse hook**: Detects skill invocation and clears the stop gate
- **Session state**: Sets `handover_skill_invoked` flag when complete

## Example

```
/handover

> git status --porcelain shows no changes
> Post-commit hook revealed 50 lint errors in other files

Created task aops-abc123: "Fix lint errors revealed by authentication feature"

## Framework Reflection
**Outcome**: success
**Accomplishments**: Implemented user authentication, added tests, updated documentation
**Friction points**: none
**Next step**: Fix lint errors (aops-abc123)

Handover complete. Session may now end.
```
