---
id: subagent-return-hook-spec
title: Specification — Deterministic Evidence Check Hook at Subagent-Return Boundary
type: spec
status: ready
tags: [enforcement, hooks, subagents, evidence-contract, verification]
---

# Specification: Deterministic Evidence Check Hook at Subagent-Return Boundary

This specification defines the deterministic hook mechanism for intercepting subagent reports at the exact moment of return into a controlling agent's context, evaluating the presence of checkable evidence on the face of the report, and enforcing immediate rejection of unevidenced claims before they can be relayed, acted upon, or written to the knowledge graph.

## 1. Problem Statement & Operational Objective

### The Incident Pattern (2026-08-21)

During orchestration runs, controlling agents repeatedly accepted and propagated unevidenced negative claims returned by subagents or forks:

1. **Unchecked Tooling Negation**: A fork asserted _"This context has no dispatch surface — no Agent tool, no shell"_ without attempting the tools; zero error records existed because no execution was attempted.
2. **Premature Latency Negation**: A task node inspected ~90s after container spawn showed no claim yet, and was reported to the user as _"the dispatch failed silently"_ while the container was running normally.
3. **Unsearched Anomaly Negation**: Subagents returning empty idle notifications (a documented harness behavior since 2026-08-16) were diagnosed as novel defects without searching prior knowledge.

### Objective

Provide a zero-cost, deterministic surface check at the exact instant a subagent report enters the controlling agent's context:

> **Core Invariant**: Does every load-bearing claim in this report have checkable evidence attached on the face of it? If not, it goes back immediately — before it is relayed to the user, acted upon, or written to the knowledge graph.

This check does not verify semantic truth or run empirical investigations; it checks solely for the _structural presence_ of primary evidence (command + output, file:line, resolving URL, quoted source, or explicit reproduction query) accompanying load-bearing assertions.

## 2. Client Hook Architecture & Event Mapping

Deterministic non-hook code execution is structurally impossible at the native subagent return boundary because client runtimes directly pass subagent text returns to model prompt assembly without invoking intermediary user code. Therefore, the hook lifecycle is the sole deterministic interception boundary.

### A. Claude Code Implementation Specification

| Attribute                    | Specification                                                                                                                                                                                                                                                                                                             |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Canonical Event**          | `PostToolBatch` (and `PostToolUse` for per-tool granularity)                                                                                                                                                                                                                                                              |
| **Target Client**            | Claude Code                                                                                                                                                                                                                                                                                                               |
| **Recipient Audience**       | Controlling Orchestrator Agent (e.g. `ida`, `james`, or session controller)                                                                                                                                                                                                                                               |
| **Firing Timing**            | Synchronously after a tool execution batch completes, immediately before prompt generation for the next turn                                                                                                                                                                                                              |
| **Wire Payload (`stdin`)**   | JSON containing `tool_calls: [{"tool_name": "Agent", "tool_input": {...}, "tool_use_id": "...", "tool_response": "<subagent output string>"}, ...]` along with `session_id`, `agent_type`, `transcript_path`, and `cwd`                                                                                                   |
| **Deterministic Action**     | 1. Filter `tool_calls` for `tool_name == "Agent"`.<br>2. Extract `tool_response` text.<br>3. Execute deterministic surface evidence scan (presence of evidence markers vs unevidenced negative assertions).<br>4. If unevidenced claims are detected, emit advisory payload with `additionalContext` and `systemMessage`. |
| **Injected Response Format** | `{"hookSpecificOutput": {"hookEventName": "PostToolBatch", "additionalContext": "<REJECTION NOTICE & DIRECTIVE>"}, "systemMessage": "<USER-FACING NOTICE>"}`                                                                                                                                                              |
| **Evidence of Existence**    | Documented in `specs/ARCHITECTURE.md` (lines 205, 241, 246) and implemented in `lib/hooks/dispatch.py` (`HookContext.tool_calls`, `CONTINUATION_EVENTS`). Verified in Claude Code 2.1.x hook schemas.                                                                                                                     |

### B. Antigravity (`agy`) Implementation Specification

| Attribute                    | Specification                                                                                                                                                                                                                                                                                                                        |
| :--------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Canonical Event**          | `PreInvocation` (with transcript step inspection)                                                                                                                                                                                                                                                                                    |
| **Target Client**            | Antigravity (`agy`)                                                                                                                                                                                                                                                                                                                  |
| **Recipient Audience**       | Active Controlling Agent                                                                                                                                                                                                                                                                                                             |
| **Firing Timing**            | Immediately before model invocation begins, following subagent message receipt or task tool completion                                                                                                                                                                                                                               |
| **Wire Payload (`stdin`)**   | JSON containing `invocationNum`, `initialNumSteps`, `transcriptPath`, `conversationId`, `workspacePaths`, `modelName`                                                                                                                                                                                                                |
| **Deterministic Action**     | 1. Read trailing entries from `transcriptPath` (`transcript.jsonl`).<br>2. Identify incoming subagent messages or tool return steps (e.g., from `invoke_subagent` or task completion).<br>3. Execute deterministic surface evidence scan.<br>4. If unevidenced claims are detected, return `injectSteps` with an `ephemeralMessage`. |
| **Injected Response Format** | `{"injectSteps": [{"ephemeralMessage": "<REJECTION NOTICE & DIRECTIVE>"}]}`                                                                                                                                                                                                                                                          |
| **Evidence of Existence**    | Documented in the Antigravity hooks specification (`hooks.json` contract for `PreInvocation`). Supported by `agy` 1.1.x runtime.                                                                                                                                                                                                     |

## 3. Surface Detection Logic (The Deterministic Evidence Checker)

The hook implementation executes lightweight regex and structural heuristics over the candidate subagent report text:

```python
import re

NEGATIVE_CLAIM_PATTERNS = [
    r"(?i)\b(no|not|neither|none)\b.*\b(dispatch surface|agent tool|shell|bash|tools? available)\b",
    r"(?i)\b(failed silently|never started|not running|timed out)\b",
    r"(?i)\b(novel defect|unknown bug|does not exist|not found in kb|no prior record)\b",
    r"(?i)\b(cannot find|unable to find|unsupported|impossible to)\b",
]

EVIDENCE_MARKERS = [
    r"`[^`]+`",                          # Inline command or code citation
    r"(?i)(exit code|status|stdout|stderr):\s*\d+", # Command execution output
    r"[\w\-\./]+\.\w+:\d+(?:-\d+)?",    # file:line pinpoint citation
    r"https?://\S+",                     # Resolving URL
    r"(?i)(query|searched for):\s*\"[^\"]+\"", # Explicit search query cited
    r"aops_[a-f0-9]{8}",                 # PKB node / task identifier
]

def check_report_evidence(report_text: str) -> tuple[bool, str]:
    """Returns (is_compliant, violation_reason)."""
    has_negative_claim = any(re.search(p, report_text) for p in NEGATIVE_CLAIM_PATTERNS)
    has_evidence = any(re.search(e, report_text) for e in EVIDENCE_MARKERS)
    
    if has_negative_claim and not has_evidence:
        return False, "Report asserts negative claims without attaching checkable command output, search query, or pinpoint citation."
    return True, ""
```

## 4. Coverage of the Three 2026-08-21 Failure Cases

1. **Case 1: "No dispatch surface / no Agent tool / no shell"**
   - _Detection_: Matches `NEGATIVE_CLAIM_PATTERNS` ("no dispatch surface / no Agent tool").
   - _Evidence Check_: Report contains zero command executions, zero tool attempts, and zero error outputs.
   - _Hook Action_: Fires immediately upon receipt of `Agent` response in `PostToolBatch` / `PreInvocation`, injecting a mandatory rejection directive. The controller is blocked from adopting the claim or relaying it to Nic.

2. **Case 2: "Dispatch failed silently" based on 90s observation delay**
   - _Detection_: Matches `NEGATIVE_CLAIM_PATTERNS` ("failed silently").
   - _Evidence Check_: Report shows no container inspection command (`docker inspect`, `docker ps`, `tmux ls`), only a single early read of a task node.
   - _Hook Action_: Injects rejection directive citing missing container process audit before asserting failure.

3. **Case 3: Empty idle notification diagnosed as novel defect**
   - _Detection_: Matches `NEGATIVE_CLAIM_PATTERNS` ("novel defect / does not exist").
   - _Evidence Check_: Report cites no prior KB search query (`pkb__search`) or historical defect search.
   - _Hook Action_: Injects rejection directive requiring explicit KB query citation before classifying an observation as novel.

## 5. Non-Hook Alternatives Evaluated and Findings

| Mechanism                                              | Class        | Boundary             | Determinism                          | Verdict                                                                                                 |
| :----------------------------------------------------- | :----------- | :------------------- | :----------------------------------- | :------------------------------------------------------------------------------------------------------ |
| **Agent Prompt Prose (`ida.md`)**                      | Instruction  | Model Context        | Non-deterministic (Model discretion) | **Rejected**: Failed 3x on 2026-08-21; prompt text is frequently skipped during generation.             |
| **Standing Axioms (`lib/axioms/`)**                    | Rule Channel | Global System Prompt | Non-deterministic (Model discretion) | **Inadequate as sole gate**: Present on every turn, but relies on model compliance.                     |
| **Custom Tool Wrapper (`pc`)**                         | Structural   | Tool CLI             | Deterministic                        | **Partial**: Guards container launches via `pc`, but blind to native `Agent` / `invoke_subagent` calls. |
| **Task Boundary (`release_task`)**                     | Task Graph   | Task Close           | Deterministic (Presence check)       | **Wrong Boundary**: Fires at task release, after claims have already leaked to chat or graph.           |
| **Lifecycle Hook (`PostToolBatch` / `PreInvocation`)** | Hook Channel | Subagent Return      | **Deterministic**                    | **Authoritative**: Executes synchronous validation at the exact moment of return.                       |
