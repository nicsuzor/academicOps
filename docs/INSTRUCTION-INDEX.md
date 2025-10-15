# academicOps Instruction Index

**Purpose**: Complete reference for all instruction files in the academicOps framework.

**Audience**: Third-party users who have cloned academicOps as a standalone repository or submodule.

**Maintenance**: Auto-checked by CI/CD. Run `scripts/check_instruction_orphans.py` to verify no orphans.

---

## Quick Reference

- **What is this file for?** → See [File Registry](#file-registry)
- **How do agents load instructions?** → See [Loading Hierarchy](#loading-hierarchy)
- **What files do I need in my repo?** → See [External Files](#external-files-agents-reference)
- **Why are there multiple X files?** → See [Shadow & Override Relationships](#shadow--override-relationships)

---

## Loading Hierarchy

academicOps implements a hierarchical instruction system where more specific contexts override general ones.

### Entry Point

**CLAUDE.md** or **GEMINI.md** (repository root)
- First file loaded by AI agents
- Points to `docs/INSTRUCTIONS.md` for full instructions

### Three-Level Override System

Agents check for instructions in this order (most specific to least specific):

1. **Project-Specific** (if exists): `./docs/agent/INSTRUCTIONS.md` or `./docs/agents/INSTRUCTIONS.md`
   - In your project directory
   - **SUPERSEDES all other instructions**
   - Use for project-specific rules

2. **User-Global** (if exists): `${PARENT_REPO}/docs/INSTRUCTIONS.md`
   - In parent repository (if academicOps is used as submodule)
   - Personal preferences across all projects

3. **Base Framework**: `bot/agents/{agent_name}.md` and `bot/docs/INSTRUCTIONS.md`
   - From academicOps repository
   - Default behavior if no overrides exist

### Loading Flow

```
Agent starts
    ↓
Read CLAUDE.md (entry point)
    ↓
Load docs/INSTRUCTIONS.md (base instructions)
    ↓
Check for project-specific ./docs/agent/INSTRUCTIONS.md
    ├─ If exists → Load and OVERRIDE base
    └─ If not → Check for ${PARENT}/docs/INSTRUCTIONS.md
        ├─ If exists → Load and OVERRIDE base
        └─ If not → Use base only
    ↓
Load agent-specific file: agents/{agent_name}.md
    ↓
Load referenced supporting docs as needed
```

---

## File Registry

Every instruction file in academicOps with metadata.

### Format
- **Purpose**: What this file does
- **Loaded by**: What triggers loading this file
- **References**: What other files it points to
- **Issues**: GitHub issues related to this file (if any)
- **Status**: ✅ Required | ⚠️ Optional | 🔧 Maintenance

---

### Entry Points (2 files)

**CLAUDE.md**
- **Purpose**: Entry point for Claude Code / Claude Desktop agents
- **Loaded by**: AI agent on startup
- **References**: `docs/INSTRUCTIONS.md`
- **Status**: ✅ Required

**GEMINI.md**
- **Purpose**: Entry point for Gemini CLI agents
- **Loaded by**: AI agent on startup
- **References**: `docs/INSTRUCTIONS.md`
- **Status**: ✅ Required

---

### Primary Instructions (3 files)

**docs/INSTRUCTIONS.md**
- **Purpose**: Complete core instructions for academicOps
- **Loaded by**: CLAUDE.md, GEMINI.md → All agents
- **References**: 8 supporting docs (modes, INDEX, error-handling, etc.)
- **Status**: ✅ Required
- **Note**: This is the BASE. Project-specific or parent repo INSTRUCTIONS.md files override this.

**docs/AGENT-INSTRUCTIONS.md**
- **Purpose**: Detailed operational guide with security rules, extraction patterns, git polyrepo workflow, Python execution policy
- **Loaded by**: docs/INSTRUCTIONS.md
- **References**: AUTO-EXTRACTION.md, PATH-RESOLUTION.md
- **Status**: ✅ Required
- **Issues**: #81 (git polyrepo), #82 (Python execution policy)

**README.md**
- **Purpose**: Repository overview, quick reference, core axioms
- **Loaded by**: Referenced from parent INSTRUCTIONS.md files
- **References**: Agent definitions, key docs
- **Status**: ✅ Required

---

### Agent Definitions (8 files)

**agents/base.md**
- **Purpose**: Core rules ALL agents must follow
- **Loaded by**: All agents (inherited)
- **References**: modes.md, INDEX.md, other agent definitions
- **Status**: ✅ Required (foundational)
- **Issues**: -

**agents/developer.md**
- **Purpose**: Software development workflow, debugging, testing, INTERFACE MISMATCH CHECKPOINT
- **Loaded by**: When developer agent is invoked
- **References**: base.md (inherits)
- **Status**: ✅ Required
- **Issues**: #88 (localized fix without impact analysis)
- **Shadows**: None

**agents/analyst.md**
- **Purpose**: Data analysis, running queries, generating insights (with MANDATORY dbt-only data access)
- **Loaded by**: When analyst agent is invoked
- **References**: base.md, project README files, docs/methodologies/*.md (especially dbt-practices.md)
- **Auto-loads**: README.md files, data/README.md, data/projects/*.md, docs/methodologies/*.md (for dbt projects)
- **Status**: ✅ Required
- **Issues**: #78 (computational research methodologies), #79 (data access policy enforcement)

**agents/strategist.md**
- **Purpose**: Planning, zero-friction information extraction, task prioritization
- **Loaded by**: When strategist agent is invoked
- **References**: base.md, scripts.md
- **Auto-loads**: data/goals/*.md, data/context/*.md, data/views/*.json
- **Status**: ✅ Required
- **Issues**: #75 (prioritization framework), #77 (task summary guidance)

**agents/academic_writer.md**
- **Purpose**: Academic prose expansion with source fidelity
- **Loaded by**: When academic_writer agent is invoked
- **References**: base.md, STYLE.md (external)
- **Status**: ✅ Required
- **Issues**: -

**agents/documenter.md**
- **Purpose**: Documentation creation and maintenance
- **Loaded by**: When documenter agent is invoked
- **References**: base.md, STYLE.md (external), WRITING-STYLE-EXTRACTOR.md
- **Status**: ✅ Required
- **Issues**: -

**agents/mentor.md**
- **Purpose**: Strategic guidance (read-only tools)
- **Loaded by**: When mentor agent is invoked
- **References**: base.md
- **Status**: ✅ Required
- **Issues**: -

**agents/TRAINER.md**
- **Purpose**: Meta-agent for improving other agents, includes Design Principles & Decision Framework
- **Loaded by**: When trainer agent is invoked
- **References**: base.md, LLM client docs (external)
- **Status**: ✅ Required
- **Issues**: #73, #97 (silent documentation evaluation)
- **Note**: Contains evolving design philosophy consulted before all interventions

---

### Supporting Documentation (17 files)

**docs/AUTO-EXTRACTION.md**
- **Purpose**: ADHD-optimized information extraction guide
- **Loaded by**: AGENT-INSTRUCTIONS.md, INSTRUCTIONS.md
- **References**: Data file paths (external)
- **Status**: ✅ Required
- **Issues**: -

**docs/PATH-RESOLUTION.md**
- **Purpose**: Multi-machine path configuration using environment variables
- **Loaded by**: AGENT-INSTRUCTIONS.md, INSTRUCTIONS.md, SETUP.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -

**docs/SETUP.md**
- **Purpose**: Setup instructions for academicOps
- **Loaded by**: README.md
- **References**: PATH-RESOLUTION.md
- **Status**: ✅ Required
- **Issues**: -

**docs/INDEX.md**
- **Purpose**: Resource identifiers and tool locations
- **Loaded by**: INSTRUCTIONS.md, base.md
- **References**: 14 doc files
- **Status**: ✅ Required
- **Issues**: -

**docs/modes.md**
- **Purpose**: Interaction mode definitions (WORKFLOW, SUPERVISED, DEVELOPMENT)
- **Loaded by**: INSTRUCTIONS.md, base.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -
- **Shadows**: May be shadowed by parent repo docs/modes.md if used as submodule

**docs/error-quick-reference.md**
- **Purpose**: Quick error response guide
- **Loaded by**: INSTRUCTIONS.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -
- **Shadows**: May be shadowed by parent repo docs/error-quick-reference.md

**docs/error-handling.md**
- **Purpose**: Comprehensive error handling strategy
- **Loaded by**: INSTRUCTIONS.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -
- **Shadows**: May be shadowed by parent repo docs/error-handling.md

**docs/architecture.md**
- **Purpose**: academicOps architecture overview
- **Loaded by**: INSTRUCTIONS.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -
- **Shadows**: May be shadowed by parent repo docs/architecture.md (different content)

**docs/DEVELOPMENT.md**
- **Purpose**: Development workflow for academicOps itself
- **Loaded by**: INDEX.md, INSTRUCTIONS.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: -
- **Shadows**: Different from agents/developer.md (file vs agent) and parent docs/DEVELOPMENT.md

**docs/scripts.md**
- **Purpose**: Script documentation and parallel-safety notes
- **Loaded by**: strategist.md
- **References**: OMCP-EMAIL.md
- **Status**: ✅ Required
- **Issues**: #80 (email/omcp migration)

**docs/OMCP-EMAIL.md**
- **Purpose**: Outlook MCP server email interaction guide (PRIMARY method for email)
- **Loaded by**: INDEX.md, scripts.md
- **References**: None
- **Status**: ✅ Required
- **Issues**: #80 (email/omcp migration)

**docs/methodologies/computational-research.md**
- **Purpose**: Overview of academicOps approach to computational research
- **Loaded by**: analyst.md (when working on empirical projects)
- **References**: dbt-practices.md
- **Status**: ✅ Required
- **Issues**: #78 (computational research methodologies)

**docs/methodologies/dbt-practices.md**
- **Purpose**: DBT best practices and MANDATORY data access policy (no direct upstream queries)
- **Loaded by**: analyst.md (when working on dbt projects)
- **References**: None
- **Status**: ✅ Required
- **Issues**: #78 (computational research methodologies), #79 (data access policy)

**docs/WRITING-STYLE-EXTRACTOR.md**
- **Purpose**: Process for creating writing style guides
- **Loaded by**: documenter.md
- **References**: None
- **Status**: ⚠️ Optional
- **Issues**: -

**docs/configuration-hierarchy.md**
- **Purpose**: Explanation of config hierarchy system
- **Loaded by**: INDEX.md (listed but not actively loaded)
- **References**: Instruction file paths
- **Status**: ⚠️ Optional
- **Issues**: -

**docs/AGENT-INSTRUCTION-MAP.md**
- **Purpose**: Navigation map showing loading trees and file connections
- **Loaded by**: Not automatically loaded (reference documentation)
- **References**: All instruction files
- **Status**: 🔧 Maintenance tool
- **Issues**: #73

**docs/INSTRUCTION-INDEX.md** (this file)
- **Purpose**: Complete file registry with metadata
- **Loaded by**: Not automatically loaded (reference documentation)
- **References**: All instruction files
- **Status**: 🔧 Maintenance tool
- **Issues**: #73

---

### Orphaned Files (Not in Active Loading Path)

**docs/CONTEXT-EXTRACTION-ARCHITECTURE.md**
- **Purpose**: Context system design
- **Status**: ❌ Orphaned
- **Action Needed**: Link from AUTO-EXTRACTION.md or archive
- **Issues**: #73

**docs/DATA-ARCHITECTURE.md**
- **Purpose**: Data architecture
- **Status**: ❌ Orphaned
- **Action Needed**: Link from architecture.md or archive
- **Issues**: #73

**docs/DEBUGGING.md**
- **Purpose**: Debugging methodology
- **Status**: ❌ Orphaned
- **Action Needed**: Link from developer.md or archive
- **Issues**: #73

**docs/DEEP-MINING-PATTERNS.md**
- **Purpose**: Advanced extraction patterns
- **Status**: ❌ Orphaned
- **Action Needed**: Link from AUTO-EXTRACTION.md or strategist.md
- **Issues**: #73

**docs/DOCUMENTATION_MAINTENANCE.md**
- **Purpose**: Documentation maintenance guide
- **Status**: ❌ Orphaned
- **Action Needed**: Link from documenter.md
- **Issues**: #73

**docs/EXPLORATION-BEFORE-IMPLEMENTATION.md**
- **Purpose**: Pre-coding exploration requirements
- **Status**: ⚠️ Cross-referenced by projects but not in bot loading path
- **Action Needed**: Link from developer.md
- **Issues**: #73

**docs/FAIL-FAST-PHILOSOPHY.md**
- **Purpose**: Fail-fast principles
- **Status**: ❌ Orphaned
- **Action Needed**: Link from INSTRUCTIONS.md or error-handling.md
- **Issues**: #73

**docs/IMPACT-ANALYSIS.md**
- **Purpose**: Shared infrastructure analysis protocol
- **Status**: ⚠️ Cross-referenced by projects but not in bot loading path
- **Action Needed**: Link from developer.md
- **Issues**: #73

**docs/GOALS.md**
- **Purpose**: Bot goals and principles
- **Status**: ❌ Orphaned
- **Action Needed**: Link from README.md or archive
- **Issues**: #73

**docs/LOGS.md**
- **Purpose**: Logging conventions
- **Status**: ❌ Orphaned
- **Action Needed**: Link from INSTRUCTIONS.md or archive
- **Issues**: #73

**docs/TECHSTACK.md**
- **Purpose**: Technology stack
- **Status**: ❌ Orphaned
- **Action Needed**: Link from README.md or archive
- **Issues**: #73

**docs/WORKFLOW-MODE-CRITICAL.md**
- **Purpose**: Workflow mode enforcement
- **Status**: ❌ Orphaned (may duplicate modes.md)
- **Action Needed**: Consolidate with modes.md or link from INSTRUCTIONS.md
- **Issues**: #73

---

## External Files Agents Reference

academicOps agents look for these files in external contexts. Third-party users should create them as needed.

### Parent Repository (if academicOps used as submodule)

**${PARENT}/docs/INSTRUCTIONS.md**
- **When referenced**: If no project-specific instructions exist
- **Purpose**: User's global preferences across all projects
- **Overrides**: bot/docs/INSTRUCTIONS.md
- **Optional**: Yes, fallback to bot instructions

**${PARENT}/docs/STYLE.md** and **${PARENT}/docs/STYLE-QUICK.md**
- **When referenced**: By academic_writer and documenter agents
- **Purpose**: User's writing style guide
- **Overrides**: None (academicOps doesn't provide default)
- **Optional**: Yes, agents can function without

**${PARENT}/docs/modes.md**
- **When referenced**: By base.md and INSTRUCTIONS.md
- **Purpose**: Custom mode definitions
- **Overrides**: bot/docs/modes.md
- **Optional**: Yes, fallback to bot modes

**${PARENT}/data/** directory structure
- **When referenced**: By strategist and analyst agents for auto-extraction
- **Expected structure**:
  ```
  data/
  ├── goals/          # Strategic goals
  ├── projects/       # Project descriptions
  ├── tasks/          # Task management
  ├── context/        # Current priorities, planning
  └── views/          # Aggregated views
  ```
- **Optional**: Yes, but required for strategist features

### Project-Specific (in working directory)

**./docs/agent/INSTRUCTIONS.md** or **./docs/agents/INSTRUCTIONS.md**
- **When referenced**: Checked by all agents on startup
- **Purpose**: Project-specific rules that override all others
- **Overrides**: Everything (highest priority)
- **Optional**: Yes, fallback to user or bot instructions

**./README.md**
- **When referenced**: By analyst agent (auto-loads context)
- **Purpose**: Project overview and setup
- **Optional**: Recommended for analyst features

**./data/projects/{project}.md**
- **When referenced**: By analyst agent
- **Purpose**: Project context and metadata
- **Optional**: Yes, but helps analyst understand context

---

## Shadow & Override Relationships

Several files exist in multiple locations with different purposes or to allow overriding.

### docs/DEVELOPMENT.md vs agents/developer.md

**NOT duplicates** - Different purposes:
- **docs/DEVELOPMENT.md**: How to develop academicOps framework itself (meta)
- **agents/developer.md**: How the developer agent should behave when developing user code

### bot/docs/*.md vs parent/docs/*.md (when used as submodule)

**Intentional override system**:
- **bot/docs/modes.md**: Default mode definitions
- **parent/docs/modes.md** (if exists): User's custom modes (overrides bot)

Same pattern for:
- error-handling.md
- error-quick-reference.md
- architecture.md (but different content - bot architecture vs user architecture)

### Project-Specific vs Bot Instructions

**Complete override hierarchy**:
1. **./docs/agent/INSTRUCTIONS.md** (project) - Highest priority
2. **parent/docs/INSTRUCTIONS.md** (user global) - Medium priority
3. **bot/docs/INSTRUCTIONS.md** (framework) - Lowest priority (fallback)

---

## Maintenance Protocol

### For Agent Trainers

When modifying instruction files:

1. **Update this index** with any new files or changed purposes
2. **Run orphan checker**: `python scripts/check_instruction_orphans.py`
3. **Link new files**: Add references from parent files in loading hierarchy
4. **Update issues**: Reference relevant GitHub issues in file entries
5. **Commit together**: Index + instruction changes in same commit

### For File-to-Issue Mapping

**Manual method** (current):
- Add issue numbers in this index when files are related to issues
- Search codebase for issue references: `grep -r "#73" docs/`

**Automated option** (future):
- Use GitHub API to query issues mentioning files
- Script: `gh api graphql -f query='{...}'` to find file references
- Could auto-generate issue links in this index

### CI/CD Integration

The orphan checker runs automatically on:
- Pull requests modifying instruction files
- Pushes to main branch

Fails CI if critical orphans found (files in `agents/`, `docs/INSTRUCTIONS.md`, etc.)

---

## Quick Maintenance Commands

```bash
# Check for orphaned files
python scripts/check_instruction_orphans.py

# Find all references to a specific file
grep -r "filename.md" docs/ agents/

# Find files never referenced
# (Output of orphan checker)

# Search GitHub issues mentioning a file
gh issue list --repo user/repo --search "filename.md"
```

---

## Version History

- **2025-01-07**: Created comprehensive index with loading trees, orphan tracking, CI/CD integration (#73)
