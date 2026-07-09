# Agentic E2E QA Certification

This protocol defines the End-to-End Certification for the academicOps framework. In accordance with the **Judgment is Non-Delegable** axiom, this certification is executed and evaluated by a _smart agent_ (e.g., the orchestrator or `marsha`), not by rigid deterministic scripts.

## The Role of the Evaluating Agent

As the evaluating agent, you are the Test Driver. You will:

1. Spawn a live, headless instance of the framework inside a `tmux` session.
2. Simulate a human user by injecting prompts via `tmux send-keys`.
3. Use your qualitative judgment to observe the test agent's behavior via `tmux capture-pane` and its session transcript.
4. Evaluate whether the framework components (Hooks, MCP, Skills, Subagents) functioned correctly and gracefully.

## Step 1: Harness Setup

Create a dedicated headless environment for the test agent.

```bash
# Create a unique session ID and start a headless tmux session running agy (or claude)
SESSION_ID="e2e-test-$(date +%s)"
tmux new-session -d -s $SESSION_ID 'agy --model gemini-3.5-flash'
# Wait a few seconds for the agent to boot and initialize plugins
sleep 5
```

## Step 2: The E2E Scenario Execution

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

## Step 3: Log Verification via `marsha`

Visual verification of the `tmux` pane is necessary but not sufficient. You MUST delegate the rigorous extraction of log evidence to **`marsha` (The QA Reviewer)**, who is specialized in reading system logs.

1. **Locate the Logs:** Identify the sandbox session's logs directory (`transcript_full.jsonl` and `*-hooks.jsonl`).
2. **Invoke Marsha:** Dispatch `marsha` with the paths to the logs and instruct her to:
   - Extract verbatim proof that expected hooks fired and returned cleanly (`exit_code: 0`, no `stderr`).
   - Extract verbatim proof from the transcript that context injections successfully reached the LLM's prompt.
   - Cross-reference the transcript with the `tmux` pane captures to confirm the user UI remained clean.

## Step 4: Axiom Verification via `rbg`

Once `marsha` provides the raw evidence and proofs, you MUST delegate the legal/axiomatic review to **`rbg` (The Judge)**.

1. **Invoke RBG:** Pass `marsha`'s compiled evidence to `rbg` and ask for a ruling on:
   - **Data Boundaries:** Does the evidence definitively prove that internal system context was properly isolated from the human surface?
   - **Honest Epistemics:** Does `marsha`'s extracted proof actually support the claim of success, or are there gaps?
   - **Halt on Failure:** Did the agent safely halt on any intentional roadblocks, or did it try to invent a workaround?

## Step 5: Synthesis & Certification Report

You must synthesize the findings from `marsha` and the rulings from `rbg` into a **Certification Report** and **OUTPUT it directly back to the user** (either in the conversational response or as a prominent Artifact).

The report MUST include **validation proof** (brief excerpts from the logs, transcript, or pane captures as extracted by `marsha`) confirming your evaluation.

If the system passes, clean up the harness:

```bash
tmux kill-session -t $SESSION_ID
```

Present the final Certification Report to the user, and optionally persist it to the PKB.
