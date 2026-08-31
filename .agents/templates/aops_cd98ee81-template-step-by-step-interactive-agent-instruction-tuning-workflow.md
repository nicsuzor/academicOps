---
created: 2026-08-12T11:21:37.055549675+00:00
id: aops_cd98ee81
last_modified: 2026-08-13T04:54:21.428004367+00:00
modified: 2026-08-13T04:54:21.428002033+00:00
priority: 2
project: aops
status: ready
tags:
- interactive-testing
- template
- workflow
- instruction-tuning
- harness
title: 'Template: Step-by-Step Interactive Agent Instruction Tuning Workflow'
type: template
---

# Step-by-Step Interactive Agent Instruction Tuning & Feature Verification Protocol

## Purpose

This workflow establishes a generalizable, human-in-the-loop procedure for verifying framework features step-by-step with a live target agent instance (`agy` or `claude`).

Instead of running an agent end-to-end unsupervised (where failures are hard to isolate), the driver agent and user walk through the expected task plan one discrete step at a time. If the target agent deviates, fails, or produces sub-optimal results:

1. The target session is stopped/killed immediately.
2. The user and driver discuss prompt/instruction gaps ("how to persuade the agent").
3. Instruction/code fixes are made in-place.
4. Hot distribution artifacts (`./dist/`) are rebuilt so the target reloads updated plugins on restart.
5. The step is re-tested interactively until it passes cleanly.

---

## Standard 4-Phase Protocol

### Phase 1: Research & Step Decomposition

1. **Thorough PKB & Spec Search**:
   - Query PKB, `/workspace/specs/`, `.agents/skills/`, and `plugins/` for relevant specifications, rules, axioms, and prior art.
   - Map out all hard invariants (paths, schemas, rules, formatting, user data preservation).
2. **Formulate Step-by-Step Expected Micro-Actions**:
   - Break down the task into numbered, granular micro-steps.
   - For each micro-step, specify:
     - **Input / Prompt**: Exact prompt or trigger given to target agent.
     - **Expected Actions**: Expected tools called, files read/written, or text generated.
     - **Verification / Pass Criteria**: Empirical signals to confirm success before moving to step N+1.

### Phase 2: Test Harness Setup & Local Dist Staging

1. **Environment & Dist Staging**:
   - Verify `$POLECAT_HOME`, `$GEMINI_CONFIG_DIR`, `$AOPS_SESSIONS`, and `$PKB_MCP_URL`.
   - Ensure local plugin build target `./dist/` is fresh (`make build` / plugin dist sync).
2. **Interactive Session Launch**:
   - Spin up target agent in a dedicated `tmux` session using `debug` skill conventions:
     ```bash
     export TMUX_NAME="step-test-$RANDOM"
     # Launch script pointing at local ./dist/ plugins
     tmux new-session -d -s "$TMUX_NAME" -x 220 -y 50 "/tmp/launch-$TMUX_NAME.sh"
     ```
   - Verify boot readiness signal (auth race cleared, TUI prompt ready).

### Phase 3: Interactive Step-by-Step Execution Loop

For each step in the micro-action sequence:

1. **Inject Step Prompt**: Send single-step command via `tmux send-keys -t "$TMUX_NAME" -l "<prompt>"; tmux send-keys -t "$TMUX_NAME" Enter`.
2. **Monitor Output**: Capture pane state (`tmux capture-pane -t "$TMUX_NAME" -p -S -2000`) and inspect raw JSONL transcripts (`$AOPS_SESSIONS/.../transcript_full.jsonl`).
3. **Evaluate against Criteria**:
   - **PASS**: Output matches expected behavior. Record observation and proceed to next step.
   - **FAIL / DEVIATION**:
     - **Kill Target**: `/exit` or `tmux kill-session -t "$TMUX_NAME"`.
     - **Persuasion Analysis**: User and driver analyze why the model failed (unclear prompt, missing constraint in SKILL.md, tool edge case).
     - **Apply Fix In-Place**: Update prompt instructions, skill definition, or plugin code. Rebuild `./dist/` (`make build` / plugin sync).
     - **Re-Test Step**: Restart target instance, re-inject step prompt, and verify fix.

### Phase 4: Verification & Handover

1. Validate end-to-end outcome against feature specifications.
2. Record learnings in PKB via `learn` skill or task release summary.
3. Clean up temporary test sessions and harness files.
