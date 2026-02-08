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

### Step 1: Check for Uncommitted Changes

```bash
git status --porcelain
```

If there are uncommitted changes:

- **Staged changes**: Commit them now with descriptive message
- **Unstaged changes**: Stage relevant files and commit, or explicitly note why changes are not being committed

> **CRITICAL**: Do not proceed to Step 2 with uncommitted work unless you explicitly document why (e.g., "Changes intentionally not committed because...")

### Step 1.5: Check for Revealed Work

If your session revealed errors or warnings that weren't caused by your changes (e.g., post-commit hook output, CI failures in other areas, deprecation warnings):

1. **Create a follow-up task** to track fixing them:
   ```
   create_task(title="Fix [category] errors revealed by [your change]", project="aops", priority=3)
   ```
2. **Note the task ID** in your reflection under "Next step"

> **Why**: P#30 (Nothing Is Someone Else's Responsibility) - revealed problems are now your responsibility to track, even if not to fix immediately.

### Step 2: Output Framework Reflection

Output the following structure **exactly** (the stop hook validates this format):

```markdown
## Framework Reflection

**Outcome**: success|partial|failure
**Accomplishments**: [What was completed this session]
**Friction points**: [Issues encountered, or "none"]
```

**Field definitions**:

- **Outcome**:
  - `success` - All planned work completed
  - `partial` - Some work completed, some deferred
  - `failure` - Unable to complete primary objective
- **Accomplishments**: Brief bullet points of what was done
- **Friction points**: Framework issues, tool problems, blockers, or "none"

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
