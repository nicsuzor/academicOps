---
name: audit
category: instruction
description: Framework index curation and acceptance testing. Ensures documentation stays in sync with implementation.
allowed-tools: Read,Glob,Grep,Edit,Write,Bash,Skill,TodoWrite
version: 6.0.0
permalink: skills-audit
---

# Framework Audit Skill

Simplified audit focused on keeping framework indices up to date and running acceptance tests.

## Workflow Entry Point

**IMMEDIATELY call TodoWrite** with the following items, then work through each one:

```
TodoWrite(todos=[
  {content: "Phase 1: Structure audit - sync filesystem to INDEX.md", status: "pending", activeForm: "Auditing structure"},
  {content: "Phase 2: Index curation - update SKILLS.md, WORKFLOWS.md, AXIOMS.md, HEURISTICS.md, and enforcement-map.md", status: "pending", activeForm: "Curating indices"},
  {content: "Phase 3: Documentation accuracy - update README.md flowchart and tables", status: "pending", activeForm: "Updating documentation"},
  {content: "Phase 4: Acceptance Tests - run agent-driven e2e tests in tests/acceptance/", status: "pending", activeForm: "Running acceptance tests"},
  {content: "Phase 5: Persist report - save to $ACA_DATA/projects/aops/audit/YYYY-MM-DD-HHMMSS-audit.md", status: "pending", activeForm: "Persisting report"}
])
```

## Phase Instructions

### Phase 1: Structure Audit

Compare filesystem to `INDEX.md`:

1. **Scan filesystem**: `find . -type f -not -path "*/.git/*" -not -path "*/__pycache__/*" | sort`
2. **Update INDEX.md**: Add missing files and remove stale entries.
3. **Verify wikilinks**: Check for broken `[[...]]` links and report them in the final report.

### Phase 2: Index Curation

Curate root-level index files using LLM judgment. For each file, read the source materials and ensure it accurately reflects the current state.

| Index File         | Sources                                               |
| ------------------ | ----------------------------------------------------- |
| AXIOMS.md          | `axioms/*.md` files                                   |
| HEURISTICS.md      | `heuristics/*.md` files                               |
| SKILLS.md          | `skills/*/SKILL.md` frontmatter                       |
| WORKFLOWS.md       | `workflows/*.md`, `skills/*/workflows/*.md`           |
| enforcement-map.md | `hooks/*.py` "Enforces:" docstrings, `gate_config.py` |

**Generated File Header**:
Each curated index (except WORKFLOWS.md) must include:
`> **Curated by audit skill** - Regenerate with Skill(skill="audit")`

### Phase 3: Documentation Accuracy

1. **README.md Flowchart**: Invoke `Skill(skill="flowchart")` to regenerate the core loop flowchart from `hooks/router.py` and `gate_config.py`.
2. **README.md Tables**: Update Commands, Skills, and Hooks tables in README.md to match current files.
   - For skills with multiple workflows, include them in a "Sub-workflows" column.

### Phase 4: Acceptance Tests

Run agent-driven e2e tests defined in `tests/acceptance/`.

1. **Locate tests**: Find all `.md` files in `tests/acceptance/`.
2. **Execute tests**: Follow the instructions in each test file (read test case, execute via specified method, evaluate pass criteria).
3. **Record results**: Capture PASS/FAIL status and notes for the final report.

Refer to [[references/acceptance-tests]] for instructions on how to add/format these tests.

### Phase 5: Persist Report (MANDATORY)

Save a complete audit report to `$ACA_DATA/projects/aops/audit/`.

```bash
mkdir -p "$ACA_DATA/projects/aops/audit"
REPORT_PATH="$ACA_DATA/projects/aops/audit/$(date +%Y-%m-%d-%H%M%S)-audit.md"
```

Report format:
- YAML frontmatter with date and summary stats.
- Results from each phase.
- Acceptance test results table.
- List of broken wikilinks or other issues requiring human attention.

## Specialized Workflows

### Session Effectiveness Audit

Qualitative assessment of session transcripts to evaluate framework performance.

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

Workflow defined in `workflows/session-effectiveness.md`.
