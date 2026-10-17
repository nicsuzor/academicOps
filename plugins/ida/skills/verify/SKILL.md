---
name: verify
description: Judgement-based QA pass verifying artifacts against acceptance criteria and fitness rubrics. Assumes artifacts are broken until runtime verification proves excellence.
---

# Verify

Rigorous quality review evaluating correctness, completion, and fitness for purpose. Default posture: assume the artifact is broken until proven working.

## 1. Classify the Bar

- **Mechanical**: Verify strictly against acceptance criteria.
- **Fitness / Mixed**: Verify against acceptance criteria and the spec's fitness rubric. If the rubric is missing on a fitness task, return `REVISE -- fitness rubric missing`.

## 2. Mandatory Forcing Checks

All four checks must be answered explicitly in the report before rendering a `PASS`:
0. **Premise test**: Is the underlying premise sound, or would a sharp principal reject it? (Bad premise = `FAIL`).

1. **Sentinel and placeholder audit**: Check for and report empty or placeholder values (`N/A`, `TODO`, etc.).
2. **Principal's-eye top-line read**: Quote the primary user-facing output verbatim and verify correctness for the actual end user.
3. **Floor versus ceiling**: Answer explicitly: "Exceptional, or merely working?" Merely working fails fitness tasks.

## 3. Immediate Fail Triggers

Render an immediate `FAIL` on:

- Bad premise or invalidated requirements.
- Sentinel values or placeholder text in production outputs.
- Silent exception swallowing without error logging.
- Tests that assert existence or tautologies rather than functional behavior.
- Data that diverges from primary source records.
- Edits made directly to runtime install directories instead of source repos.
- Container or Dockerfile changes passed without building the image and showing changed content present in it, or stating plainly that the worker could not build.

## 4. Visual Verification

Evaluate live rendered screenshots (1920x1080) across three dimensions:

- **Legibility**: Overlapping text, poor contrast, or unreadable sizing.
- **Layout**: Clipped elements, collapsed margins, and unintended whitespace.
- **Hierarchy**: Geometry and visual weight matched to semantic importance.

## 5. Container and Dockerfile Verification

Any change touching a container image or Dockerfile requires:

1. **Built image**: Build the container image.
2. **Content inspection**: Show the changed content present in the built image (files, permissions, or commands).
3. **Inability to build**: If the environment prevents building (daemon unavailable or insufficient permissions), state plainly that the worker could not build and why. Never pass on source inspection or host tests alone.

## 6. Output Format

Emit the report using `/dump`'s handback envelope and record it on the task record. VERDICT is your judgement of the artifact, in the verdict vocabulary `premise-check` uses; STATUS is the release status of your own task.

```markdown
## Handover: <agent> <session-id>

1. **Task**: Task id, title, verified target and bar (`mechanical | fitness | mixed`).
2. **Summary**: Findings, forcing checks (0–3), and remediations for `FAIL`/`REVISE`.
3. **Verdict & Safeguards**:
   - VERDICT: <PASS | REVISE | FAIL>
   - STATUS: <release status: done | partial | review | failed | cancelled | in_progress>
   - GATE: <acceptance criterion id tested and observed result>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <clean-room/differential control result, or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Argument**: The `argument` block recorded under the task's `## Report`, asked by the task's ask ids.
6. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
```
