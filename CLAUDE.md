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

### Basic Memory (bmem) Tool Usage

**When using ANY `mcp__bmem__*` tool, you MUST use `project="main"`.**

Examples:
- `mcp__bmem__search_notes(query="...", project="main")`
- `mcp__bmem__read_note(identifier="...", project="main")`
- `mcp__bmem__write_note(title="...", content="...", folder="...", project="main")`

Do NOT use `project="aops"` or any other value. Always use `project="main"`.

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
- **Always use `model: "opus"` when invoking the Plan agent**
- README.md is SSoT for aOps file structure.

## Other rules
- Never duplicate information. If you have the same information in multiple files, decide whether to (a) maintain clear separation; or (b) join files without duplication.
- ALWAYS read and understand relevant files before proposing code edits. Do not speculate about code you have not inspected. If the user references a specific file/path, you MUST open and inspect it before explaining or proposing fixes. Be rigorous and persistent in searching code for key facts. Thoroughly review the style, conventions, and abstractions of the codebase before implementing new features or abstractions.
- Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused.
- Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs). Don't use backwards-compatibility shims when you can just change the code.
- Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of complexity is the minimum needed for the current task. Reuse existing abstractions where possible and follow the DRY principle.