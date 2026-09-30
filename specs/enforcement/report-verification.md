# Report verification: claim-ledger reports, premise-check at arrival, and the verdict trace

Status: **proposal** for `aops_90ee4118` (split from `aops_89015fc6` on 2026-09-30; the hooks implementation is tracked under `aops_89015fc6`). Incorporates research findings from `ida_research_nl_output_contracts` and `aops-nl-output-contracts-and-logic-syntax`. Revised after independent review and aligned with Nic's 2026-09-30 directives; open questions for Nic are set out in §9.

## The failure this answers

On 2026-09-26 Ida Prime relayed a peer's halt report on `aops_22659d3d` to Nic unchecked. The blocker was a refused `ls` on a directory. Nothing showed that the directory was the one the workflow-library skill specifies. The halt rested on that unstated premise, and in prose the premise read as background.

Nic, verbatim (2026-09-26): _"how the fuck can i convince you to properly check incoming reports? what can i possibly do?"_

Nic, verbatim (2026-09-30): _"we need priority 1 to be the input output contract + possible hook on all communications from ida from below."_

Three things were missing:

1. A report shape that makes every inferential step visible, so an unstated bridging premise shows up as a visible gap.
2. A verification procedure that systematically walks the report's inferences without opening primary sources in Prime's context.
3. A trigger that puts the procedure in front of the receiver at the moment the report arrives, before it can be relayed to the user.

This spec supplies all three. It also supplies an OpenTelemetry trace, so that whether the check occurred can be audited post-hoc.

## Constraints and doctrine governing this design

- **Hooks deliver and never decide** ([enforcement.md](enforcement.md) line 18). Every arrival-time element a hook carries is an advisory reminder (JIT injection). The verdict is always an agent's judgment. No arrival hook blocks, and none keys on the content of a report.
- **What a hook may key on.** A hook may key on fields the client sets (`tool_response.status`, the transcript's `origin` object, the harness-authored envelope at the head of a prompt). It never keys on words the reporting agent wrote ("BLOCKED", "cannot"). That would be content-sniffing ([enforcement.md](enforcement.md) line 20).
- **Reports stay prose.** The format is a hint to the reader, never "a regex over field names" ([evidence-contract.md](evidence-contract.md) lines 122–130). The claim ledger below consists of numbered English sentences. Nothing parses it mechanically.
- **Ida's verification is a logic check** (`plugins/ida/agents/ida.md:57`). She never opens a primary source, never authenticates internal ledgers, and never runs code to verify a claim. When a pointer needs spot-checking, she dispatches the spot-check.
- **Basis vocabulary is unchanged.** The design uses the seven tags at `evidence-contract.md:95-103` as they stand (`[observed]`, `[attempted-and-failed]`, `[exhaustively-searched]`, `[not-observed]`, `[inferred]`, `[assumed]`, `[reported-by-another]`).
- **Least-invasive rung first** ([enforcement.md](enforcement.md) lines 58–62; design principles 2–3 at lines 77–78). Arrival reminders ship as JIT injection. Blocking-once enforcement is restricted strictly to procedural exit/contact gates (`Stop` and channel reply tools per Nic's 2026-09-30 ruling), never content evaluation.
- **Ida Twin execution topology** (`mem_eb7b438c`). Ida Prime is the conversational face to Nic. Her `Agent` tool was deliberately denied on 2026-09-22; she communicates with twins over the cross-session bus (`SendMessage`). Reports from below arrive at Prime as peer messages, not subagent tool returns.
- **Hooks-off ruling scope** (`mem_v9_arch_decisions`). While the standing doctrine keeps dormant hooks built and off, Nic's 2026-09-30 ruling explicitly lifted this restriction for hearsay, honesty, and quiet hooks (`aops_89015fc6`).

---

## 1. The report format: the claim ledger (Argdown-Lite)

As established in `ida_research_nl_output_contracts` and synthesized in `aops-nl-output-contracts-and-logic-syntax`, cognitive deliberative boundaries require natural-language output contracts rather than rigid JSON schemas or unconstrained narrative prose. Constraining LLM reasoning to strict JSON schemas triggers premature serialization and logit masking, while unstructured prose allows unstated premises to pass unnoticed.

The recommended format is **Argdown-Lite**: a semi-structured claim ledger synthesizing Argdown's numbered premises and derivation lines, Toulmin's explicit structural warrants, Catala's defeasible exception clauses (`UNLESS`), and FActScore/Claimify's atomic proposition discipline.

The ledger forms the body of the evidence contract's `CLAIM`/`EVIDENCE` fields (`evidence-contract.md:91-94`). Where the six-field handback is used, the ledger replaces a single CLAIM/EVIDENCE pair with a numbered set; it does not replace the outer handback schema.

### Governing Rules

1. **The outcome line names its spine:** The report's status line (VERDICT / STATUS / HALTED / Summary) explicitly names the terminal claim it rests on: `VERDICT: BLOCKED (from C4)`. The spine is the outcome line plus every line it transitively uses. Only the spine must be in ledger form; narrative context may stay in prose below the ledger.
2. **One numbered line per claim (`C1`, `C2`, …):** Each line expresses a single, decontextualized atomic proposition that reads clearly in isolation.
3. **Every leaf line ends with a basis tag and pinpoint pointer:** For example, `[observed: plugins/ida/skills/pull/SKILL.md:25]`.
4. **Derived lines trace their lineage:** A derived line specifies the exact premises and warrants it uses: `C4. THEREFORE (C1, C2, C3 via W1 - D1): …`. A derived line carries no independent basis tag; its strength is strictly bounded by the weakest basis among its transitive leaves (the status-survival / anti-laundering rule).
5. **Explicit written warrants:** If a deduction requires a bridging invariant or domain rule, that warrant must be explicitly written out as a numbered line: `[Wn] WARRANT: <structural mechanism or domain invariant>`. An unstated warrant exposes a hidden premise.
6. **Defeaters handled via UNLESS:** Competing hypotheses or exception conditions must be stated with `[Dn] UNLESS: <condition>` and tagged with an empirical basis (typically `[not-observed]`).
7. **Explicit scope:** Claims must quantify their domain explicitly ("every", "no", "at least one") and name boundaries ("in `plugins/ida/`", "at commit `5382d880`", "in session `02a8…`").
8. **Negative and capability lines require empirical bounding:** A negative or capability assertion must cite `[attempted-and-failed: cmd → verbatim error]` or `[exhaustively-searched: tool/query/scope → 0 matches]`. Otherwise, it is classified as `[not-observed]` and cannot ground a conclusion.

**Short form:** A report whose outcome rests on a single observed fact requires no deduction: `STATUS: DONE (from C1)` followed by a single tagged line. The ledger expands only with the inferential depth of the argument.

### The Specimen, Rewritten

In incident `aops_22659d3d`, the peer reported a refused directory listing as a complete capability blocker. In ledger form, what the peer realistically observed is:

```text
VERDICT: BLOCKED (from C2)
C1. `ls <dir>` exited "Operation not permitted". [attempted-and-failed: `ls <dir>` → "ls: <dir>: Operation not permitted"]
C2. THEREFORE (C1): the project template tier cannot be listed in this session.
```

Rule 4 forces C2 to name what it uses, exposing that C1 alone does not entail that the template tier cannot be listed. The inferential jump is immediately visible on the page. The receiver catches the missing warrant: _"the workflow-library skill reads project templates from `<dir>`, and from nowhere else."_ The receiver returns the report with: _"C2: cite the SKILL.md line that names `<dir>` as the only project-template location."_

If the author had attempted to state the premise explicitly, the ledger would have read:

```text
VERDICT: BLOCKED (from C4)
C1. `ls <dir>` exited "Operation not permitted". [attempted-and-failed: `ls <dir>` → "ls: <dir>: Operation not permitted"]
C2. The workflow-library skill reads project templates from <dir>. [assumed]
C3. The workflow-library skill names no other project-template location. [not-observed]
W1. WARRANT: When all documented locations for a template tier are unreadable, the tier cannot be listed.
D1. UNLESS: The template tier is readable via an alternative path permitted to the session. [not-observed]
C4. THEREFORE (C1, C2, C3 via W1 - D1): the project template tier cannot be listed in this session.
```

The report still fails to establish a capability block: it rests on an `[assumed]` leaf and a `[not-observed]` negative claim, which grounds nothing under Rule 8. In the original unstructured prose, neither C2 nor C3 was stated at all, and no deduction was exposed.

### Proven Viability on Real PKB Reports

The viability of Argdown-Lite was validated in `aops-nl-output-contracts-and-logic-syntax` across two real historical PKB verification reports without adding unevidenced facts:

#### Real Report 1: `aops_pr_review_2636_20260912` (PR #2636 review)

```text
VERDICT: READY-TO-MERGE (from C11)

C1. Git diff on PR commit ca72af5f4 touches exactly 4 files: .claude/setup.sh, lib/py/transcripts/domain/context.py, plugins/ts/README.md, and tests/test_shipped_hooks.py. [observed: git show ca72af5f4]
C2. All deleted lines in commit ca72af5f4 reference session-end-sync.sh, AOPS_TS_SYNC_DEST, or AOPS_TS_SYNC_RAW. [observed: git show ca72af5f4]
C3. File plugins/ts/hooks/tailscale-up.sh and its associated tests and documentation are byte-identical to parent. [observed: git diff parent..PR -- plugins/ts/hooks/tailscale-up.sh]
C4. Command `grep -rn 'session-end-sync\|AOPS_TS_SYNC' --exclude-dir=.git .` on branch polecat/ts-drop-sync-s1 returned 0 matches with exit code 1. [exhaustively-searched: branch polecat/ts-drop-sync-s1 -> 0 matches]
C5. Test execution `uv run pytest tests/test_shipped_hooks.py -o addopts="" -v` produced 19 passed, 6 skipped. [observed: pytest run output]
C6. Function has_user_context in lib/py/transcripts/domain/context.py has 0 direct test references in repository. [exhaustively-searched: repo test files -> 0 matches]
C7. Remote GitHub Actions CI run 34660450245 on PR branch failed on Lint and Pytest jobs. [observed: gh run view 34660450245]
C8. Remote GitHub Actions CI runs 34591740449 (Lint) and 34591740441 (Pytest) on base branch v0.10 tip failed prior to PR branch creation. [observed: gh run list --branch v0.10]
W1. WARRANT: When CI failures on a PR branch match identical failures on the base branch tip prior to branching, and the PR diff does not touch the failing components, the PR did not introduce the failure.
D1. UNLESS: The PR diff modifies configuration or code affecting the failing CI jobs. Evaluated: git diff confirms untouched. [observed: C1, C2]
--------------------------------------------------------------------------------
C9. THEREFORE (C7, C8 via W1 - D1): The CI failures on PR #2636 are pre-existing orthogonal baseline defects, not regressions introduced by the PR.
C10. THEREFORE (C1, C2, C3, C4, C5, C6, C9): PR #2636 satisfies Acceptance Criteria 1-4 without defects or scope creep.
--------------------------------------------------------------------------------
C11. THEREFORE (C10): VERDICT is READY-TO-MERGE.
```

#### Real Report 2: `aops_pr_review_2638_20260912` (PR #2638 review)

```text
VERDICT: FIXED-THEN-READY (from C10)

C1. Recreated specs/ARCHITECTURE.md and specs/README.md accurately describe existing plugins, hooks, handlers, and build stages present in the tree. [observed: tree inspection]
C2. Citations in specs/build-and-install.md:44 and specs/enforcement/auto-mode-classifier.md:22-28 broke because they targeted sections dropped during ARCHITECTURE.md recreation. [observed: check_refs.py output]
C3. File specs/agents/reify.md matches pre-rename commit f4f02058c^ byte-for-byte except for updating plugins/aops/workflows/ to plugins/aops/templates/. [observed: git diff f4f02058c^:specs/agents/reify.md specs/agents/reify.md]
C4. File specs/enforcement/workflow.md is an exact byte-for-byte restore of pre-rename commit f4f02058c^:specs/enforcement/workflow.md. [observed: git diff f4f02058c^:specs/enforcement/workflow.md specs/enforcement/workflow.md]
C5. Deletion of handler-liveness-tracking reference in specs/enforcement/evidence-contract.md removed an active governance rule rather than a dead reference. [observed: specs/enforcement/evidence-contract.md diff]
C6. Fix commit 01ee39656 pushed to branch polecat/doc-refs-v010-s1 repointed broken citations from C2 and restored the liveness-tracking governance acknowledgment from C5. [observed: git log -1 01ee39656]
C7. Execution of scripts/check_refs.py on commit 01ee39656 yields exactly 15 broken references, all targeting lib/axioms owned by PR #2631. [observed: scripts/check_refs.py run]
C8. Pytest execution on PR HEAD (commit 01ee39656) and base branch origin/v0.10 yields an identical set of 58 FAILED+ERROR tests. [observed: pytest diff]
W1. WARRANT: When PR defects identified during verification are resolved by pushed fix commits, and residual test and reference failures are identical to base branch HEAD, the PR introduces no new defects.
--------------------------------------------------------------------------------
C9. THEREFORE (C1, C3, C4, C6, C7, C8 via W1): Acceptance criteria 1-5 are satisfied and all introduced defects are resolved.
--------------------------------------------------------------------------------
C10. THEREFORE (C9): VERDICT is FIXED-THEN-READY.
```

---

## 2. How the receiver verifies a report

This operationalizes the "Audit Criteria" in `plugins/ida/skills/premise-check/SKILL.md` (lines 22–29) into an executable 7-step procedure mapping directly to `hearsay.md`'s six logic-check questions. Steps 0–6 are purely logical deductions and require no external tool calls (`plugins/ida/agents/ida.md:57`).

0. **Normalise:** If the report arrives in narrative prose rather than ledger form, rewrite only its spine into ledger lines:
   - Preserve the sender's own basis tags.
   - If an unstated warrant must be supplied to make the argument cohere, label it `SUPPLIED`. A spine requiring a supplied warrant cannot be accepted (step 7).
   - If the prose does not permit reconstructing what the outcome rests on, RETURN immediately with: _"State the outcome and the ledger lines it rests on."_
1. **Find the spine:** Trace backward from the outcome line and extract only the claims it transitively uses. Disregard non-load-bearing narrative detail.
2. **Check each inferential step (`hearsay.md` Q3, Q6):** For each `THEREFORE`, evaluate whether the conclusion follows strictly from the stated premises and warrants:
   - If an additional bridging fact is required, write it down as a sentence; that sentence is the missing warrant.
3. **Check each leaf premise (`hearsay.md` Q1, Q4):**
   - Verify every leaf has an explicit basis tag.
   - Verify pinpoint pointers are checkable (`file:line`, command output, node ID).
   - Ensure negative or capability assertions carry `[attempted-and-failed]` or `[exhaustively-searched]`.
4. **Check scope (`hearsay.md` Q5):** Compare the domain covered by the premise against the scope asserted in the conclusion. Searching a single directory does not warrant a repo-wide or environment-wide claim.
5. **Cap the conclusion (`hearsay.md` Q4):**
   - The outcome inherits the weakest basis among the spine's leaf premises.
   - Any leaf tagged `[inferred]`, `[assumed]`, or `[reported-by-another]` caps the entire outcome at that level (status survival).
6. **Evaluate alternatives and defeaters (`hearsay.md` Q2):**
   - For outcomes asserting BLOCKED, FAIL, or inability, evaluate whether obvious alternative explanations or bypass routes were tested via `UNLESS`.
7. **Emit a categorical verdict token:**
   - **`ACCEPT`**: Every inferential step is valid, all leaves are adequately based, and the resulting cap is `[observed]`, `[attempted-and-failed]`, or `[exhaustively-searched]`.
   - **`DOWNGRADE`**: Reasoning is valid, but the cap is `[inferred]`, `[assumed]`, or `[reported-by-another]`. The outcome may be relayed only with its basis qualification stated in the same sentence.
   - **`RETURN`**: A missing warrant, invalid step, scope mismatch, unbased negative, or supplied warrant was identified.
     - Send the report back to the author, citing the exact claim numbers and specifying the missing warrant or scope gap.
     - If the author session has ended, dispatch the question to a new worker (`plugins/ida/agents/ida.md:70`).
     - Limit exchanges to two RETURN rounds. If unresolved, record the task as `review` on the graph with the open question.
   - **`NO-CLAIM`**: The message contains no load-bearing outcome (e.g. an acknowledgement, question, or task routing). Record to balance arrival telemetry.
   - **Prohibition on self-repair:** The receiver must never fill an empirical gap with personal assumptions. Spot-checking a pointer is a separate task and must be dispatched (`plugins/ida/agents/ida.md:57`).

A `RETURN` verdict never reaches Nic, hedged or otherwise (`plugins/ida/skills/premise-check/SKILL.md:39`). A `DOWNGRADE` reaches him only with its cap explicitly declared and the source agent attributed.

---

## 3. The write obligation

The write obligation must be delivered **before** the author writes its report. In Claude Code, a subagent returning via `SubagentHandback` emits its return content prior to `SubagentStop`, making stop-event reminders too late to shape the text.

| Surface                                                             | Binding                                                                                                                             | Mechanism & Severity        |
| :------------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------- | :-------------------------- |
| `specs/enforcement/evidence-contract.md`                            | Authoritative definition of Claim Ledger rules (§1).                                                                                | `instructions` (imperative) |
| `plugins/ida/skills/dump/SKILL.md:52`                               | Receipts written as a claim ledger; `Summary (from C_outcome)`.                                                                     | `instructions` (imperative) |
| `plugins/ida/skills/pull/SKILL.md:25`                               | Require full 7-tag basis vocabulary and ledger format for release evidence.                                                         | `instructions` (imperative) |
| Worker definitions (`james.md`, `sara.md`, `marsha.md`, `pauli.md`) | "Hand back as a claim ledger (`evidence-contract.md` § Claim ledger)."                                                              | `instructions` (imperative) |
| `SubagentStart` (`honest_output`, `honesty.md`)                     | Injected before first prompt: "Write the spine of your report as a numbered claim ledger; every THEREFORE names the lines it uses." | `JIT injection` (advisory)  |
| Peer Briefs (Prime to twins)                                        | Cross-session briefs mandate claim ledger handback format in task brief footer.                                                     | `instructions` (imperative) |

`honesty.md` previously reached non-Ida sessions via the `search_the_pkb` fallback on `UserPromptSubmit` (`plugins/ida/hooks/handlers.py:158`). This inadvertently reminded receiving agents how to _write_ a report on turns where they were _reading_ incoming handbacks. Hook A2 replaces this fallback on report-arrival turns.

The write obligation remains advisory. A poorly formatted report is not rejected at write time; it is intercepted at the receiver, where epistemic judgment belongs.

---

## 4. The read obligation: where the reminder attaches

Reports arrive across four distinct runtime channels:

| #      | Channel                                                                                   | Runtime Event in Receiver                                                                                                                                                                                          | Basis                                                               |
| :----- | :---------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **R1** | Foreground subagent returning text                                                        | `PostToolUse` on `Agent` with `tool_response.status == "completed"` and report in `tool_response.content`.                                                                                                         | [observed: hooks docs, `PostToolUse` "Agent" `tool_response` table] |
| **R2** | Hand-back, background completion, or twin-to-twin message arriving while receiver is idle | Turn starts and `UserPromptSubmit` fires. Prompt opens with harness envelope (`<agent-message from=…>`). Transcript entry carries `origin: {kind: "peer", from, senderTaskId, body}` and `promptSource: "system"`. | [observed: transcript `02a8997d`, entries 111, 191]                 |
| **R3** | Background completion or peer message arriving **mid-turn**                               | The `<task-notification>` is queued as a `queued_command` attachment; `UserPromptSubmit` fires mid-turn.                                                                                                           | [observed: transcript `02a8997d`, entries 132–134, 170–171]         |
| **R4** | Report read from persistent graph (`/gather`, `/reconcile`, `/pull` reading task body)    | No hook event. Governed by skill instruction text.                                                                                                                                                                 | [inferred]                                                          |

**De-duplication:** Background subagents that hand back can produce both a peer message and a subsequent task-notification. Injections and telemetry counters de-duplicate on sender ID (`origin.from`, `senderTaskId`, `<task-id>`).

### Hook Attachments

- **A1: R1 reminder on `PostToolUse(Agent)`.**
  - Scope: Worker supervisor sessions (James, twins coordinating subagents). Per `mem_eb7b438c`, Ida Prime's `Agent` tool is denied, so A1 does not fire in Prime.
  - Trigger: `tool_response.status == "completed"`.
  - Action: Inject advisory text: _"A subagent report just arrived. Run premise-check on its spine before acting on it or relaying it."_
  - Implementation: Re-register `rule_against_hearsay` (`plugins/ida/hooks/handlers.py:339-346`, currently commented out at line 496) on `PostToolUse` instead of `PostToolBatch`.
- **A2: R2/R3 reminder on `UserPromptSubmit`.**
  - Scope: Ida Prime and peer twins. This is Ida Prime's primary arrival channel for reports from below.
  - Trigger: Harness envelope at head of `prompt`, or transcript entry with `origin.kind == "peer"` or `<task-notification>`.
  - Action: Inject: _"A report just arrived from <sender>. Run premise-check on its spine before acting on it or relaying it to Nic."_
  - Exclusions: `origin.kind == "human"` (Nic's statements are directives, not reports to premise-check; `plugins/ida/agents/ida.md:92`).
- **A3: Stop gate / reminder on `Stop` / `SubagentStop`.**
  - Trigger: Session stop event when local session state records an unverified arrival lacking a recorded verdict.
  - Action: Per Nic's 2026-09-30 ruling, `honesty.md` is re-enabled on `Stop` **blocking once** for all agents (`aops_89015fc6`). The hook returns `Kind.BLOCK` on the first stop attempt, instructing the agent: _"Reports from <sender> have no recorded premise-check verdict. Record a verdict (ACCEPT, DOWNGRADE, RETURN, or NO-CLAIM) using scripts/verdict.py before finishing."_ On the second stop attempt, `stop_hook_active` allows the session to exit.
- **A4: Contact gate on channel replies (`quiet.md`).**
  - Trigger: `PreToolUse` on channel reply tools (`telegram_reply`, `discord_reply`) and `AskUserQuestion` in Ida Prime.
  - Action: Per Nic's 2026-09-30 ruling, `quiet.md` is enabled on `PreToolUse` for telegram/discord replies **blocking once** (`aops_89015fc6`), preventing unverified worker claims from being transmitted to Nic.

### Cross-Session Twin Communication (`mem_eb7b438c`)

Ida twins operate as independent Claude Code sessions communicating over the cross-session bus:

- **Sender:** A twin completes its task via `/dump`, writes the claim ledger to the PKB task body, and calls `SendMessage` to Ida Prime with the **full ledger** in the message body.
- **Receiver (Ida Prime):** A2 fires on message arrival. Prime verifies the ledger logic, records the verdict via `scripts/verdict.py`, and appends the verdict to the PKB task.
- **Closing the Loop:** On `RETURN`, Prime sends the specific line-numbered questions back to the twin via `SendMessage`. The twin answers in ledger format.

### agy Runtimes

- agy maps `PreInvocation` to `UserPromptSubmit` (`plugins/ida/hooks/dispatch.py`).
- agy enforces `allow_blocking_agy = false` (`tests/policy.toml:51`). Blocking hooks gracefully degrade to advisory warnings on agy sessions.

---

## 5. The verdict trace (OTel)

The existing `plugins/ida/hooks/premise_check_verdict.py` emits a generic `TOOL` span with hardcoded text, preventing aggregation. The replacement emits structured OpenInference spans via `claude_code_tracer`:

- **Verdict Span (`premise_check.verdict`):** Emitted by `scripts/verdict.py` with span kind `EVALUATOR`. Attributes sit under `premise_check.`:
  - `report.id`: PKB task ID or `senderTaskId`.
  - `report.sender`: `origin.from` or subagent ID.
  - `report.channel`: `subagent | handback | peer | notification | graph`.
  - `report.format`: `ledger | prose` (`prose` indicates step 0 normalization occurred).
  - `report.spine`: e.g. `"C4<-C1,C2,C3"`.
  - `outcome`: `ACCEPT | DOWNGRADE | RETURN | NO-CLAIM`.
  - `cap`: Weakest leaf basis on the spine.
  - `round`: RETURN exchange round (integer, starting at 1).
  - `defect.{n}.line`: e.g. `C2`.
  - `defect.{n}.kind`: `missing-warrant | invalid-step | scope-mismatch | unbased-negative | untagged | supplied-warrant | missing-alternative | no-spine`.
  - `defect.{n}.question`: Prompt returned to author.
- **Arrival Span (`premise_check.arrival`):** Emitted by A1 and A2 upon arrival. Provides the denominator for coverage queries in Phoenix.
- **Local State Tracking:** `scripts/verdict.py` and hooks A1/A2 append structured entries to a session-scoped file keyed by `$AOPS_SESSION_ID`. Hook A3 checks this local state to enforce the Stop gate without querying Phoenix.

### Observability Metrics in Phoenix

- **Coverage Rate:** Ratio of `premise_check.verdict` spans to `premise_check.arrival` spans per session. Directly measures the unverified-relay rate.
- **Defect Distribution:** Frequencies of `defect.kind` grouped by agent persona, pinpointing author instruction weaknesses.
- **Format Uptake:** Percentage of incoming reports adhering natively to `report.format = ledger`.

---

## 6. Probes owed before wiring

| Probe  | Question                                                                                                                                            | Method                                                                                                                     |
| :----- | :-------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------- |
| **P1** | Does a twin `SendMessage` arriving while idle fire `UserPromptSubmit`? Does the payload `prompt` carry the harness envelope? Is `origin` populated? | Run two local sessions; send cross-session message; capture payload with `dump_payload`.                                   |
| **P2** | Does a cross-session peer message arriving **mid-turn** queue as a `queued_command` and fire `UserPromptSubmit`?                                    | Send message to session during long tool execution; capture payload and transcript.                                        |
| **P3** | agy: Does a cross-session message reach an agy session, and does `PreInvocation` fire?                                                              | Replicate P1 with agy receiver.                                                                                            |
| **P4** | Delivery and compliance of A1/A2 JIT reminders.                                                                                                     | Model-echo control test and measure verdict coverage in Phoenix.                                                           |
| **P5** | What `origin.kind` does an incoming channel (Telegram) message from Nic carry?                                                                      | Send test message via Telegram; inspect transcript entry for `origin.kind == "human"`.                                     |
| **P6** | Operational viability of claim ledger syntax.                                                                                                       | Rewrite five historical handbacks into Argdown-Lite; conduct blind premise checks; evaluate friction and defect discovery. |

---

## 7. Enforcement map rows to add & Article 19(3) Evaluation

### 7.1 Enforcement Map Rows (specs/ENFORCEMENT-MAP.md)

Rows structured strictly according to the 4-column schema of [enforcement.md](enforcement.md) lines 38–45:

| Rule / nudge                                                                                                                                                                                                                     | Mechanism     | Severity      | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------ | :------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Axiom: Honest Epistemics](../../plugins/rbg/axioms/honest-epistemics.md) -- Write report spine as an Argdown-Lite claim ledger with atomic premises, explicit warrants, and basis tags                                          | instructions  | imperative    | [evidence-contract.md](evidence-contract.md) lines 90–120; [dump/SKILL.md](../../plugins/ida/skills/dump/SKILL.md) line 52; [pull/SKILL.md](../../plugins/ida/skills/pull/SKILL.md) line 25; worker agent definitions (`james.md`, `sara.md`, `marsha.md`, `pauli.md`). Justifying incidents: `aops_22659d3d` (unstated bridging premises in prose halt report), `admin_b0558883` / `task_c186cf41` (prose claim of status change never written to graph), Nic verbatim 2026-09-30 ("priority 1 to be the input output contract"). |
| [Axiom: Honest Epistemics](../../plugins/rbg/axioms/honest-epistemics.md) -- Advise subagents and twins before drafting to emit report spine in ledger syntax                                                                    | JIT injection | advisory      | `SubagentStart` hook `honest_output` ([handlers.py](../../plugins/ida/hooks/handlers.py) line 497); brief template ending for twin briefs. Justifying incidents: `aops_22659d3d` (prose hiding unstated premises); unverified subagent handback summaries.                                                                                                                                                                                                                                                                         |
| [Persona: Ida](../../plugins/ida/agents/ida.md) line 57 -- Scrutinize logic of incoming peer and subagent reports before acting or relaying                                                                                      | JIT injection | advisory      | A1 on `PostToolUse(Agent)` with `completed` status (James/worker supervisors); A2 on `UserPromptSubmit` on peer `SendMessage` / handback arrival envelope (Ida Prime & twins). Justifying incident: `aops_22659d3d` (Ida Prime relayed peer halt report on refused `ls` without logic checking); Nic verbatim 2026-09-26 ("how the fuck can i convince you to properly check incoming reports?").                                                                                                                                  |
| [Axiom: Honest Epistemics](../../plugins/rbg/axioms/honest-epistemics.md) / [Evidence Contract](evidence-contract.md) lines 163–165 -- Refuse exit turn once if incoming reports lack recorded premise-check verdict or NO-CLAIM | structural    | block         | A3 on `Stop` / `SubagentStop` in receiving session ([handlers.py](../../plugins/ida/hooks/handlers.py) line 495); returns `block()` once under `stop_hook_active` guard. Justifying incidents: `aops_22659d3d` (Ida stopped and relayed without verdict); Nic's 2026-09-30 verbatim ruling re-enabling `honesty.md` blocking once on `Stop` (`aops_89015fc6`).                                                                                                                                                                     |
| [Persona: Ida](../../plugins/ida/agents/ida.md) line 57 / [[goal_ws_conversation_discipline]] -- Prevent unverified peer claims from reaching user via Telegram/Discord                                                          | structural    | block         | `quiet.md` hook on `PreToolUse` for channel reply tools (`telegram_reply`, `discord_reply`) and `AskUserQuestion`. Justifying incident: `aops_22659d3d` (unchecked halt relayed to Nic); Nic's 2026-09-30 verbatim instruction ("quiet.md enabled for ida prime on 'stop' and on 'pretooluse' for telegram/discord replies (blocking once)").                                                                                                                                                                                      |
| [Axiom: Evidence Immutable](../../plugins/rbg/axioms/evidence-immutable.md) / [Workflow Contract](workflow.md) -- Graph status transitions and task handovers require a recorded premise-check verdict                           | process       | required gate | `/gather` step 2 ("Check each one on the papers"); `/reconcile` obligations 4–5. Justifying incidents: `admin_b0558883` (unverified status claim on task), `aops_pr_review_2636_20260912` (verifying baseline CI vs PR defects).                                                                                                                                                                                                                                                                                                   |
| [Axiom: Full Observability](../../plugins/rbg/axioms/full-observability.md) -- Measure arrival vs verdict span coverage in Phoenix telemetry                                                                                     | post-hoc      | observability | `premise_check.arrival` (A1/A2) vs `premise_check.verdict` (`verdict.py`) spans emitted via `claude_code_tracer`. Justifying incident: `aops_22659d3d` (lack of telemetry to detect unverified relay occurrences).                                                                                                                                                                                                                                                                                                                 |

### 7.2 Article 19(3) Necessity Evaluation of New Enforcement Code (`mem_96366172`)

Under Nic's standing ruling (`mem_96366172`), all new enforcement code (hooks, gates, telemetry emitters, blockers) must satisfy the three-part Article 19(3) ICCPR necessity test before being proposed or wired:

1. **Arrival JIT Injections (Hooks A1 and A2):**
   - **Legality:** Authorised by `plugins/ida/agents/ida.md:57` (mandate that verification is a logic check on incoming reports) and Nic's 2026-09-30 directive ("possible hook on all communications from ida from below").
   - **Legitimate Aim:** Prevention of unverified hearsay relay where incoming agent reports contain unstated premises or false capability claims. Evidenced by incident `aops_22659d3d`.
   - **Necessity:** Standalone instruction text in `ida.md` repeatedly failed to prevent premature relay because instructions in system context are drowned by long conversational turns. A lightweight, advisory JIT reminder at the exact turn of report arrival is the least intrusive intervention that reliably focuses attention.
2. **Stop-Event Block-Once Gate (Hook A3 / honesty.md on Stop):**
   - **Legality:** Explicitly authorized by Nic's verbatim ruling on 2026-09-30 ("reenable the honesty.md hook on the 'stop' event (blocking once) for all agents", `aops_89015fc6`) and grounded in `evidence-contract.md:163-165` (presence-only procedural checks).
   - **Legitimate Aim:** Eliminating premature session exits where an agent finishes its turn without recording a verdict on incoming subagent or peer findings. Evidenced by `aops_22659d3d`.
   - **Necessity:** Advisory warnings on Stop were routinely ignored or absorbed without action. A single non-fatal continuation block (`Kind.BLOCK`) forces the agent to pause and record a verdict without causing permanent deadlock (guarded by `stop_hook_active`). It performs no content inspection, checking only whether an unverified arrival exists in local session state.
3. **Channel Reply Gate (Hook A4 / quiet.md on PreToolUse):**
   - **Legality:** Explicitly commanded by Nic's 2026-09-30 directive ("quiet.md enabled for ida prime on 'stop' and on 'pretooluse' for telegram/discord replies (blocking once)", `aops_89015fc6`) and `goal_ws_conversation_discipline`.
   - **Legitimate Aim:** Preventing unvetted agent halts, speculative blockers, or unverified claims from being transmitted directly to the human user.
   - **Necessity:** Instructions alone failed when agents panicked on worker errors and relayed them immediately. Gating the transmission tool directly before external output ensures human attention is protected.
4. **Verdict and Arrival Telemetry Spans (`verdict.py` and A1/A2):**
   - **Legality:** Authorised by `[Axiom: Full Observability](../../plugins/rbg/axioms/full-observability.md)` and OpenInference evaluation standards.
   - **Legitimate Aim:** Providing empirical visibility into the unverified-relay rate and defect taxonomy, replacing subjective impressions with audit data.
   - **Necessity:** Telemetry is passive post-hoc observability (`post-hoc → observability`), introducing zero runtime friction or blocking behavior.

---

## 8. Code this replaces or retires

- `plugins/ida/hooks/premise_check_gate.py`: **Retire and delete.**
  - Currently returns `refuse()` on `Agent`/`Task` dispatches (lines 196–215). `dispatch.py:48-51` reserves REFUSE strictly for structural impossibility, noting it "is never a rule verdict".
  - The gate is currently commented out in `handlers.py:489-498`, so deleting it causes no regression in live behavior. The obligation is cleanly assumed by A1–A3 and `quiet.md`.
- `plugins/ida/hooks/premise_check_verdict.py`: **Replace with §5 OpenTelemetry span schema.**
  - It imports `disarm()` from the gate (line 20); both will be retired together in `aops_89015fc6`.
- `plugins/ida/skills/premise-check/scripts/verdict.py`: **Retain and refactor.**
  - Update path resolution: lines 12–13 reference nonexistent `plugins/orchestrate/hooks/` and `dist/orchestrate-*/hooks/`, and line 26 references nonexistent `lib/hooks`. Repoint imports directly to `plugins/ida/hooks/`.

---

## 9. Open questions for Nic and recorded decision departures

### 1. Departure from `mem_v9_arch_decisions` ("Hooks stay built and off"): Re-enabling Hearsay, Honesty, and Quiet Hooks

- **Recorded Decision:** `mem_v9_arch_decisions` ("Ruling 2026-08-28: hooks stay built and off... This is a deliberate standing state, not a defect").
- **Why this is open:** Nic's verbatim directive on 2026-09-30 specifically commanded: _"yes, dispatch the implementatoin. I want the hearsay.md turned on again for ida instructions injected on UserPromptSubmit (which captures both subagent messages and cross-session messages), and also reenable the honesty.md hook on the 'stop' event (blocking once) for all agents, and quiet.md enabled for ida prime on 'stop' and on 'pretooluse' for telegram/discord replies (blocking once) as well (new hook invocation)"_.
- **Options:**
  - _Option A:_ Maintain the blanket "hooks off" policy from `mem_v9_arch_decisions` and rely exclusively on instruction prompts in agent profiles.
  - _Option B:_ Re-enable the hooks strictly as advisory JIT injections (non-blocking).
  - _Option C (Recommended):_ Formally record Nic's 2026-09-30 instruction as an explicit exception / update to `mem_v9_arch_decisions`, enabling this specific triplet (hearsay on UserPromptSubmit, honesty on Stop blocking once, quiet on Stop and PreToolUse channel replies blocking once) under `aops_89015fc6`, while leaving all other dormant hooks built and off.

### 2. Departure from `enforcement.md:18` ("No programmatic, deterministic, or mechanical verdict on quality or process"): Blocking Once on Stop and PreToolUse

- **Recorded Decision:** `specs/enforcement/enforcement.md:18-20` (_"The framework enforces no programmatic, deterministic, or mechanical verdict on quality or process... The only mechanical enforcement is structural prevention... never content-sniffing, never a deterministic pass/fail on the substance of an agent's work"_).
- **Why this is open:** Nic's directive specifies "blocking once" on `Stop` (`honesty.md`) and on `PreToolUse` (`quiet.md`). A hook blocking an agent from exiting or sending a reply enforces a procedural gate.
- **Options:**
  - _Option A:_ Reject blocking and keep all hooks advisory (`additionalContext`), strictly adhering to `enforcement.md:18`.
  - _Option B (Recommended):_ Classify "blocking once" as an authorized structural delivery guard / procedural friction mechanism under `evidence-contract.md:163-165` (presence-only check of recorded verdict before exit). Because the hook inspects only whether a verdict entry exists in local session state and never evaluates report text, it remains strictly non-content-sniffing and preserves the principle that verdicts belong solely to agents.
  - _Option C:_ Hard block until a passing verdict (`ACCEPT`) is recorded. (Rejected: violates `enforcement.md:18` and creates unrecoverable deadlocks).

### 3. Execution Topology Mismatch: Ida Prime has no `Agent` Tool (`mem_eb7b438c`)

- **Recorded Decision:** `mem_eb7b438c` (_"Ida prime, the face... never executes. Her Agent tool is deliberately denied (Nic removed it 2026-09-22)... her only execution route is a brief to a peer Ida over the cross-session bus"_; also `plugins/ida/agents/ida.md:29`).
- **Why this is open:** The original proposal attached hook A1 to `PostToolUse(Agent)`. However, Ida Prime—the face who speaks to Nic and where unverified relays to Nic actually occur—cannot call `Agent`. Twin reports arrive at Prime via `SendMessage` over the cross-session bus (Channel R2).
- **Options:**
  - _Option A:_ Retain A1 only for worker supervisors (e.g. James or twins executing subagent batches), and rely on A2 (`UserPromptSubmit` on peer message envelope / `origin.kind == "peer"`) as the sole arrival hook for Ida Prime.
  - _Option B:_ Restore the `Agent` tool to Ida Prime.
  - _Option C (Recommended):_ Option A. Preserve Ida Prime's detachment boundary per `mem_eb7b438c`. A1 protects supervisor subagent workflows, while A2 serves as Prime's primary defense on peer message receipt.

### 4. Runtime Mechanics of `PreToolUse` Blocking on Channel Replies (`quiet.md`)

- **Recorded Decision:** `plugins/ida/hooks/dispatch.py:128` (`BLOCKABLE_EVENTS = STOP_EVENTS`); Claude Code Hooks specification.
- **Why this is open:** Nic directed that `quiet.md` run on `PreToolUse` for telegram and discord replies "(blocking once)". In `dispatch.py`, only `Stop` and `SubagentStop` are in `BLOCKABLE_EVENTS`. In Claude Code, `PreToolUse` can return `decision: "deny"`, but in `dispatch.py` this is mapped to `Kind.REFUSE`, which is reserved strictly for structural impossibility (`dispatch.py:48-51`). Furthermore, standard `PreToolUse` `additionalContext` is delivered to the session along with the tool result (i.e. _after_ the telegram message has already been sent).
- **Options:**
  - _Option A:_ Enhance `dispatch.py` in `aops_89015fc6` to support an interceptor disposition (`decision: "deny"`) on `PreToolUse` for communication tools that aborts the transmission once and returns an instructional warning.
  - _Option B (Recommended):_ Enforce `quiet.md` as a blocking-once gate on `Stop` (preventing session finish without review) and rely on prominent JIT injection on `UserPromptSubmit` (A2) to restrain channel replies, while implementing Option A in `aops_89015fc6` as an engine extension.
  - _Option C:_ Rely exclusively on instruction rules in `plugins/ida/agents/ida.md:57, 97`.

### 5. Rollout Sequence and Probe Dependencies

- **Why this is open:** Several runtime characteristics of cross-session message queueing and envelope delivery are unestablished empirical questions (Probes P1–P6).
- **Options:**
  - _Option A:_ Wire all hooks and format requirements simultaneously.
  - _Option B (Recommended):_ Staged delivery:
    1. Deploy Argdown-Lite format instructions in `evidence-contract.md` and worker profiles; run P6 dogfooding.
    2. Deploy Phoenix telemetry spans (`premise_check.arrival`, `premise_check.verdict`) via `scripts/verdict.py` to establish baseline unverified-relay rate.
    3. Execute Probes P1 and P2 to confirm envelope payloads on `UserPromptSubmit`.
    4. Wire arrival reminders A1 and A2.
    5. Wire A3 and A4 block-once gates in `aops_89015fc6` and measure compliance delta in Phoenix.
