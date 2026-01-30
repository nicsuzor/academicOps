# AcademicOps Framework Acceptance Testing Guide

This guide details the step-by-step instructions for an agent (or execution harness) to perform full acceptance testing on the academicOps framework, particularly verifying recent fixes to hydration, installation, and agent execution.

## 1. Prerequisites & Environment Check

Before running tests, ensure the environment is clean and configured:

1. **Check `AOPS` variable**: Ensure `$AOPS` is set and points to the framework root.
2. **Check `uv` installation**: Ensure `uv` is in path.

```bash
echo $AOPS
uv --version
```

## 2. Installation Verification (Setup Regression)

Verify that the setup script correctly installs commands and workflows (fixing the recent regression).

1. **Run Setup**:

    ```bash
    cd $AOPS
    ./setup.sh
    ``

2. **Verify Global Workflows**: Check if `~/.gemini/antigravity/global_workflows` contains framework workflows.

    ```bash
    ls ~/.gemini/antigravity/global_workflows
    ```

    *Expectation*: Should list files like `audit.md`, `email.md`, etc.

## 3. Hydration & Hook Verification

Verify that the hydration system (which injects context) is working and failing hooks are visible.

1. **Verify Hook Configuration**:
    Check `aops-core/gemini-extension.json` ensures `hooks` are pointing to the correct router.
2. **Manual Hook Check** (Optional):
    Inspect `logs/user_prompt_submit.log` (if enabled) or ensure the previous silent failures are now logging errors.

## 4. Automated Agent Testing (The Harness)

Use the `automated_test_harness.py` to run end-to-end tests with headless agents.

### Test A: Gemini Headless Execution

Run the harness using Gemini to verify the `polecat -> gemini` path.

```bash
uv run scripts/automated_test_harness.py --create "Check current directory and print files" --agent gemini
```

*Success Criteria*:

- Harness creates a "TEST" task.
- Polecat output shows successful worktree setup and agent run.
- Agent successfully lists files.
- Harness finds and verifies the generated transcript.

### Test B: Claude Headless Execution

Run the harness using Claude to verify the `polecat -> claude` path.

```bash
uv run scripts/automated_test_harness.py --create "Check current directory and print files" --agent claude
```

*Success Criteria*:

- Similar to Gemini, but verifies Claude CLI invocation (`--permission-mode plan`).
- Transcript is generated and verified.

### Test C: Real Work (Stack Pull)

Verify that the harness can pull a real task from the stack and operate without destruction (Worktree preservation).

```bash
uv run scripts/automated_test_harness.py --agent gemini
```

*Success Criteria*:

- Harness claims the next tasks.
- Agent runs successfully.
- Harness defaults to `--keep` (no cleanup) for safety.

## 5. Artifact Validation

After tests, verify that artifacts are correct:

1. **Transcripts**: Check `~/writing/sessions/` for generated transcripts.
    - **CRITICAL**: Worker session IDs do NOT match task IDs. To find a transcript:
      ```bash
      rg "task-id" ~/writing/sessions/  # Search by task ID mentioned in transcript
      ```
    - Use `session_transcript.py` to generate readable transcripts:
      ```bash
      uv run python $AOPS/aops-core/scripts/session_transcript.py <session.jsonl> -o ~/writing/sessions/<task-id>-transcript.md
      ```
    - Ensure transcripts contain task context injected by hydration.
    - Ensure transcripts contain the agent's output.

2. **Task Status**: Check that test tasks are either closed or in the expected state (if `--keep` was used).

3. **Worker Session Tracking** (Known Gap):
    - Worker sessions generate auto-IDs (e.g., `59513a-f50d0dd2`) that differ from task IDs (e.g., `aops-dd44aefa`)
    - **Workaround**: Search transcripts by task ID content, not filename
    - **Future fix**: See task `aops-f24e2bb8` for session ID tracking implementation

## 5.1 Review Workflow (Before Merge)

Before merging worker output to main:

1. **Find the transcript** - Search by task ID in `~/writing/sessions/`
   - Transcripts may be named with session hash, not task ID
   - Use `rg "<task-id>" ~/writing/sessions/` to find relevant transcript
2. **Review the DIFF, not just agent claims** - Check actual code changes:
   ```bash
   cd ~/.aops/polecat/<task-id>
   git diff  # See uncommitted changes
   git log --oneline -5  # See what was committed
   ```
3. **Watch for Gemini escaping regressions** - Gemini may replace `\n` with `\\n` across files
4. **Verify tests pass** - Run `pytest` in the worktree
5. **Check for uncommitted work** - Workers often mark done without committing (known bug)
6. **Commit if salvaging uncommitted work**:
   ```bash
   cd ~/.aops/polecat/<task-id>
   git add -A && git commit -m "feat(<area>): <task summary>"
   ```
7. **Create REVIEW task** - Document findings for approval before merge
8. **Merge only after approval** - Use the correct workflow:
   ```bash
   # Step 1: Push from worktree to origin (worktrees use separate repo)
   cd ~/.aops/polecat/<task-id>
   git push origin polecat/<task-id>:polecat/<task-id>

   # Step 2: Fetch and merge in main worktree
   cd $AOPS
   git fetch origin polecat/<task-id>
   git merge origin/polecat/<task-id> --no-ff -m "Merge <task-id>: <description>"
   git push origin main
   ```

**IMPORTANT**: You CANNOT merge directly from worktree path - polecat worktrees use a separate bare repo (`~/.aops/polecat/.repos/aops.git`). Must push to origin first.

## 6. Report Generation

Run the `generate_walkthrough` or manually update `walkthrough.md` with:

- Versions tested.
- Pass/Fail status of each test.
- Links to relevant transcripts.
- Any regressions found.
