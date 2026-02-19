# AcademicOps Framework v1.1 - Acceptance Test Report

**Date**: 2026-01-30
**Tester**: Claude Code (automated via acceptance testing guide)

## Versions Tested

| Component             | Version |
| --------------------- | ------- |
| AcademicOps Framework | v1.1    |
| Claude Code           | 2.1.15  |
| Gemini CLI            | 0.26.0  |
| uv                    | 0.9.10  |

## Test Results Summary

| Test                    | Status | Notes                                         |
| ----------------------- | ------ | --------------------------------------------- |
| Prerequisites Check     | PASS   | `$AOPS` set, `uv` available                   |
| Installation (setup.sh) | PASS   | 42 workflows, 12 skills, 9 commands installed |
| Test A: Gemini Headless | PASS   | Task aops-9e78192b completed successfully     |
| Test B: Claude Headless | PASS   | Task aops-64a8071a completed successfully     |
| Artifact Validation     | PASS   | Transcripts generated with task context       |

**Overall Result**: ALL TESTS PASSED

## Detailed Test Results

### 1. Prerequisites Check

```
AOPS=/home/user/src/academicOps
uv 0.9.10
```

### 2. Installation Verification

- setup.sh executed successfully
- Extensions installed: aops-core, aops-tools
- Global workflows: 42 files linked to `~/.gemini/antigravity/global_workflows/`
- Global skills: 12 skills linked
- Global commands: 9 commands linked

### 3. Test A: Gemini Headless Execution

- **Task ID**: aops-9e78192b
- **Command**: `uv run scripts/automated_test_harness.py --create "Check current directory and print files" --agent gemini`
- **Result**: PASS
- **Observations**:
  - Task created and claimed by polecat
  - Worktree set up at `/home/user/.aops/polecat/aops-9e78192b`
  - Agent executed successfully in YOLO mode
  - Task marked as `done`
  - Transcript verified

### 4. Test B: Claude Headless Execution

- **Task ID**: aops-64a8071a
- **Command**: `uv run scripts/automated_test_harness.py --create "Check current directory and print files" --agent claude`
- **Result**: PASS
- **Transcript**: `/home/user/writing/sessions/claude/20260130-06-64a8071a-96f01f0e-session-abridged.md`
- **Observations**:
  - Task created and claimed by polecat
  - Worktree set up successfully
  - Agent executed with `/pull` skill invocation
  - Hydration context injected (prompt-hydrator invoked)
  - Task marked as `done`
  - Transcript contains task ID and context

### 5. Artifact Validation

- **Gemini Transcript**: Generated and verified by harness
- **Claude Transcript**: `/home/user/writing/sessions/claude/20260130-06-64a8071a-96f01f0e-session-abridged.md`
  - Contains session metadata
  - Shows skill/workflow invocations: `aops-core:framework`, `aops-core:prompt-hydrator`
  - Token usage tracked: 97 in / 71 out, 1.4M cache read

## Known Issues / Observations

1. **SessionEnd Hook Schema**: Minor schema validation warning for Claude's SessionEnd hook output. Does not affect functionality.

2. **Task Status Coercion**: Several legacy tasks have non-standard statuses (`planning`, `ongoing`, etc.) that get coerced to `active`. This is expected behavior.

3. **Hydration Gate (Warn Mode)**: Four-gate check running in warn mode during testing. In production, would enforce:
   - Task binding
   - Plan mode invocation
   - Critic invocation
   - Todo with handover

## Conclusion

The AcademicOps Framework v1.1 passes all acceptance tests for both Gemini CLI and Claude Code headless execution. The polecat orchestrator successfully:

- Creates and manages worktrees
- Invokes agents in headless/YOLO mode
- Generates and verifies transcripts
- Tracks task lifecycle (active -> in_progress -> done)

**Framework is ready for v1.1 release.**
