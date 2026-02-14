---
id: audit
category: governance
bases: [base-handover]
---

# Audit Workflow

Framework governance audit workflow. Runs structure checking, justification verification, and index regeneration.

## When to Use

**Manual trigger** (recommended):

- After significant framework changes (new skills, hooks, or agents)
- Before major releases or milestones
- When suspecting drift between documentation and implementation

**Session-end** (optional):

- Session end hook can trigger session-effectiveness sub-workflow
- Full governance audit is NOT suitable for session-end (too heavy)

**Periodic** (weekly/monthly):

- Schedule via external cron or reminder
- Run full audit to catch accumulated drift

Do NOT use for:

- Quick sanity checks (use individual scripts instead)
- Session transcript analysis only (use session-effectiveness sub-workflow)

## Invocation

**Full governance audit:**

```
Skill(skill="audit")
```

**Session effectiveness only:**

```
Skill(skill="audit", args="session-effectiveness /path/to/transcript.md")
```

<!-- check for duplication and remove anything here that is covered in the skill. -->

## Workflow Phases

The full audit runs 11 phases (see `skills/audit/SKILL.md` for details):

| Phase | Name                      | Purpose                                                          |
| ----- | ------------------------- | ---------------------------------------------------------------- |
| 0     | Health Metrics            | Run `audit_framework_health.py` for baseline metrics             |
| 1     | Structure Audit           | Compare filesystem to INDEX.md                                   |
| 2     | Reference Graph           | Build reference map, find orphans and broken links               |
| 3     | Skill Content             | Verify size limits (<500 lines) and actionability                |
| 4     | File Justification        | Ensure files trace to specs                                      |
| 4b    | Instruction Justification | Verify instructions trace to framework/enforcement-map.md        |
| 5     | Documentation Accuracy    | Verify README.md flowchart matches hooks                         |
| 6     | Regenerate Indices        | Rebuild INDEX.md, WORKFLOWS.md, etc.                             |
| 7     | Other Updates             | Fix violations, update tables                                    |
| 8     | Persist Report            | Save to `$ACA_DATA/projects/aops/audit/`                         |
| 8b    | Transcript QA             | Scan recent sessions for hydration gaps and operational failures |
| 9     | Create Tasks              | File tasks for actionable findings                               |

## Scripts Reference

Individual checks can be run standalone:

```bash
cd $AOPS

# Full health metrics (Phase 0)
uv run python scripts/audit_framework_health.py -m

# Specific checks
uv run python scripts/check_skill_line_count.py
uv run python scripts/check_broken_wikilinks.py
uv run python scripts/check_orphan_files.py

# Reference graph (Phase 2)
uv run python skills/audit/scripts/build_reference_map.py
uv run python skills/audit/scripts/find_orphans.py

# Transcript QA (Phase 8b)
cd aops-core && uv run python -c "from lib.transcript_error_analyzer import scan_recent_sessions; print(scan_recent_sessions(hours=48).format_markdown())"
```

## Report Output

Reports are saved to: `$ACA_DATA/projects/aops/audit/YYYY-MM-DD-HHMMSS-audit.md`

Format defined in `skills/audit/references/report-format.md`:

- YAML frontmatter with summary stats
- Executive summary
- Phase-by-phase findings
- Human review queue
- Created task IDs

## Constraints

### Completeness

- All 11 phases must run for a full audit
- Partial runs should be documented as such

### No Rationalization

- Report ALL discrepancies found
- Do NOT justify ignoring files as "generated" or "acceptable"
- The user decides what's acceptable, not the auditor

### Evidence Required

- Every finding must cite specific file:line references
- Link to source evidence, not just claims

## Triggers

- Framework change committed → consider manual audit
- Weekly schedule → run periodic audit
- Session end → session-effectiveness sub-workflow only
- Drift suspected → run full audit

## How to Check

- **Audit complete**: All 11 phases executed, report saved
- **Report valid**: Contains YAML frontmatter with summary stats
- **Tasks created**: Actionable findings have corresponding task IDs
- **No skipped phases**: Each phase has findings (even if "no issues found")
