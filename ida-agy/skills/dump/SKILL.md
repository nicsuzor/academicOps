---
name: dump
description: Session exit and handover -- commit and push work, release claimed PKB tasks, and emit a final report. Use when completing, pausing, or handing off a session.
---

# Dump -- Session Exit

Finalize session work and provide a structured handover before exit.

## Handover Process

### 1. Save and Push Work

1. Commit all modified files. If work is incomplete, describe what is partial in the commit message.
2. Push commits to the remote branch (`git push`).
3. For pull requests (`gh pr create`), target the diverged base branch (e.g. `--base "${BASE_BRANCH:-${POLECAT_BASE_BRANCH}}"`).
4. Record the branch name and commit SHA in the final report.

### 2. Release Claimed Tasks

For each claimed task (releasing child tasks first), call `pkb.release_task` (the `services` MCP server's code-mode interface: `listToolFiles` → `readToolFile("servers/pkb.pyi")` → `executeToolCode` calling `pkb.release_task(...)`) with the appropriate terminal status:

- `done`: All acceptance criteria are fully met with verified evidence.
- `partial`: Agent work remains -- a scope seam, an external dependency, or a missing tool. A follow-up task carries the remainder; record it under Next.
- `review`: Only when the next step is a decision only Nic can make. Name that decision in the required `reason` as a question for Nic. A pending agent step (QA run or re-run, merge, deploy, retry, routing or dispatch call) is `partial`, never `review`.
- `cancelled`: Task is obsolete or invalidated. Document reason.
- `in_progress`: Use only if an active successor session is immediately continuing work.
- Wire directed `blocks` edges to represent dependencies.

Task report format:

```markdown
### Task: <task-id> (<title>) -- <status>

- **Update**: [1-3 sentences on work completed and remaining]
- **Output**: [Branch, commit SHA, PR link, or artifact path]
- **Next**: [Clear instructions for successor agent]
```

If the release tool is unavailable, record the failure trace and list claimed task IDs in the final report.

### 3. Emit Final Handover Report

Compile the overall session outcome:

```markdown
## Handover: <agent> <session-id>

1. **Task**: Restatement of original objective and scope.
2. **Summary**: Concise synthesis of findings and modifications.
3. **Verdict & Safeguards**:
   - VERDICT: <PASS | PARTIAL | FAIL | BLOCKED | NEEDS-PRINCIPAL>
   - GATE: <the acceptance criterion tested, and observed result against it>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <did a clean-room/differential control run? result? -- or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Receipts** (Claim Ledger): The load-bearing claims as a claim ledger, written per the `claim-ledger` skill.
6. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
```
