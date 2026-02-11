---
name: audit
category: instruction
description: Comprehensive framework governance audit - structure checking, justification checking, and index file updates.
allowed-tools: Read,Glob,Grep,Edit,Write,Bash,Skill,TodoWrite
version: 5.0.0
permalink: skills-audit
---

# Framework Audit Skill

Comprehensive governance audit for the academicOps framework.

**NO RATIONALIZATION**: An audit reports ALL discrepancies. Do NOT justify ignoring files as "generated", "acceptable", or "probably don't need to be tracked". Every gap is reported. The user decides what's acceptable - not the auditor.

## Workflow Entry Point

**IMMEDIATELY call TodoWrite** with the following items, then work through each one:

```
TodoWrite(todos=[
  {content: "Phase 0: Run health metrics script", status: "pending", activeForm: "Running health audit"},
  {content: "Phase 1: Structure audit - compare filesystem to INDEX.md", status: "pending", activeForm: "Auditing structure"},
  {content: "Phase 2: Reference graph - invoke Skill(skill='framework') then run link audit scripts", status: "pending", activeForm: "Building reference graph"},
  {content: "Phase 3: Skill content audit - check size and actionability", status: "pending", activeForm: "Auditing skill content"},
  {content: "Phase 4: Justification audit - check specs for file references", status: "pending", activeForm: "Auditing file justifications"},
  {content: "Phase 4b: Instruction justification - verify every instruction traces to framework/enforcement-map.md", status: "pending", activeForm: "Auditing instruction justifications"},
  {content: "Phase 5: Documentation accuracy - verify README.md flowchart vs hooks", status: "pending", activeForm": "Verifying documentation"},
  {content: "Phase 6: Regenerate indices - invoke Skill(skill='flowchart') for README.md flowchart", status: "pending", activeForm: "Regenerating indices"},
  {content: "Phase 7: Other updates", status: "pending", activeForm: "Finalizing updates"},
  {content: "Phase 8: Save audit report to $ACA_DATA/projects/aops/audit/YYYY-MM-DD-HHMMSS-audit.md", status: "pending", activeForm: "Persisting report"},
  {content: "Phase 9: Create tasks for actionable findings", status: "pending", activeForm: "Creating tasks"}
])
```

**CRITICAL**: Work through EACH phase in sequence. When a phase requires a skill, invoke it explicitly as shown below.

## Specialized Workflows

### Session Effectiveness Audit

Qualitative assessment of session transcripts to evaluate framework performance.

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

Workflow defined in `workflows/session-effectiveness.md`.

## Individual Scripts (Reference Only)

These scripts run individual checks. They are NOT a substitute for the full workflow:

```bash
uv run python scripts/audit_framework_health.py -m  # Phase 0 only
uv run python scripts/check_skill_line_count.py
uv run python scripts/check_broken_wikilinks.py
uv run python scripts/check_orphan_files.py
```

## Phase Instructions

### Phase 0: Health Metrics

Run comprehensive health audit first:

```bash
uv run python scripts/audit_framework_health.py \
  --output /tmp/health-$(date +%Y%m%d).json
```

This generates:

- `/tmp/health-YYYYMMDD.json` - Machine-readable metrics
- `/tmp/health-YYYYMMDD.md` - Human-readable report

**Metrics tracked**: Component counts, hook coverage, skill sizes, wikilink validation

**→ Continue to Phase 1** (do not stop here)

### Phase 1: Structure Audit

Compare filesystem to documentation:

1. **Scan filesystem**: `find . -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" | sort`
2. **Compare to INDEX.md**: Flag missing or extra entries
3. **Check cross-references**: Verify `→` references point to existing files
4. **Find broken wikilinks**: Grep for `[[...]]` patterns, validate targets exist

### Phase 2: Reference Graph & Link Audit

**First**: Invoke `Skill(skill="framework")` to load framework conventions for linking rules.

Then build reference graph and check linking conventions:

```bash
# Generate graph for aops-core
uv run python aops-core/skills/audit/scripts/build_reference_map.py --root aops-core --output data/aops/reference-graph-core.json

# Find orphans in aops-core
uv run python aops-core/skills/audit/scripts/find_orphans.py --graph data/aops/reference-graph-core.json

# Or use the health script for wikilink/orphan checks
uv run python scripts/audit_framework_health.py -m
```

**Linking rules to enforce** (from framework skill):

- Skills via invocation (`Skill(skill="x")`), not file paths
- No backward links (children → parent)
- Parents must reference children
- Use wikilinks, not backticks for graph connectivity
- Full relative paths in wikilinks

### Phase 3: Skill Content Audit

For each `$AOPS/skills/*/SKILL.md`:

1. **Size check**: Must be <500 lines
2. **Actionability test**: Each section must tell agents WHAT TO DO
3. **Content separation violations**:
   - ❌ Multi-paragraph "why" → move to spec
   - ❌ Historical context → delete
   - ❌ Reference material >20 lines → move to `references/`

### Phase 4: Justification Audit (Files)

For each significant file in `$AOPS/`:

1. **Search specs**: Grep `$AOPS/specs/` for references
2. **Check core docs**: JIT-INJECTION.md, README.md, INDEX.md
3. **Classify**: Justified / Implicit / Orphan

**Skip**: `__pycache__/`, `.git/`, individual files within skills, tests, assets

### Phase 4b: Instruction Justification Audit

**Every behavioral instruction injected to agents must trace to framework/enforcement-map.md.**

Unjustified instructions are bloat - they cost tokens and create confusion about what's actually enforced.

**Sources to scan** (files injected at SessionStart or via hooks):

- `FRAMEWORK-PATHS.md` - core instructions
- `AXIOMS.md`, `HEURISTICS.md` - principle statements
- `skills/*/SKILL.md` - skill-specific instructions
- `commands/*.md` - command instructions
- `agents/*.md` - agent instructions

**What constitutes a "behavioral instruction":**

- Imperative statements: "always do X", "never do Y", "you MUST", "you SHOULD"
- Conditional rules: "when X, do Y", "if X then Y"
- Workflow requirements: "invoke skill X first", "before doing X, check Y"

**Validation process:**

1. Extract behavioral instructions from each source file (look for imperatives, MUSTs, SHOULDs, "always", "never", "before", "first")
2. For each instruction, search enforcement-map.md for:
   - Direct reference to the instruction text
   - Reference to the source file + line number
   - Mapping to an axiom or heuristic that covers this instruction
3. Classify each instruction:
   - **Justified**: Appears in enforcement-map.md with axiom/heuristic mapping
   - **Implicit**: Derives from a documented axiom/heuristic but not explicitly in enforcement-map.md
   - **Orphan**: No traceability - FLAG FOR REVIEW

**Example orphan** (discovered in session):

```
FRAMEWORK-PATHS.md:35 - "When working with session logs, always invoke Skill(skill='transcript') first"
→ NOT in enforcement-map.md
→ No axiom/heuristic reference
→ ORPHAN - needs justification or removal
```

**Output format:**

```
### Instruction Justification Status

**Justified** (N instructions):
- FRAMEWORK-PATHS.md:78 "NEVER hardcode paths" → [[axioms/dry-modular-explicit.md]]

**Implicit** (N instructions):
- skills/python-dev/SKILL.md:42 "use uv run" → derives from [[axioms/use-standard-tools.md]]

**Orphan** (N instructions) - REQUIRES ACTION:
- FRAMEWORK-PATHS.md:35 "invoke transcript skill first for session logs" → NO JUSTIFICATION
- commands/learn.md:56 "..." → NO JUSTIFICATION
```

**Resolution for orphans:**

1. Create heuristic if rule is valuable
2. Add to enforcement-map.md with axiom/heuristic mapping
3. Or DELETE the instruction if it's not worth formalizing

### Phase 5: Documentation Accuracy

Verify README.md flowchart reflects actual hook architecture:

1. Parse Mermaid for hook names
2. Compare to hooks/router.py dispatch mappings
3. Compare to settings.json hook events
4. Flag drift

### Phase 6: Curate Index Files

Index files are root-level files for agent consumption. The auditing agent curates these using LLM judgment, not mechanical script generation.

**Target files**: INDEX.md, enforcement-map.md, WORKFLOWS.md, SKILLS.md, AXIOMS.md, HEURISTICS.md, docs/ENFORCEMENT.md, README.md (flowchart section).

**Approach**: For each index file, read the source materials, then write a curated index that accurately reflects current state. Use your judgment to:

- Prioritize what's most useful for agent routing and context
- Remove stale entries that no longer match the filesystem
- Add missing entries discovered during earlier audit phases
- Keep descriptions concise and actionable

#### Per-File Instructions

| Index File | Sources | Key Judgment |
|-----------|---------|-------------|
| AXIOMS.md | `axioms/*.md` files | Priority ordering, concise summaries |
| HEURISTICS.md | `heuristics/*.md` files | Priority ordering, concise summaries |
| SKILLS.md | `skills/*/SKILL.md` frontmatter, `commands/*.md` | Routing triggers, description accuracy |
| WORKFLOWS.md | `workflows/*.md`, `skills/*/workflows/*.md` | Decision tree accuracy, scope routing |
| INDEX.md | Filesystem scan of `$AOPS/` | File tree with accurate purpose annotations |
| enforcement-map.md | `hooks/*.py` "Enforces:" docstrings, `gate_config.py` | Axiom-to-hook mapping accuracy |
| docs/ENFORCEMENT.md | `specs/enforcement.md`, existing content | Mechanism ladder, root cause model |
| README.md (flowchart) | `hooks/router.py`, `gate_config.py`, `gates.py` | Invoke `Skill(skill="flowchart")` first. Mermaid accuracy |

#### WORKFLOWS.md Curation

**Source data**: Each workflow file in `workflows/*.md` has YAML frontmatter with:

- `id`: Workflow identifier
- `category`: Workflow category (development, operations, routing, etc.)
- `bases`: Array of base patterns this workflow composes (e.g., `[base-task-tracking, base-tdd]`)

**Generation requirements**:

1. **Preserve existing structure**: Keep the decision tree, key distinctions, and project-specific sections
2. **Preserve annotations**: Do NOT delete `<!-- @nic: -->` or `<!-- @claude: -->` comments - these contain design history
3. **Add Bases column**: In workflow tables, include a "Bases" column showing which base patterns each workflow composes
4. **Extract from frontmatter**: Read `bases:` field from each workflow's YAML frontmatter
5. **Handle missing bases**: If a workflow lacks `bases:` in frontmatter, show "-" in the Bases column

**Table format**:

```markdown
| Workflow | When to Use | Bases |
| -------- | ----------- | ----- |
| [[tdd-cycle]] | Any testable code change | task-tracking, tdd, verification, commit |
| [[debugging]] | Cause unknown, investigating | task-tracking, verification |
| [[simple-question]] | Pure information, no modifications | - |
```

**Why this matters**: The `bases:` metadata enables the hydrator to compose workflow steps rather than just listing options (see task aops-4f512f50).

#### enforcement-map.md Derivation

**Hook-Axiom Declaration Convention**: Every hook that enforces an axiom declares it in its module docstring:

```python
"""
Hook description.

Enforces: current-state-machine (Current State Machine)
"""
```

**Cross-reference validation**:

1. Parse all hooks for "Enforces:" declarations
2. Compare against enforcement-map.md Axiom-Enforcement table
3. Flag discrepancies (hook declares axiom not in map, map lists hook without declaration, etc.)

#### README.md Flowchart

**First**: Invoke `Skill(skill="flowchart")` to load Mermaid conventions.

Regenerate the core loop flowchart from `hooks/router.py` dispatch mappings, `gate_config.py` gate definitions, and `hooks/*.py` implementations. Every gate in `gate_config.py` must be represented.

#### Generated File Header

Each curated index must include:

```
> **Curated by audit skill** - Regenerate with `Skill(skill="audit")`
```

### Phase 7: Other Updates

1. **Fix README.md**: Update tables including sub-workflows (see below)
2. **Report orphans**: Flag for human review (do NOT auto-delete)
3. **Report violations**: List with file:line refs

#### Sub-Workflow Extraction for README.md

Skills with multiple workflows/modes MUST have each sub-workflow documented separately in the Skills table.

**Detection**: For each `skills/*/SKILL.md`:

1. Grep for `^## Workflow:` or `^## Mode` headers
2. Check for `workflows/` subdirectory with separate workflow files
3. Check for `## Modes` section listing multiple invocation patterns

**Output format** (add third column to Skills table):

```markdown
| Skill            | Purpose                     | Sub-workflows                                |
| ---------------- | --------------------------- | -------------------------------------------- |
| session-insights | Session transcript analysis | Current (default), Batch, Issues             |
| audit            | Framework governance        | Full audit (default), Session effectiveness  |
| tasks            | Task lifecycle              | View/archive/create (default), Email capture |
````

**Rules**:

- Mark default workflow with "(default)"
- List workflows in order they appear in SKILL.md
- If only one workflow exists, leave sub-workflows column as "—"
- Extract workflow names from `## Workflow: X` headers or `workflows/*.md` filenames

### Phase 8: Persist Report (MANDATORY)

**Every audit MUST save a written report to `$ACA_DATA/projects/aops/audit/`.**

```bash
# Create directory if needed
mkdir -p "$ACA_DATA/projects/aops/audit"

# Generate timestamped filename (format: YYYY-MM-DD-HHMMSS-audit.md)
REPORT_PATH="$ACA_DATA/projects/aops/audit/$(date +%Y-%m-%d-%H%M%S)-audit.md"
```

Use the Write tool to save the complete audit report (see Report Format below) to `$REPORT_PATH`.

**Report file MUST include:**

- YAML frontmatter with date, duration, and summary stats
- All phase results from Phase 0-7
- Clear pass/fail status for each validation criterion

After writing, confirm: `Audit report saved to: [path]`

### Phase 9: Create Tasks for Actionable Findings

**Create tasks for findings that require human action.**

For each finding from Phases 0-7 that requires action:

1. **Classify finding type** using the mapping below
2. **Create task** with appropriate metadata via tasks MCP
3. **Track task IDs** for summary

#### Finding Type → Issue Mapping

| Finding Type                                     | Priority | Issue Type | Labels              |
| ------------------------------------------------ | -------- | ---------- | ------------------- |
| Broken wikilinks                                 | P2       | bug        | audit,documentation |
| Orphan files                                     | P3       | chore      | audit,cleanup       |
| Skill >500 lines                                 | P2       | chore      | audit,refactor      |
| Explanatory content in skill                     | P2       | chore      | audit,refactor      |
| Missing from INDEX.md                            | P3       | chore      | audit,documentation |
| Orphan instruction (no enforcement-map.md trace) | P2       | bug        | audit,governance    |
| README.md flowchart drift                        | P2       | bug        | audit,documentation |
| Hook→Axiom mismatch                              | P2       | bug        | audit,governance    |

#### Task Creation Pattern

```python
mcp__plugin_aops-core_task_manager__create_task(
    title="[Finding Type]: [specific details]",
    type="task",
    priority=[2|3],
    tags=["audit", "[category]"],
    body="[context from audit]"
)
```

#### Skip Conditions

Do NOT create issues for:

- **Regenerated indices** (Phase 6 actions) - already handled
- **Pass status** findings - no action needed
- **Justified files** (Phase 4) - no action needed
- **Implicit files** (Phase 4) - acceptable, no action needed

#### Output Summary

After creating tasks, add to audit report:

```markdown
### Tasks Created

Created N tasks:

- ns-xxx: Broken wikilink: [[foo.md]] in bar.md
- ns-yyy: Orphan file: docs/old.md
- ns-zzz: Skill over limit: skills/big/SKILL.md
```

## Report Format

See [[references/report-format]] for the complete report template and validation criteria.
