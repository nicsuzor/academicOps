## CRITICAL: Basic Memory (bmem) Project Parameter

**MANDATORY FOR ALL AGENTS**: When using ANY `mcp__bmem__*` tool, you MUST use `project="main"`.

Examples:
- `mcp__bmem__search_notes(query="...", project="main")`
- `mcp__bmem__read_note(identifier="...", project="main")`
- `mcp__bmem__write_note(title="...", content="...", folder="...", project="main")`

**This is non-negotiable.** Do NOT use `project="aops"`, `project="academicOps"`, or any other value. ALWAYS use `project="main"`.

## Framework Skill Delegation Model

ALL work in this repo flows through the `framework` skill, but the framework skill may delegate implementation:

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

## Framework Documentation, Paths, and state:

- **Framework state**: See "Framework State (Authoritative)" section in [[README.md]]
- **Paths**: `README.md` (file tree in root of repository)

## Framework Repository Instructions

This is the academicOps framework repository containing generic, reusable automation infrastructure.

**User-specific configuration belongs in your personal repository**, not here. When you install academicOps:

1. User context files live in `$ACA_DATA/` (your private data repository):
   - ACCOMMODATIONS.md (work style)
   - CORE.md (user context, tools)
   - STYLE.md, STYLE-QUICK.md (writing style)
   - projects/aops/VISION.md, ROADMAP.md (your vision/roadmap)

2. Each project gets its own `CLAUDE.md` with project-specific instructions

3. Framework principles (generic) are in this repo.

## Agent Protocol: framework development

**For framework development work**: See README.md for structure and $ACA_DATA/projects/aops/STATE.md for current status.

**MANDATORY before proposing any new framework component (hook, skill, script, command, workflow):**

- Invoke `framework` skill for strategic context
- Use the `framework` skill for ALL questions or decisions about the documentation or tools in this project.
- Use haiku by default when invoking claude code for testing purposes
- README.md is SSoT for aOps file structure.
