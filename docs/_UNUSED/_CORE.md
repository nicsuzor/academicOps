# Agent Working Instructions for academicOps Repository

**Context**: You are working in the academicOps framework repository (PUBLIC).

## Repository Organization

**Human documentation** (descriptive, "the system does..."):

- `README.md` - User-facing guide to components and capabilities
- `ARCHITECTURE.md` - Technical specifications and system design
- `docs/*.md` (except `docs/bots/`) - Developer documentation

**Agent instructions** (imperative, "you MUST..."):

- `core/*.md` - Universal rules (auto-loaded at SessionStart)
- `chunks/*.md` - Shared axioms and principles (referenced by core/, symlinked by skills/)
- `docs/bots/*.md` - Framework development instructions (auto-loaded at SessionStart)
- `agents/*.md` - Specialized workflows (loaded on-demand via Task tool)

**Critical separation (Axiom #2)**: NEVER put agent instructions in human docs or vice versa.

## File Modification Rules

**README.md is user-facing documentation ONLY**:

- ❌ NO agent instructions ("you MUST...")
- ❌ NO procedural rules for robots
- ✅ YES descriptive explanations of what tools do
- ✅ YES capabilities and component reference
- ✅ YES human-readable getting started guide

**Before adding >5 lines anywhere** (Anti-Bloat Protocol):

- [ ] Tried scripts/hooks/config instead of instructions?
- [ ] Checked for existing content to reference (chunks/, BEST-PRACTICES.md)?
- [ ] Verified not duplicating chunks/AXIOMS.md or other files?
- [ ] Using bullet points, not prose paragraphs?
- [ ] Specific instructions, not vague directives?

**Adding >10 lines**: STOP, create GitHub issue, get user approval.

## Core Principles (Quick Reference)

See `chunks/AXIOMS.md` for complete axioms. Key principles:

1. **Fail-fast**: No defaults, no workarounds - if tools fail, STOP and report (Axiom #7)
2. **DRY**: One source of truth - reference, don't duplicate (Axiom #9)
3. **Experiment-driven**: Test changes, measure outcomes, decide keep/revert/iterate
4. **Anti-bloat**: Scripts > hooks > config > instructions (enforcement hierarchy)
5. **Modular**: chunks/ = single source, symlinked to skills/*/resources/

## Key Workflows

**Making changes to framework**:

- Use `/trainer` command → loads aops-trainer skill
- All changes require experiment logs in `experiments/YYYY-MM-DD_name.md`
- Search GitHub issues first (3+ searches)
- Document diagnostics + solution design in GitHub

**Creating/editing components**:

- Skills: Use skill-creator skill
- Commands: Must invoke corresponding skill as MANDATORY first step
- Agents: Light orchestration only, delegate to skills
- Hooks: Automated enforcement, no instructions

**Updating documentation**:

- Instruction tree: `python scripts/generate_instruction_tree.py`
- Component descriptions: Add to frontmatter, verify extraction
- Validate: `python scripts/validate_instruction_tree.py`

## When You Don't Know

**If instructions or tools fail** (Axiom #7):

1. Read error message - what exactly failed?
2. ONE retry maximum with corrected input
3. STOP after 2nd failure - report problem and wait for user

**NEVER**:

- Try 3+ variations to "figure it out"
- Work around broken infrastructure
- Continue without confirmation

See `chunks/AXIOMS.md` Tool Failure Protocol for complete workflow.
