# Issue Triage — 2026-03-30

**Scope**: All 157 open issues in nicsuzor/academicops.
**Method**: Clustered by failure pattern, prioritized by safety impact and fixability.

---

## Priority 1: Safety & Authority Violations (fix or escalate now)

These issues describe agents taking destructive, unauthorized, or out-of-scope actions. They represent the highest-risk failures because they can cause data loss, leak credentials, or damage shared state.

### P1a: Destructive/unauthorized actions — need hard gates

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #382 | Agent pushed cron workflows to 8 repos without confirmation | **Escalate P#50 (Explicit Approval)**: add PreToolUse gate for `gh workflow` / multi-repo push patterns |
| #346 | Bulk destructive ops (83 dirs, 14 branches) without confirmation | **Escalate P#50**: policy_enforcer.py should block `rm -rf` with >N targets and bulk `git branch -D` |
| #323 | Agent leaked OAuth credentials via shell `cat` | **Hard gate**: extend deny rules to block `cat`/`head`/`grep` on known credential paths (`~/.config/gh/`, OAuth token files) |
| #322 | Committed to main instead of feature branch — no branch check | **Escalate P#26 (Verify First)**: add PreToolUse check that `git commit` is not on main/master when a feature branch exists |
| #275 | Force-push after rebase without checking for remote-only commits | Already have `git push --force` block — verify it's active. Add corollary: fetch before force-push |

### P1b: Cross-boundary writes — need deny rules

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #381 | Directly modified plugin cache and dist artifacts | **Verify** `~/.claude/plugins/**` deny rule is active; add `dist/` write block in policy_enforcer.py |
| #311 | Wrote to wrong repo (brain PKB instead of source) | **Escalate**: polecat sandbox already restricts writes to worktree; verify main agent has equivalent guard |
| #229 | Modified upstream library code without authorization | Enforce CORE.md cross-repo safety rule via PreToolUse path check |
| #196 | Edited files outside project scope | Same as #229 — needs path-based enforcement |
| #354 | Manually copied to dist/ instead of build pipeline | Covered by dist/ deny rule if enforced |

### P1c: Scope creep without approval — rule escalation candidates

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #313 | Expanded scope beyond user's 5 explicit requests | **Escalate P#5 (Do One Thing)**: custodiet should detect when agent acts beyond explicit request list |
| #326 | Expanded diagnostic question into multi-file changes | **Escalate P#50**: multi-file writes after a question-only prompt should trigger approval gate |
| #330 | Expanded scope after completing bounded directive | Same pattern as #313 — custodiet drift detection |
| #316 | Made config changes without user consent | **Escalate P#50**: config file modifications should require explicit approval |
| #351 | Changed global pytest config without blast-radius analysis | **Escalate P#41 (Plan-First)**: changes to shared config files need plan-mode |
| #342 | Ignored explicit user redirection to design-mode | **Escalate P#5**: user redirection is binding — add to AXIOMS.md as P#5 corollary |

---

## Priority 2: Custodiet System (the compliance checker is itself broken)

Custodiet is the primary runtime enforcement mechanism, but it has multiple bugs that undermine the entire enforcement layer. Fixing custodiet has outsized leverage.

### P2a: Critical custodiet bugs

| Issue | Summary | Fix Type |
|-------|---------|----------|
| #319 | Fires mid-work and falsely BLOCKs partial progress | **Code fix**: add phase-awareness — don't evaluate incomplete work as final |
| #314 | Returns CANNOT_ASSESS with empty session narrative for entire sessions | **Code fix**: session narrative extraction is broken — debug transcript parser |
| #338 | WARN verdicts have no behavioral effect on main agent | **Escalate to hard gate**: WARN must inject context or block, not just log |
| #331 | Re-reads entire audit file every invocation — O(n²) tokens | **Code fix**: cache or truncate audit file; only read incremental changes |
| #341 | Checks process compliance but not substantive correctness | **Design**: add content verification (not just "did they follow steps") |

### P2b: Custodiet false positives / gaps

| Issue | Summary | Fix Type |
|-------|---------|----------|
| #176 | P#41 false positives on direct user requests | **Code fix**: exempt explicit user directives from plan-mode requirement |
| #292 | Ignores tool return values (AskUserQuestion, ExitPlanMode) | **Code fix**: parse tool results in session narrative |
| #383 | Fails to enforce axiom against single-use test files | **Rule addition**: detect `/tmp/test_*.py` pattern as P#24 violation |
| #291 | Should detect '-v2' filename anti-pattern | **Rule addition**: add filename pattern check |
| #186 | Audit narrative missing ExitPlanMode approval confirmation | **Code fix**: include ExitPlanMode in narrative extraction |
| #368 | Missed plan-mode requirement for bulk editorial task | **Threshold**: define what "bulk" means (>N files?) for P#41 trigger |

---

## Priority 3: Verification & Testing Failures (agents ship broken work)

Systematic pattern: agents declare success without adequate verification. This undermines trust in all agent output.

### P3a: False-passing / skipped tests

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #359 | Shipped false-passing tests without verifying output semantics | **Escalate P#27 (No Excuses)**: add heuristic "verify test assertions match expected behavior" |
| #350 | Flaky test converted to `pytest.skip`, masking regressions | **Escalate P#82**: `pytest.skip` on failure is a P#82 violation — add to custodiet detection |
| #391 | Changed `pytest.fail` to `pytest.skip` despite explicit instruction | **Escalate P#5**: ignoring explicit instruction is already a P#5 violation — needs stronger enforcement |
| #235 | PR merged with untested code path | **CI enforcement**: require coverage for new parameters in PR pipeline |
| #324 | Filed PR with known-failing tests without flagging | **Escalate P#27**: PR description must declare test status |

### P3b: Verification skipped entirely

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #335 | Skipped entire post-work phase (tests + QA) on 6-file change | **Escalate**: stop gate already requires QA — verify it's functioning |
| #396 | Shallow-checked PR then asked instead of acting | **Heuristic**: "make sure ready" means verify all checks, not spot-check |
| #376 | Declared diagnosis complete without reproduction | **Escalate P#26**: diagnosis requires reproduction evidence |
| #380 | Substituted passing test when requested test fails | **Escalate P#5**: test substitution is scope drift |
| #320 | Skipped visual verification for UI code | **Heuristic**: UI changes require screenshot/visual confirmation |
| #308 | Verification loop doesn't enforce testing against production data | **Heuristic**: test against real data when available |

---

## Priority 4: Agent Reasoning Failures (systemic patterns)

These are instruction-level fixes — most don't need hard gates but need clearer rules or heuristics.

### P4a: Investigation before action

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #373 | Jumps to fix proposals before understanding symptoms | **Heuristic**: "diagnose before prescribing" — read all error context first |
| #374 | Rationalizes visual anomalies instead of investigating | **Heuristic**: user-reported anomaly = investigate, don't explain away |
| #318 | Shotgun-debugs 2h without reproducing failure | **Escalate P#26**: reproduce before fixing — add to AXIOMS.md corollary |
| #362 | Iterates fix-test cycles instead of analyzing error output | **Heuristic**: read error output completely before attempting fix |
| #361 | Applied speculative fix without testing hypothesis | **Heuristic**: state hypothesis, test it, then fix |
| #317 | Asserts model capabilities without evidence | **Escalate P#3**: claims about external systems require evidence |

### P4b: User intent failures

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #337 | Invested 1h in plan without clarifying ambiguous intent | **Escalate**: existing heuristic `user-intent-discovery` not being followed |
| #357 | Guesses at user concern instead of clarifying via HALT | Same as #337 — reinforce `use-askuserquestion` heuristic |
| #353 | Proposed wrong fix before articulating design approach | **Heuristic**: state approach before implementing |
| #367 | Substituted mechanical append for editorial synthesis | **Escalate P#5**: "merge" means synthesize, not append |
| #277 | QA agent produces pass/fail checklist when qualitative assessment requested | **Escalate P#115**: qualitative-evaluation-over-quantitative already exists — needs enforcement |
| #140 | P#5 corollary for intent substitution | **Rule escalation**: intent substitution is a P#5 violation — formalize as corollary |

---

## Priority 5: Task & Workflow Management Gaps

These cause dropped threads and lost work tracking.

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #329 | 2.5-hour session with no task tracked | **Escalate**: stop gate should detect "no task claimed" for substantial sessions |
| #360 | /dump skips historical task creation | **Code fix**: /dump skill instruction compliance |
| #309 | Agents should file tool issues at point of discovery | **Heuristic**: "file-at-discovery" pattern |
| #86 | No guardrail for external dependency tracking | **Heuristic**: external dependency → create waiting task |
| #133 | Observation-without-task is a dropped thread (P#27) | **Escalate P#27 corollary**: every identified problem → PKB task |
| #200 | Agent bypasses /remember skill, writes directly to MEMORY.md | **Already enforced** via MCP tool injection — verify it's active |
| #232 | Saves learnings to ephemeral MEMORY.md on disposable containers | Same as #200 — verify enforcement |
| #327 | /remember captures unvalidated hypotheses as facts | **Escalate P#3**: memories must be validated before persistence |
| #349 | /dump uses H4 instead of required H2 — breaks parser | **Code fix**: simple format compliance |

---

## Priority 6: Infrastructure & Tooling Bugs (concrete fixes)

| Issue | Summary | Complexity |
|-------|---------|------------|
| #5 | Hydration deadlock — subagent blocked by its own hook | Medium — whitelist prompt-hydrator in hook logic |
| #102 | router.sh UV_CACHE_DIR blocks Claude in Docker | Low — fix already described in issue |
| #194 | transcript.py missing from plugin dist | Low — add to build manifest |
| #167 | Auditor agent prompt has unsubstituted GHA template variables | Low — fix template |
| #244 | repo-sync-cron silently swallows push/fetch failures | Low — remove `2>/dev/null` |
| #339 | Dead task_add.py reference in 9 of 11 files | Low — bulk find-and-replace |
| #325 | Agent uses interactive shell commands in non-interactive env | Already covered by P#55 — verify enforcement |
| #355 | Crew resume sync --ff-only fails on crew branches | Medium — change merge strategy |
| #266 | botnicbot PRs blocked by CI requiring manual approval | Low — add bot to trusted actors |
| #222 | Cancelled PR run can leave stale APPROVED review | Medium — add review staleness check |
| #253 | Docker E2E tests fail in DooD environment | Medium — staging path resolution |
| #334 | Butler post-work lacks branch+PR workflow for multi-file changes | Medium — skill instruction update |

---

## Priority 7: Subagent & Polecat Efficiency

| Issue | Summary | Proposed Action |
|-------|---------|-----------------|
| #344 | Explorer subagent wastes 69K tokens on file discovery | **Heuristic**: use Glob/Grep before spawning Explore agents |
| #336 | 3 redundant Explore agents reading same files | **Heuristic**: deduplicate subagent dispatch |
| #343 | Spawns subagent for simple in-repo investigation | **Heuristic**: direct tools first, subagent only for complex queries |
| #390 | Subagent checks upstream defaults instead of user's actual config | **Escalate P#26**: verify against user state, not defaults |
| #352 | Parallel tool call cancellation cascade | Platform limitation — document workaround |
| #304 | Systemic zero-output polecat dispatches | **Gate**: add readiness check before dispatch |
| #97 | Burst-supervisor dispatches all workers to same repo | **Code fix**: per-item project field in burst queue |
| #96 | Gemini polecat reasoning loop on ambiguous task | **Code fix**: add circuit breaker for stuck agents |
| #306 | Polecat project routing not discoverable | **Documentation**: make routing mechanism explicit |

---

## Priority 8: Enhancements & Scale

| Issue | Summary | Priority |
|-------|---------|----------|
| #83 | Scale sleep cycle for 1000+ task graph | Medium-term |
| #297 | Sleep skill lacks convergence detection | Medium-term |
| #312 | Sleep cycles commit bulk to main bypassing review | **Escalate**: sleep should use branch+PR for bulk changes |
| #258 | Task status transitions should capture provenance | Enhancement |
| #268 | Supervisor task state grows unbounded | Cleanup needed |
| #300 | /loop re-injects full skill prompt every fire — token waste | Optimization |
| #204-207 | PKB temporal filtering, synthesis triggers, chunking | Design decisions needed |

---

## Rule Escalation Summary

Rules that need to move up the enforcement hierarchy based on repeated failures:

| Current Level | Proposed Level | Rule | Evidence (issues) |
|---------------|---------------|------|-------------------|
| Prompt (AXIOMS.md) | **Hard gate** (PreToolUse) | P#50: Explicit Approval for bulk/destructive ops | #382, #346, #326, #316 |
| Prompt (AXIOMS.md) | **Hard gate** (PreToolUse) | P#26: Verify branch before commit | #322 |
| Prompt (AXIOMS.md) | **Deny rule** | P#6: Block credential file reads via shell | #323 |
| Prompt (AXIOMS.md) | **Custodiet detection** | P#5: Scope drift after user redirection | #313, #330, #342 |
| Prompt (AXIOMS.md) | **Custodiet detection** | P#3: Claims about external systems need evidence | #317, #283, #299 |
| Heuristic | **Axiom corollary** | P#26: Reproduce before fixing | #318, #376, #361 |
| Heuristic | **Axiom corollary** | P#5: Intent substitution = violation | #140, #367 |
| Heuristic | **Axiom corollary** | P#27: Observation without task = dropped thread | #133, #329 |
| Advisory (warn) | **Hard gate** (block) | Custodiet WARN verdicts | #338 |
| Prompt | **Stop gate check** | No-task-claimed detection for substantial sessions | #329, #360 |
| Heuristic | **Axiom** | P#82: `pytest.skip` on failure = violation | #350, #391 |
| Prompt | **Hard gate** | P#97: Block writes to dist/ | #354, #381 |

---

## Recommended Execution Order

1. **Custodiet fixes** (P2a) — highest leverage; fixes the enforcement mechanism itself
2. **Hard gate additions** (P1a) — prevent the most dangerous failures
3. **Deny rule extensions** (P1b) — prevent cross-boundary writes
4. **Infrastructure fixes** (P6, low-complexity items) — quick wins
5. **Rule escalations** — formalize corollaries for P#5, P#26, P#27
6. **Heuristic additions** (P4a/P4b) — improve agent reasoning patterns
7. **Subagent efficiency** (P7) — reduce token waste
8. **Enhancements** (P8) — scale and optimization
