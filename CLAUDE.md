ANY work in this repo MUST be carried out with the `framework` skill. NO EXCUSES, EVER. HALT IF THE SKILL FAILS.

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
