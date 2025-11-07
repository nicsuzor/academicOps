<!-- LEGACY FILE: Being phased out in favor of bot/agents/INSTRUCTIONS.md and docs/agents/INSTRUCTIONS.md -->
<!-- This file is NO LONGER loaded automatically. Core instructions now loaded via validate_env.py hook. -->
<!-- See bot/docs/ARCHITECTURE.md for new loading hierarchy. -->

# LEGACY: Agent Instructions (docs/INSTRUCTIONS.md)

**⚠️ DEPRECATED**: This file is being phased out. Core instructions now loaded via:

1. `bot/agents/_CORE.md` (generic rules)
2. `docs/agents/INSTRUCTIONS.md` (user-specific context)

**New architecture**: See `bot/docs/ARCHITECTURE.md`

---

## Remaining Content (To Be Migrated or Removed)

## Content Preserved Below (Legacy Reference)

The following sections remain as reference but should be migrated to appropriate locations:

## MANDATORY: Scope Detection and Context Loading

**Before ANY work**, agents MUST execute this startup sequence:

### 1. Detect Current Location

```bash
# Detect project name from current working directory
pwd | grep -oE 'projects/[^/]+' | cut -d/ -f2 || \
pwd | grep -oE 'papers/[^/]+/[^/]+' | rev | cut -d/ -f1 | rev || \
echo "parent_repo"
```

### 2. Load Project Registry

```bash
cat docs/projects/INDEX.md
```

**REQUIRED**: Understand project types, dependencies, and relationships.

### 3. Load Project Context (if in submodule)

```bash
cat docs/projects/{project_name}.md
```

**REQUIRED**: Understand project-specific constraints, dependencies, and protocols.

### 4. Check Cross-Cutting Concerns (for infrastructure changes)

```bash
cat docs/CROSS_CUTTING_CONCERNS.md
```

**REQUIRED for**:

- Any changes to `buttermilk` (affects 4 dependent projects)
- Data schema changes (BigQuery, dbt)
- Deployment architecture changes
- MCP protocol changes

### 5. HALT Conditions

Agents MUST halt and request user approval when:

**Automatic Halts**:

- [ ] Breaking changes to buttermilk API
- [ ] Schema changes to shared BigQuery tables
- [ ] Changes to golden datasets (TJA articles, etc.)
- [ ] Deployment to production without tests passing
- [ ] Deletion of data or models
- [ ] Project not found in registry

**Warning Conditions** (proceed with testing):

- [ ] Compatible buttermilk changes → test all dependents
- [ ] dbt model refactoring → version and test
- [ ] Docker architecture divergence → document reason

### 6. Auto-Update on Completion

After significant changes, call:

```bash
bot/scripts/project_sync.py --project {project_name} --event {event_type} --message "{description}"
```

**Event types**:

- `commit`: Code changes
- `milestone`: Feature completion, deployment
- `test_status`: Test results
- `breaking_change`: API/schema breaking changes

**Examples**:

```bash
# After deploying
uv run bot/scripts/project_sync.py --project zotmcp --event deployment --message "MCP server v2.1"

# After tests pass
uv run bot/scripts/project_sync.py --project buttermilk --event test_status --message "PASS (245/245)"

# After breaking change
uv run bot/scripts/project_sync.py --project buttermilk --event breaking_change --message "Agent API refactor"
```

## Project Context System

**Purpose**: Bridge strategic planning and execution layers across 7 projects.

**Files**:

- `docs/projects/INDEX.md` - Registry of all projects
- `docs/projects/{project}.md` - Technical context for each project (7 files)
- `docs/CROSS_CUTTING_CONCERNS.md` - Dependency graph and change protocols
- `bot/scripts/project_sync.py` - Auto-update mechanism

**Key Principle**: Parent repo owns cross-project context. Submodules stay clean.

**See**: Issue #64 for complete design and rationale.

## INTERACTION MODES

You operate in distinct modes. **ALWAYS start in WORKFLOW MODE**.

- [Modes](modes.md): Strict guidelines for when and how to operate

**CRITICAL**: In WORKFLOW MODE, you MUST follow established workflows exactly. NO improvisation. NO workarounds. NO skipping steps. HALT on ALL errors.

## WORKFLOW DECISION TREE

```
1. READ context & verify assumptions
2. CHECK current mode (default: WORKFLOW)
3. IF executing workflow:
   → Follow EVERY step in sequence
   → STOP at ANY failure
   → WAIT for user instruction
4. IF no workflow exists:
   → Request permission to switch to SUPERVISED MODE
5. IF in SUPERVISED MODE:
   → Execute ONLY what user explicitly requests
6. IF blocked:
   → Report exact issue and wait for guidance
```

## 📚 DOCUMENTATION INDEX

**Core References** (read when needed):

- [INDEX.md](INDEX.md): Agent tools and resource identifiers
- [Accommodations](accommodations.md): User needs, work style, communication preferences
- [Error Quick Reference](error-quick-reference.md): What to do when things go wrong

**Development Resources**:

- [DEVELOPMENT.md](DEVELOPMENT.md): CRITICAL - read before ANY development work
- [Architecture](architecture.md): Where everything goes and how components fit together
- [Error Handling Strategy](error-handling.md): Systematic failure handling

## SECURITY - DATA BOUNDARIES

**CRITICAL**: `bot/` = PUBLIC (GitHub), everything else = PRIVATE

**NEVER**:

- ❌ Copy private content into bot/ (would leak to GitHub)
- ❌ Include personal examples in bot/docs/
- ❌ Embed task content or project names in bot/

**ALWAYS**:

- ✅ Reference private content from bot/ (`See ../docs/...`)
- ✅ Keep bot/ generic - usable by ANY user
- ✅ Store personal data in data/, docs/, projects/

## PROJECT ISOLATION

**CRITICAL**: Projects must be self-contained and work independently.

**Project-Specific Content Location**:

- ❌ NEVER: `docs/projects/{project}/` (parent repo)
- ❌ NEVER: References to parent repos (academicOps, writing)
- ❌ NEVER: Relative paths outside project (e.g., `../../writing/`)
- ✅ ALWAYS: Inside project repo (e.g., `projects/buttermilk/docs/`)

**Rationale**:

- Projects may be cloned/used independently
- External users shouldn't need parent repo context
- Clean separation enables portability and reuse

**Parent Repo vs Project Repo**:

- `docs/projects/*.md` - Cross-project coordination ONLY (dependencies, impacts)
- `projects/{name}/docs/` - All project-specific implementation details

## FAIL FAST - ERROR HANDLING

When ANY error occurs:

1. **STOP IMMEDIATELY** - No recovery attempts
2. **REPORT EXACTLY** - "Step [N] failed: [exact error]"
3. **WAIT FOR INSTRUCTION** - Do not proceed

**NEVER**:

- ❌ "I'll fix this by..."
- ❌ "Let me try a different approach..."
- ❌ Continue with partial completion

## AUTO-EXTRACTION (ADHD-OPTIMIZED)

**Extract information DURING conversation, not after**:

- Tasks with deadlines → `data/tasks/inbox/`
- Project updates → `data/projects/*.md`
- Goals → `data/goals/*.md`
- Use `bot/scripts/task_add.py` for task creation

**Principles**:

1. Extract immediately, don't ask for clarification
2. Infer when unclear - better to capture with assumptions
3. Maintain conversation flow
4. Save everything - tasks, projects, deadlines, contacts

**See**: Auto-extraction details below

### Repository Structure

```
$ACADEMIC_OPS_ROOT/            # This parent repository (PRIVATE)
├── data/                      # Personal task/project database
│   ├── goals/                 # Strategic goals
│   ├── projects/              # Active projects
│   ├── tasks/                 # Task management
│   └── views/                 # Aggregated views
├── docs/                      # System documentation
├── projects/                  # Academic project submodules
└── bot/                       # Public submodule (nicsuzor/academicOps)
    ├── scripts/               # Automation tools
    ├── agents/                # Agent definitions
    └── docs/                  # Generic agent documentation
```

### Extraction Patterns

**CRITICAL DISTINCTION: Projects vs Tasks**:

- **Project files** (`data/projects/*.md`): Strategic descriptions, goals, stakeholders
- **Task files** (`data/tasks/*.md`): Specific actionable items with deadlines
- **NEVER** embed tasks in project descriptions - create separate task files
- When user mentions action items, CREATE TASK FILES, don't update project files

**Mode-Specific Behaviors**:

- **Email Processing**: Extract sender info, tasks, deadlines, updates
- **Strategy Mode**: Update projects, create goals, link tasks
- **Meeting Mode**: Capture action items without interrupting flow

**Conversation Thread Management**:

- **TRACK INCOMPLETE ITEMS**: Before switching topics, note unresolved questions
- **RETURN TO THREADS**: After handling interruptions, check for dropped items
- **EXPLICIT CONFIRMATION**: When user provides clarification, update ALL affected files

### Path Resolution

Use environment variables for all paths:

- `$ACADEMIC_OPS_DATA` - Data directory
- `$ACADEMIC_OPS_SCRIPTS` - Scripts directory
- `$ACADEMIC_OPS_DOCS` - Documentation directory

### Writing Style

When drafting content in the author's voice, consult:

- **Quick reference**: `docs/STYLE-QUICK.md` (for most tasks)
- **Comprehensive guide**: `docs/STYLE.md` (for deep writing tasks)

## CORE RULES

1. **ALWAYS FOLLOW THE WORKFLOW**
2. **VERIFY FIRST, ASSUME NEVER, and ASK IF NOT EXPLICITLY GIVEN**
3. **NEVER mark a task as completed if any component failed**
