---
title: Framework Development Instructions
type: instructions
permalink: root-claude-instructions
description: Framework skill delegation model, repository conventions, and development guidelines for academicOps
---

## Standard process for framework development

- update the feature specs and roadmap first
- make a plan, get it reviewed, get approval
- update indices (README.md, INDEX.md, etc.)

### To test a feature:
- to get an inventory: run claude code headless and report the '/diag' command
- test a feature: run claude code headless with an instruction

## Framework Skill Delegation Model

ALL work in this repo flows through `Skill(skill="framework")`, but the framework skill may delegate implementation:

**Framework skill role**: Strategic context, planning, design decisions, documentation

**Delegation allowed**: Framework skill MAY delegate implementation to specialized skills:
- `python-dev` for production Python code
- `analyst` for data analysis
- Other specialized skills as appropriate

**Token enforcement**: When framework skill delegates, it MUST include the string "FRAMEWORK SKILL CHECKED" in the delegation message. Sub-agents receiving requests WITHOUT this token MUST refuse and fail loudly.

**Pattern**:
1. User request → Framework skill invoked (or auto-invoked via hook)
2. Framework skill provides context, makes decisions, creates plan
3. Framework skill delegates with "FRAMEWORK SKILL CHECKED" token
4. Specialized skill implements according to framework's plan
5. Framework skill validates and integrates results

**Prohibited**: Bypassing framework skill entirely - all work must START with framework context.

We are starting again in this aOps repo. This time, the watchword is MINIMAL. We are not just avoiding bloat, we are ACTIVELY FIGHTING it. and I want to win.

## Framework State: VISION.md and ROADMAP.md

**These two files ARE the framework's memory.** Without them being current, agents cannot understand what the framework is, what's working, or what needs attention.

Why this matters: Agents have no persistent memory. Every session starts from zero. VISION.md and ROADMAP.md are the ONLY reliable source of truth about the framework's current state. If they're stale, agents will waste time rediscovering what's already known, repeat completed work, or miss critical context.

**VISION.md** (`$AOPS/VISION.md`):
- Purpose: End state. What we're building and why.
- Update: When fundamental direction changes (rare).
- Keep out: Implementation details, current status.

**ROADMAP.md** (`$AOPS/ROADMAP.md`):
- Purpose: Current status. What's done, in progress, blocked.
- Update: After completing significant work.
- Keep out: Detailed how-to, specs, future speculation.

**After any framework session**: Check if VISION or ROADMAP need updates based on what was accomplished or decided. This is not optional housekeeping - it's preserving institutional memory for the next session.

## Framework Documentation, Paths, and state:

- **Framework state**: See "Framework State (Authoritative)" section in [[README]]
- **Paths**: [[README]] (file tree in root of repository)

### Memory System

**To persist knowledge**: Use `Skill(skill="remember")` - do NOT write markdown directly.

The framework uses an mcp-memory server. The `remember` skill handles writing markdown AND syncing to the memory server. If you skip the skill, the content won't be searchable.

**To search knowledge**: Use `mcp__memory__retrieve_memory(query="...")` or `mcp__memory__retrieve_with_quality_boost(query="...")`.

## Framework Repository Instructions

This is the academicOps framework repository containing generic, reusable automation infrastructure.

**User-specific configuration belongs in your personal repository**, not here. When you install academicOps:

1. User context files live in `$ACA_DATA/` (your private data repository):
   - ACCOMMODATIONS.md (work style)
   - CORE.md (user context, tools)
   - STYLE.md, STYLE-QUICK.md (writing style)
   - $AOPS/VISION.md, ROADMAP.md (framework vision/roadmap)

2. Each project gets its own `CLAUDE.md` with project-specific instructions

3. Framework principles (generic) are in this repo.

## Agent Protocol: framework development

**For framework development work**: See [[README]] for structure and $ACA_DATA/projects/aops/STATE.md for current status.

**MANDATORY before proposing any new framework component (hook, skill, script, command, workflow):**

- Invoke `Skill(skill="framework")` for strategic context
- Use `Skill(skill="framework")` for ALL questions or decisions about the documentation or tools in this project.
- Use haiku by default when invoking claude code for testing purposes
- **Always use `model: "opus"` when invoking the Plan or Critic agent**
- README.md is SSoT for aOps file structure.

## Git workflow
- **Never amend commits that are already pushed.** If you need to fix something after pushing, create a new commit. Don't use `--amend` followed by force push.
- If remote has changes, merge or rebase - don't force push.

## Other rules
- Never duplicate information. If you have the same information in multiple files, decide whether to (a) maintain clear separation; or (b) join files without duplication.
- ALWAYS read and understand relevant files before proposing code edits. Do not speculate about code you have not inspected. If the user references a specific file/path, you MUST open and inspect it before explaining or proposing fixes. Be rigorous and persistent in searching code for key facts. Thoroughly review the style, conventions, and abstractions of the codebase before implementing new features or abstractions.
- Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused.
- Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs). Don't use backwards-compatibility shims when you can just change the code.
- Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of complexity is the minimum needed for the current task. Reuse existing abstractions where possible and follow the DRY principle.
- when i give you an example with 'e.g' or 'i.e.', use that example explicitly as representing a broader, more general class. Don't just make changes based on the example; make changes based on the class.
