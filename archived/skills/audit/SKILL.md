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
  {content: "Phase 4b: Instruction justification - verify every instruction traces to RULES.md", status: "pending", activeForm: "Auditing instruction justifications"},
  {content: "Phase 5: Documentation accuracy - verify FLOW.md vs hooks", status: "pending", activeForm: "Verifying documentation"},
  {content: "Phase 6: Regenerate indices - invoke Skill(skill='flowchart') for FLOW.md", status: "pending", activeForm: "Regenerating indices"},
  {content: "Phase 7: Other updates", status: "pending", activeForm: "Finalizing updates"},
  {content: "Phase 8: Save audit report to $ACA_DATA/qa/aops/audit-YYYYMMDD-HHMMSS.md", status: "pending", activeForm: "Persisting report"},
  {content: "Phase 9: Create bd issues for actionable findings", status: "pending", activeForm: "Creating issues"}
])
```

**CRITICAL**: Work through EACH phase in sequence. When a phase requires a skill, invoke it explicitly as shown below.

## Specialized Workflows

### Session Effectiveness Audit

Qualitative assessment of session transcripts to evaluate framework performance.

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

See [[workflows/session-effectiveness.md]] for full workflow.

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
cd $AOPS && uv run python scripts/audit_framework_health.py \
  --output /tmp/health-$(date +%Y%m%d).json
```

This generates:

- `/tmp/health-YYYYMMDD.json` - Machine-readable metrics
- `/tmp/health-YYYYMMDD.md` - Human-readable report

**Metrics tracked**: See [[specs/framework-health.md]]

**→ Continue to Phase 1** (do not stop here)

### Phase 1: Structure Audit

Compare filesystem to documentation:

1. **Scan filesystem**: `find $AOPS -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" | sort`
2. **Compare to INDEX.md**: Flag missing or extra entries
3. **Check cross-references**: Verify `→` references point to existing files
4. **Find broken wikilinks**: Grep for `[[...]]` patterns, validate targets exist

### Phase 2: Reference Graph & Link Audit

**First**: Invoke `Skill(skill="framework")` to load framework conventions for linking rules.

Then build reference graph and check linking conventions:

```bash
cd $AOPS

# Generate graph
uv run python skills/audit/scripts/build_reference_map.py

# Find orphans and violations
uv run python skills/audit/scripts/find_orphans.py

# Or use the health script for wikilink/orphan checks
uv run python scripts/check_broken_wikilinks.py
uv run python scripts/check_orphan_files.py
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

**Every behavioral instruction injected to agents must trace to RULES.md.**

Unjustified instructions are bloat - they cost tokens and create confusion about what's actually enforced.

**Sources to scan** (files injected at SessionStart or via hooks):

- `FRAMEWORK.md` - core instructions
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
2. For each instruction, search RULES.md for:
   - Direct reference to the instruction text
   - Reference to the source file + line number
   - Mapping to an axiom or heuristic that covers this instruction
3. Classify each instruction:
   - **Justified**: Appears in RULES.md with axiom/heuristic mapping
   - **Implicit**: Derives from a documented axiom/heuristic but not explicitly in RULES.md
   - **Orphan**: No traceability - FLAG FOR REVIEW

**Example orphan** (discovered in session):

```
FRAMEWORK.md:35 - "When working with session logs, always invoke Skill(skill='transcript') first"
→ NOT in RULES.md
→ No axiom/heuristic reference
→ ORPHAN - needs justification or removal
```

**Output format:**

```
### Instruction Justification Status

**Justified** (N instructions):
- FRAMEWORK.md:78 "NEVER hardcode paths" → [[axioms/dry-modular-explicit.md]]

**Implicit** (N instructions):
- skills/python-dev/SKILL.md:42 "use uv run" → derives from [[axioms/use-standard-tools.md]]

**Orphan** (N instructions) - REQUIRES ACTION:
- FRAMEWORK.md:35 "invoke transcript skill first for session logs" → NO JUSTIFICATION
- commands/learn.md:56 "..." → NO JUSTIFICATION
```

**Resolution for orphans:**

1. Create heuristic if rule is valuable
2. Add to RULES.md with axiom/heuristic mapping
3. Or DELETE the instruction if it's not worth formalizing

### Phase 5: Documentation Accuracy

Verify `FLOW.md` reflects actual hook architecture:

1. Parse Mermaid for hook names
2. Compare to hooks/router.py dispatch mappings
3. Compare to settings.json hook events
4. Flag drift

### Phase 6: Regenerate Generated Indices

Generated indices are root-level files for agent consumption. See [[specs/generated-indices]].

**Regenerate each deterministically from sources:**

#### AXIOMS.md and HEURISTICS.md

```bash
cd $AOPS && uv run python scripts/generate_principle_indices.py
```

Reads `axioms/` and `heuristics/` folders, generates machine-readable indices sorted by priority (1-100 bands: 1-20 core, 21-40 behavioral, 41-60 domain, 61-80 derived, 81-100 experimental).

#### INDEX.md

- Scan `$AOPS/` directory structure
- Extract file purposes from frontmatter/headers
- Output annotated file tree

#### RULES.md

**Hook→Axiom Declaration Convention**:

Every hook that enforces an axiom MUST declare it in its module docstring:

```python
"""
Hook description.

Enforces: current-state-machine (Current State Machine)
"""
```

Multiple axioms: `Enforces: fail-fast-code, trust-version-control (Fail-Fast, Trust Version Control)`

**Derivation sources**:

- `hooks/*.py` docstrings - parse "Enforces:" lines for axiom mappings
- `config/claude/settings.json` - deny rules map to axioms via comments
- `.pre-commit-config.yaml` - commit-time checks

**Cross-reference validation**:

1. Parse all hooks for "Enforces:" declarations
2. Compare against RULES.md Axiom→Enforcement table
3. Flag discrepancies:
   - Hook declares axiom but RULES.md shows "Prompt" level only
   - RULES.md lists hook but hook lacks "Enforces:" declaration
   - Axiom has Hard/Soft Gate in RULES.md but no hook declares it

**Output**: Table mapping each axiom to its enforcement mechanism, hook, trigger point, and level.

#### WORKFLOWS.md

Derive task routing from:

- `skills/*/SKILL.md` frontmatter - what task types each skill handles
- `agents/*.md` - what workflows each agent uses
- `RULES.md` (Soft Gate Guardrails section) - type→guardrail mappings

Output: Table of task types, when to use each, workflow, and skill.

#### FLOW.md

**First**: Invoke `Skill(skill="flowchart")` to load Mermaid diagram conventions.

Regenerate from hook architecture sources:

1. Parse `hooks/router.py` for dispatch mappings (event→handler)
2. Parse `config/claude/settings.json` for hook event registrations
3. Parse `hooks/*.py` for hook implementations and "Enforces:" declarations
4. Generate Mermaid flowchart following flowchart skill conventions:
   - Use decision diamonds for conditional logic
   - Apply classDef for semantic coloring (hooks, skills, tools, outcomes)
   - Group by execution phase (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop)
   - Label edges with event types and conditions

**Structure** (per [[specs/execution-flow-spec.md]]):

- Vertical main flow showing session lifecycle
- Horizontal insertion points for each hook event
- Subgraphs for phase groupings

#### docs/ENFORCEMENT.md

Derive practical enforcement guide from:

- `docs/ENFORCEMENT.md` (existing mechanism ladder content - preserve)
- `specs/enforcement.md` "Component Responsibilities" section - root cause model

**Root Cause Analysis section** (append to end):

1. Copy root cause definition from spec
2. Copy responsibility tables (Pre/Execution/Post phases)
3. Copy root cause categories
4. Add failure→responsibility mapping examples from observed patterns

**Each generated index must include header:**

```
> **Generated by audit skill** - Do not edit manually.
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
```

**Rules**:

- Mark default workflow with "(default)"
- List workflows in order they appear in SKILL.md
- If only one workflow exists, leave sub-workflows column as "—"
- Extract workflow names from `## Workflow: X` headers or `workflows/*.md` filenames

### Phase 8: Persist Report (MANDATORY)

**Every audit MUST save a written report to `$ACA_DATA/qa/aops/`.**

```bash
# Create directory if needed
mkdir -p "$ACA_DATA/qa/aops"

# Generate timestamped filename
REPORT_PATH="$ACA_DATA/qa/aops/audit-$(date +%Y%m%d-%H%M%S).md"
```

Use the Write tool to save the complete audit report (see Report Format below) to `$REPORT_PATH`.

**Report file MUST include:**

- YAML frontmatter with date, duration, and summary stats
- All phase results from Phase 0-7
- Clear pass/fail status for each validation criterion

After writing, confirm: `Audit report saved to: [path]`

### Phase 9: Create bd Issues for Actionable Findings

**Create issues in bd for findings that require human action.**

For each finding from Phases 0-7 that requires action:

1. **Classify finding type** using the mapping below
2. **Run bd create** with appropriate metadata
3. **Track issue IDs** for summary

#### Finding Type → Issue Mapping

| Finding Type                           | Priority | Issue Type | Labels              |
| -------------------------------------- | -------- | ---------- | ------------------- |
| Broken wikilinks                       | P2       | bug        | audit,documentation |
| Orphan files                           | P3       | chore      | audit,cleanup       |
| Skill >500 lines                       | P2       | chore      | audit,refactor      |
| Explanatory content in skill           | P2       | chore      | audit,refactor      |
| Missing from INDEX.md                  | P3       | chore      | audit,documentation |
| Orphan instruction (no RULES.md trace) | P2       | bug        | audit,governance    |
| FLOW.md drift                          | P2       | bug        | audit,documentation |
| Hook→Axiom mismatch                    | P2       | bug        | audit,governance    |

#### bd create Command Pattern

```bash
bd create "[Finding Type]: [specific details]" \
  --type [bug|chore] \
  --priority [2|3] \
  --labels audit,[category] \
  --description "[context from audit]"
```

#### Skip Conditions

Do NOT create issues for:

- **Regenerated indices** (Phase 6 actions) - already handled
- **Pass status** findings - no action needed
- **Justified files** (Phase 4) - no action needed
- **Implicit files** (Phase 4) - acceptable, no action needed

#### Output Summary

After creating issues, add to audit report:

```markdown
### Issues Created

Created N issues in bd:

- beads-xxx: Broken wikilink: [[foo.md]] in bar.md
- beads-yyy: Orphan file: docs/old.md
- beads-zzz: Skill over limit: skills/big/SKILL.md
```

## Report Format

Output a structured report with YAML frontmatter:

```markdown
---
title: Framework Audit Report
date: YYYY-MM-DD HH:MM:SS
duration_minutes: N
summary:
  structure_issues: N
  skill_violations: N
  orphan_files: N
  indices_regenerated: N
  issues_created: N
status: PASS | ISSUES_FOUND
---

# Audit Report

### Structure Issues

- Missing from INDEX.md: skills/foo/
- Broken wikilinks: [[nonexistent.md]] in X.md

### Skill Content Violations

- skills/foo/SKILL.md:45-67 - explanatory content (move to spec)
- skills/bar/SKILL.md - 623 lines (>500 limit)

### Execution Flow Drift

- Hook in code, missing from diagram: unified_logger.py (PostToolUse)
- Hook in diagram, not in router.py: old_hook.py

### Justification Status

**Justified** (N files) - spec exists:

- AXIOMS.md → specs/meta-framework.md
- hooks/user_prompt_submit.py → specs/prompt-enricher.md

**Implicit** (N files) - in docs, no dedicated spec:

- FRAMEWORK.md → JIT-INJECTION.md
- README.md → framework convention

**Orphan candidates** (N files) - no reference found:

- docs/OLD-FILE.md

### Generated Indices Regenerated

- INDEX.md: [N] files mapped
- RULES.md: [N] enforcement mechanisms
- WORKFLOWS.md: [N] task types
- FLOW.md: [N] hooks in flow diagram

### Other Actions Taken

- Updated README.md commands table

### Requires Human Review

- Orphan: docs/OLD-FILE.md - delete or create spec?

### Issues Created

Created N issues in bd:

- beads-xxx: [title]
- beads-yyy: [title]
```

## Output Targets

See [[references/output-targets.md]] for README.md and INDEX.md structure targets.

## Validation Criteria

- README.md < 200 lines
- README.md has "How Enforcement Works" section with Mermaid diagram
- README.md Skills table has "Sub-workflows" column for skills with multiple workflows
- INDEX.md has every directory
- All `→` references resolve
- No broken `[[wikilinks]]`
- All SKILL.md files < 500 lines
- No explanatory content in SKILL.md files
- Orphan count reported (0 ideal)
- `FLOW.md` matches hooks/router.py dispatch table (regenerated via flowchart skill)
- Generated indices (INDEX.md, RULES.md, WORKFLOWS.md, FLOW.md) include "Generated by audit" header
- Generated indices reflect current source file state
- **Hook→Axiom accuracy**: Every hook with "Enforces:" declaration is in RULES.md with correct level (not just "Prompt")
- **Enforcement completeness**: Every axiom with Hard/Soft Gate in RULES.md has a corresponding hook with "Enforces:" declaration
- **Sub-workflow coverage**: Skills with `## Workflow:` headers or `workflows/` subdirectories have all workflows listed in README.md
