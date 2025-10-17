# Agent Instruction Map - Loading Trees & File Registry

**Purpose**: Navigate the agent instruction system by understanding what loads what and when.

**Quick Answers**:

- "What loads this file?" → See [File Registry](#file-registry)
- "What files are orphaned?" → See [Disconnected Files](#disconnected-files)
- "How do agents load in X context?" → See [Loading Trees](#loading-trees)

---

## Loading Trees

Each tree shows the actual loading path from CLAUDE.md entry points.

### Parent Repository (${ACADEMICOPS_PERSONAL}/)

```
CLAUDE.md (Root)
├─→ docs/INSTRUCTIONS.md (PRIMARY - all parent repo agents)
│   ├─→ docs/INDEX.md (tool/resource lookup)
│   ├─→ docs/modes.md (interaction modes)
│   ├─→ docs/error-quick-reference.md (quick error responses)
│   ├─→ docs/error-handling.md (comprehensive error strategy)
│   ├─→ docs/architecture.md (system architecture)
│   ├─→ docs/DEVELOPMENT.md (development workflow)
│   ├─→ docs/accommodations.md (user preferences)
│   ├─→ docs/STYLE-QUICK.md (writing style quick ref)
│   ├─→ docs/STYLE.md (comprehensive style guide)
│   ├─→ docs/CROSS_CUTTING_CONCERNS.md (project dependencies)
│   ├─→ docs/projects/INDEX.md (project registry)
│   └─→ docs/projects/{7 project files} (project context)
│
└─→ bot/README.md (overview, referenced from INSTRUCTIONS)
    ├─→ bot/docs/AGENT-INSTRUCTIONS.md (core operational guide)
    ├─→ bot/docs/AUTO-EXTRACTION.md (extraction patterns)
    ├─→ bot/docs/PATH-RESOLUTION.md (path configuration)
    ├─→ bot/docs/SETUP.md (setup instructions)
    └─→ bot/agents/{8 agent definitions}
        ├─→ base.md
        │   ├─→ docs/INDEX.md (tool lookup)
        │   └─→ bot/docs/modes.md (mode constraints)
        ├─→ developer.md (inherits base)
        ├─→ analyst.md (inherits base)
        │   └─→ README.md files + data/projects/*.md (auto-loads context)
        ├─→ strategist.md (inherits base)
        │   ├─→ bot/docs/scripts.md (tool documentation)
        │   └─→ data/goals/*.md + data/context/*.md (session init)
        ├─→ academic_writer.md (inherits base)
        │   └─→ docs/STYLE.md, docs/STYLE-QUICK.md (writing style)
        ├─→ documenter.md (inherits base)
        │   ├─→ docs/STYLE.md, docs/STYLE-QUICK.md (writing style)
        │   └─→ bot/docs/WRITING-STYLE-EXTRACTOR.md
        ├─→ mentor.md (read-only)
        └─→ trainer.md
            └─→ Claude Code/Gemini docs (external references)
```

### Bot (${ACADEMICOPS_BOT}/)

```
bot/CLAUDE.md
└─→ bot/docs/INSTRUCTIONS.md (PRIMARY - bot context)
    ├─→ bot/docs/AGENT-INSTRUCTIONS.md (core operational guide)
    │   ├─→ bot/docs/AUTO-EXTRACTION.md
    │   └─→ bot/docs/PATH-RESOLUTION.md
    ├─→ bot/docs/INDEX.md (resource index)
    ├─→ bot/docs/modes.md
    ├─→ bot/docs/error-quick-reference.md
    ├─→ bot/docs/error-handling.md
    ├─→ bot/docs/architecture.md
    ├─→ bot/docs/DEVELOPMENT.md
    └─→ bot/docs/PATH-RESOLUTION.md
```

## File Registry

Every instruction/documentation file with connection analysis.

### Format

**File**: Path

- **Loaded by**: What explicitly loads it
- **References**: What it points to
- **Purpose**: What it's for
- **Status**: Connected/Weakly-connected/Orphaned

---

### Entry Points (4 files)

**CLAUDE.md** (parent)

- **Loaded by**: All agents in parent repo context
- **References**: docs/INSTRUCTIONS.md, bot/README.md
- **Purpose**: Entry point for parent repository
- **Status**: ✅ Connected (root)

**bot/CLAUDE.md**

- **Loaded by**: All agents in bot context
- **References**: bot/docs/INSTRUCTIONS.md
- **Purpose**: Entry point for bot submodule
- **Status**: ✅ Connected (root)


---

### Primary Instruction Files (3 files)

**docs/INSTRUCTIONS.md** (parent repo primary)

- **Loaded by**: CLAUDE.md → All agents in parent context
- **References**: 16 supporting docs (modes, INDEX, error handling, DEVELOPMENT, architecture, etc.)
- **Purpose**: Complete instructions for parent repository operations
- **Status**: ✅ Connected (primary)

**bot/docs/INSTRUCTIONS.md** (bot primary)

- **Loaded by**: bot/CLAUDE.md → All agents in bot context
- **References**: 8 supporting docs (AGENT-INSTRUCTIONS, AUTO-EXTRACTION, modes, INDEX, etc.)
- **Purpose**: Bot-specific core instructions
- **Status**: ✅ Connected (primary)

**bot/docs/AGENT-INSTRUCTIONS.md** (core operational)

- **Loaded by**: bot/README.md, bot/docs/INSTRUCTIONS.md
- **References**: AUTO-EXTRACTION.md, PATH-RESOLUTION.md, ../docs/STYLE.md
- **Purpose**: Core operational guide for all agents
- **Status**: ✅ Connected (primary)

---

### Agent Definitions (8 core + 2 project-specific)

**bot/agents/base.md**

- **Loaded by**: All agents (inherit from this)
- **References**: docs/INDEX.md, bot/docs/modes.md, agent definition files
- **Purpose**: Core rules all agents must follow
- **Status**: ✅ Connected (foundational)

**bot/agents/developer.md**

- **Loaded by**: Developer agent
- **References**: Base agent (inherits all base rules)
- **Purpose**: Development workflow, debugging methodology
- **Status**: ✅ Connected

**bot/agents/analyst.md**

- **Loaded by**: Analyst agent
- **References**: Base agent, README.md, data/projects/*.md
- **Purpose**: Data analysis with automatic context loading
- **Status**: ✅ Connected

**bot/agents/strategist.md**

- **Loaded by**: Strategist agent
- **References**: Base agent, bot/docs/scripts.md, data/goals/*.md, data/context/*.md
- **Purpose**: Planning and zero-friction information extraction
- **Status**: ✅ Connected

**bot/agents/academic_writer.md**

- **Loaded by**: Academic writer agent
- **References**: Base agent, docs/STYLE.md, docs/STYLE-QUICK.md
- **Purpose**: Academic prose expansion with source fidelity
- **Status**: ✅ Connected

**bot/agents/documenter.md**

- **Loaded by**: Documenter agent
- **References**: Base agent, docs/STYLE.md, bot/docs/WRITING-STYLE-EXTRACTOR.md
- **Purpose**: Documentation creation and maintenance
- **Status**: ✅ Connected

**bot/agents/mentor.md**

- **Loaded by**: Mentor agent
- **References**: Base agent
- **Purpose**: Strategic guidance (read-only)
- **Status**: ✅ Connected

**bot/agents/trainer.md**

- **Loaded by**: Trainer agent
- **References**: Base agent, external LLM client docs
- **Purpose**: Meta-agent for improving other agents
- **Status**: ✅ Connected

**projects/buttermilk/docs/agents/debugger.md**

- **Loaded by**: Explicitly invoked in Buttermilk context
- **References**: debugging.md (golden path)
- **Purpose**: Live debugging and validation
- **Status**: ✅ Connected (Buttermilk-specific)

**projects/buttermilk/docs/agents/tester.md**

- **Loaded by**: Explicitly invoked in Buttermilk context
- **References**: TESTING_PHILOSOPHY.md
- **Purpose**: Test maintenance and fixing
- **Status**: ✅ Connected (Buttermilk-specific)

---

### Project-Specific Instructions (2 files)

**projects/buttermilk/docs/agent/INSTRUCTIONS.md**

- **Loaded by**: Buttermilk CLAUDE.md → All agents in Buttermilk
- **References**: 7 supporting docs (TESTING_PHILOSOPHY, debugging, TEST_FIXER_AGENT, exploration, impact-analysis, INDEX, data-architecture)
- **Purpose**: Buttermilk-specific rules (testing, validation, debugging)
- **Status**: ✅ Connected (project primary)

**projects/wikijuris/docs/agent/INSTRUCTIONS.md**

- **Loaded by**: WikiJuris CLAUDE.md → All agents in WikiJuris
- **References**: None (self-contained)
- **Purpose**: WikiJuris editorial guidelines and workflows
- **Status**: ✅ Connected (project primary)

---

### Supporting Documentation - Parent Repo (13 files)

**docs/INDEX.md**

- **Loaded by**: docs/INSTRUCTIONS.md, base.md
- **References**: 12 tool/workflow files
- **Purpose**: Resource identifiers and tool locations
- **Status**: ✅ Connected

**docs/modes.md**

- **Loaded by**: docs/INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md, base.md
- **References**: None
- **Purpose**: Interaction mode definitions (WORKFLOW, SUPERVISED, DEVELOPMENT)
- **Status**: ✅ Connected

**docs/STYLE.md**

- **Loaded by**: academic_writer, documenter, AGENT-INSTRUCTIONS
- **References**: None
- **Purpose**: Comprehensive writing style guide
- **Status**: ✅ Connected

**docs/STYLE-QUICK.md**

- **Loaded by**: academic_writer, documenter, docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Quick writing style reference
- **Status**: ✅ Connected

**docs/error-quick-reference.md**

- **Loaded by**: docs/INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Quick error response guide
- **Status**: ✅ Connected

**docs/error-handling.md**

- **Loaded by**: docs/INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Comprehensive error handling strategy
- **Status**: ✅ Connected

**docs/architecture.md**

- **Loaded by**: docs/INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md
- **References**: workflows/*.md, error-handling.md
- **Purpose**: System architecture overview
- **Status**: ✅ Connected

**docs/DEVELOPMENT.md**

- **Loaded by**: docs/INSTRUCTIONS.md, docs/INDEX.md
- **References**: .md (malformed reference)
- **Purpose**: Development workflow rules
- **Status**: ✅ Connected

**docs/accommodations.md**

- **Loaded by**: docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: User needs and work style preferences
- **Status**: ✅ Connected

**docs/CROSS_CUTTING_CONCERNS.md**

- **Loaded by**: docs/INSTRUCTIONS.md (when infrastructure changes)
- **References**: data/projects/{project}.md, docs/projects/{project}.md
- **Purpose**: Cross-project dependency tracking
- **Status**: ✅ Connected

**docs/STRATEGY.md**

- **Loaded by**: docs/INDEX.md
- **References**: reviews/YYYY-MM-weekly-WW.md
- **Purpose**: Strategic planning guidance
- **Status**: ✅ Connected

**docs/AGENT_HIERARCHY.md**

- **Loaded by**: (Not explicitly loaded)
- **References**: bot/agents/*.md, instructions files
- **Purpose**: Agent system overview
- **Status**: ⚠️ Weakly connected (not in loading path)

**docs/EMAIL.md**

- **Loaded by**: docs/INDEX.md
- **References**: None
- **Purpose**: Email processing workflow
- **Status**: ✅ Connected

---

### Supporting Documentation - Bot Submodule (17 files)

**bot/docs/AUTO-EXTRACTION.md**

- **Loaded by**: bot/README.md, bot/docs/AGENT-INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md
- **References**: data file paths
- **Purpose**: ADHD-optimized extraction guide
- **Status**: ✅ Connected

**bot/docs/PATH-RESOLUTION.md**

- **Loaded by**: bot/README.md, bot/docs/AGENT-INSTRUCTIONS.md, bot/docs/INSTRUCTIONS.md, bot/docs/SETUP.md
- **References**: None
- **Purpose**: Multi-machine path configuration
- **Status**: ✅ Connected

**bot/docs/SETUP.md**

- **Loaded by**: bot/README.md
- **References**: bot/docs/PATH-RESOLUTION.md, docs/INSTRUCTIONS.md
- **Purpose**: Setup instructions
- **Status**: ✅ Connected

**bot/docs/INDEX.md**

- **Loaded by**: bot/docs/INSTRUCTIONS.md
- **References**: 14 bot doc files
- **Purpose**: Bot documentation index
- **Status**: ✅ Connected

**bot/docs/scripts.md**

- **Loaded by**: strategist.md
- **References**: None
- **Purpose**: Script documentation and parallel-safety
- **Status**: ✅ Connected

**bot/docs/WRITING-STYLE-EXTRACTOR.md**

- **Loaded by**: documenter.md
- **References**: None
- **Purpose**: Process for creating style guides
- **Status**: ✅ Connected

**bot/docs/configuration-hierarchy.md**

- **Loaded by**: (Not explicitly loaded)
- **References**: Instruction file paths
- **Purpose**: Configuration hierarchy explanation
- **Status**: ⚠️ Weakly connected (INDEX lists it but not loaded)

**bot/docs/DEVELOPMENT.md**

- **Loaded by**: bot/docs/INDEX.md, bot/docs/INSTRUCTIONS.md
- **References**: .md (malformed)
- **Purpose**: Bot development guide
- **Status**: ✅ Connected

**bot/docs/architecture.md**

- **Loaded by**: bot/docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Bot architecture
- **Status**: ✅ Connected

**bot/docs/error-handling.md**

- **Loaded by**: bot/docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Bot error handling
- **Status**: ✅ Connected

**bot/docs/error-quick-reference.md**

- **Loaded by**: bot/docs/INSTRUCTIONS.md
- **References**: None
- **Purpose**: Bot quick error reference
- **Status**: ✅ Connected

**bot/docs/modes.md**

- **Loaded by**: base.md
- **References**: None
- **Purpose**: Mode definitions (appears to duplicate parent docs/modes.md)
- **Status**: ⚠️ Possible duplicate

---

### Orphaned Files - Bot Submodule (8 files)

These files are NOT explicitly referenced in any loading path:

**bot/docs/CONTEXT-EXTRACTION-ARCHITECTURE.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Context system design
- **Status**: ❌ Orphaned
- **Action**: Link from AUTO-EXTRACTION.md or archive

**bot/docs/DATA-ARCHITECTURE.md**

- **Loaded by**: Never referenced (but Buttermilk references bot/docs/data-architecture.md?)
- **References**: N/A
- **Purpose**: Data architecture
- **Status**: ❌ Orphaned
- **Action**: Verify if needed, link from architecture.md or remove

**bot/docs/DEBUGGING.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Debugging methodology
- **Status**: ❌ Orphaned
- **Action**: Link from developer.md or consolidate with Buttermilk debugging.md

**bot/docs/DEEP-MINING-PATTERNS.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Advanced extraction patterns
- **Status**: ❌ Orphaned
- **Action**: Link from AUTO-EXTRACTION.md or strategist.md

**bot/docs/DOCUMENTATION_MAINTENANCE.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Doc maintenance guide
- **Status**: ❌ Orphaned
- **Action**: Link from documenter.md

**bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md**

- **Loaded by**: Never referenced in bot/ (but Buttermilk references it)
- **References**: N/A
- **Purpose**: Pre-coding exploration requirements
- **Status**: ⚠️ Cross-referenced but not in bot loading path
- **Action**: Link from developer.md

**bot/docs/FAIL-FAST-PHILOSOPHY.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Fail-fast principles
- **Status**: ❌ Orphaned
- **Action**: Link from bot/docs/INSTRUCTIONS.md or error-handling.md

**bot/docs/IMPACT-ANALYSIS.md**

- **Loaded by**: Never referenced in bot/ (but Buttermilk references it)
- **References**: N/A
- **Purpose**: Shared infrastructure analysis protocol
- **Status**: ⚠️ Cross-referenced but not in bot loading path
- **Action**: Link from developer.md

**bot/docs/GOALS.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Bot goals and principles
- **Status**: ❌ Orphaned
- **Action**: Link from bot/README.md or archive

**bot/docs/LOGS.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Logging conventions
- **Status**: ❌ Orphaned
- **Action**: Link from bot/docs/INSTRUCTIONS.md or archive

**bot/docs/TECHSTACK.md**

- **Loaded by**: Never referenced
- **References**: N/A
- **Purpose**: Technology stack
- **Status**: ❌ Orphaned
- **Action**: Link from bot/README.md or archive

**bot/docs/WORKFLOW-MODE-CRITICAL.md**

- **Loaded by**: Never referenced (INDEX mentions bot/.gemini/WORKFLOW-MODE-CRITICAL.md)
- **References**: N/A
- **Purpose**: Workflow mode enforcement (may duplicate modes.md)
- **Status**: ❌ Orphaned
- **Action**: Consolidate with modes.md or link from INSTRUCTIONS.md

---

### Orphaned Files - Buttermilk (8 files)

**projects/buttermilk/docs/agents/debugging.md**

- **Loaded by**: debugger.md references it, INSTRUCTIONS references it
- **References**: Many (it's the golden path guide)
- **Purpose**: Debugging golden path (GUIDE, not agent definition)
- **Status**: ✅ Connected (functional guide)
- **Note**: Confusing location (in agents/ but not an agent)

**projects/buttermilk/docs/bots/TEST_FIXER_AGENT.md**

- **Loaded by**: INSTRUCTIONS.md references it
- **References**: None
- **Purpose**: Test fixing protocol
- **Status**: ✅ Connected

**projects/buttermilk/docs/bots/config.md**

- **Loaded by**: INSTRUCTIONS.md references it
- **References**: None
- **Purpose**: Configuration guide
- **Status**: ✅ Connected

**projects/buttermilk/docs/bots/data-architecture.md**

- **Loaded by**: INSTRUCTIONS.md references it
- **References**: None
- **Purpose**: Buttermilk data architecture
- **Status**: ✅ Connected

**projects/buttermilk/docs/bots/techstack.md**

- **Loaded by**: INSTRUCTIONS.md references it, INDEX references it
- **References**: None
- **Purpose**: Tech stack
- **Status**: ✅ Connected

**projects/buttermilk/docs/TESTING_PHILOSOPHY.md**

- **Loaded by**: INSTRUCTIONS.md, tester.md
- **References**: None
- **Purpose**: Testing philosophy
- **Status**: ✅ Connected

**projects/buttermilk/docs/bots/exploration-before-implementation.md**

- **Loaded by**: INSTRUCTIONS.md
- **References**: None
- **Purpose**: Exploration requirements (duplicates bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md?)
- **Status**: ✅ Connected (but may be duplicate)

**projects/buttermilk/docs/bots/impact-analysis.md**

- **Loaded by**: INSTRUCTIONS.md
- **References**: None
- **Purpose**: Impact analysis protocol (duplicates bot/docs/IMPACT-ANALYSIS.md?)
- **Status**: ✅ Connected (but may be duplicate)

---

### Supporting Documentation - Buttermilk Reference (5+ files)

**projects/buttermilk/docs/reference/concepts.md**

- **Loaded by**: README.md
- **References**: None
- **Purpose**: Core concepts
- **Status**: ✅ Connected (user-facing)

**projects/buttermilk/docs/reference/cloud_infrastructure_setup.md**

- **Loaded by**: Never referenced
- **References**: None
- **Purpose**: Cloud setup guide
- **Status**: ⚠️ Orphaned (user doc, not agent)

**projects/buttermilk/docs/reference/llm_agent.md**

- **Loaded by**: Never referenced
- **References**: None
- **Purpose**: LLM agent guide
- **Status**: ⚠️ Orphaned (user doc, not agent)

**projects/buttermilk/docs/reference/tracing.md**

- **Loaded by**: Never referenced
- **References**: None
- **Purpose**: Tracing guide
- **Status**: ⚠️ Orphaned (user doc, not agent)

**projects/buttermilk/docs/reference/zotero_vectordb_guide.md**

- **Loaded by**: Never referenced
- **References**: None
- **Purpose**: Zotero vector DB guide
- **Status**: ⚠️ Orphaned (user doc, not agent)

**projects/buttermilk/docs/testing/BOUNDARY_MOCKING.md**

- **Loaded by**: Never referenced
- **References**: None
- **Purpose**: Mocking guidelines
- **Status**: ⚠️ Weakly connected (testing doc)

---

## Disconnected Files Summary

### Orphaned (Never Referenced) - 12 files

These are never explicitly loaded by any agent:

**bot/docs/** (8):

- CONTEXT-EXTRACTION-ARCHITECTURE.md
- DATA-ARCHITECTURE.md
- DEBUGGING.md
- DEEP-MINING-PATTERNS.md
- DOCUMENTATION_MAINTENANCE.md
- FAIL-FAST-PHILOSOPHY.md
- GOALS.md
- LOGS.md
- TECHSTACK.md
- WORKFLOW-MODE-CRITICAL.md

**Buttermilk reference/** (3):

- cloud_infrastructure_setup.md
- llm_agent.md
- tracing.md

### Cross-Referenced but Not in Bot Loading Path - 2 files

Referenced by project-specific instructions but not linked from bot:

- bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md (Buttermilk uses it)
- bot/docs/IMPACT-ANALYSIS.md (Buttermilk uses it)

### Weakly Connected - 4 files

In file system but not explicitly in loading tree:

- docs/AGENT_HIERARCHY.md (overview doc, not loaded)
- bot/docs/configuration-hierarchy.md (INDEX lists it)
- bot/docs/modes.md (possibly duplicates parent docs/modes.md)
- projects/buttermilk/docs/testing/BOUNDARY_MOCKING.md

---

## Issues Identified

### 1. Broken References

**WikiJuris CLAUDE.md**: References `docs/agents/INSTRUCTIONS.md` but file is at `docs/agent/INSTRUCTIONS.md` (singular)

### 2. Duplicates

**Potential duplicates across parent/bot**:

- docs/modes.md vs bot/docs/modes.md
- docs/error-handling.md vs bot/docs/error-handling.md
- docs/error-quick-reference.md vs bot/docs/error-quick-reference.md
- docs/architecture.md vs bot/docs/architecture.md

**Confirmed duplicates bot/Buttermilk**:

- bot/docs/EXPLORATION-BEFORE-IMPLEMENTATION.md vs projects/buttermilk/docs/bots/exploration-before-implementation.md
- bot/docs/IMPACT-ANALYSIS.md vs projects/buttermilk/docs/bots/impact-analysis.md

### 3. Confusing File Locations

**projects/buttermilk/docs/agents/debugging.md**: Is a GUIDE not an agent definition, but lives in agents/ folder

### 4. Missing Links

- developer.md should link to EXPLORATION-BEFORE-IMPLEMENTATION.md and IMPACT-ANALYSIS.md
- strategist.md should link to DEEP-MINING-PATTERNS.md
- documenter.md should link to DOCUMENTATION_MAINTENANCE.md

---

## Recommended Actions

### Immediate (Fix Broken References)

1. Fix WikiJuris CLAUDE.md path reference
2. Link EXPLORATION-BEFORE-IMPLEMENTATION.md from developer.md
3. Link IMPACT-ANALYSIS.md from developer.md

### Short-term (Connect Orphaned Files)

1. Link DEEP-MINING-PATTERNS.md from strategist.md or AUTO-EXTRACTION.md
2. Link DOCUMENTATION_MAINTENANCE.md from documenter.md
3. Link FAIL-FAST-PHILOSOPHY.md from INSTRUCTIONS.md or error-handling.md
4. Link DEBUGGING.md from developer.md

### Medium-term (Consolidate Duplicates)

1. Determine if bot/docs/{error,modes,architecture}.md should exist separately
2. Merge or clarify relationship between bot/ and Buttermilk exploration/impact-analysis docs
3. Move debugging.md out of agents/ folder or rename to indicate it's a guide

### Archive Candidates

Consider archiving if not needed:

- bot/docs/GOALS.md (covered in bot/README.md?)
- bot/docs/LOGS.md (if logging conventions are stable)
- bot/docs/TECHSTACK.md (if stable and in README)
- bot/docs/CONTEXT-EXTRACTION-ARCHITECTURE.md (if AUTO-EXTRACTION.md is sufficient)

---

## Maintenance

### Check for Disconnected Files

Run this to find files not referenced anywhere:

```bash
# In /writing/ directory
find . -name "*.md" \( -path "*/docs/*" -o -name "CLAUDE.md" -o -name "INSTRUCTIONS.md" \) \
  ! -path "*/papers/*" ! -path "*/vendor/*" ! -path "*/node_modules/*" \
  ! -path "*/.venv/*" ! -path "*/dbt_packages/*" ! -path "*/archive/*" ! -path "*/lib/*" \
  -type f -print0 | \
  xargs -0 -I {} sh -c 'grep -r -l --include="*.md" "$(basename {})" . > /dev/null || echo "Orphaned: {}"'
```

### Adding New Files

When adding new instruction/documentation:

1. Determine where it fits in loading tree (which agent/file should reference it)
2. Add reference from parent file
3. Update this map
4. Create GitHub issue if significant

### Quarterly Review

- Run disconnected file check
- Verify all loading tree paths still valid
- Check for new orphaned files
- Review archive candidates
