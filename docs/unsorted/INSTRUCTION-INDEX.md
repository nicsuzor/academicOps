# Complete Instruction Index - Parent Repository

**Purpose**: Comprehensive map of ALL instruction files across parent repo and submodules.

**Audience**: Internal use (Nic's writing repository).

**Maintenance**: Run `bot/scripts/check_instruction_orphans.py` to check for orphans.

**Related**: See `bot/docs/INSTRUCTION-INDEX.md` for the public academicOps index.

---

## Quick Reference

- **What is this file for?** → See registries below
- **How do agents load in my setup?** → See [Complete Loading Flow](#complete-loading-flow)
- **Bot (academicOps) files** → See [Bot Submodule Registry](#bot-submodule-academicops)
- **My parent repo files** → See [Parent Repository Registry](#parent-repository-registry)
- **Project-specific files** → See [Project-Specific Registries](#project-specific-registries)

---

## Complete Loading Flow

This shows how agents load instructions in YOUR complete setup (parent repo + bot submodule + projects).

```
Working in parent repo (/writing/):
    ↓
Read CLAUDE.md
    ↓
Load docs/INSTRUCTIONS.md (parent - YOUR preferences)
    ├→ References bot/README.md
    ├→ References bot/docs/AGENT-INSTRUCTIONS.md
    ├→ Loads docs/modes.md (YOUR modes, shadows bot/docs/modes.md)
    ├→ Loads docs/STYLE.md, docs/STYLE-QUICK.md (YOUR style)
    ├→ Loads docs/INDEX.md, docs/error-*.md, etc.
    └→ Loads docs/projects/INDEX.md (project registry)
    ↓
Load agent from bot/agents/{agent_name}.md
    ├→ Inherits from bot/agents/base.md
    └→ May reference additional bot/docs/ files
    ↓
If specific agent needs:
    ├→ strategist: Loads data/goals/, data/context/, data/projects/
    ├→ analyst: Loads project README, data/projects/{project}.md
    ├→ writer/documenter: Uses docs/STYLE.md
    └→ developer: References bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md

Working in project (e.g., /writing/projects/buttermilk/):
    ↓
Read projects/buttermilk/CLAUDE.md
    ↓
Load projects/buttermilk/docs/agent/INSTRUCTIONS.md (OVERRIDES ALL)
    ├→ Project-specific rules
    ├→ References docs/bots/*.md (Buttermilk-specific guides)
    ├→ References docs/agents/*.md (Buttermilk-specific agents)
    └→ References back to bot for some shared docs
    ↓
Load agent from bot/agents/{agent_name}.md (base behavior)
    ↓
Project-specific functionality:
    ├→ debugger: Uses docs/agents/debugging.md (golden path)
    └→ tester: Uses docs/TESTING_PHILOSOPHY.md
```

---

## Bot Submodule (academicOps)

**Location**: `/writing/bot/` (public GitHub: nicsuzor/academicOps)

**See**: `bot/docs/INSTRUCTION-INDEX.md` for complete public index

**Summary**:

- 2 entry points (CLAUDE.md, GEMINI.md)
- 3 primary instructions (INSTRUCTIONS.md, AGENT-INSTRUCTIONS.md, README.md)
- 8 agent definitions (base, developer, analyst, strategist, academic_writer, documenter, mentor, trainer)
- 17 supporting docs
- 12 orphaned files needing attention

**Key Files**:

- `bot/agents/*.md` - Agent behavior definitions
- `bot/docs/INSTRUCTIONS.md` - Base framework instructions
- `bot/docs/AUTO-EXTRACTION.md` - Extraction guide
- `bot/docs/PATH-RESOLUTION.md` - Path configuration

**Issues**: #73 (instruction mapping and orphan cleanup)

---

## Parent Repository Registry

Files in `/writing/` (private, Nic-specific).

### Entry Point

**CLAUDE.md**

- **Purpose**: Entry point for parent repo agents
- **References**: docs/INSTRUCTIONS.md, bot/README.md
- **Status**: ✅ Required

**GEMINI.md**

- **Purpose**: Entry point for Gemini agents
- **References**: docs/INSTRUCTIONS.md, bot/README.md
- **Status**: ✅ Required

---

### Primary Instructions

**docs/INSTRUCTIONS.md**

- **Purpose**: Complete parent repo instructions (YOUR preferences)
- **Loaded by**: CLAUDE.md → All parent repo agents
- **References**: 16 supporting docs
- **Overrides**: bot/docs/INSTRUCTIONS.md
- **Status**: ✅ Required
- **Issues**: -

**docs/INDEX.md**

- **Purpose**: Resource identifiers and tool locations (YOUR tools)
- **Loaded by**: docs/INSTRUCTIONS.md
- **References**: workflows, tools, bot docs
- **Status**: ✅ Required
- **Issues**: -

---

### Mode & Error Handling

**docs/modes.md**

- **Purpose**: Interaction modes (YOUR custom modes if different from bot)
- **Loaded by**: docs/INSTRUCTIONS.md
- **Overrides**: bot/docs/modes.md
- **Status**: ✅ Required
- **Issues**: -

**docs/error-quick-reference.md**

- **Purpose**: Quick error responses (YOUR workflow)
- **Loaded by**: docs/INSTRUCTIONS.md
- **Overrides**: bot/docs/error-quick-reference.md
- **Status**: ✅ Required
- **Issues**: -

**docs/error-handling.md**

- **Purpose**: Comprehensive error strategy (YOUR strategy)
- **Loaded by**: docs/INSTRUCTIONS.md
- **Overrides**: bot/docs/error-handling.md
- **Status**: ✅ Required
- **Issues**: -

---

### Architecture & Development

**docs/architecture.md**

- **Purpose**: YOUR system architecture (data/, projects/, workflows/)
- **Loaded by**: docs/INSTRUCTIONS.md
- **Different from**: bot/docs/architecture.md (which is academicOps architecture)
- **Status**: ✅ Required
- **Issues**: -

**docs/DEVELOPMENT.md**

- **Purpose**: Development workflows for YOUR projects
- **Loaded by**: docs/INSTRUCTIONS.md, docs/INDEX.md
- **Different from**: bot/docs/DEVELOPMENT.md (academicOps meta-development)
- **Status**: ✅ Required
- **Issues**: -

---

### Writing & Style

**docs/STYLE.md**

- **Purpose**: YOUR comprehensive writing style guide
- **Loaded by**: academic_writer, documenter (via bot/agents/)
- **Status**: ✅ Required
- **Issues**: -

**docs/STYLE-QUICK.md**

- **Purpose**: YOUR quick writing style reference
- **Loaded by**: academic_writer, documenter, docs/INSTRUCTIONS.md
- **Status**: ✅ Required
- **Issues**: -

---

### User Preferences

**docs/accommodations.md**

- **Purpose**: YOUR needs, ADHD accommodations, work style
- **Loaded by**: docs/INSTRUCTIONS.md
- **Status**: ✅ Required
- **Issues**: -

---

### Project Management

**docs/CROSS_CUTTING_CONCERNS.md**

- **Purpose**: Cross-project dependency tracking (YOUR 7 projects)
- **Loaded by**: docs/INSTRUCTIONS.md (when infrastructure changes)
- **References**: data/projects/_.md, docs/projects/_.md
- **Status**: ✅ Required
- **Issues**: #64

**docs/projects/INDEX.md**

- **Purpose**: Registry of YOUR 7 active projects
- **Loaded by**: docs/INSTRUCTIONS.md (scope detection)
- **References**: All 7 project context files
- **Status**: ✅ Required
- **Issues**: #64

**docs/projects/{project}.md** (7 files)

- **Purpose**: Technical context for each project
- **Files**: automod.md, buttermilk.md, mediamarkets.md, osbchatmcp.md, tja.md, wikijuris.md, zotmcp.md
- **Loaded by**: docs/projects/INDEX.md, docs/CROSS_CUTTING_CONCERNS.md
- **Status**: ✅ Required
- **Issues**: #64

---

### Strategic Context

**docs/STRATEGY.md**

- **Purpose**: Strategic planning guidance (YOUR strategy workflows)
- **Loaded by**: docs/INDEX.md
- **Status**: ✅ Required
- **Issues**: -

**docs/EMAIL.md**

- **Purpose**: Email processing workflow (YOUR email rules)
- **Loaded by**: docs/INDEX.md
- **Status**: ✅ Required
- **Issues**: -

**docs/EMAIL-TRIAGE-DESIGN.md**

- **Purpose**: Email triage system design
- **Loaded by**: Not explicitly loaded
- **Status**: ⚠️ Weakly connected
- **Issues**: -

**docs/AGENT_HIERARCHY.md**

- **Purpose**: Agent system overview
- **Loaded by**: Not explicitly loaded
- **Status**: ⚠️ Weakly connected (overview doc)
- **Issues**: -

**docs/PROJECT_SETUP.md**

- **Purpose**: Project setup guidelines
- **Loaded by**: Not explicitly loaded
- **Status**: ⚠️ Weakly connected
- **Issues**: -

---

### Workflows

**docs/workflows/INDEX.md**

- **Purpose**: Workflow index
- **Loaded by**: docs/INDEX.md
- **Status**: ✅ Required
- **Issues**: -

**docs/workflows/daily-planning.md** **docs/workflows/idea-capture.md** **docs/workflows/project-creation.md** **docs/workflows/strategy.md** **docs/workflows/weekly-review.md**

- **Purpose**: Specific workflow procedures
- **Loaded by**: Referenced from docs/workflows/INDEX.md
- **Status**: ✅ Required
- **Issues**: -

**docs/workflows/empirical-research-workflow.md**

- **Purpose**: Personal cross-project preferences for computational research (dbt, Streamlit, academicOps)
- **Loaded by**: analyst.md (when working on empirical projects)
- **References**: bot/docs/methodologies/computational-research.md, bot/docs/methodologies/dbt-practices.md
- **Status**: ✅ Required
- **Issues**: #78 (computational research methodologies)

---

### Data Files

**data/goals/*.md**

- **Purpose**: YOUR strategic goals and theories of change
- **Loaded by**: strategist agent (session initialization)
- **Status**: ✅ Required for strategist
- **Issues**: -

**data/projects/*.md**

- **Purpose**: YOUR active project descriptions
- **Loaded by**: strategist, analyst agents
- **Different from**: docs/projects/*.md (technical context vs project descriptions)
- **Status**: ✅ Required for strategist
- **Issues**: -

**data/context/*.md**

- **Purpose**: Current priorities, future planning, accomplishments
- **Loaded by**: strategist agent
- **Status**: ✅ Required for strategist
- **Issues**: -

**data/tasks/**

- **Purpose**: Task management files
- **Loaded by**: strategist agent, task management scripts
- **Status**: ✅ Required for task system
- **Issues**: -

**data/views/current_view.json**

- **Purpose**: Aggregated current task view
- **Loaded by**: strategist agent
- **Status**: ✅ Required for task system
- **Issues**: -

---

## Project-Specific Registries

### Buttermilk (/writing/projects/buttermilk/)

**Entry Point**:

- `CLAUDE.md` → `docs/agent/INSTRUCTIONS.md`

**Primary Instructions**:

- **docs/agent/INSTRUCTIONS.md** - Complete Buttermilk rules (OVERRIDES ALL)
  - Testing protocols, validation rules, debugging workflows
  - Critical failure modes, prevention systems
  - References 9 supporting docs
  - **Issues**: -

- **docs/AGENT_INSTRUCTIONS.md** - Alternative/duplicate?
  - **Status**: ⚠️ May duplicate docs/agent/INSTRUCTIONS.md
  - **Action needed**: Verify if duplicate and consolidate

**Functional Agents** (not in bot/agents/):

- **docs/agents/debugger.md** - Debug Pipeline Manager
  - Live debugging, validation
  - References docs/agents/debugging.md
- **docs/agents/tester.md** - Test Fixer Agent
  - Test maintenance and fixing
  - References docs/TESTING_PHILOSOPHY.md
- **docs/agents/debugging.md** - Golden path guide (NOT an agent, GUIDE)
  - **Status**: ⚠️ Confusing location (in agents/ but not an agent)

**Supporting Docs**:

- **docs/TESTING_PHILOSOPHY.md** - Testing philosophy (mock at boundaries)
- **docs/bots/TEST_FIXER_AGENT.md** - Test fixing protocol
- **docs/bots/debugging.md** - Debugging workflows (duplicate of agents/debugging.md?)
- **docs/bots/exploration-before-implementation.md** - Exploration requirements
  - **Duplicates**: bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md
- **docs/bots/impact-analysis.md** - Impact analysis protocol
  - **Duplicates**: bot/docs/IMPACT-ANALYSIS.md
- **docs/bots/INDEX.md** - Buttermilk docs index
- **docs/bots/config.md** - Configuration guide
- **docs/bots/data-architecture.md** - Buttermilk data architecture
- **docs/bots/techstack.md** - Tech stack

**Reference Docs** (User-facing, not agent):

- docs/reference/concepts.md
- docs/reference/cloud_infrastructure_setup.md ⚠️ Orphaned
- docs/reference/llm_agent.md ⚠️ Orphaned
- docs/reference/tracing.md ⚠️ Orphaned
- docs/reference/zotero_vectordb_guide.md ⚠️ Orphaned

**Testing Docs**:

- docs/TEST_FIXING_PATTERNS.md
- docs/testing/BOUNDARY_MOCKING.md ⚠️ Weakly connected

**Issues**: Duplicates with bot/, confusing agent/guide location

---

### WikiJuris (/writing/projects/wikijuris/)

**Entry Point**:

- `CLAUDE.md` → `docs/agent/INSTRUCTIONS.md`
  - **⚠️ BROKEN**: CLAUDE.md references `docs/agents/INSTRUCTIONS.md` (plural) but file is `docs/agent/INSTRUCTIONS.md` (singular)

**Primary Instructions**:

- **docs/agent/INSTRUCTIONS.md** - WikiJuris editorial guidelines
  - Content treatment, legal analysis, tone, formatting
  - Workflow types (processing contributions, reviewing PRs, issues)
  - Self-contained, no sub-references

**Issues**: Path mismatch in CLAUDE.md

---

### Other Projects

**dotfiles** (/writing/dotfiles/):

- CLAUDE.md → @docs/README.md
- docs/README.md, docs/nicwsl.md, docs/memory-investigation-2025-10-02.md

**Others**: Some have README files but no agent-specific instructions (use parent defaults)

---

## Shadow & Override Summary

### Files That Shadow Each Other

**docs/modes.md (parent) SHADOWS bot/docs/modes.md**

- Parent defines YOUR custom modes
- Bot provides defaults if parent doesn't exist

**docs/error-handling.md (parent) SHADOWS bot/docs/error-handling.md**

- Parent defines YOUR error workflows
- Bot provides defaults

**docs/error-quick-reference.md (parent) SHADOWS bot/docs/error-quick-reference.md**

- Parent defines YOUR quick reference
- Bot provides defaults

### Files With Same Name But Different Content

**docs/architecture.md vs bot/docs/architecture.md**

- **Parent**: YOUR system architecture (data/, projects/, workflows)
- **Bot**: academicOps framework architecture
- **NOT shadows**: Different content, both may be referenced

**docs/DEVELOPMENT.md vs bot/docs/DEVELOPMENT.md vs bot/agents/developer.md**

- **Parent docs/DEVELOPMENT.md**: YOUR development workflows
- **Bot docs/DEVELOPMENT.md**: How to develop academicOps itself
- **Bot agents/developer.md**: How developer agent should behave
- **NOT duplicates**: Three different purposes

### Project-Specific Duplicates

**bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md vs projects/buttermilk/docs/bots/exploration-before-implementation.md**

- **Status**: ⚠️ Likely duplicates
- **Action needed**: Consolidate or clarify differences

**bot/docs/IMPACT-ANALYSIS.md vs projects/buttermilk/docs/bots/impact-analysis.md**

- **Status**: ⚠️ Likely duplicates
- **Action needed**: Consolidate or clarify differences

---

## Maintenance Protocol

### Quarterly Review Checklist

- [ ] Run `bot/scripts/check_instruction_orphans.py` from parent repo
- [ ] Review orphaned files list - archive or link
- [ ] Verify project-specific INSTRUCTIONS still accurate
- [ ] Check for new duplicate files across parent/bot/projects
- [ ] Update GitHub issue references in this index
- [ ] Verify loading flow still matches actual agent behavior

### When Adding New Files

1. Determine location (parent vs bot vs project)
2. Add to appropriate section in this index
3. Add references from parent files in loading hierarchy
4. Run orphan checker to verify not orphaned
5. Add GitHub issue references if applicable
6. Commit index + new file together

### When Modifying Instructions

1. Check if file is shadowed (does parent override bot?)
2. Update correct version (parent override or bot base)
3. Update this index if purpose changed
4. Run orphan checker
5. Commit together

---

## File-to-Issue Mapping

### GitHub Issues Affecting Multiple Files

**#73 - Agent Instruction Map**

- bot/docs/AGENT-INSTRUCTION-MAP.md
- bot/docs/INSTRUCTION-INDEX.md
- docs/INSTRUCTION-INDEX.md (this file)
- bot/scripts/check_instruction_orphans.py
- All orphaned files listed in orphan section

**#64 - Project Context System**

- docs/CROSS_CUTTING_CONCERNS.md
- docs/projects/INDEX.md
- docs/projects/*.md (7 files)

### Automated Issue Tracking

**Current method**: Manual references in this index

**Proposed improvement**: Query GitHub API

```bash
# Find issues mentioning a file
gh issue list --repo nicsuzor/academicOps --search "filename.md in:body"

# Could generate issue mapping automatically
# See bot/docs/INSTRUCTION-INDEX.md maintenance section for details
```

---

## Quick Commands

```bash
# Check for orphans (from parent repo)
cd /writing && python bot/scripts/check_instruction_orphans.py

# Check for orphans (from bot submodule)
cd /writing/bot && python scripts/check_instruction_orphans.py

# Find all references to a file
grep -r "filename.md" docs/ bot/docs/ projects/*/docs/

# Search issues mentioning file
gh issue list --search "filename.md"

# Find files never referenced (orphan checker output)
python bot/scripts/check_instruction_orphans.py | grep "❌"
```

---

## Version History

- **2025-01-07**: Created comprehensive parent repo index with complete file mappings, shadow relationships, project-specific registries (#73)
