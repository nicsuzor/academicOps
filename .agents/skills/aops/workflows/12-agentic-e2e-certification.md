# Agentic E2E QA Certification

This protocol defines the End-to-End Certification for the academicOps framework. In accordance with the **Judgment is Non-Delegable** axiom, this certification is executed and evaluated by a _smart agent_ (e.g., the orchestrator or `marsha`), not by rigid deterministic scripts.

Two tracks share this protocol's framing and closing pipeline (the "Closing Pipeline" section below):

- **Part 1: Framework Smoke Test** — a bare `agy`/`claude` client in tmux, for a quick check that hooks/MCP/skills/subagents behave when nothing about container dispatch, plugin allowlists, or credential scoping is in question.
- **Part 2: Polecat Container Certification** — a real `polecat run`/`polecat crew` container dispatch, for verifying the things Part 1 cannot reach at all: `polecat.yaml` gate-mode fidelity, the four-plugin allowlist, and git credential isolation. Run Part 2 whenever polecat infra, gate definitions, the plugin allowlist, or `entrypoint.sh` changed, or as a standing periodic audit — see [[../SKILL.md]] router row "Verify polecat container dispatch."

Do not run Part 2 as a substitute for Part 1's quick checks or vice versa — they exercise different dispatch paths and a pass on one says nothing about the other.

## The Role of the Evaluating Agent

As the evaluating agent, you are the Test Driver. You will:

1. Spawn a live instance of the framework — a bare tmux client (Part 1) or a real polecat container (Part 2).
2. Simulate a human user by injecting prompts (`tmux send-keys`, or the polecat CLI's own prompt-injection path).
3. Use your qualitative judgment to observe the test agent's behavior via pane captures, transcripts, hooks JSONL, and session state — never a single string match standing in for a verdict.
4. Evaluate whether the framework components (Hooks, MCP, Skills, Subagents, and — for Part 2 — gates, plugins, and credentials) functioned correctly and gracefully.

### Computed ≠ Delivered ≠ Seen

A hooks-JSONL record proves a gate **computed** a verdict. It does not prove that verdict was **delivered** onto the wire (the client's own protocol may reject or silently drop fields — e.g. agy's `PostToolHookResult` cannot carry any message at all, so a gate's `system_message` can be fully computed and logged yet never leave the router process). Delivery onto the wire, in turn, does not prove the human or agent **saw** it — that requires the text to actually appear in the rendered transcript or `tmux capture-pane` output the user/agent was reading.

Treat these as three separate, independently falsifiable claims, and verify each one on its own evidence — never infer a later stage from an earlier one:

- **Computed**: the hooks JSONL's `output.system_message` / `output.context_injection` / `output.metadata.gate_transitions` show the gate fired and produced the expected content.
- **Delivered**: the log's `exit_code` is `0` with no `error` traceback, and the client-specific wire payload (e.g. `translate_agy`'s returned dict, or Claude's `hookSpecificOutput`) actually contains that content for the event in question — some events structurally cannot carry certain fields (see `resolve_policy_for_agy` in `aops-core/hooks/router.py`) and a gate assigned to one of those events can compute perfect content that is unconditionally undeliverable.
- **Seen**: the exact expected text is present in the `tmux capture-pane` output or rendered transcript the user/agent actually consumed this turn — not a paraphrase, not "a message of roughly that shape appeared."

A finding that only checks the hooks JSONL and reports "the gate fired and delivered its message" is incomplete and can be actively misleading — e.g. a crashed hook's log entry still carries the gate's pre-crash `system_message`, which reads exactly like a successful delivery unless you separately confirm `exit_code`/`error` and cross-check the pane/transcript. Every certification pass in this workflow (Axis 1/2 below, and the Closing Pipeline's marsha/rbg review) must state which of the three layers its evidence actually proves, per expected signal — not just whether "the hook worked."

## Part 1: Framework Smoke Test

### Step 1: Harness Setup

Create a dedicated headless environment for the test agent.

```bash
# Create a unique session ID and start a headless tmux session running agy (or claude)
SESSION_ID="e2e-test-$(date +%s)"
tmux new-session -d -s $SESSION_ID 'agy --model gemini-3.5-flash'
# Wait a few seconds for the agent to boot and initialize plugins
sleep 5
```

### Step 2: The E2E Scenario Execution

You will drive the test agent through three core scenarios. Send each prompt, wait for the agent to reach quiescence (by polling `tmux capture-pane -p`), and evaluate the result before proceeding.

**CRITICAL QUIESCENCE RULE:** You MUST NOT evaluate a test based on a loading screen. If your `tmux capture-pane` shows `Working...`, `Loading...`, or an active spinner (e.g. `⣟`, `⣻`), the agent has not reached quiescence. You must `sleep` and re-capture until you see the LLM's final response and a clean `>` prompt indicating it is ready for the next turn. Passing a test without observing its final state is a failure of your non-delegable judgment.

**CRITICAL FLOW RULE (Block and Satisfy):** If the test agent encounters an intentional block (e.g. a `Stop hook error` triggered by `rbg_review=block` or `qa=block`), you MUST NOT just say "it halted, pass." You must test the FULL flow:

1. Send a follow-up prompt instructing the agent to satisfy the gate (e.g., `"Run the rbg review to unblock this"`).
2. Wait for the agent to run the review and unblock the gate.
3. Verify that the agent successfully resumes its _original_ task once the block is cleared.

### Scenario A: MCP Config & Hook Gates

**Action:**

```bash
tmux send-keys -t $SESSION_ID "Use the aops MCP server to search for a task with the phrase 'test framework integrity'." C-m
```

**Evaluation Criteria:**

- _Infrastructure:_ Did the `PreToolUse` gate allow the MCP call? Did `PostToolUse` successfully record the observation?
- _Capability:_ Did the MCP server respond correctly without crashing or timing out?

### Scenario B: Skills & OS Commands

**Action:**

```bash
tmux send-keys -t $SESSION_ID "Now use the /aops skill to run a terminal command: echo 'infrastructure_test_pass'." C-m
```

**Evaluation Criteria:**

- _Infrastructure:_ Did the slash command parser hydrate the skill context?
- _Capability:_ Did the OS command tool execute safely and capture the output?

### Scenario C: Subagent Orchestration

**Action:**

```bash
tmux send-keys -t $SESSION_ID "Finally, delegate a quick check to the 'ida' subagent to verify the current directory name, then stop." C-m
```

**Evaluation Criteria:**

- _Infrastructure:_ Did the `SubagentStart` and `SubagentStop` hooks route context correctly? Did the `Stop` gate satisfy safely without trapping the agent in an error loop?
- _Capability:_ Did the subagent execute and report back its findings accurately?

### Step 3: Render the transcript yourself before delegating

Before invoking `marsha` or `rbg`, run `aops-core/scripts/transcript.py` **yourself** against the test session's own transcript file to produce a pinned, human-readable artifact:

```bash
python3 aops-core/scripts/transcript.py /path/to/<session-id>.jsonl -o /path/to/unique/e2e-<timestamp>
# generates e2e-<timestamp>-full.md and e2e-<timestamp>-abridged.md
```

Do this yourself rather than telling a subagent to go find the transcript — a subagent instructed to "verify against primary evidence" may independently search for "a session matching this description" and can collide with a stale, same-named leftover session from a prior run (tmux session names like `e2e-test-*`, `e2e-claude`, `e2e-agy` repeat across days and orphaned/trapped sessions can linger for a long time, continuing to write to their own logs — a fresh mtime does NOT mean a fresh session; check the session-ID timestamp prefix and, if the tmux session is still alive, its own `tmux list-sessions` "created" time). Rendering the transcript yourself gives you one unambiguous, timestamped artifact whose provenance you personally verified, to hand downstream instead of a bag of file paths.

## Part 2: Polecat Container Certification

This track answers a different question than Part 1: not "does the framework work in an agent's hands," but "does the _containerized dispatch path itself_ — config, plugins, credentials — do what it claims." Treat it as a supervisor's verification brief: state the acceptance gates up front, demand proof over claims, and never let a script's exit code substitute for your judgment.

**State these seven acceptance axes before dispatching anything**, so a reader can later tell what you set out to prove versus what you found:

1. Hooks fire appropriately for the events that occurred.
2. The agent's responses are appropriate to the prompt and to any gate constraint in play.
3. The agent can actually execute commands/tools inside the container (not merely attempt them).
4. The hook router recognizes the commands issued and opens the correct gate at the correct moment.
5. The agent has access to exactly the two aops plugins (`aops`, `aops-tools`) — no more, no fewer.
6. Gate status in the running session matches what `polecat.yaml` configures for the dispatch mode used.
7. The agent has `botnicbot` git credentials and _no other_ reachable git/GitHub identity or secret.

### Step 1: Dispatch — two real passes, not a simulation

Use the actual `polecat run` (or `polecat crew`) CLI — never hand-roll a bare tmux+client session for this track, since that bypasses the container, `polecat.yaml`, and credential scoping entirely (that's what Part 1 is for, and it cannot answer axes 4-7). Dispatch once with `--client claude` and once with `--client agy`, using the same task/prompt for both so results are comparable.

Reuse the existing boot sequence from [[11-self-test#2-polecat-session-validation]] rather than re-deriving it: image freshness check, plugin pre-check, tmux boot signals (same permission flags as a real `polecat run`, no plan mode — plan mode does not reflect real dispatch behaviour), and first-`UserPromptSubmit` liveness. Apply the same quiescence and block-and-satisfy rules from Part 1 Step 2 to every prompt you send here too.

### Step 2: Axis-by-axis verification

For each axis, the deliverable is a judgment (pass / fail / inconclusive) plus the evidence you judged it on — never a bare verdict.

- **Axis 1 — Hooks fire appropriately.** Read the session's hooks JSONL (path convention for polecat workers: `$POLECAT_HOME/polecats/<task-id>/<workspace>/<session-id>-hooks.jsonl`, per [[09-session-hook-forensics]]). Judge whether the _expected set_ of events occurred for the turns actually taken — apply the "Step 0: Verify hooks are operational in THIS session" method in [[11-self-test]] of reading raw stderr on every hook attachment, not a grep for one crash marker; a hook that attached with empty stderr but never fired for an event it should have covered is itself a finding. This axis only proves the **Computed** layer (see "Computed ≠ Delivered ≠ Seen" above) — check `exit_code`/`error` on the same record for **Delivered**, and do not mark this axis green on a log entry alone if the expected content was meant to reach the user.
- **Axis 2 — Agent responds appropriately.** Read the transcript AND cross-check against the raw `tmux capture-pane`/rendered pane output — not the hooks JSONL — for the **Seen** layer: judge whether the response addresses the actual prompt and respects any gate-imposed constraint (does it wait/comply rather than route around a hydration block?), and whether every expected user-facing signal (a gate's advisory text, a context injection, a subagent's reported result) actually appears in what the user/agent was shown this turn, verbatim — not a string match, and not inferred from the fact that a hook computed it.
- **Axis 3 — Agent can run commands.** Confirm at least one real tool/shell invocation inside the container returned a genuine success (exit code and output), not just that a tool call was attempted. Distinguish "blocked by a gate as designed" (a pass — that's a different axis) from "failed because of a container/environment defect" (a fail, this axis).
- **Axis 4 — Router recognizes commands and opens the correct gate.** Cross-reference the `GateTrigger` patterns in `aops-core/lib/gates/definitions.py` against the tool/subagent names actually invoked this session. Judge whether each trigger that should have matched produced the expected `GateTransition` in session state, at the correct turn boundary — use the "Check Gate Behavior" step under [[09-session-hook-forensics#steps]] as the mechanic; this axis supplies the judgment of whether it was the _right_ gate at the _right_ time, not merely _a_ gate.
- **Axis 5 — Exactly the two aops plugins.** Inside the container, run the plugin pre-check (`claude plugin list` on Claude; structural `ls ~/.gemini/antigravity-cli/plugins/` on agy — there is no `agy plugin list`; do not check `gemini extensions list`, that surface is deprecated and intentionally not installed, per the "§0.5 Plugin pre-check" note in [[11-self-test#2-polecat-session-validation]]) and diff against `polecat/defaults/claude-settings.json`'s `enabledPlugins` (`aops`, `aops-tools`, each present under both the `aops` and `academicOps` marketplace names — 2 distinct plugins, not 4). Explicitly confirm `aops-cowork` and `aops-ts` are **absent** — a positive-absence check, not just "the expected ones showed up."
- **Axis 6 — Gate status matches `polecat.yaml`.** Read the resolved `PolecatConfig.for_mode(...)` values for the mode you dispatched (`crew` or `run`) and compare against the `gate_modes` actually observed in session state at runtime. A gate configured `block` that never visibly blocks anything observable in this session is **inconclusive**, not a pass — say so rather than asserting green.
- **Axis 7 — `botnicbot`-only git credentials.** Inside the container, check `git config user.name`/`user.email`, `env | grep -i 'GIT_\|GH_\|GITHUB_'`, confirm `SSH_AUTH_SOCK` is unset, and inspect the credential helper / `insteadOf` rule. Note before you judge: `polecat/entrypoint.sh:5-6` defaults this identity to `aops-bot` via an explicit, reviewed `allow-fallback` annotation — that default is not itself a defect. The user-facing requirement names `botnicbot` specifically, and no repo document currently reconciles the two names. **If the observed in-container identity is anything other than `botnicbot`, do not silently pass and do not patch `entrypoint.sh` inline as part of a verification run.** Instead HALT and file a PKB task stating the observed identity, quoting the requirement, and citing `entrypoint.sh:5-6` plus the distinct PR-authorship-inconsistency issue (aops-ae3aa475, `specs/workflows/pr-pipeline.md` ~line 1158) for context — that issue is about _which bot opens a PR_, a different problem, so cite it as related context only, not as evidence this axis is already resolved. Separately, "no other credential reachable" _is_ directly assertable pass/fail regardless of which name wins: no personal token env vars, no other SSH keys mounted, `GIT_ASKPASS=true` present, HTTPS-forced `insteadOf` active.

### Step 3: Cross-client comparison

Run all seven axes for both the `claude` and `agy` passes and produce a diff table — axis × client × verdict × evidence pointer. Asymmetric breakage (one client fails an axis the other passes) is itself a finding worth escalating on its own, independent of whether either individual pass "succeeded."

### Step 4: Failure handoff

On any axis failure, root-cause it via [[09-session-hook-forensics]] before filing anything. File one PKB task per root cause, not one per symptom and not one per axis. If a failure reveals a recurring process gap rather than a one-off defect, route it through [[07-learning-log]] instead of (or in addition to) a bug task. Clean up regardless of outcome: `/exit`, `tmux kill-session`, `polecat nuke`.

## Closing Pipeline (shared by both parts)

Run this after whichever track(s) you executed above — Part 1 alone, Part 2 alone, or both.

### A. Log Verification via `marsha`

Visual verification of the `tmux` pane is necessary but not sufficient. You MUST delegate the rigorous extraction of log evidence to **`marsha` (The QA Reviewer)**, who is specialized in reading system logs.

1. **Locate the Logs:** Identify the sandbox session's raw transcript/hooks-log paths, plus the `-full.md`/`-abridged.md` pair you rendered in Step 3.
2. **Invoke Marsha:** Dispatch `marsha` with the exact raw log paths (she needs the raw `jsonl`, not just the rendered markdown, for exhaustive verbatim `exit_code`/`stderr` extraction) and instruct her to:
   - Extract verbatim proof that expected hooks fired and returned cleanly (`exit_code: 0`, no `stderr`).
   - Extract verbatim proof from the transcript that context injections successfully reached the LLM's prompt.
   - Cross-reference the transcript with the `tmux` pane captures to confirm the user UI remained clean.
   - For Part 2: extract verbatim proof for each of the seven axes above (gate transitions in session state, plugin list output, git identity/env output), not just the framework-smoke-test signals.
   - State explicitly that these are the only artifacts in scope — she should not go looking for other candidate sessions.

### B. Axiom Verification via `rbg`

Once `marsha` provides the raw evidence and proofs, you MUST delegate the legal/axiomatic review to **`rbg` (The Judge)**.

1. **Invoke RBG:** Feed rbg the **abridged markdown transcript** you rendered in Step 3 (not raw log paths) alongside `marsha`'s compiled evidence, and ask for a ruling on:
   - **Data Boundaries:** Does the evidence definitively prove that internal system context was properly isolated from the human surface?
   - **Honest Epistemics:** Does `marsha`'s extracted proof actually support the claim of success, or are there gaps?
   - **Halt on Failure:** Did the agent safely halt on any intentional roadblocks, or did it try to invent a workaround?
   - For Part 2: did the credential-isolation axis get a genuine HALT-and-file-task treatment if the observed identity wasn't `botnicbot`, rather than a silent pass or an inline patch?
2. **Pin the artifact, don't let rbg re-discover it.** State the exact abridged-transcript path (and the raw paths `marsha` verified) directly in the prompt, and instruct rbg to rule on _those specific files_ — not to independently search for "a session matching this description." If rbg's ruling cites a session ID or file path you didn't hand it, that is a signal the ruling is invalid: stop, confirm which artifact is actually yours (check the session-ID timestamp prefix and, for any still-live tmux session, its own `created` time — not file mtime, which a still-looping orphaned session keeps refreshing), and re-invoke rbg with the correct pinned artifact rather than either accepting or silently overruling the mismatched verdict.

### C. Synthesis & Certification Report

You must synthesize the findings from `marsha` and the rulings from `rbg` into a **Certification Report** and **OUTPUT it directly back to the user** (either in the conversational response or as a prominent Artifact).

The report MUST include **validation proof** (brief excerpts from the logs, transcript, or pane captures as extracted by `marsha`) confirming your evaluation.

If the system passes, clean up the harness:

```bash
tmux kill-session -t $SESSION_ID
```

Present the final Certification Report to the user, and optionally persist it to the PKB.
