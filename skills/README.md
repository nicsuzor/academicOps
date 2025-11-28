# Skills Overview

LLM agent skills for working in this repository. Each skill provides specialized instructions for specific types of work.

## Available Skills

### analyst

**Purpose**: Academic research data analysis using dbt and Streamlit

**When to use**:

- Working in computational research projects (dbt/, Streamlit apps, empirical data pipelines)
- Building or updating data analysis dashboards
- Creating or modifying dbt models
- Validating data quality
- Statistical analysis and hypothesis testing

**Core workflow**: Single-step collaborative approach - perform ONE action at a time, then yield to user for feedback.

**Key features**:

- Reproducible data pipelines with dbt
- Automated testing and fail-fast validation
- Self-documenting code and research workflows
- Statistical analysis with proper reporting standards
- Streamlit visualization patterns

**Reference files loaded**:

- `_CHUNKS/` - research-documentation, methodology-files, methods-vs-methodology, experiment-logging, dbt-workflow, streamlit-workflow
- `references/` - statistical-analysis, test_selection_guide, assumptions_and_diagnostics, effect_sizes_and_power, bayesian_statistics, reporting_standards, dbt-workflow, streamlit-patterns, context-discovery, matplotlib, seaborn, statsmodels, streamlit

**Location**: `skills/analyst/SKILL.md`

---

### bmem

**Purpose**: Obsidian-compatible knowledge graph maintenance and session mining

**When to use**:

- Creating/editing markdown files in knowledge base
- User mentions project updates, decisions, insights
- Extracting strategic context from conversations
- Building knowledge graph connections
- Silent background session mining

**Core workflow**: Zero-friction capture - extracts information silently as mentioned, never interrupts user flow.

**Key features**:

- Write/edit Obsidian-compatible bmem files
- Silent session mining and information extraction
- Knowledge graph maintenance (relations, WikiLinks)
- Observation quality enforcement (additive, no duplicates)
- Integration with task skill for task operations

**Reference files loaded**:

- `references/` - approved-categories-relations, detail-level-guide, observation-quality-guide, obsidian-compatibility, obsidian-format-spec

**Location**: `skills/bmem/SKILL.md`

---

### docs-update

**Purpose**: Update and verify framework documentation, particularly README.md file tree structure

**When to use**:

- Before committing framework changes
- After adding new files (skills, hooks, commands, scripts)
- When documentation drift is suspected
- To generate updated file tree structure
- To detect conflicts between documentation files

**Core workflow**: Agent-driven verification and update - scans repository, compares with documented state, generates complete file trees

**Key features**:

- Scans repository to discover all files
- Generates two-level file tree (overview + detailed breakdown)
- Detects missing or outdated documentation entries
- Validates wikilink references resolve correctly
- Detects documentation conflicts and violations of SSoT
- Ensures README.md is authoritative and up-to-date

**Reference files loaded**: None (all inline in SKILL.md)

**Location**: `skills/docs-update/SKILL.md`

---

### feature-dev

**Purpose**: Test-first feature development from idea to validated implementation

**When to use**:

- Adding new features
- Building significant functionality
- Implementing user-requested capabilities
- _NOT_ for simple bug fixes or documentation-only changes

**Core workflow**: Seven phases from user story capture to validation

1. User Story Capture (zero-friction)
2. Requirements Analysis
3. Experiment Design
4. Test-First Design (write tests before code)
5. Development Planning
6. Execution
7. Validation & Decision (keep/revert/iterate)

**Key features**:

- Integration tests before implementation
- Explicit success criteria
- Experiment-driven development
- Fail-fast behavior
- ADHD accommodations (zero-friction capture, bias for action)

**Reference files loaded**: None (all inline in SKILL.md)

**Location**: `skills/feature-dev/SKILL.md`

---

### framework

**Purpose**: Maintain the automation framework and design experiments

**When to use**:

- Modifying framework infrastructure
- Designing and tracking experiments
- Maintaining framework documentation
- Working on cross-cutting framework features

**Key features**:

- Experiment tracking and validation
- Framework bloat prevention
- Single source of truth maintenance
- Integration with other skills

**Reference files loaded**:

- `workflows/` - 01-design-new-component, 02-debug-framework-issue, 03-experiment-design, 04-monitor-prevent-bloat, 05-review-pull-request, 06-develop-specification
- `references/` - hooks_guide

**Location**: `skills/framework/SKILL.md`

---

### python-dev

**Purpose**: Production-quality Python development with fail-fast philosophy

**When to use**:

- Writing new Python code (functions, classes, modules)
- Refactoring existing code
- Code review and quality validation
- Debugging Python issues
- API design

**Core philosophy**:

- Fail-fast: No defaults, no fallbacks (silent defaults corrupt research data)
- Type safety always (type hints on all signatures)
- Testing: Mock only at boundaries (never mock your own code)
- Modern Python patterns (pathlib, f-strings, comprehensions)
- Code quality standards (docstrings, clear names, focused functions)

**Key features**:

- TDD workflow (test-first development)
- Pydantic for configuration validation
- No `.get()` with defaults for required config
- Uses standard tools: pytest, mypy, ruff
- Production-quality standards for academic/research code

**Reference files loaded**:

- `references/` - fail-fast, type-safety, testing, modern-python, code-quality, pandas, hydra, fastapi, fastmcp, bigquery

**Location**: `skills/python-dev/SKILL.md`

---

### tasks

**Purpose**: Manage task lifecycle using scripts (view, archive, create)

**When to use**:

- User mentions task completion or asks to archive tasks
- User asks about urgent/priority tasks or requests task list
- User requests task status or wants to view current tasks
- Creating new tasks

**Core workflow**: Script-based operations - never write task files directly

**Key features**:

- View tasks with filtering and sorting (`task_view.py`)
- Archive completed tasks (`task_archive.py`)
- Priority framework (P0-P3)
- Integration with data/tasks/ directory structure

**Reference files loaded**:

- `workflows/` - email-capture

**Location**: `skills/tasks/SKILL.md`

---

## Skill Structure

Each skill follows this structure:

```
skill-name/
├── SKILL.md              # Main skill definition with frontmatter metadata
├── references/           # Detailed reference documentation
├── templates/            # Templates for workflows
├── _CHUNKS/             # Chunked documentation (loaded on-demand)
└── assets/              # Supporting assets
```

## Using Skills

Skills are invoked via the Skill tool in Claude Code. Skills provide:

- Specialized workflows and decision trees
- Domain-specific best practices
- Templates and patterns
- Reference documentation
- Quality standards and validation

## Skill Design Principles

All skills follow [[../AXIOMS.md]].

## Agents vs Skills

**Agents** (in `agents/`): Thin wrappers that route to appropriate skills based on task context. Agents do ONE step and return.

**Skills** (in `skills/`): Detailed workflows and instructions for specific work types.

**When to create agent**: Need routing logic across multiple skills (e.g., 'dev' agent routes to python-dev or feature-dev based on task).

**When to create skill**: Need detailed workflow for specific domain (e.g., python-dev for Python code quality standards).

## Available Agents

### dev

**Purpose**: Routes development tasks to appropriate skills (python-dev, feature-dev)

**Location**: `agents/dev.md`

**Routing logic**:

- Test creation → python-dev skill
- Implementation → python-dev skill
- Feature workflow → feature-dev skill

## Adding New Skills

When adding a skill:

1. Create skill directory in `skills/`
2. Create `SKILL.md` with frontmatter metadata:
   ```yaml
   ---
   name: skill-name
   description: Brief description of when and how to use this skill
   permalink: skills/skill-name
   ---
   ```
3. Follow single-source-of-truth principle (reference, don't duplicate)
4. Add entry to this README
5. Test skill invocation
6. Document in experiment log if significant

---

**Last updated**: 2025-11-26
