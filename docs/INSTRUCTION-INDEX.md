# academicOps Instruction Index

**Purpose**: Complete reference for all instruction files in the academicOps framework.

**Audience**: Third-party users who have adopted academicOps as a standalone repository.

**Maintenance**: Auto-checked by CI/CD. Run `scripts/check_instruction_orphans.py` to verify no orphans.

---

## Quick Reference

- **What is this file for?** → See [File Registry](#file-registry)
- **How do agents load instructions?** → See [Loading System](#loading-system)
- **What files do I need in my repo?** → See [Setup Requirements](#setup-requirements)
- **What changed recently?** → See [Migration Notes](#migration-notes-2025-10-18)

---

## Loading System

### Single Instruction Loading Pathway

academicOps uses a **simplified 3-tier hierarchy** where all agents load `_CORE.md` from all three levels at SessionStart.

**No project-specific slash commands. No complex discovery. Just one clear path.**

### SessionStart Hook Chain

Claude Code starts session
    ↓
SessionStart hook triggers
    ↓
load_instructions.py executes
    ↓
Calls: read_instructions.py _CORE.md
    ↓
Loads from 3 tiers:
    1. $ACADEMICOPS_BOT/agents/_CORE.md      (required)
    2. $ACADEMICOPS_PERSONAL/agents/_CORE.md (optional)
    3. $PROJECT/agents/_CORE.md              (optional)
    ↓
Output to user (stdout): "Loaded _CORE.md: ✓ bot ✓ personal ✓ project"
Output to agent (stderr): Full text of all 3 files
    ↓
Agent has complete context

### Agent-Specific Loading

When you invoke `@agent-{name}`:

1. SessionStart instructions already loaded (`_CORE.md` from all 3 tiers)
2. Agent-specific file loads: `$ACADEMICOPS_BOT/agents/{NAME}.md`

**Example**: `@agent-developer`

- Already has: `_CORE.md` (core axioms + user context + project context)
- Loads: `DEVELOPER.md` (developer-specific workflows)

### Priority Order

**Highest to Lowest:**

1. **Project** (`$PROJECT/agents/_CORE.md`) - Project-specific rules
2. **Personal** (`$ACADEMICOPS_PERSONAL/agents/_CORE.md`) - User global preferences
3. **Bot** (`$ACADEMICOPS_BOT/agents/_CORE.md`) - Framework defaults

Later files can reference or override earlier ones.

### Fail-Fast Behavior

- **At least ONE `_CORE.md` must exist** (blocks with exit code 1 if all missing)
- Missing files at any tier are silently skipped
- No fallbacks, no defaults, no guessing

---

## File Registry

Complete list of instruction files with metadata.

### Format

- **Purpose**: What this file does
- **Loaded by**: What triggers loading this file
- **References**: What other files it points to
- **Status**: ✅ Required | ⚠️ Optional | 🔧 Maintenance | ❌ Archived

---

## Entry Points (2 files)

### CLAUDE.md

- **Path**: `$ACADEMICOPS_BOT/CLAUDE.md`
- **Purpose**: Entry point for Claude Code agents
- **Content**: Single line: `Read \`./agents/_CORE.md\` for core axioms and project instructions.`
- **Loaded by**: AI agent on startup (automatic)
- **References**: `agents/_CORE.md`
- **Status**: ✅ Required

### GEMINI.md

- **Path**: `$ACADEMICOPS_BOT/GEMINI.md`
- **Purpose**: Entry point for Gemini CLI agents
- **Loaded by**: AI agent on startup (automatic)
- **References**: `agents/_CORE.md`
- **Status**: ⚠️ Optional (experimental)

---

## Core Instructions (1 file)

### agents/_CORE.md

- **Path**: `$ACADEMICOPS_BOT/agents/_CORE.md`
- **Purpose**: Core axioms and inviolable rules for ALL agents
- **Loaded by**: SessionStart hook → `load_instructions.py` → `read_instructions.py`
- **Content**:
- Core Axioms (fail-fast, DRY, no fallbacks, etc.)
- Repository structure
- Key tools and policies
- Error handling philosophy
- **References**: None (this is the foundation)
- **Status**: ✅ Required (blocking if missing)
- **Issues**: #119 (modular configuration architecture)

**External Versions** (loaded by same mechanism):

- `$ACADEMICOPS_PERSONAL/agents/_CORE.md` - User global preferences
- `$PROJECT/agents/_CORE.md` - Project-specific context

---

## Agent Definitions (5 files)

### agents/TRAINER.md

- **Path**: `$ACADEMICOPS_BOT/agents/TRAINER.md`
- **Purpose**: Meta-agent for framework maintenance and optimization
- **Loaded by**: `/trainer` slash command OR `@agent-trainer` invocation
- **Content**:
- Agent performance responsibility
- Fail-fast enforcement checklist
- Design principles & decision framework
- Modular documentation architecture
- Enforcement hierarchy (scripts > hooks > config > instructions)
- GitHub issue management protocol
- Instruction index maintenance workflow
- **References**: LLM client docs (Claude Code, Gemini CLI)
- **Status**: ✅ Required
- **Issues**: #111 (modularity), #119 (configuration architecture)

### agents/STRATEGIST.md

- **Path**: `$ACADEMICOPS_BOT/agents/STRATEGIST.md`
- **Purpose**: Planning, task prioritization, context extraction
- **Loaded by**: `@agent-strategist` invocation
- **Content**:
- Zero-friction information extraction
- Task management workflows
- Planning and scheduling
- Auto-extraction patterns
- **Auto-loads**: `data/goals/*.md`, `data/context/*.md`, `data/views/*.json`
- **References**: `_CORE.md` (inherits)
- **Status**: ✅ Required
- **Issues**: #75 (prioritization framework), #77 (task summary guidance)

### agents/DEVELOPER.md

- **Path**: `$ACADEMICOPS_BOT/agents/DEVELOPER.md`
- **Purpose**: Software development workflow, debugging, testing
- **Loaded by**: `@agent-developer` invocation
- **Content**:
- TDD methodology
- Interface mismatch checkpoint
- Debugging workflows
- Testing patterns
- **References**: `_CORE.md` (inherits)
- **Status**: ✅ Required
- **Issues**: #88 (localized fix without impact analysis)

### agents/CODE.md

- **Path**: `$ACADEMICOPS_BOT/agents/CODE.md`
- **Purpose**: Code review and git commit operations
- **Loaded by**: `@agent-code-review` invocation
- **Content**:
- Code quality validation
- Git commit workflow
- Pre-commit hook execution
- Pull request creation
- **References**: `_CORE.md` (inherits)
- **Status**: ✅ Required

### agents/ANALYST.md

- **Path**: `$ACADEMICOPS_BOT/agents/ANALYST.md`
- **Purpose**: Data analysis, dbt workflows, SQL optimization
- **Loaded by**: `@agent-analyst` invocation
- **Content**:
- MANDATORY dbt-only data access policy
- Computational research methodologies
- Data pipeline patterns
- **Auto-loads**: `README.md`, `data/README.md`, `data/projects/*.md`, `docs/methodologies/*.md`
- **References**: `_CORE.md`, `docs/methodologies/dbt-practices.md`, `docs/methodologies/computational-research.md`
- **Status**: ✅ Required
- **Issues**: #78 (computational research), #79 (data access enforcement)

---

## Framework Documentation (4 files)

### ARCHITECTURE.md

- **Path**: `$ACADEMICOPS_BOT/ARCHITECTURE.md`
- **Purpose**: System overview, design philosophy, loading mechanisms
- **Loaded by**: Not auto-loaded (reference documentation)
- **Content**:
- Single instruction loading pathway
- Agent responsibilities
- Validation & enforcement system
- Setup process
- Migration notes
- **References**: All major system components
- **Status**: 🔧 Maintenance (this file)
- **Issues**: #119 (reflects new simplified architecture)

### docs/INSTRUCTION-INDEX.md (this file)

- **Path**: `$ACADEMICOPS_BOT/docs/INSTRUCTION-INDEX.md`
- **Purpose**: Complete file registry with metadata
- **Loaded by**: Not auto-loaded (reference documentation)
- **References**: All instruction files
- **Status**: 🔧 Maintenance
- **Issues**: #119 (updated for new structure)

### docs/hooks_guide.md

- **Path**: `$ACADEMICOPS_BOT/docs/hooks_guide.md`
- **Purpose**: Hook system documentation and usage guide
- **Loaded by**: Referenced by trainer agent
- **Status**: ⚠️ Optional

### README.md

- **Path**: `$ACADEMICOPS_BOT/README.md`
- **Purpose**: Repository overview, quick start, installation
- **Loaded by**: Referenced from parent INSTRUCTIONS.md files
- **References**: ARCHITECTURE.md, setup instructions
- **Status**: ✅ Required

---

## Methodologies (2 files)

### docs/methodologies/computational-research.md

- **Path**: `$ACADEMICOPS_BOT/docs/methodologies/computational-research.md`
- **Purpose**: academicOps approach to computational research
- **Loaded by**: `agents/ANALYST.md` (when working on empirical projects)
- **References**: `dbt-practices.md`
- **Status**: ✅ Required
- **Issues**: #78 (computational research methodologies)

### docs/methodologies/dbt-practices.md

- **Path**: `$ACADEMICOPS_BOT/docs/methodologies/dbt-practices.md`
- **Purpose**: DBT best practices and MANDATORY data access policy
- **Loaded by**: `agents/ANALYST.md` (when working on dbt projects)
- **Content**: No direct upstream queries - dbt models only
- **Status**: ✅ Required
- **Issues**: #78 (methodologies), #79 (data access policy enforcement)

---

## Scripts (8 critical files)

### scripts/load_instructions.py

- **Path**: `$ACADEMICOPS_BOT/scripts/load_instructions.py`
- **Purpose**: SessionStart hook that triggers instruction loading
- **Loaded by**: Claude Code SessionStart hook (automatic)
- **Behavior**: Calls `read_instructions.py _CORE.md` and formats output for Claude
- **Exit codes**: 0 (success), 1 (all files missing)
- **Status**: ✅ Required (blocking)
- **Issues**: #119 (simplified to call read script)

### scripts/read_instructions.py

- **Path**: `$ACADEMICOPS_BOT/scripts/read_instructions.py`
- **Purpose**: Unified 3-tier instruction file reader
- **Loaded by**: `load_instructions.py` OR manual invocation
- **Usage**: `read_instructions.py <filename>`
- **Behavior**:
- Reads `<filename>` from bot, personal, project levels
- stdout: User-friendly colored status
- stderr: Full instruction text for agent
- Exit 1 if ALL files missing
- **Status**: ✅ Required (blocking)
- **Issues**: #119 (new script for simplified loading)

### scripts/validate_tool.py

- **Path**: `$ACADEMICOPS_BOT/scripts/validate_tool.py`
- **Purpose**: PreToolUse hook for enforcing tool restrictions
- **Loaded by**: Claude Code PreToolUse hook (automatic)
- **Rules Enforced**:
- Protected file modifications (`.claude/*`, `.gemini/*`)
- No new documentation files (prevents bloat)
- Python requires `uv run` prefix
- Inline Python blocked
- Git commits warn for non-code-review agents
- `/tmp` files blocked (violates replication axiom)
- **Exit codes**: 0 (allow), 1 (warn), 2 (block)
- **Status**: ✅ Required
- **Issues**: Fixed in Issue #119 (hook syntax corrected)

### scripts/validate_stop.py

- **Path**: `$ACADEMICOPS_BOT/scripts/validate_stop.py`
- **Purpose**: SubagentStop and Stop hooks
- **Loaded by**: Claude Code Stop hooks (automatic)
- **Status**: ✅ Required

### scripts/setup_academicops.sh

- **Path**: `$ACADEMICOPS_BOT/scripts/setup_academicops.sh`
- **Purpose**: Setup script for installing academicOps in new projects
- **Usage**: `./scripts/setup_academicops.sh [target-directory]`
- **Creates**:
- `.claude/settings.json` (from `dist/.claude/settings.json`)
- `.claude/agents/` (symlinked to academicOps)
- `agents/_CORE.md` (from `dist/agents/INSTRUCTIONS.md` template)
- `.academicOps/scripts/` (symlinked validation scripts)
- `.gitignore` updates
- **Verifies**: Environment variables, load_instructions.py exists
- **Status**: ✅ Required
- **Issues**: #119 (updated to create `_CORE.md` and deploy scripts to `.academicOps/`)

### scripts/check_instruction_orphans.py

- **Path**: `$ACADEMICOPS_BOT/scripts/check_instruction_orphans.py`
- **Purpose**: Validates instruction files are properly linked
- **Usage**: `python scripts/check_instruction_orphans.py`
- **Behavior**: Fails CI if critical files are orphaned
- **Status**: 🔧 Maintenance
- **Issues**: #73 (orphan tracking)

### scripts/code_review.py

- **Path**: `$ACADEMICOPS_BOT/scripts/code_review.py`
- **Purpose**: Code quality validation rules
- **Loaded by**: Code review agent
- **Status**: ⚠️ Optional

### scripts/check_test_architecture.py

- **Path**: `$ACADEMICOPS_BOT/scripts/check_test_architecture.py`
- **Purpose**: Test file location validation (pre-commit hook)
- **Status**: ⚠️ Optional

---

## Configuration Templates (3 files)

### dist/.claude/settings.json

- **Path**: `$ACADEMICOPS_BOT/dist/.claude/settings.json`
- **Purpose**: Template Claude Code settings for new projects
- **Copied to**: `$PROJECT/.claude/settings.json` by setup script
- **Content**:
- Permission rules (allow, deny patterns)
- Hook definitions (SessionStart, PreToolUse, Stop)
- Hook paths use `.academicOps/scripts/` (local symlinks)
- **Status**: ✅ Required (template)
- **Issues**: #119 (hook paths updated to use `.academicOps/scripts/`)

### dist/agents/INSTRUCTIONS.md

- **Path**: `$ACADEMICOPS_BOT/dist/agents/INSTRUCTIONS.md`
- **Purpose**: Template for project `_CORE.md` files
- **Copied to**: `$PROJECT/agents/_CORE.md` by setup script
- **Content**: Placeholder project instructions
- **Status**: ✅ Required (template)
- **Issues**: #119 (used as `_CORE.md` template)

### dist/.gitignore

- **Path**: `$ACADEMICOPS_BOT/dist/.gitignore`
- **Purpose**: academicOps exclusions to add to project `.gitignore`
- **Appended by**: `setup_academicops.sh`
- **Status**: ✅ Required (template)

---

## Slash Commands (2 active)

### .claude/commands/trainer.md

- **Path**: `$ACADEMICOPS_BOT/.claude/commands/trainer.md`
- **Purpose**: Activate trainer agent mode
- **Loads**: `agents/TRAINER.md`
- **Status**: ✅ Required

### .claude/commands/log-failure.md

- **Path**: `$ACADEMICOPS_BOT/.claude/commands/log-failure.md`
- **Purpose**: Log agent performance failures to experiment tracking
- **Status**: ✅ Required
- **Issues**: #118 (experiment tracking enforcement)

### REMOVED Commands (migrated to project `_CORE.md`)

- `/mm` - MediaMarkets analysis mode → `$PROJECT/agents/_CORE.md`
- `/bm` - Buttermilk development mode → `$PROJECT/agents/_CORE.md`
- `/tja` - TJA analysis mode → `$PROJECT/agents/_CORE.md`

**Rationale**: Project context now auto-loads. No need for dedicated commands.

---

## Archived Files (32+ files)

### docs/_UNUSED/

- **Path**: `$ACADEMICOPS_BOT/docs/_UNUSED/`
- **Purpose**: Archived obsolete documentation
- **Status**: ❌ Archived (not referenced in active loading paths)
- **Issues**: #111 (Phase 2 cleanup)
- **Contents**:
- Obsolete architecture docs (superseded by ARCHITECTURE.md)
- Deprecated agent templates
- Outdated indexes and references
- Project-specific content (moved out)

**Do not reference these files** - they are obsolete.

---

## External Files (Project/Personal Level)

These files exist in external repositories and are loaded by the same mechanisms.

### $ACADEMICOPS_PERSONAL/agents/_CORE.md

- **When referenced**: SessionStart (if `ACADEMICOPS_PERSONAL` set)
- **Purpose**: User's global preferences across all projects
- **Overrides**: `$ACADEMICOPS_BOT/agents/_CORE.md`
- **Optional**: Yes (skipped with warning if missing)

### $PROJECT/agents/_CORE.md

- **When referenced**: SessionStart (always checked)
- **Purpose**: Project-specific rules and context
- **Overrides**: Both bot and personal `_CORE.md`
- **Optional**: Yes (skipped silently if missing)
- **Created by**: `setup_academicops.sh` (from template)

### $PROJECT/.claude/settings.json

- **When referenced**: Claude Code startup (automatic)
- **Purpose**: Project-level Claude Code configuration
- **Created by**: `setup_academicops.sh` (copied from `dist/.claude/settings.json`)
- **Status**: ✅ Required for Claude Code projects

### $PROJECT/.academicOps/scripts/*.py

- **When referenced**: By hooks (SessionStart, PreToolUse, Stop)
- **Purpose**: Local deployment of validation scripts
- **Created by**: `setup_academicops.sh` (symlinked from `$ACADEMICOPS_BOT/scripts/`)
- **Contains**: `load_instructions.py`, `validate_tool.py`, `validate_stop.py`, `hook_models.py`
- **Status**: ✅ Required for hook execution

### $PROJECT/.claude/commands/*.md

- **When referenced**: When user invokes `/command-name`
- **Purpose**: Project-specific slash commands (if truly needed)
- **Optional**: Yes (most projects won't need this)

---

## Setup Requirements

### Environment Variables

**Required:**

```bash
export ACADEMICOPS_BOT=/path/to/academicOps

Optional:
export ACADEMICOPS_PERSONAL=/path/to/writing  # User global context

Add to ~/.bashrc, ~/.zshrc, etc.

Installation Steps

1. Set environment variables (see above)
2. Run setup script:
cd $PROJECT
$ACADEMICOPS_BOT/scripts/setup_academicops.sh
3. Customize agents/_CORE.md for your project
4. Launch Claude Code from project directory
5. Verify core instructions load at session start

Files Created by Setup

- .claude/settings.json - Claude Code configuration
- .claude/agents/ - Symlink to academicOps agents
- agents/_CORE.md - Project context (from template)
- .academicOps/scripts/ - Symlinked validation scripts
- .gitignore updates - Excludes academicOps managed files

---
Migration Notes (2025-10-18)

What Changed (Issue #119)

From: Complex multi-tier submodule architecture with project-specific slash commands

To: Simplified 3-tier _CORE.md loading with single instruction pathway

Changes:
1. ✅ Renamed INSTRUCTIONS.md → _CORE.md at all levels
2. ✅ Created read_instructions.py for unified 3-tier loading
3. ✅ Updated load_instructions.py to call read script
4. ✅ Removed project-specific slash commands (/mm, /bm, /tja)
5. ✅ Migrated slash command content to project _CORE.md files
6. ✅ Updated setup_academicops.sh to create _CORE.md template
7. ✅ Setup script now deploys validation scripts to .academicOps/scripts/ via symlinks
8. ✅ Hook paths updated to use .academicOps/scripts/ (local deployment)
9. ✅ Fixed .claude/agents symlink (was circular, now correct)

Migration Path for Existing Projects

If you have /mm, /bm, /tja commands:
1. Copy command content to $PROJECT/agents/_CORE.md
2. Delete the slash command files
3. Verify project context loads at SessionStart

If you have agents/INSTRUCTIONS.md:
1. Rename to agents/_CORE.md
2. Content remains the same
3. Update any references in documentation

To adopt new local script deployment:
1. Run setup_academicops.sh in your project
2. Verify .academicOps/scripts/ directory created with symlinks
3. Update .claude/settings.json hook paths to use .academicOps/scripts/

---
Maintenance Protocol

For Agent Trainers

When modifying instruction files:

1. Update this index with new files or changed purposes
2. Run orphan checker: python scripts/check_instruction_orphans.py
3. Link new files: Add references from parent files
4. Update ARCHITECTURE.md: Reflect structural changes
5. Document in GitHub: Link to relevant issues
6. Commit together: Index + instruction changes in same commit

Orphan Detection

Manual check:
python scripts/check_instruction_orphans.py

CI/CD integration:
- Runs automatically on PRs modifying instruction files
- Fails CI if critical files orphaned

File-to-Issue Mapping

Current method: Manual annotation in this index

Future automation: GitHub API queries for file references

---
Success Metrics

System is working when:
- All projects have agents/_CORE.md (verified by setup script)
- SessionStart loads 3-tier hierarchy automatically
- No orphaned instruction files (CI passes)
- ARCHITECTURE.md accurately reflects system
- This index is up-to-date with all active files
- No project-specific slash commands needed (context auto-loads)
- .academicOps/scripts/ contains validation scripts in all projects
