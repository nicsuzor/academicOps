# academicOps Instruction Index

**Purpose**: Complete reference for all instruction files in the academicOps framework.

**Audience**: Third-party users who have adopted academicOps as a standalone repository.

**Maintenance**: Auto-checked by CI/CD. Run `scripts/check_instruction_orphans.py` to verify no orphans.

---

## Quick Reference

- **What do agents automatically know?** → See [What Agents Actually See](#what-agents-actually-see)
- **What is this file for?** → See [File Registry](#file-registry)
- **How do agents load instructions?** → See [Loading System](#loading-system)
- **What files do I need in my repo?** → See [Setup Requirements](#setup-requirements)
- **What changed recently?** → See [Migration Notes](#migration-notes-2025-10-18)

## TL;DR - What Agents Know vs Don't Know

**Agents AUTOMATICALLY SEE at session start (SHOWN):**
- `agents/_CORE.md` from all 3 tiers (framework/personal/project) - FULL TEXT
- Git repository info
- That's it.

**Agents DON'T know unless explicitly told (REFERENCED):**
- This INSTRUCTION-INDEX.md
- Other agent files (DEVELOPER.md, ANALYST.md, etc.)
- Documentation files (ARCHITECTURE.md, hooks_guide.md, etc.)
- What hooks are configured
- What slash commands exist
- Directory structure

**How agents discover additional context:**
1. User says "Read docs/INSTRUCTION-INDEX.md"
2. User invokes slash command like `/trainer` (loads agents/trainer.md)
3. References in `_CORE.md` suggest reading specific files

---

## What Agents Actually See

### Critical Distinction: Shown vs Referenced

**SHOWN = Full text injected into agent context (they MUST read it)**
**REFERENCED = Mentioned/suggested but NOT loaded (agents MIGHT read it IF they choose)**

This distinction is critical for understanding what agents know vs what they can discover.

---

## Loading System

### SessionStart: What Every Agent Gets (SHOWN)

When Claude Code starts, the SessionStart hook (`hooks/load_instructions.py`) AUTOMATICALLY loads and INJECTS full text into every agent's context:

**1. Git Repository Info** (if in a git repo)
   - Git remote origin URL

**2. agents/_CORE.md from all 3 tiers** (stacked in priority order)
   - `$PROJECT/agents/_CORE.md` (Project-specific, HIGHEST priority)
   - `$ACADEMICOPS_PERSONAL/agents/_CORE.md` (User global preferences)
   - `$ACADEMICOPS_BOT/agents/_CORE.md` (Framework defaults, REQUIRED)

**Format in agent context:**
```
# Agent Instructions

## REPOSITORY
Git remote origin: git@github.com:...

---

## PROJECT: Current Project Context
[Full text of $PROJECT/agents/_CORE.md]

---

## PERSONAL: Your Work Context
[Full text of $ACADEMICOPS_PERSONAL/agents/_CORE.md]

---

## FRAMEWORK: Core Rules
[Full text of $ACADEMICOPS_BOT/agents/_CORE.md]
```

**What agents know at session start:**
- Core axioms and behavioral rules
- Repository they're working in
- User's global preferences and context
- Project-specific context and rules
- **THEY DO NOT KNOW:** What other instruction files exist, what hooks are configured, what the INSTRUCTION-INDEX contains

### Slash Commands: Additional Context Loading (SHOWN)

Slash commands can load additional instruction files using the same 3-tier system:

**Example:** `/trainer` command loads `agents/trainer.md`

1. Command executes: `uv run python ${ACADEMICOPS_BOT}/hooks/load_instructions.py trainer.md`
2. Agent receives FULL TEXT from all available tiers (project → personal → framework)
3. This supplements (doesn't replace) the `_CORE.md` already loaded at SessionStart

**Format:**
```
# === PROJECT: trainer.md ===
[Full text if exists]

# === PERSONAL: trainer.md ===
[Full text if exists]

# === FRAMEWORK: trainer.md ===
[Full text - REQUIRED]
```

### What Agents DON'T Automatically Know (REFERENCED)

Unless explicitly loaded via slash command, agents have NO KNOWLEDGE of:

- **This INSTRUCTION-INDEX.md** - They don't know what files exist or where things are documented
- **docs/hooks_guide.md** - They don't know how hooks work
- **Other agent files** (DEVELOPER.md, ANALYST.md, etc.) - Until loaded via slash command
- **Chunked instructions** (docs/_CHUNKS/*) - Unless symlinked into agents/ and loaded
- **Hook configuration** - They don't see config/settings.json
- **Available slash commands** - They don't get a command list

**How they discover these:**
1. **Explicit user instruction** - "Read docs/INSTRUCTION-INDEX.md"
2. **References in _CORE.md** - "See docs/X.md for details"
3. **Trial and error** - Running commands and seeing if they exist

### Priority Order (When Same File Exists in Multiple Tiers)

**Highest to Lowest:**

1. **Project** (`$PROJECT/agents/`) - Overrides everything
2. **Personal** (`$ACADEMICOPS_PERSONAL/agents/`) - Overrides framework defaults
3. **Framework** (`$ACADEMICOPS_BOT/agents/`) - Base defaults

All three are shown to agents (stacked). Later tiers can reference or override earlier ones.

### Fail-Fast Behavior

- **Framework tier REQUIRED** - Blocks with exit code 1 if `$ACADEMICOPS_BOT/agents/_CORE.md` missing
- **Other tiers optional** - Silently skipped if missing (no errors)
- **No fallbacks, no defaults, no guessing**

---

## File Registry

Complete list of instruction files with visibility metadata.

### Format

- **Purpose**: What this file does
- **Visibility**: 🔴 SHOWN (auto-loaded, full text) | 🔵 REFERENCED (agents must explicitly read) | 🟡 INFRASTRUCTURE (hooks/config)
- **Loaded by**: What triggers loading this file
- **References**: What other files it points to
- **Status**: ✅ Required | ⚠️ Optional | 🔧 Maintenance | ❌ Archived

---

## Entry Points (2 files)

### CLAUDE.md

- **Path**: `$ACADEMICOPS_BOT/CLAUDE.md`
- **Purpose**: Initial entry point that Claude Code reads, then defers to SessionStart hook
- **Visibility**: 🔵 REFERENCED (Claude reads this first, but actual loading happens via SessionStart hook)
- **Content**: Points to `agents/_CORE.md` and includes repository info
- **Loaded by**: Claude Code startup (automatic, before SessionStart hook)
- **References**: `agents/_CORE.md`
- **Status**: ✅ Required
- **Note**: This is a vestigial mechanism - the real loading happens via SessionStart hook

### GEMINI.md

- **Path**: `$ACADEMICOPS_BOT/GEMINI.md`
- **Purpose**: Entry point for Gemini CLI agents
- **Visibility**: 🔵 REFERENCED
- **Loaded by**: Gemini CLI on startup (automatic)
- **References**: `agents/_CORE.md`
- **Status**: ⚠️ Optional (experimental)

---

## Core Instructions (1 file)

### agents/_CORE.md

- **Path**: `$ACADEMICOPS_BOT/agents/_CORE.md`
- **Purpose**: Core axioms and inviolable rules for ALL agents
- **Visibility**: 🔴 SHOWN (auto-loaded at SessionStart, FULL TEXT injected into every agent)
- **Loaded by**: SessionStart hook → `hooks/load_instructions.py` (automatic, every session)
- **Content**:
  - Core Axioms (fail-fast, DRY, no fallbacks, etc.)
  - Behavioral Rules (NO WORKAROUNDS, VERIFY FIRST, etc.)
  - Tool Failure Protocol
  - Key tools and policies
- **References**: None (this is the foundation)
- **Status**: ✅ Required (blocks session start if missing)
- **Issues**: #119 (modular configuration architecture)

**External Versions** (also SHOWN via same mechanism):

- `$ACADEMICOPS_PERSONAL/agents/_CORE.md` - User global preferences (SHOWN if exists)
- `$PROJECT/agents/_CORE.md` - Project-specific context (SHOWN if exists)

---

## Agent Definitions (5 files)

### agents/trainer.md

- **Path**: `$ACADEMICOPS_BOT/agents/trainer.md`
- **Purpose**: Meta-agent for framework maintenance and optimization
- **Visibility**: 🔴 SHOWN (when slash command `/trainer` invoked)
- **Loaded by**: `/trainer` slash command → `hooks/load_instructions.py trainer.md`
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

### agents/DEVELOPER.md

- **Path**: `$ACADEMICOPS_BOT/agents/DEVELOPER.md`
- **Purpose**: Software development workflow, debugging, testing
- **Visibility**: 🔵 REFERENCED (agents must explicitly load via slash command or Read tool)
- **Loaded by**: Manual - no slash command currently configured
- **Content**:
  - TDD methodology
  - Interface mismatch checkpoint
  - Debugging workflows
  - Testing patterns
- **References**: `_CORE.md` (inherits)
- **Status**: ✅ Required
- **Issues**: #88 (localized fix without impact analysis)

### agents/ANALYST.md (symlink)

- **Path**: `$ACADEMICOPS_BOT/agents/ANALYST.md` → `docs/_CHUNKS/ANALYST.md`
- **Purpose**: Data analysis, dbt workflows, SQL optimization
- **Visibility**: 🔴 SHOWN (when slash command `/analyst` invoked)
- **Loaded by**: `/analyst` slash command → `hooks/load_instructions.py ANALYST.md`
- **Content**:
  - MANDATORY dbt-only data access policy
  - Computational research methodologies
  - Data pipeline patterns
- **References**: `_CORE.md`, DBT.md, TESTING.md
- **Status**: ✅ Required
- **Issues**: #78 (computational research), #79 (data access enforcement)

### Other Agent Files (symlinked to docs/_CHUNKS/)

All symlinked to docs/_CHUNKS/ for modular management:

- **DBT.md** - dbt best practices
- **E2E-TESTING.md** - End-to-end testing workflows
- **FAIL-FAST.md** - Extended fail-fast philosophy examples
- **GIT-WORKFLOW.md** - Git commit and PR workflows
- **HYDRA.md** - Hydra configuration patterns
- **TESTING.md** - Testing architecture and patterns
- **TESTS.md** - Test writing guidelines

**Visibility**: 🔵 REFERENCED (must be explicitly loaded)
**Status**: ⚠️ Optional (loaded when relevant to task)

---

## Framework Documentation (4 files)

### ARCHITECTURE.md

- **Path**: `$ACADEMICOPS_BOT/ARCHITECTURE.md`
- **Purpose**: System overview, design philosophy, loading mechanisms
- **Visibility**: 🔵 REFERENCED (agents must explicitly read)
- **Loaded by**: Never auto-loaded
- **Content**:
  - Single instruction loading pathway
  - Agent responsibilities
  - Validation & enforcement system
  - Setup process
  - Migration notes
- **References**: All major system components
- **Status**: 🔧 Maintenance
- **Issues**: #119 (reflects new simplified architecture)

### docs/INSTRUCTION-INDEX.md (this file)

- **Path**: `$ACADEMICOPS_BOT/docs/INSTRUCTION-INDEX.md`
- **Purpose**: Complete file registry with SHOWN vs REFERENCED metadata
- **Visibility**: 🔵 REFERENCED (agents don't know this exists unless told)
- **Loaded by**: Never auto-loaded
- **Content**: What agents see at session start, what files exist, how to discover additional context
- **References**: All instruction files
- **Status**: 🔧 Maintenance
- **Issues**: #119 (updated for new structure)

### docs/hooks_guide.md

- **Path**: `$ACADEMICOPS_BOT/docs/hooks_guide.md`
- **Purpose**: Hook system documentation and usage guide
- **Visibility**: 🔵 REFERENCED
- **Loaded by**: Never auto-loaded
- **Status**: ⚠️ Optional

### README.md

- **Path**: `$ACADEMICOPS_BOT/README.md`
- **Purpose**: Repository overview, quick start, installation
- **Visibility**: 🔵 REFERENCED
- **Loaded by**: Never auto-loaded
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

## Scripts (Hook Infrastructure)

All scripts are INFRASTRUCTURE - agents never see them, but they control what agents see.

### hooks/load_instructions.py

- **Path**: `$ACADEMICOPS_BOT/hooks/load_instructions.py`
- **Purpose**: SessionStart hook that loads _CORE.md from 3 tiers and injects into agent context
- **Visibility**: 🟡 INFRASTRUCTURE (agents never see this, but it determines what they DO see)
- **Loaded by**: Claude Code SessionStart hook (automatic, every session)
- **Behavior**: Loads _CORE.md from framework/personal/project tiers, outputs JSON with full text
- **Exit codes**: 0 (success), 1 (framework tier missing)
- **Status**: ✅ Required (blocks session start if fails)
- **Issues**: #119 (simplified to unified 3-tier loading)

### hooks/validate_tool.py

- **Path**: `$ACADEMICOPS_BOT/hooks/validate_tool.py`
- **Purpose**: PreToolUse hook for enforcing tool restrictions
- **Visibility**: 🟡 INFRASTRUCTURE (agents only see block/warn messages)
- **Loaded by**: Claude Code PreToolUse hook (automatic, before every tool use)
- **Rules Enforced**:
  - Protected file modifications (config/*, hooks/*)
  - No new documentation files (prevents bloat)
  - Python requires `uv run` prefix
  - Git commits warn for non-code-review agents
  - `/tmp` files blocked (violates replication axiom)
- **Exit codes**: 0 (allow), 1 (warn), 2 (block)
- **Status**: ✅ Required
- **Issues**: #119 (updated paths after refactoring)

### hooks/validate_stop.py

- **Path**: `$ACADEMICOPS_BOT/hooks/validate_stop.py`
- **Purpose**: SubagentStop and Stop hooks validation
- **Visibility**: 🟡 INFRASTRUCTURE
- **Loaded by**: Claude Code Stop hooks (automatic)
- **Status**: ✅ Required

### hooks/stack_instructions.py

- **Path**: `$ACADEMICOPS_BOT/hooks/stack_instructions.py`
- **Purpose**: PostToolUse hook for context-aware instruction loading
- **Visibility**: 🟡 INFRASTRUCTURE (may inject additional context based on tool use)
- **Loaded by**: Claude Code PostToolUse hook (automatic, after tool use)
- **Status**: ⚠️ Optional

### Logging Hooks

- **hooks/log_posttooluse.py** - Logs tool usage
- **hooks/log_userpromptsubmit.py** - Logs user prompts
- **hooks/log_sessionend.py** - Logs session end
- **hooks/log_precompact.py** - Logs context compaction
- **hooks/log_notification.py** - Logs notifications

**Visibility**: 🟡 INFRASTRUCTURE (silent logging, agents never see output)
**Status**: ⚠️ Optional (telemetry)

### Other Supporting Scripts

- **scripts/setup_academicops.sh** - Setup script for new projects
- **scripts/check_instruction_orphans.py** - CI validation for orphaned instruction files
- **scripts/code_review.py** - Code quality validation
- **scripts/check_test_architecture.py** - Test architecture validation

**Visibility**: 🟡 INFRASTRUCTURE
**Status**: 🔧 Maintenance tools

---

## Configuration (INFRASTRUCTURE)

### config/settings.json

- **Path**: `$ACADEMICOPS_BOT/config/settings.json`
- **Purpose**: Claude Code settings - defines hooks, permissions, status line
- **Visibility**: 🟡 INFRASTRUCTURE (agents never see this, but it controls their environment)
- **Content**:
  - Environment variables (ACADEMICOPS_BOT)
  - Permissions (allow/deny patterns)
  - Hook definitions (SessionStart, PreToolUse, PostToolUse, Stop, etc.)
  - Status line configuration
- **Loaded by**: Claude Code at startup (automatic)
- **Status**: ✅ Required
- **Note**: Hook paths reference `$ACADEMICOPS_BOT/hooks/` directly

### Template Files (dist/)

Distribution templates for new project setup:

- **dist/.claude/settings.json** - Legacy template (deprecated in favor of root config/)
- **dist/agents/INSTRUCTIONS.md** - Template for project `_CORE.md`
- **dist/.gitignore** - academicOps exclusions for project `.gitignore`

**Visibility**: 🟡 INFRASTRUCTURE (templates, not used directly)
**Status**: 🔧 Maintenance

---

## Slash Commands

Slash commands trigger additional instruction loading or specific workflows.

### Active Commands (7)

- **commands/trainer.md** - Loads agents/trainer.md, invokes aops-trainer skill
- **commands/analyst.md** - Loads agents/ANALYST.md for data analysis workflows
- **commands/dev.md** - Development workflow guidance (TDD, testing, debugging)
- **commands/ttd.md** - Test-driven development workflow
- **commands/STRATEGIST.md** - Strategic planning and task extraction
- **commands/ops.md** - academicOps framework help and guidance
- **commands/error.md** - Quick experiment outcome logging
- **commands/log-failure.md** - Log agent performance failures to experiment tracker

**Visibility**: 🔴 SHOWN (when invoked, loads full text of corresponding agent file)
**Status**: ✅ Required

**Mechanism**: Slash commands execute `hooks/load_instructions.py <filename>` to load additional context from 3-tier system.

### REMOVED Commands (migrated to project `_CORE.md`)

Project-specific commands removed in Issue #119:
- `/mm` - MediaMarkets → moved to project `_CORE.md`
- `/bm` - Buttermilk → moved to project `_CORE.md`
- `/tja` - TJA analysis → moved to project `_CORE.md`

**Rationale**: Project context auto-loads at SessionStart. No separate commands needed.

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
