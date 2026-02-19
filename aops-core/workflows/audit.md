---
id: audit
category: governance
bases: [base-handover]
---

# Audit Workflow

Simplified framework governance audit. Focuses on index curation and running acceptance tests.

## When to Use

**Manual trigger** (recommended):

- After significant framework changes (new skills, hooks, or agents)
- Before major releases or milestones
- To ensure documentation and indices are in sync with the filesystem

**Session-end** (optional):

- Session end hook can trigger session-effectiveness sub-workflow
- Full audit is NOT suitable for session-end (too heavy)

## Invocation

**Full audit:**

```
Skill(skill="audit")
```

**Session effectiveness only:**

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

## Workflow Phases

The full audit runs 5 phases (see `skills/audit/SKILL.md` for details):

| Phase | Name                   | Purpose                                                     |
| ----- | ---------------------- | ----------------------------------------------------------- |
| 1     | Structure Audit        | Sync filesystem to INDEX.md                                 |
| 2     | Index Curation         | Update SKILLS.md, WORKFLOWS.md, AXIOMS.md, HEURISTICS.md    |
| 3     | Documentation Accuracy | Update README.md flowchart and tables                       |
| 4     | Acceptance Tests       | Run agent-driven e2e tests in tests/acceptance/             |
| 5     | Persist Report         | Save audit report to `$ACA_DATA/projects/aops/audit/`       |

## Report Output

Reports are saved to: `$ACA_DATA/projects/aops/audit/YYYY-MM-DD-HHMMSS-audit.md`

Format defined in `skills/audit/references/report-format.md`:

- YAML frontmatter with summary stats
- Executive summary
- Phase-by-phase findings
- Acceptance test results
- Human review queue

## Constraints

### Completeness

- All 5 phases must run for a full audit

### No Rationalization

- Report ALL discrepancies found
- Do NOT justify ignoring files as "generated" or "acceptable"
- The user decides what's acceptable, not the auditor

### Evidence

- Every finding must cite specific file:line references
- Link to source evidence, not just claims
