---
name: learn
description: Diagnose systemic root causes from session execution records, recommend minimally effective workflow remedies first, and persist session transcripts. Use for "diagnose this error", "why did the session fail", "learn from this run", or session post-mortems. Exclude for non-traceable sessions or immediate task retries.
---

# Learn

Perform root-cause analysis on systemic failure classes using session execution records. Diagnose observable failure mechanisms from OpenTelemetry spans (or session logs where the surface does not emit traces), generate and durably persist session transcripts, and recommend minimally effective workflow remedies before escalating to the framework enforcement-map process; do not inspect source code directly.

## Execution Environment and Worker

Mandate execution exclusively within an isolated polecat container in the `academicOps` repository environment (`project: aops`). Never run `/learn` in other project workspaces or uncontained local sessions. Running inside `academicOps` guarantees the worker has direct access to framework governance specifications ([`specs/ENFORCEMENT-MAP.md`](../../../../specs/ENFORCEMENT-MAP.md), [`specs/enforcement/enforcement.md`](../../../../specs/enforcement/enforcement.md), and [`plugins/rbg/skills/axioms/`](../../../rbg/skills/axioms/)).

Dispatch `/learn` to **`pauli`** (`TypeName: "pauli"`), never `james`. Pauli operates strictly from session execution records (`ida:session-trace`), governance specifications, and the PKB graph without searching or reading application source code directly.

## Protocol

1. **Retrieve session execution record and persist transcripts**:
   - From within the `academicOps` polecat environment, read and analyze error session execution records and transcripts using the `ida:session-trace` skill, with direct access to `academicOps` governance documents ([`specs/ENFORCEMENT-MAP.md`](../../../../specs/ENFORCEMENT-MAP.md) and [`specs/enforcement/enforcement.md`](../../../../specs/enforcement/enforcement.md)).
   - Generate a full markdown transcript and condensed outline using `ida:session-trace`:
     ```bash
     uv run python "${CLAUDE_SKILL_DIR:-plugins/ida/skills/session-trace}/scripts/phoenix_transcript.py" \
       <session_id> \
       --out "./scratch/<session_slug>.transcript.md" \
       --sanitize-paths
     ```
     If Phoenix spans are unavailable (e.g. non-instrumented runs), extract turn records directly from the session log or execution transcript with equivalent markdown formatting.
   - Save both documents into the PKB using `pkb_create`:
     - Full transcript: `type: "note"`, `title: "Transcript: <session_slug> (<summary>)"`, `slug: "tr-<session_slug>"`, `tags: ["session-trace", "transcript", "learn"]`.
     - Outline: `type: "note"`, `title: "Outline: <session_slug> (<summary>)"`, `slug: "out-<session_slug>"`, `tags: ["session-trace", "outline", "learn"]`.
   - If the surface does not emit traces, proceed using the session's execution log directly. If the surface emits traces but the trace is absent, unexported, or incomplete, halt immediately and state that the trace is unavailable.
   - Do not fall back to inspecting, grepping, or reading application source code. Ground analysis in runtime execution records and governance specifications.
2. **Diagnose systemic cause from execution evidence**:
   - **Root causes are framework defects, never agent faults.** A root cause is never an agent's fault, capability limitation, choice, or action; it is always the framework's: the instructions, skills, workflows, contracts, or tools that led the agent to act as it did. An agent's action (e.g. dispatching to an agent without necessary credentials or access, rewording an ask, skipping a step, never delivering a result) is an intermediate event on the execution trace, never the root cause. When an agent acts, locate and quote the instruction, skill, workflow, or prompt text that led that agent to take that action, and identify the framework defect (missing constraint, contradictory rule, or ambiguous guidance) that permitted or caused the failure. Never cite an agent, its brief, its capabilities, or its choices as the root cause.
   - **Workflow non-compliance is never a missing rule:** When an agent fails to follow an applicable workflow or skips steps within a workflow, diagnose the failure as poor workflow compliance or ambiguous/unclear instructions within that workflow under the universal framework rule ("follow the applicable workflow"). Never diagnose workflow execution failures as a missing framework-level enforcement rule, and never propose or file issues minting per-workflow framework rules, specs, or gates.
   - **Login and authentication failures are configuration failures, not bugs.** Login and authentication failures (for example a server or service requiring re-authentication) are configuration failures, not bugs. `/learn` files no issue and posts no comment for them; return to the caller that the failure is a configuration failure.
   - **No passive voice; name the actor and quote the instruction.** Use active voice throughout all findings, issue descriptions, and reports; passive voice is strictly prohibited (e.g. "the run went to X" or "a file was modified" is forbidden). Every finding must explicitly state who acted by naming the specific actor (e.g. "Ida Prime sent the run to Pauli"), followed immediately by quoting the exact instruction, skill, or workflow text that led them to act (e.g. "The instructions provided to Ida in `<file>` state: `[extract]`"). Then state the framework defect in those instructions or tools.
   - Ground findings in observable runtime mechanisms shown in the trace (or session log if the surface does not emit traces): failing tool invocations, unexpected tool error payloads, schema mismatches, hook blocks, timeout spikes.
   - Describe what the session attempted and where execution broke down. The runtime execution record is the evidence; do not inspect source files or name responsible code lines.
   - Treat an agent's account of its causes as hearsay, never as evidence of mechanism. Re-read the case from the primary user words independently of the caller's framing; what each agent received, ran, and chose on the record is the evidence.
   - Address the class of failure rather than proximate mistakes. Focus on mechanisms and contracts rather than speculating on agent psychology or internal states.
3. **Generalise the instance**: when the ask names one instance, take both steps below yourself, even if the instance is already fixed.
   - _General bug_: name the mechanism that produced the instance and will produce more like it.
   - _Verification miss_: search for the existing control (in axioms, rules, skills, and enforcement maps) governing the failure class; determine why that control did not fire or pass, and never assert that no control exists without an exhaustive search.
4. **Proportional Workflow Remedy Ladder**:
   - After diagnosing the root cause and verification miss, evaluate remedies with an explicit priority toward addressing problems at local project workflows, local project rules and instructions, and user workflow levels first, backed by a clear understanding of framework behavioral doctrine:
     1. **Local project workflows, rules, and instructions**: If the failure relates to project-specific conventions, execution pipelines, or missing domain steps, propose or update project-scoped templates (`type: template`, `project: <project_id>`) or local project rules and instructions (`.agents/rules/`, `AGENTS.md`).
     2. **User-level PKB workflow** (`type: template`, `project: null`): If the failure relates to individual interaction conventions, personal guidance, or prompt habits, propose or update a user-scoped template in the PKB.
     3. **Universal workflow** (`plugins/ida/skills/workflow-library/workflows/`): If the failure is a recurring operational failure across multiple projects representing a reusable stage template, propose a minimally effective patch to universal templates (`wf-*.md`).
     4. **Framework enforcement issue** (Fallback of last resort): Only when the failure cannot be remedied via workflow instructions, rules, or prompt guidance (e.g. hard security bounds, credential leakage, container isolation failures, or universal behavioral rules derived from axioms), escalate to the formal enforcement loop by evaluating against [`specs/ENFORCEMENT-MAP.md`](../../../../specs/ENFORCEMENT-MAP.md) and [`specs/enforcement/enforcement.md`](../../../../specs/enforcement/enforcement.md), searching existing issues, and filing a GitHub issue or evidence-bump comment under `.github/ISSUE_TEMPLATE/learn.md`.
   - **Workflow remedies bypass the formal framework change process:** Workflows are not rules and do not enforce rules; creating or modifying workflows requires no Stage 1/Stage 2 framework change decomposition gate, no enforcement map extract, and owes 0 rows on `specs/ENFORCEMENT-MAP.md`. User and project workflow remedies are updated or created directly in the PKB; universal workflow remedies are opened as standard PRs into `dev`.
   - **Minimally effective standard:** Prefer patching an existing workflow template over creating a new one. Address the exact missing step, handback requirement, or acceptance criterion that failed without introducing redundant narrative or checklist bloat.
5. **Cross-repository remediation via `/q`**:
   - If the diagnosed problem resides in an external repository (outside `academicOps`), the worker running in the `academicOps` polecat must not attempt direct source code modifications in that remote repository.
   - The worker must immediately queue follow-up tasks on the PKB graph using `/q`, targeted to the owning repository and project with concise goal, scope, acceptance criteria, and diagnosed remedy. Follow-up tasks will be dispatched on the next sweep by an external process.
   - Before releasing, ensure all external repository remediation work is queued on the graph, then release the current task as `partial`, explicitly citing the queued follow-up task IDs and external repository dependencies in `reason`.
6. **File issues or post evidence-bump comments** (Fallback for Tier 4 only):
   - File no issue and post no comment for login or authentication failures, or for issues resolved at Tiers 1–3.
   - For each finding escalating to Tier 4, search existing issues within the owning repository for the error class before creating a new issue to avoid duplicate reports. Target the remote repository directly by name (`owner/repo`) for both search and issue/comment creation rather than relying on a local checkout.
   - When the evidence belongs to an issue that already exists, summarise that evidence into an evidence-bump comment on that existing issue; do not file a separate issue for the evidence.
   - When no existing issue covers the finding, file in the owning repository:
     - When the primary failure is already well known and has a handler, file one issue for the handler's failure only.
     - When the primary failure is not already handled, file both issues (the general bug and the verification miss).
   - Format every filed issue using the repository's issue template at `.github/ISSUE_TEMPLATE/learn.md`, completing each section with concrete trace data and omitting speculation.
   - Ground the issue description or evidence-bump comment in the execution record (tool calls, error payloads, latencies). Strip personal names, credentials, file paths containing sensitive usernames, raw environment details, session IDs, private telemetry domains, and PKB IDs (`aops_...`, `task_...`, `mem_...`).

## Output

Return a markdown report containing:

- **Transcripts**: PKB note wikilinks for the full transcript (`[[<transcript_note_id>]]`) and condensed outline (`[[<outline_note_id>]]`).
- **Evidence**: Session ID / Conversation ID, relevant OTel span IDs (or session log excerpts if the surface does not emit traces), and execution excerpts (tool calls, error payloads, latencies).
- **Root cause**: The framework or workflow defect the execution record shows let the failure happen: the missing, unreached, ambiguous, or contradicted instruction, workflow step, contract, or tool that led the agent to act as it did. State strictly in active voice, name the actor who acted, quote the governing instruction text that led them to act, and explain the framework defect. Never cite an agent, an agent's capability limitation, or an agent's choice as the root cause, and never use passive voice.
- **Verification miss**: The check that should have caught the instance, and why it did not.
- **Remedy**: The proposed minimally effective remedy according to the Proportional Workflow Remedy Ladder (naming tier: Project, User, Universal, or Framework escalation) with draft template changes or PR link, or the specific justification for escalating to Tier 4.
- **Cross-repository tasks**: PKB IDs of follow-up tasks queued via `/q` when remedies reside in external repositories, with task release status `partial`.
- **Artifacts**: Links to created or updated PKB template notes, PR for universal workflows, or filed GitHub issue(s) / evidence-bump comment(s).

For login or authentication failures, return to the caller that the failure is a configuration failure (file no issue and post no comment).
