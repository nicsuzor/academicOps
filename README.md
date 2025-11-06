# academicOps Agent Framework

**Modular, hierarchical agent framework for rigorous, context-aware automation in academic research projects.**

**Status**: PUBLIC repository, used as git submodule in personal/project repositories.

---

## Purpose

academicOps provides infrastructure for AI agent workflows that require:

- **Fail-fast philosophy** - No fallbacks, no defensive programming, infrastructure that works
- **DRY compliance** - Single source of truth via modular chunks and symlinks
- **Anti-bloat enforcement** - Hard limits on file sizes, architectural solutions over instructions
- **Experiment-driven development** - All changes tested and measured
- **Three-tier loading** - Framework → personal → project instruction hierarchy

**This README defines the desired state.** See `docs/AUDIT.md` for current compliance status.

---

## Core Principles (Invariants)

### 1. Fail-Fast Philosophy

**Scripts/hooks/config > instructions** (reliability hierarchy)

- Infrastructure works perfectly, or fails immediately
- No defensive programming, no error recovery, no workarounds
- Agents stop on errors, trainers fix root causes

**Source**: `chunks/AXIOMS.md` Axiom #7

### 2. DRY (Don't Repeat Yourself)

**One canonical source per concept**

- If content appears in >1 place → BUG
- Reference via @notation or symlinks
- Default: DELETE documentation rather than add

**Enforcement**: Modular `chunks/` + `resources/` symlinks

### 3. Anti-Bloat by Design

**Hard limits enforced**:

- Skills: SKILL.md <300 lines
- Agents: Instructions <500 lines
- Adding >10 lines requires GitHub issue + approval

**Before adding >5 lines, verify**:
- No architectural solution (scripts/hooks/config)?
- No existing content to reference?
- Not repeating chunks/ or BEST-PRACTICES.md?
- Bullet points, not prose?
- Specific instructions, not vague?

**Source**: `skills/skill-creator/SKILL.md`, `docs/bots/BEST-PRACTICES.md`

### 4. Experiment-Driven Development

**We don't know until we test**

- Every change requires experiment log (`experiments/YYYY-MM-DD_name.md`)
- Single variable per experiment
- Explicit success criteria
- Document outcomes: Success/Failure/Partial
- Keep/revert/iterate based on measurements

**No speculation**. Test, measure, decide.

### 5. Modular Architecture

**Chunks system**:

```
chunks/FILE.md (single source)
    ↓ @reference from core/_CORE.md (agents via SessionStart)
    ↓ symlink to skills/*/resources/FILE.md (skills load explicitly)
```

**Benefits**:
- Skills get framework context without SessionStart hooks
- Zero duplication
- Live integration tests verify infrastructure

**Source**: `ARCHITECTURE.md`, `tests/test_chunks_loading.py`

### 6. Knowledge Organization (bmem)

**Vector search + relational mapping for documentation and tasks**

**basic-memory** (internal ref: `bmem`) provides:
- Just-in-time concept loading via vector search (<2s)
- Relational mapping between concepts
- Task management with markdown + YAML frontmatter
- Cross-repository context building

**Integration**:
- MCP server: `mcp__basic-memory__*` tools
- Projects: `aops` ($ACADEMICOPS), `ns` ($ACADEMICOPS_PERSONAL)
- Storage: Markdown files + SQLite graph
- Access pattern: Search → load relevant concepts only

**Benefits**:
- Reduced SessionStart token cost (load on-demand vs load-all)
- Documentation discoverability via vector search
- Learning loops (agents update concepts from experiment outcomes)
- Unified knowledge graph across framework + personal repos

**Status**: Integration in progress (Issue #193)

**Source**: `chunks/INFRASTRUCTURE.md`, Issue #193

---

## Components & Capabilities

Quick reference for what tools to use for what tasks. See ARCHITECTURE.md for technical specifications.

### Core Instructions (Auto-loaded)

```
core/
├── _CORE.md              # References chunks/ - Universal axioms
├── DEVELOPMENT.md        # Development standards
├── TESTING.md            # Testing requirements
├── DEBUGGING.md          # Debugging workflow
└── STYLE.md              # Writing style guide

chunks/                   # Shared context modules (symlinked to skills)
├── AXIOMS.md             # Universal principles (fail-fast, DRY, experiment-driven)
├── INFRASTRUCTURE.md     # Framework paths, env vars, bmem integration
├── AGENT-BEHAVIOR.md     # Conversational rules
└── SKILL-PRIMER.md       # Skill execution context
```

### Agents (Specialized Workflows)

Invoke via Task tool or slash commands. Load specific instructions + orchestrate skills.

```
agents/
├── ANALYST.md            # Data analysis, experimental evaluation with academic rigor
├── DEVELOPER.md          # Code writing, refactoring, testing, debugging
├── STRATEGIST.md         # Strategic planning, task review, context navigation
├── SUPERVISOR.md         # Multi-agent workflow orchestration with quality gates
├── scribe.md             # Silent task/context extraction from conversations
├── task-manager.md       # EXPERIMENTAL: Email-to-task extraction
└── end-of-session.md     # Automated commit + accomplishment capture
```

### Slash Commands (User Shortcuts)

Quick invocations that load workflows. Type `/command` to activate.

```
commands/
├── /analyst              # Load analyst skill for data analysis (dbt & Streamlit)
├── /dev                  # Load development workflow and coding standards
├── /email                # Check email, update task DB, present digest
├── /error                # Quick experiment outcome logging
├── /log-failure          # Log agent performance failure
├── /ops                  # academicOps framework help
├── /STRATEGIST           # Strategic facilitation with silent context capture
└── /trainer              # Activate agent trainer mode
```

### Skills (Reusable Expertise)

Installed to `~/.claude/skills/`. Invoked by agents or directly.

**Framework Skills** (academicOps-specific):
```
├── agent-initialization  # Workspace setup, skill index generation
├── aops-bug              # Bug tracking, experiment logs, architecture drift
├── aops-trainer          # Agent optimization, anti-bloat enforcement
├── claude-hooks          # Hook creation, configuration, debugging
├── claude-md-maintenance # CLAUDE.md refactoring, @reference enforcement
├── skill-creator         # Create/maintain skills with anti-bloat principles
└── skill-maintenance     # Audit/update skills to current framework patterns
```

**Development Skills**:
```
├── git-commit            # Validated commits with quality gates
├── github-issue          # Exhaustive issue search, documentation, lifecycle
├── test-writing          # TDD with integration tests, real configs/data
└── no-throwaway-code     # Intervention: nudge toward reusable solutions
```

**Utility Skills**:
```
├── analyst               # Academic research data analysis (dbt + Streamlit)
├── archiver              # Archive experiments to Jupyter notebooks with HTML
├── email                 # Outlook MCP integration, triage, signal detection
├── markdown-ops          # Enforce academicOps + bmem markdown structure
├── pdf                   # Convert markdown → professional PDFs
├── scribe                # Silent knowledge base maintenance
├── strategic-partner     # Strategic facilitation, thinking partnership
├── tasks                 # Task management operations (create, view, update, archive)
└── tja-research          # TJA research methodology tracing
```

### Hooks (Runtime Enforcement)

Automated checks at key moments. Configured in `.claude/settings.json`.

```
hooks/
├── load_instructions.py      # SessionStart: Load 3-tier context hierarchy
├── validate_tool.py          # PreToolUse: Check permissions before tool execution
├── validate_stop.py          # Stop: Validate workflow completion
├── stack_instructions.py     # PostToolUse: Conditional loading on file reads
├── autocommit_tasks.py       # PostToolUse: Auto-commit task DB changes
└── log_*.py                  # Various: Debug logging and state tracking
```

### Documentation

```
docs/
├── bots/                     # Agent development context (SessionStart loaded)
│   ├── BEST-PRACTICES.md     # Evidence-based guidance (Anthropic + experiments)
│   ├── skills-inventory.md   # Skill catalog with invocation guide
│   └── INDEX.md              # Navigation to all framework docs
│
├── _CHUNKS/                  # Domain-specific documentation
│   ├── HYDRA.md, PYTHON-DEV.md, DBT.md
│   ├── SEABORN.md, STATSMODELS.md, STREAMLIT.md
│   └── E2E-TESTING.md, FAIL-FAST.md, GIT-WORKFLOW.md
│
├── AUDIT.md                  # Current state vs desired state
└── INSTRUCTION-INDEX.md      # Complete file registry (SHOWN vs REFERENCED)
```

### Quick Reference: Which Tool When

| Task | Use This |
|------|----------|
| Extract tasks from conversation | **scribe** skill (auto-invoke proactively) |
| Commit code changes | **git-commit** skill |
| Data analysis (dbt/Streamlit) | **analyst** agent (via `/analyst`) |
| Write/refactor/debug code | **dev** agent (via `/dev`) |
| Strategic planning | **STRATEGIST** agent (via `/STRATEGIST`) |
| Check/process email | **email** skill (via `/email`) |
| Create/update tasks | **tasks** skill |
| Generate PDFs | **pdf** skill |
| Multi-step complex workflows | **supervisor** agent |
| Track framework bugs | **aops-bug** skill |
| Optimize agents/skills | **aops-trainer** skill (via `/trainer`) |
| Convert markdown to PDF | **pdf** skill |
| Archive experiments | **archiver** skill |
| Work with GitHub issues | **github-issue** skill |
| Write tests | **test-writing** skill |
| Knowledge organization (bmem) | Use bmem MCP tools (search, write, read notes) |

---
---

## Three-Tier Instruction Loading

**SessionStart hook loads instructions from three tiers**:

```
Framework tier    ($ACADEMICOPS/core/_CORE.md, docs/bots/INDEX.md)
    ↓
Personal tier     ($ACADEMICOPS_PERSONAL/docs/bots/*.md)
    ↓
Project tier      ($PWD/docs/bots/*.md)
```

Each tier can override or extend the previous tier, allowing customization while maintaining framework defaults.

---

## Key References

- **Core axioms**: `chunks/AXIOMS.md`, `core/_CORE.md`
- **Best practices**: `docs/bots/BEST-PRACTICES.md` (evidence-based guidance)
- **Architecture**: `ARCHITECTURE.md` (technical specifications)
- **Testing**: `docs/TESTING.md`, `tests/`
- **Current state**: `docs/AUDIT.md`
- **Skill creation**: `skills/skill-creator/SKILL.md`
- **Agent optimization**: `skills/aops-trainer/SKILL.md`

---

## Quick Start

```bash
# Set environment
export ACADEMICOPS=/path/to/academicOps

# Install via setup script
$ACADEMICOPS/scripts/setup_academicops.sh

# Launch Claude Code
claude
```

**First time**: SessionStart hook auto-loads `core/_CORE.md`. Slash commands are ready to use.

---

## License

Apache 2.0 - See LICENSE file

---

**This README is the authoritative user guide.** See `ARCHITECTURE.md` for technical specifications and `docs/AUDIT.md` for current compliance status.

**Last updated**: 2025-11-06
