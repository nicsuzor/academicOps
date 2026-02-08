---
name: framework
category: instruction
description: "Primary entry point for framework infrastructure work - workflow routing, task lifecycle, and categorical conventions"
allowed-tools: Task, Read, Glob, Grep, Bash, Edit, Write
version: 7.0.0
permalink: skills-framework
---

# Framework Skill

You are the **primary entry point for framework infrastructure work** in academicOps. This skill provides workflow routing, task lifecycle procedures, and categorical conventions.

## Workflow Router

Route your task to the appropriate workflow:

| If you need to... | Use workflow |
|-------------------|--------------|
| **Add a hook, skill, command, or agent** | [01-design-new-component](workflows/01-design-new-component.md) |
| **Fix something broken in the framework** | [02-debug-framework-issue](workflows/02-debug-framework-issue.md) |
| **Test a new approach or optimization** | [03-experiment-design](workflows/03-experiment-design.md) |
| **Check for bloat or trim the framework** | [04-monitor-prevent-bloat](workflows/04-monitor-prevent-bloat.md) |
| **Build a significant new feature** | [05-feature-development](workflows/05-feature-development.md) |
| **Write or update a specification** | [06-develop-specification](workflows/06-develop-specification.md) |
| **Record a lesson or observation** | [07-learning-log](workflows/07-learning-log.md) |
| **Unstick a blocked decision** | [08-decision-briefing](workflows/08-decision-briefing.md) |

### Quick Decision Tree

```
Is this a bug or something broken?
  → YES: 02-debug-framework-issue

Is this adding a new component (hook/skill/command/agent)?
  → YES: 01-design-new-component

Is this a significant feature with multiple phases?
  → YES: 05-feature-development

Is this testing an idea before committing?
  → YES: 03-experiment-design

Is this documentation/spec work?
  → YES: 06-develop-specification

Is this cleanup/maintenance?
  → YES: 04-monitor-prevent-bloat

Is this capturing a learning?
  → YES: 07-learning-log

Is something stuck waiting for a decision?
  → YES: 08-decision-briefing
```

---

## Categorical Conventions

### Logical Derivation System

This framework is a **validated logical system**. Every component must be derivable from axioms:

| Priority | Document      | Contains                       |
| -------- | ------------- | ------------------------------ |
| 1        | AXIOMS.md     | Inviolable principles          |
| 2        | HEURISTICS.md | Empirically validated guidance |
| 3        | VISION.md     | What we're building            |

**Derivation rule**: Every convention MUST trace to an axiom. If it can't, the convention is invalid.

### File Boundaries (ENFORCED)

| Location      | Action                     | Reason                                  |
| ------------- | -------------------------- | --------------------------------------- |
| `$AOPS/*`     | Direct modification OK     | Public framework files                  |
| `$ACA_DATA/*` | **MUST delegate to skill** | User data requires repeatable processes |

### Core Conventions

- **Skills are Read-Only**: No dynamic data in skills/
- **Just-In-Time Context**: Information surfaces when relevant
- **One Spec Per Feature**: Specs are timeless
- **Single Source of Truth**: Each info exists in ONE location
- **Trust Version Control**: No backup files, git tracks changes

---

## Full Task Lifecycle

Every task MUST follow this lifecycle. No shortcuts.

### Phase 1: Pre-Work (BEFORE any implementation)

```
1. TASK TRACKING (choose based on context)

   IF task exists:
     mcp__plugin_aops-core_tasks__get_task(id="<id>")
     mcp__plugin_aops-core_tasks__update_task(id="<id>", status="active")

   IF creating new tracked work:
     mcp__plugin_aops-core_tasks__create_task(task_title="[description]", type="task", project="aops", priority=2)
     mcp__plugin_aops-core_tasks__update_task(id="<id>", status="active")

   IF quick ad-hoc work (< 15 min, no dependencies):
     Use TodoWrite for session tracking only
     # Note: Still requires full post-work phase

2. LOAD CONTEXT (as needed)
   - Read AXIOMS.md if verifying principles
   - Read VISION.md if checking scope alignment
   - mcp__memory__retrieve_memory(query="[topic]") for prior work
```

### Phase 2: Planning (For Non-Trivial Work)

**Non-trivial work** = any of:
- Changes more than 2 files
- Touches core abstractions (AXIOMS, hooks, enforcement)
- Creates new patterns or conventions
- Involves architectural decisions

**Trivial work** (skip to Phase 3):
- Single file edits following existing patterns
- Documentation updates
- Typo fixes

```
1. ENTER PLAN MODE (if editing framework files)
   EnterPlanMode()

2. DESIGN WITH CRITIC REVIEW (MANDATORY for non-trivial work)
   Task(subagent_type="critic", model="opus", prompt="
   Review this plan for errors and hidden assumptions:
   [PLAN SUMMARY]
   Check for: logical errors, unstated assumptions, missing verification.
   ")

3. ADDRESS CRITIC FEEDBACK
   PROCEED: Continue to Phase 3
   REVISE: Fix issues, re-run critic (max 2 iterations, then escalate to user)
   HALT: Stop immediately. Report issues to user. Do NOT proceed.
```

### Phase 3: Implementation

```
1. USE APPROPRIATE SKILLS
   - Python code: Skill(skill="python-dev")
   - New feature: Skill(skill="feature-dev")
   - Data work: Skill(skill="analyst")

2. FOLLOW CATEGORICAL IMPERATIVE
   - Every change must be justifiable as universal rule
   - No ad-hoc fixes
   - If no rule exists, propose one first

3. UPDATE TASK AS YOU WORK (if tracking with task)
   mcp__plugin_aops-core_tasks__update_task(id="<id>", body="[progress note]")

4. ITERATION LOOP
   If implementation reveals plan was incomplete:
   - STOP implementation
   - Return to Phase 2 with new information
   - Re-run critic review
   - Continue only after revised plan approved
```

### Phase 3a: Handling Failures

```
IF skill invocation fails:
  - Log the error exactly (H5: Error Messages Are Primary Evidence)
  - Check if skill exists: Glob("**/skills/<name>/SKILL.md")
  - If missing: HALT, report to user
  - If exists but failed: Check error, retry once, then HALT if still failing

IF tests fail:
  - Do NOT auto-fix if fix is out of scope
  - Report failure to user with exact error
  - Ask: "Should I fix this (in scope) or create a separate task?"

IF git operations fail:
  - git push fails: Try git pull --rebase, retry push
  - Merge conflicts: HALT, report to user
  - No remote tracking: HALT, ask user for branch configuration
```

### Phase 4: Post-Work (MANDATORY - No Exceptions)

```
1. RUN QA VERIFICATION
   Invoke /qa or Skill(skill="qa-eval")
   # Verify with REAL DATA, not just test passage
   # If QA fails: Do NOT proceed. Fix issues first.

2. RUN TESTS (if code changed)
   uv run pytest tests/ -v --tb=short
   # Framework tests MUST pass
   # If tests fail: See Phase 3a failure handling

3. FORMAT AND COMMIT
   ./scripts/format.sh           # Format all files
   git add -A
   git commit -m "[descriptive message]

   Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

4. PUSH
   git pull --rebase            # Handle conflicts per Phase 3a
   git push                     # Push to remote
   git status                   # Verify: MUST show "up to date with origin"

   IF push not possible (no remote, read-only):
   - Report: "Changes committed locally but not pushed: [reason]"
   - This is a PARTIAL completion, not full completion

5. COMPLETE TASK (if tracking with task)
   mcp__plugin_aops-core_tasks__complete_task(id="<id>")

6. PERSIST LEARNINGS (if applicable)
   Task(subagent_type="general-purpose", model="haiku",
        run_in_background=true,
        description="Remember: [summary]",
        prompt="Invoke Skill(skill='remember') to persist: [key decisions]")
```

---

## HALT Protocol

When you encounter something you cannot derive:

1. **STOP** - Do not guess or work around
2. **STATE** - "I cannot determine [X] because [Y]"
3. **ASK** - Use AskUserQuestion for clarification
4. **DOCUMENT** - Once resolved, add the rule

---

## Quality Gates

### Before Claiming Complete

- [ ] All tests pass (`uv run pytest`)
- [ ] QA verification with real data passed
- [ ] Changes committed with proper message
- [ ] Changes pushed to remote
- [ ] Task completed
- [ ] Learnings persisted (if applicable)

### Work is NOT Complete Until

- `git status` shows "up to date with origin"
- All acceptance criteria met (verified, not assumed)

---

## Rules

### Core Principle

**We don't control agents** - they're probabilistic. Framework improvement targets the system, not agent behavior.

| Wrong (Proximate) | Right (Root Cause) |
|-------------------|---------------------|
| "Agent skipped skill" | "Router didn't explain WHY skill needed" |
| "Agent didn't verify" | "Guardrail instruction too generic" |
| "I forgot to check X" | "Instruction for X not salient at decision point" |

### What You Do NOT Do

- Skip any lifecycle phase
- Claim complete without pushing
- Bypass critic review for plans
- Make ad-hoc changes without rules
- Assume tests pass without running them
- Mark tasks complete without verification
