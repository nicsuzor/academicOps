---
name: file-taxonomy
title: File Taxonomy
type: spec
category: spec
description: Classification system for framework files. Defines seven categories with distinct purposes and editing rules.
permalink: file-taxonomy
tags: [framework, architecture, governance]
---

# File Taxonomy

Every framework file belongs to exactly one category. This classification determines reading purpose, editing rules, and validation requirements.

## Categories

| Category        | Purpose                                         | Editing Rule                                   | Frontmatter             |
| --------------- | ----------------------------------------------- | ---------------------------------------------- | ----------------------- |
| **SPEC**        | OUR framework design (architecture, rationale)  | Deliberate; RFC for significant changes        | `category: spec`        |
| **REF**         | External knowledge (libraries, concepts, tools) | Update when external tools change              | `category: ref`         |
| **DOCS**        | Implementation guides, how-to content           | Update as practices evolve                     | `category: docs`        |
| **SCRIPT**      | Executable code                                 | TDD required; tests must pass                  | N/A (code files)        |
| **INSTRUCTION** | Workflow/process for agents to follow           | Must be generalizable (categorical imperative) | `category: instruction` |
| **TEMPLATE**    | Pattern to fill in with dynamic content         | Update when format changes                     | `category: template`    |
| **STATE**       | Auto-generated current system state             | DO NOT manually edit                           | `category: state`       |

## Category Definitions

### SPEC (Framework Design)

**What**: Documents that explain WHY OUR framework works the way it does. Architectural decisions, expected behavior, rationale for our system.

**Reading purpose**: Understand design before implementing or modifying.

**Editing rule**: Changes require deliberation. Significant changes may need RFC process or user approval.

**Location pattern**:

- `specs/*.md` - Primary spec location
- Root docs: `VISION.md`, `README.md`, `INDEX.md`, `ROADMAP.md` (design/status for humans)

**Examples**:

- `specs/hook-router.md` - Hook router architecture
- `specs/prompt-hydration.md` - Prompt hydration design
- `VISION.md` - Framework end state
- `INDEX.md` - File accounting for audits

**Key distinction**: SPEC is about OUR framework. External tool knowledge goes in REF.

### REF (External Reference)

**What**: Reference material about external tools, libraries, concepts, and techniques. Knowledge that comes from outside our framework.

**Reading purpose**: Learn how to use external tools correctly.

**Editing rule**: Update when external tools change or we learn better patterns.

**Location pattern**:

- `skills/*/references/*.md` - Domain-specific reference material

**Examples**:

- `skills/analyst/references/bayesian_statistics.md` - Statistical methods
- `skills/analyst/references/matplotlib.md` - Matplotlib usage
- `skills/python-dev/references/fastapi.md` - FastAPI patterns
- `skills/framework/references/hooks_guide.md` - Claude Code hooks (external tool)

**Key distinction**: REF is about EXTERNAL tools/concepts. Our framework design goes in SPEC.

### DOCS (Implementation Guides)

**What**: Practitioner's guides explaining HOW to do things within the framework. Living documents that capture current practices.

**Reading purpose**: Learn how to perform specific tasks.

**Editing rule**: Update as practices evolve. These are learning documents.

**Location pattern**:

- `docs/*.md` - Implementation guides

**Examples**:

- `docs/ENFORCEMENT.md` - How to choose enforcement mechanisms
- `docs/HOOKS.md` - How to work with hooks
- `docs/OBSERVABILITY.md` - How to observe framework behavior

**Key distinction**: DOCS is HOW-TO content. SPEC is WHY/WHAT design. REF is external knowledge.

### SCRIPT (Executable Code)

**What**: Python, Bash, or other executable files that automate tasks.

**Reading purpose**: Execute or modify automation.

**Editing rule**: TDD required. Tests must pass before commit. Scripts are simple tools - they transform data, they don't reason.

**Location pattern**:

- `scripts/*.py` - Utility scripts
- `lib/*.py` - Shared library code
- `hooks/*.py` - Hook implementations
- `skills/*/scripts/*.py` - Skill-specific scripts
- `tests/*.py` - Test files

**Examples**:

- `scripts/audit_framework_health.py`
- `hooks/user_prompt_submit.py`
- `skills/pdf/scripts/generate_pdf.py`

### INSTRUCTION (Agent Workflows)

**What**: Documents that tell agents what to do. Workflows, procedures, skill definitions.

**Reading purpose**: Follow the workflow during task execution.

**Editing rule**: Must be generalizable per categorical imperative. No ad-hoc instructions.

**Location pattern**:

- `skills/*/SKILL.md` - Main skill entry point
- `skills/*/instructions/*.md` - Detailed instruction sets
- `skills/*/workflows/*.md` - Multi-step workflows
- `commands/*.md` - Slash commands
- `agents/*.md` - Agent definitions
- Root instructions: `AXIOMS.md`, `HEURISTICS.md`, `FRAMEWORK.md`, `WORKFLOWS.md` (injected to agents)

**Examples**:

- `skills/pdf/SKILL.md` - PDF generation workflow
- `commands/do.md` - /do command
- `agents/planner.md` - Planning agent

### TEMPLATE (Fill-in Patterns)

**What**: Structured patterns with placeholders that get filled in with dynamic content.

**Reading purpose**: Use as pattern for generating output.

**Editing rule**: Update when output format requirements change. Templates define structure, not content.

**Location pattern**:

- `*/templates/*.md` - Template directories
- `hooks/templates/*.md` - Hook output templates
- `skills/*/templates/*.md` - Skill output templates

**Examples**:

- `hooks/templates/prompt-hydrator-context.md`
- `skills/feature-dev/templates/user-story.md`
- `skills/fact-check/templates/verification-report.md`

### STATE (Auto-generated)

**What**: Files that represent current system state. Generated by scripts, not manually edited.

**Reading purpose**: Know current status without manual inspection.

**Editing rule**: DO NOT manually edit. Regenerate instead.

**Location pattern**:

- Files marked `(auto-generated)` in INDEX.md
- Generated index files
- Build artifacts

**Examples**:

- `RULES.md` - Current enforcement rules (auto-generated)

**Note**: Currently most "state-like" files (INDEX.md, README.md feature list) are manually maintained. These are treated as SPEC until automation exists.

## Directory Mapping

| Directory                                                    | Category    | Rationale                       |
| ------------------------------------------------------------ | ----------- | ------------------------------- |
| `specs/`                                                     | SPEC        | Framework design specifications |
| `VISION.md`, `README.md`, `INDEX.md`, `ROADMAP.md`           | SPEC        | Design/status for humans        |
| `AXIOMS.md`, `HEURISTICS.md`, `FRAMEWORK.md`, `WORKFLOWS.md` | INSTRUCTION | Injected to agents              |
| `docs/`                                                      | DOCS        | Implementation guides           |
| `skills/*/references/`                                       | REF         | External domain knowledge       |
| `scripts/`                                                   | SCRIPT      | Utility scripts                 |
| `lib/`                                                       | SCRIPT      | Shared library code             |
| `hooks/*.py`                                                 | SCRIPT      | Hook implementations            |
| `skills/*/scripts/`                                          | SCRIPT      | Skill automation                |
| `tests/`                                                     | SCRIPT      | Test code                       |
| `skills/*/SKILL.md`                                          | INSTRUCTION | Skill entry points              |
| `skills/*/instructions/`                                     | INSTRUCTION | Detailed workflows              |
| `skills/*/workflows/`                                        | INSTRUCTION | Multi-step procedures           |
| `commands/`                                                  | INSTRUCTION | Slash commands                  |
| `agents/`                                                    | INSTRUCTION | Agent definitions               |
| `*/templates/`                                               | TEMPLATE    | Output patterns                 |
| `RULES.md`                                                   | STATE       | Auto-generated                  |

## Frontmatter Convention

All markdown files (except SCRIPT/test files) must declare their category:

```yaml
---
name: example
title: Example Document
type: spec
category: spec  # REQUIRED: spec | ref | docs | instruction | template | state
description: ...
---
```

**Validation**: Pre-commit hook checks that `category` matches expected value for file location.

## Agent Behavior by Category

| Category    | When Agent Encounters         | Expected Behavior                                  |
| ----------- | ----------------------------- | -------------------------------------------------- |
| SPEC        | Needs to understand design    | Read for context, don't modify without approval    |
| REF         | Needs external tool knowledge | Read to learn patterns, update if tool changed     |
| DOCS        | Needs how-to guidance         | Read and follow, update if practice evolved        |
| SCRIPT      | Needs automation              | Execute via Bash, modify with TDD                  |
| INSTRUCTION | Needs to do task              | Follow the workflow, invoke skills                 |
| TEMPLATE    | Needs structured output       | Fill in placeholders, don't modify template itself |
| STATE       | Needs current status          | Read only, never modify                            |

## Validation Rules

1. **Location-category alignment**: File location must match its category
2. **Frontmatter required**: Markdown files must declare `category`
3. **No mixed-category directories**: Each directory has a primary category
4. **STATE files immutable**: Pre-commit blocks manual edits to STATE files

## Edge Cases

### Borderline: SPEC vs REF

- **SPEC**: "How our hook router dispatches events" (our design)
- **REF**: "How Claude Code hooks work" (external tool)

### Borderline: SPEC vs DOCS

- **SPEC**: "Why we chose this architecture" (design rationale)
- **DOCS**: "How to add a new hook" (practitioner guide)

### Borderline: REF vs INSTRUCTION

- **REF**: "Pandas DataFrame operations" (external knowledge)
- **INSTRUCTION**: "Use pandas to load and validate data" (workflow step)

## Axiom Derivation

- **Axiom #9 (Self-Documenting)**: Categories make file purpose explicit
- **Axiom #10 (Single-Purpose Files)**: Each file has one category, one purpose
- **Axiom #11 (DRY, Modular, Explicit)**: No guessing about file type
- **Axiom #26 (Minimal Instructions)**: Category tells agents how to handle file without extra explanation
