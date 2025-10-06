# Agent Instruction Map

**Purpose**: Complete reference showing which agents read which instruction files and when.

**Maintenance**: Update this file when adding new agents, instruction files, or changing loading patterns.

---

## Quick Reference

### Agent List (8 Total)

**Core Agents** (bot/agents/):
- `base` - Default workflow execution
- `developer` - Code development, testing, debugging
- `analyst` - Data analysis and insights
- `strategist` - Planning and information extraction
- `academic_writer` - Academic prose expansion
- `documenter` - Documentation maintenance
- `mentor` - Strategic guidance (read-only)
- `trainer` - Meta-agent for improving other agents

**Project-Specific Agents**:
- Buttermilk: `debugger`, `tester` (functional agents defined in docs/agents/*.md)
- WikiJuris: None defined (uses core agents only)

---

## Instruction Loading Hierarchy

### Universal Loading Pattern (ALL Agents)

Every agent follows this mandatory hierarchy:

1. **CLAUDE.md Entry Point** (Project root or bot root)
   - Parent repo: `/writing/CLAUDE.md` → `docs/INSTRUCTIONS.md`
   - Bot submodule: `/writing/bot/CLAUDE.md` → `bot/docs/INSTRUCTIONS.md`
   - Projects: `{project}/CLAUDE.md` → `{project}/docs/agent/INSTRUCTIONS.md`

2. **Hierarchical Override System** (from base.md)
   - Project-specific: `./docs/agents/INSTRUCTIONS.md` (if exists) **SUPERSEDES ALL**
   - Global preferences: `${OUTER}/docs/agents/INSTRUCTIONS.md` (if exists)
   - Base agents: `${OUTER}/bot/agents/{agent_name}.md` (fallback)

3. **Additional Context** (loaded as needed)
   - Project context: `docs/projects/{project}.md`
   - Cross-cutting concerns: `docs/CROSS_CUTTING_CONCERNS.md`
   - Writing style: `docs/STYLE.md` or `docs/STYLE-QUICK.md`

---

## Instruction File Inventory

### Parent Repository (/writing/)

#### Entry Points
- `CLAUDE.md` → Points to `docs/INSTRUCTIONS.md`

#### Core Instructions
- **`docs/INSTRUCTIONS.md`** - Complete parent repo instructions
  - Loaded by: ALL agents working in parent repo
  - Contains: Scope detection, project context system, modes, auto-extraction
  - References: Multiple supporting docs below

#### Supporting Documentation
- **`docs/INDEX.md`** - Resource identifiers and tool locations
- **`docs/modes.md`** - Interaction mode definitions
- **`docs/accommodations.md`** - User needs and preferences
- **`docs/STYLE.md`** - Comprehensive writing style guide
- **`docs/STYLE-QUICK.md`** - Quick style reference
- **`docs/AGENT_HIERARCHY.md`** - Agent system overview
- **`docs/DEVELOPMENT.md`** - Development workflow rules
- **`docs/architecture.md`** - System architecture
- **`docs/error-handling.md`** - Error handling strategy
- **`docs/error-quick-reference.md`** - Quick error responses
- **`docs/EMAIL.md`** - Email processing workflow
- **`docs/STRATEGY.md`** - Strategic planning guidance
- **`docs/CROSS_CUTTING_CONCERNS.md`** - Cross-project dependencies

#### Project Context (Cross-Project Coordination)
- **`docs/projects/INDEX.md`** - Project registry
- **`docs/projects/{project}.md`** - Per-project context (7 files):
  - automod.md, buttermilk.md, mediamarkets.md, osbchatmcp.md, tja.md, wikijuris.md, zotmcp.md

#### Workflow Documentation
- **`docs/workflows/INDEX.md`** - Workflow index
- **`docs/workflows/daily-planning.md`**
- **`docs/workflows/idea-capture.md`**
- **`docs/workflows/project-creation.md`**
- **`docs/workflows/strategy.md`**
- **`docs/workflows/weekly-review.md`**

### Bot Submodule (/writing/bot/)

#### Entry Points
- `README.md` - Core axioms and quick reference
- `CLAUDE.md` → Points to `bot/docs/INSTRUCTIONS.md`

#### Core Instructions
- **`docs/INSTRUCTIONS.md`** - Bot-specific core instructions
  - Loaded by: ALL agents working in bot submodule
  - Contains: Workflow mode, error handling, path resolution, git operations
  - References: All supporting docs below

#### Agent Definitions (bot/agents/)
- **`base.md`** - Base agent with core operational principles
  - Loaded by: Base agent, inherited by all agents
  - Contains: Hierarchical instructions, workflow rules, data boundaries, submodule independence
  - Critical sections: Rules 1-11 that ALL agents must follow

- **`developer.md`** - Development agent
  - Loaded by: Developer agent
  - Contains: Debugging methodology, polyrepo constraints, development workflow
  - Critical sections: Rush-to-code prevention, exploration mandate, testing requirements

- **`analyst.md`** - Analysis agent
  - Loaded by: Analyst agent
  - Contains: Automatic context loading (README files, project overviews)
  - Critical sections: Primary workflow for analysis tasks

- **`strategist.md`** - Strategic planning agent
  - Loaded by: Strategist agent
  - Contains: Session initialization protocol, zero-friction capture, task management
  - Critical sections: Deep mining patterns, state reconciliation

- **`academic_writer.md`** - Academic writing agent
  - Loaded by: Academic writer agent
  - Contains: Expansion protocol, source fidelity rules, verification checklist
  - Critical sections: What CAN/CANNOT do, quality control

- **`documenter.md`** - Documentation agent
  - Loaded by: Documenter agent
  - Contains: Quality standards, single source of truth, style guides
  - Critical sections: Workflow for creating/updating docs

- **`mentor.md`** - Strategic mentor agent
  - Loaded by: Mentor agent
  - Contains: Socratic guidance, pattern recognition, intervention protocols
  - Tools: Read-only (Glob, Grep, Read, WebFetch, TodoWrite)

- **`trainer.md`** - Meta-agent for training other agents
  - Loaded by: Trainer agent
  - Contains: Agent performance responsibility, GitHub workflow, git submodule operations
  - Critical sections: Scope of work, reflection framework, documentation standards

#### Supporting Documentation
- **`docs/AGENT-INSTRUCTIONS.md`** - Core operational guide
  - Referenced by: base.md, all agent definitions
  - Contains: Project structure, security rules, extraction patterns, tool matrix

- **`docs/INDEX.md`** - Documentation index
- **`docs/PATH-RESOLUTION.md`** - Path configuration system
- **`docs/AUTO-EXTRACTION.md`** - ADHD-optimized extraction guide
- **`docs/CONTEXT-EXTRACTION-ARCHITECTURE.md`** - Context system design
- **`docs/DEEP-MINING-PATTERNS.md`** - Advanced extraction patterns
- **`docs/WRITING-STYLE-EXTRACTOR.md`** - Style guide creation process
- **`docs/EXPLORATION-BEFORE-IMPLEMENTATION.md`** - Pre-coding exploration requirements
- **`docs/IMPACT-ANALYSIS.md`** - Shared infrastructure analysis
- **`docs/FAIL-FAST-PHILOSOPHY.md`** - Fail-fast principles
- **`docs/WORKFLOW-MODE-CRITICAL.md`** - Workflow mode enforcement
- **`docs/DEBUGGING.md`** - Debugging methodology
- **`docs/DOCUMENTATION_MAINTENANCE.md`** - Doc maintenance guide
- **`docs/architecture.md`** - Bot architecture
- **`docs/error-handling.md`** - Bot error handling
- **`docs/error-quick-reference.md`** - Bot quick error reference
- **`docs/configuration-hierarchy.md`** - Config hierarchy
- **`docs/scripts.md`** - Script documentation
- **`docs/LOGS.md`** - Logging conventions
- **`docs/GOALS.md`** - Bot goals and principles
- **`docs/TECHSTACK.md`** - Technology stack
- **`docs/DEVELOPMENT.md`** - Bot development guide
- **`docs/DATA-ARCHITECTURE.md`** - Data architecture
- **`docs/SETUP.md`** - Setup instructions

### Project: Buttermilk (/writing/projects/buttermilk/)

#### Entry Points
- `CLAUDE.md` → Points to `docs/agent/INSTRUCTIONS.md`

#### Core Instructions
- **`docs/agent/INSTRUCTIONS.md`** - Buttermilk-specific instructions
  - Loaded by: ALL agents when working in Buttermilk
  - Contains: Critical failure modes, testing protocols, validation rules, debugging workflow
  - Critical sections: Standalone validation prohibition, fail-fast enforcement, shared infrastructure rules

- **`docs/AGENT_INSTRUCTIONS.md`** - Alternative instruction file (appears duplicate)

#### Functional Agent Definitions
- **`docs/agents/debugger.md`** - Debug Pipeline Manager
  - Type: Operational persona (not in bot/agents/)
  - Contains: Live debugging protocols, tool hierarchy, configuration validation
  - Tools: ws_debug_cli.py, buttermilk_logs.py, Playwright MCP

- **`docs/agents/debugging.md`** - Debugging golden path guide
  - Type: Documentation (not agent definition)
  - Contains: Validated debugging workflow, tool commands, success criteria

- **`docs/agents/tester.md`** - Test Fixer Agent
  - Type: Operational persona
  - Contains: Testing philosophy, fixture usage, command reference

#### Supporting Documentation
- **`docs/README.md`** - Buttermilk overview
- **`docs/bots/INDEX.md`** - Bot documentation index
- **`docs/bots/config.md`** - Configuration guide
- **`docs/bots/data-architecture.md`** - Buttermilk data architecture
- **`docs/bots/techstack.md`** - Tech stack
- **`docs/bots/TEST_FIXER_AGENT.md`** - Test fixing protocol
- **`docs/bots/exploration-before-implementation.md`** - Exploration requirements
- **`docs/bots/impact-analysis.md`** - Impact analysis protocol
- **`docs/TESTING_PHILOSOPHY.md`** - Testing philosophy
- **`docs/TEST_FIXING_PATTERNS.md`** - Test fixing patterns
- **`docs/testing/BOUNDARY_MOCKING.md`** - Mocking guidelines
- **`docs/reference/*.md`** - Technical reference docs
  - cloud_infrastructure_setup.md
  - concepts.md
  - job_queue.md
  - llm_agent.md
  - osb_vector_database_guide.md
  - tracing.md
  - vector_database_guide.md
  - zotero_vectordb_guide.md

### Project: WikiJuris (/writing/projects/wikijuris/)

#### Entry Points
- `CLAUDE.md` → Points to `docs/agent/INSTRUCTIONS.md` (NOTE: Path mismatch - CLAUDE.md says `docs/agents/INSTRUCTIONS.md` but file is at `docs/agent/INSTRUCTIONS.md`)

#### Core Instructions
- **`docs/agent/INSTRUCTIONS.md`** - WikiJuris-specific instructions
  - Loaded by: ALL agents when working in WikiJuris
  - Contains: Editorial guidelines, workflow types, formatting standards, git workflow
  - Critical sections: Content treatment, legal analysis focus, quality standards

---

## Agent-to-File Matrix

### All Agents (Universal)

**Always Load** (based on working directory):
1. Entry point CLAUDE.md → primary INSTRUCTIONS.md
2. Hierarchical override check (project → global → base)
3. Agent-specific file from bot/agents/{name}.md

### Agent: base

**Core Files**:
- bot/agents/base.md (agent definition)
- bot/docs/AGENT-INSTRUCTIONS.md (referenced)
- docs/modes.md (referenced for mode constraints)
- docs/INDEX.md (for tool lookup)

**Working Directory Context**:
- If in parent repo: docs/INSTRUCTIONS.md
- If in bot/: bot/docs/INSTRUCTIONS.md
- If in project: {project}/docs/agent/INSTRUCTIONS.md

### Agent: developer

**Core Files**:
- bot/agents/developer.md (agent definition)
- All base agent files (inherits from base)
- bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md (mandatory before coding)
- bot/docs/IMPACT-ANALYSIS.md (before modifying shared files)

**Project-Specific**:
- Buttermilk: docs/agent/INSTRUCTIONS.md (critical failure modes, testing protocols)
- WikiJuris: docs/agent/INSTRUCTIONS.md (editorial guidelines)

**References**:
- GitHub issues (always check before starting work)

### Agent: analyst

**Core Files**:
- bot/agents/analyst.md (agent definition)
- All base agent files

**Auto-Load Context** (from analyst.md):
1. README.md files in current directory and parents
2. data/README.md
3. data/projects/{project}.md (corresponding project overview)

**Working Directory Context**:
- Project-specific INSTRUCTIONS.md if exists

### Agent: strategist

**Core Files**:
- bot/agents/strategist.md (agent definition)
- All base agent files
- bot/docs/AUTO-EXTRACTION.md (comprehensive extraction guide)
- bot/docs/DEEP-MINING-PATTERNS.md (advanced patterns)
- bot/docs/scripts.md (tool documentation)

**Session Initialization** (auto-load silently):
1. data/goals/*.md (strategic priorities)
2. data/context/current-priorities.md
3. data/context/future-planning.md
4. data/context/accomplishments.md
5. Recently modified files in data/projects/
6. data/views/current_view.json (when tasks mentioned)

**Working Directory Context**:
- Parent repo: docs/INSTRUCTIONS.md (auto-extraction rules)

### Agent: academic_writer

**Core Files**:
- bot/agents/academic_writer.md (agent definition)
- All base agent files

**Writing Style** (referenced when drafting):
- docs/STYLE-QUICK.md (for most tasks)
- docs/STYLE.md (for deep writing)

**Working Directory Context**:
- Project-specific INSTRUCTIONS.md if exists

### Agent: documenter

**Core Files**:
- bot/agents/documenter.md (agent definition)
- All base agent files
- bot/docs/DOCUMENTATION_MAINTENANCE.md (maintenance guide)

**Writing Style** (referenced when creating docs):
- docs/STYLE-QUICK.md (for most tasks)
- docs/STYLE.md (for substantial content)
- bot/docs/WRITING-STYLE-EXTRACTOR.md (if creating style guide)

**Working Directory Context**:
- Project-specific INSTRUCTIONS.md if exists

### Agent: mentor

**Core Files**:
- bot/agents/mentor.md (agent definition)
- All base agent files

**Investigation** (reads as needed):
- Project documentation
- GitHub issues
- Architecture files
- Relevant code via Glob/Grep

**Constraints**:
- Read-only tools (no Write, Edit, or Bash)
- Uses ExitPlanMode to deliver recommendations

### Agent: trainer

**Core Files**:
- bot/agents/trainer.md (agent definition)
- All base agent files
- LLM client documentation (referenced for security/config)

**Target Files** (modifies as needed):
- bot/agents/*.md (agent definitions)
- bot/docs/*.md (supporting documentation)
- .claude/settings.json (Claude Code config)
- .gemini/settings.json (Gemini CLI config)

**References**:
- GitHub issues in academicOps (ALL training issues tracked centrally)
- Official docs: docs.claude.com, google-gemini.github.io

**Git Workflow**:
- Works in bot/ submodule
- Must use `cd /home/nic/src/writing/bot && git add ... && git commit ... && git push` (single command chain)

### Buttermilk Functional Agents

**debugger** (Debug Pipeline Manager):
- docs/agents/debugger.md (definition)
- docs/agents/debugging.md (golden path guide) - **MUST read FIRST**
- docs/agent/INSTRUCTIONS.md (project rules)
- Uses: ws_debug_cli.py, buttermilk_logs.py, Playwright MCP
- GitHub issues (required for all findings)

**tester** (Test Fixer Agent):
- docs/agents/tester.md (definition)
- docs/agent/INSTRUCTIONS.md (project rules)
- docs/TESTING_PHILOSOPHY.md (philosophy)
- docs/bots/TEST_FIXER_AGENT.md (protocol)
- Uses: pytest, ruff, existing fixtures

---

## File Categories

### Entry Points (3)
- Parent CLAUDE.md → docs/INSTRUCTIONS.md
- Bot CLAUDE.md → bot/docs/INSTRUCTIONS.md
- Project CLAUDE.md → {project}/docs/agent/INSTRUCTIONS.md

### Agent Definitions (8 core + project-specific)
- bot/agents/base.md
- bot/agents/developer.md
- bot/agents/analyst.md
- bot/agents/strategist.md
- bot/agents/academic_writer.md
- bot/agents/documenter.md
- bot/agents/mentor.md
- bot/agents/trainer.md
- projects/buttermilk/docs/agents/debugger.md (functional)
- projects/buttermilk/docs/agents/tester.md (functional)

### Primary Instructions (3)
- docs/INSTRUCTIONS.md (parent repo)
- bot/docs/INSTRUCTIONS.md (bot submodule)
- bot/docs/AGENT-INSTRUCTIONS.md (core operational guide)

### Project-Specific Instructions (2)
- projects/buttermilk/docs/agent/INSTRUCTIONS.md
- projects/wikijuris/docs/agent/INSTRUCTIONS.md

### Supporting Documentation (~50+ files)
- Mode definitions, workflows, error handling
- Writing style guides
- Technical architecture
- Tool documentation
- Project context files

---

## Critical Dependencies

### Referenced by ALL Agents
- Entry point CLAUDE.md
- Primary INSTRUCTIONS.md (repo-specific)
- bot/agents/base.md (core rules)
- bot/docs/AGENT-INSTRUCTIONS.md (operational guide)

### Referenced by Multiple Agents
- docs/STYLE.md, docs/STYLE-QUICK.md (writer, documenter)
- bot/docs/AUTO-EXTRACTION.md (strategist, base references)
- docs/modes.md (base, all agents check mode)
- docs/INDEX.md (base references for tool lookup)
- GitHub issues (developer, trainer, debugger)

### Agent-Specific Critical Files
- developer → EXPLORATION-BEFORE-IMPLEMENTATION.md, IMPACT-ANALYSIS.md
- strategist → AUTO-EXTRACTION.md, DEEP-MINING-PATTERNS.md, scripts.md
- analyst → Project README files, data/projects/*.md
- trainer → LLM client docs, bot/agents/*.md
- debugger → debugging.md (golden path)
- tester → TESTING_PHILOSOPHY.md, TEST_FIXER_AGENT.md

---

## Gaps and Issues Identified

### 1. Path Inconsistencies
- WikiJuris CLAUDE.md references `docs/agents/INSTRUCTIONS.md` but file is at `docs/agent/INSTRUCTIONS.md`

### 2. Duplicate/Overlapping Files
- Buttermilk has both `docs/agent/INSTRUCTIONS.md` and `docs/AGENT_INSTRUCTIONS.md`
- Multiple error-handling docs: parent docs/error-*.md and bot/docs/error-*.md
- Multiple architecture docs: parent docs/architecture.md and bot/docs/architecture.md

### 3. Missing Links
- No clear documentation on when to use debugger vs tester agents in Buttermilk
- Project context files (docs/projects/*.md) referenced but loading mechanism unclear
- Auto-extraction patterns in bot/docs/ not clearly linked from parent docs/INSTRUCTIONS.md

### 4. Documentation Debt
- Some files may be outdated (need verification):
  - bot/docs/WORKFLOW-MODE-CRITICAL.md (separate from modes.md?)
  - Duplicate INDEX.md files (docs/INDEX.md vs bot/docs/INDEX.md)

### 5. Unlinked Files
Files found but not clearly referenced in agent loading:
- docs/PROJECT_SETUP.md
- docs/EMAIL-TRIAGE-DESIGN.md
- bot/docs/DATA-ARCHITECTURE.md (referenced by Buttermilk but in bot/)
- Various workflow files in docs/workflows/ (some may be unused)

---

## Maintenance Protocol

### When Adding New Agents
1. Create agent definition in bot/agents/{name}.md
2. Update this map with agent's file dependencies
3. Update bot/README.md agent list
4. Create GitHub issue in academicOps documenting the addition

### When Adding New Instruction Files
1. Determine scope (parent, bot, project)
2. Add references to relevant agent definitions
3. Update this map
4. Verify no duplication with existing files

### When Modifying Instruction Hierarchy
1. Update CLAUDE.md entry points if needed
2. Update base.md hierarchical override rules if changed
3. Update this map
4. Test with agents in different contexts

### Regular Maintenance
- Quarterly: Review for outdated files
- After major changes: Verify all links still valid
- When files removed: Update all references and this map
