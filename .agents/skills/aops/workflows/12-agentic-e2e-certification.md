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
tmux send-keys -t $SESSION_ID "Use the aops-pkb MCP server to search for a task with the phrase 'test framework integrity'." C-m
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

## Part 2: Polecat Container Certification

This track answers a different question than Part 1: not "does the framework work in an agent's hands," but "does the _containerized dispatch path itself_ — config, plugins, credentials — do what it claims." Treat it as a supervisor's verification brief: state the acceptance gates up front, demand proof over claims, and never let a script's exit code substitute for your judgment.

**State these seven acceptance axes before dispatching anything**, so a reader can later tell what you set out to prove versus what you found:

1. Hooks fire appropriately for the events that occurred.
2. The agent's responses are appropriate to the prompt and to any gate constraint in play.
3. The agent can actually execute commands/tools inside the container (not merely attempt them).
4. The hook router recognizes the commands issued and opens the correct gate at the correct moment.
5. The agent has access to exactly the four aops plugins — no more, no fewer.
6. Gate status in the running session matches what `polecat.yaml` configures for the dispatch mode used.
7. The agent has `botnicbot` git credentials and _no other_ reachable git/GitHub identity or secret.

### Step 1: Dispatch — two real passes, not a simulation

Use the actual `polecat run` (or `polecat crew`) CLI — never hand-roll a bare tmux+client session for this track, since that bypasses the container, `polecat.yaml`, and credential scoping entirely (that's what Part 1 is for, and it cannot answer axes 4-7). Dispatch once with `--client claude` and once with `--client agy`, using the same task/prompt for both so results are comparable.

Reuse the existing boot sequence from [[11-self-test#2-polecat-session-validation]] rather than re-deriving it: image freshness check, plugin pre-check, tmux boot signals (same permission flags as a real `polecat run`, no plan mode — plan mode does not reflect real dispatch behaviour), and first-`UserPromptSubmit` liveness. Apply the same quiescence and block-and-satisfy rules from Part 1 Step 2 to every prompt you send here too.

### Step 2: Axis-by-axis verification

For each axis, the deliverable is a judgment (pass / fail / inconclusive) plus the evidence you judged it on — never a bare verdict.

- **Axis 1 — Hooks fire appropriately.** Read the session's hooks JSONL (path convention for polecat workers: `$POLECAT_HOME/polecats/<task-id>/<workspace>/<session-id>-hooks.jsonl`, per [[09-session-hook-forensics]]). Judge whether the _expected set_ of events occurred for the turns actually taken — apply the "Step 0: Verify hooks are operational in THIS session" method in [[11-self-test]] of reading raw stderr on every hook attachment, not a grep for one crash marker; a hook that attached with empty stderr but never fired for an event it should have covered is itself a finding.
- **Axis 2 — Agent responds appropriately.** Read the transcript and judge whether the response addresses the actual prompt and respects any gate-imposed constraint (does it wait/comply rather than route around a hydration block?) — not a string match.
- **Axis 3 — Agent can run commands.** Confirm at least one real tool/shell invocation inside the container returned a genuine success (exit code and output), not just that a tool call was attempted. Distinguish "blocked by a gate as designed" (a pass — that's a different axis) from "failed because of a container/environment defect" (a fail, this axis).
- **Axis 4 — Router recognizes commands and opens the correct gate.** Cross-reference the `GateTrigger` patterns in `aops-core/lib/gates/definitions.py` against the tool/subagent names actually invoked this session. Judge whether each trigger that should have matched produced the expected `GateTransition` in session state, at the correct turn boundary — use the "Check Gate Behavior" step under [[09-session-hook-forensics#steps]] as the mechanic; this axis supplies the judgment of whether it was the _right_ gate at the _right_ time, not merely _a_ gate.
- **Axis 5 — Exactly the four aops plugins.** Inside the container, run the plugin pre-check (`claude plugin list` / `gemini extensions list`, per the "§0.5 Plugin pre-check" note in [[11-self-test#2-polecat-session-validation]]) and diff against the allowlist in `polecat/defaults/claude-settings.json` (`aops-core`, `aops-tools`, `aops-pkb`, `aops-extras`). Explicitly confirm `aops-cowork` and `aops-ts` are **absent** — a positive-absence check, not just "the four expected ones showed up."
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

1. **Locate the Logs:** Identify the sandbox session's logs directory (`transcript_full.jsonl` and `*-hooks.jsonl`).
2. **Invoke Marsha:** Dispatch `marsha` with the paths to the logs and instruct her to:
   - Extract verbatim proof that expected hooks fired and returned cleanly (`exit_code: 0`, no `stderr`).
   - Extract verbatim proof from the transcript that context injections successfully reached the LLM's prompt.
   - Cross-reference the transcript with the `tmux` pane captures to confirm the user UI remained clean.
   - For Part 2: extract verbatim proof for each of the seven axes above (gate transitions in session state, plugin list output, git identity/env output), not just the framework-smoke-test signals.

### B. Axiom Verification via `rbg`

Once `marsha` provides the raw evidence and proofs, you MUST delegate the legal/axiomatic review to **`rbg` (The Judge)**.

1. **Invoke RBG:** Pass `marsha`'s compiled evidence to `rbg` and ask for a ruling on:
   - **Data Boundaries:** Does the evidence definitively prove that internal system context was properly isolated from the human surface?
   - **Honest Epistemics:** Does `marsha`'s extracted proof actually support the claim of success, or are there gaps?
   - **Halt on Failure:** Did the agent safely halt on any intentional roadblocks, or did it try to invent a workaround?
   - For Part 2: did the credential-isolation axis get a genuine HALT-and-file-task treatment if the observed identity wasn't `botnicbot`, rather than a silent pass or an inline patch?

### C. Synthesis & Certification Report

You must synthesize the findings from `marsha` and the rulings from `rbg` into a **Certification Report** and **OUTPUT it directly back to the user** (either in the conversational response or as a prominent Artifact).

The report MUST include **validation proof** (brief excerpts from the logs, transcript, or pane captures as extracted by `marsha`) confirming your evaluation.

If the system passes, clean up the harness:

```bash
tmux kill-session -t $SESSION_ID
```

Present the final Certification Report to the user, and optionally persist it to the PKB.
