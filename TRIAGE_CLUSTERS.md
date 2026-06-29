# Issue Triage Clusters

## Fix coordinator interaction and delegation patterns

This issue tracks a cluster of related bugs where the coordinator agent fails to properly delegate tasks, surfaces raw decisions to the user without context, or proposes wrong-altitude solutions.

### Related Issues

- #1950: Bug: coordinator surfaces a deferred-action notice in closing text instead of executing the action — 'should do' pattern
- #1916: Bug: coordinator's user-facing chat register is dense/completeness-first by default — scannable plain-language catch-up reserved for on-demand, forcing the principal to scroll and correct
- #1912: Bug: default-to-code reflex — coordinator proposed BUILDING software for a pure judgment+tool-use workflow (wrong altitude of solution)
- #1910: Bug: coordinator's second-iteration decision presentation gives a dangling 'it's saved' locator and withholds the held content the user needs to decide
- #1909: Bug: coordinator surfaces a user-facing decision as a bare option list, stripping the catch-up context a cold/context-switched user needs to decide
- #1875: Bug: coordinator executes/investigates downstream work inline instead of dispatching it — delegation discipline is advisory, not bound at directive-receipt
- #1826: Bug: coordinator originates framework doctrine and self-authorises a spec change
- #1737: Bug (instance of #1122 cluster): coordinator fixates on tractable technical sub-problem instead of the judgment-heavy task the user actually set

## Fix PKB MCP integration and state management

This issue tracks a cluster of related bugs involving the Personal Knowledge Base (PKB) MCP, including missing features, environment binding failures, and data writeback issues.

### Related Issues

- #2012: Bug: PKB MCP server fails to start in worktree sessions (pkb_mcp_url userConfig bound to wrong plugin-instance alias; no env fallback)
- #2002: Bug: declared mcp__plugin_aops-core_pkb__* namespace not registered at runtime in orchestrator AND subagent — PKB writes forced through subagent dispatch + CLI fallback (derived: no CLI body-replace)
- #1975: Bug: durable-capture stops at /tmp scratch and reports 'durable state saved' when only a pointer (not the content) is persisted; durable PKB write gated behind a user command
- #1949: Bug: PKB MCP has no created-date query; task_search since=/before= are accepted but silently ignored (no-op)
- #1925: PKB tool-contract drift: create_memory/create_task reject documented enum/field values
- #1904: Bug: PKB resolver infers false hierarchy from shared ID prefix — auto-generated child IDs (project-stem + suffix) mis-parsed as channel-under-channel nesting
- #1751: Bug: stale PKB note overrides explicit user correction + primary source; agent disbelief persists across two sessions
- #1714: Bug: PKB narrative anchors silently drift from repo ground truth on interactive research projects — no reconcile mechanism, no writeback, no project-resume entrypoint

## Fix hook triggers, RBG enforcer, and gate logic

This issue tracks a cluster of related bugs where framework hooks, RBG enforcer rules, or gate logic either fail to trigger correctly, trigger falsely, or bypass expected checks.

### Related Issues

- #2019: Bug: RBG audit returns PASS while an un-proofed load-bearing assumption drives the plan and a dispatched worker brief
- #2018: Bug: slash-command/goal-hook inlines a skill's full procedure as prose, which substitutes for invoking the Skill tool (agent executes supervision inline)
- #2013: Bug: single-source-of-truth enforcer prescribes convergence (make copies agree) instead of consolidation — entrenches the DRY violation it detected
- #1995: Bug: criterion-substitution survives the honesty/ida Stop-gate via self-graded ritual
- #1986: Bug: reconstructing per-client hook behaviour took ~47 throwaway probe sessions because the parametrised live-conformance harness didn't exist until the same day (no reusable manual-probe surface, cf #1058)
- #1985: Bug: per-client hook-capability beliefs are version-stamped once and never re-measured across client upgrades — 'Claude Stop rejects additionalContext' stayed pinned at v2.1.158 and went stale by v2.1.191
- #1984: Bug: months of hook-delivery debugging used the wrong observable (transcript-grep vs model-echo), letting a false 'agy delivery gap' belief persist and reach router code + a commit
- #1978: Bug: Ida Stop-hook's recently-sharpened content prescription (restate-request / recommendation-first / observed-vs-inferred / scannable recap) is a delivered-work register that mis-fits per-step interactive sessions and manufactures the exact meta-commentary the user rejects
- #1976: Enforcer audit: audit-complete sentinel buried mid-file → guaranteed false COVERAGE_INCOMPLETE; verdict also decoupled from gate
- #1975: Bug: durable-capture stops at /tmp scratch and reports 'durable state saved' when only a pointer (not the content) is persisted; durable PKB write gated behind a user command
- #1972: Bug: subagent_type:fork inherits full orchestrator context, drifts to next-planned artifact instead of delegated task, and self-reports in first person — delegated deliverable never produced, caught only by repo-state verification
- #1971: Bug: orchestrator delegates index-mutating subagent while holding uncommitted overlapping changes — concurrent pre-commit stash race silently aborts commits + near-miss staging contamination
- #1969: Bug: agent front-runs explicit interactive 'load context only / wait for approval' contract — emits unrequested five-phase plan + AskUserQuestion immediately after context load; third pre-warned recurrence; stop-hooks add act-now pressure during sanctioned wait
- #1923: CI must fail loud on workflow startup_failure (admission gate was silently dead Jun 17–22)
- #1901: Bug: halt-on-failure axiom breach (self-authorised workaround) escaped review — enforcer/RBG trigger blind to narrated, sub-threshold workarounds
- #1878: Enforcer compliance hook races mutating tool calls → false rbg REVISE verdicts
- #1875: Bug: coordinator executes/investigates downstream work inline instead of dispatching it — delegation discipline is advisory, not bound at directive-receipt
- #1864: Bug: /pull freshness gate has no merged-PR-but-open-task check — dispatcher relays stale merge_ready verbatim instead of flagging the contradiction
- #1850: Bug: supervisor uses `partial` for human-gate terminal state; no durable queue entry created
- #1839: Bug: scope-narrowing survives both RBG enforcer audit and stop-hook honest-delivery gate
- #1819: Bug: sanctioned QA harness not discoverable from artifact's own task/spec bodies — ORIENT depended on an out-of-band hook; canonical pointer note also records a dead path

## Fix subagent dispatch and worker environment isolation

This issue tracks a cluster of related bugs regarding subagent delegation, where subagents inherit too much context, corrupt shared state, or fail to bind correctly during dispatch.

### Related Issues

- #2019: Bug: RBG audit returns PASS while an un-proofed load-bearing assumption drives the plan and a dispatched worker brief
- #2002: Bug: declared mcp__plugin_aops-core_pkb__* namespace not registered at runtime in orchestrator AND subagent — PKB writes forced through subagent dispatch + CLI fallback (derived: no CLI body-replace)
- #1972: Bug: subagent_type:fork inherits full orchestrator context, drifts to next-planned artifact instead of delegated task, and self-reports in first person — delegated deliverable never produced, caught only by repo-state verification
- #1971: Bug: orchestrator delegates index-mutating subagent while holding uncommitted overlapping changes — concurrent pre-commit stash race silently aborts commits + near-miss staging contamination
- #1951: [retro] Two structural failures: narrated-not-executed housekeeping + subagent mislabels clear bug as design call
- #1935: RCA: ad-hoc related tasks dispatched as separate PRs, producing contradictions
- #1875: Bug: coordinator executes/investigates downstream work inline instead of dispatching it — delegation discipline is advisory, not bound at directive-receipt
- #1864: Bug: /pull freshness gate has no merged-PR-but-open-task check — dispatcher relays stale merge_ready verbatim instead of flagging the contradiction
- #1844: Bug: program-supervision charter dispatched to a single ephemeral polecat worker (altitude/category misroute)
- #1841: Bug: dispatch piped through `| head` masks failed bind behind pipeline exit 0 (silent misbind)
- #1822: Bug: prep-only / "reviewable diff" brief read as "leave work uncommitted+unpushed" — dispatched worker withholds completed work
- #1773: Bug: agy print-mode dispatch silently misbinds prompt — exits 0 with conversational reply, costing a full background dev-loop iteration
