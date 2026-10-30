---
name: verify
description: Judgement-based QA pass verifying artifacts against acceptance criteria and fitness rubrics. Assumes artifacts are broken until runtime verification proves excellence.
---

# Verify

Rigorous quality and requirement-satisfaction review evaluating whether the artifact, as presented, is amazingly good -- across runtime behaviour, actual rendered multimodal outputs, code, prose, UX, and analytical soundness. We are not chasing "works" or mediocrity. Default posture: assume every fact is wrong and every change is broken until proven otherwise.

## 1. Upfront Standard & Specification Check

Before running test suites or line-by-line code audits, identify the format/quality standard governing the artifact's genre (`specs/meta/doc-taxonomy.md` -- e.g., `specs/meta/writing-specs.md` for specifications, `craft` for agent instructions, disciplinary standards for manuscripts/articles, or task acceptance criteria for task handbacks) and locate whatever specifications, requirements, or acceptance criteria are available:

- **Match format requirements to the artifact**: Never impose task-handback sections (`## Ask`, task checklists) on non-task artifacts.
- **Missing-criteria failure signal**: If **no governing standard, specifications, requirements, or acceptance criteria are available at all**, stop immediately and return `FAIL -- no governing standard, specifications, requirements, or acceptance criteria available`.
- **Mechanical**: Verify strictly against the governing genre standard and available specifications, requirements, and acceptance criteria.
- **Fitness / Mixed**: Verify against the governing genre standard, specifications, requirements, acceptance criteria, and the spec's fitness rubric. If criteria exist but the fitness rubric is missing on a fitness task, return `REVISE -- fitness rubric missing`.
- **Primary materials**: Audit underlying primary materials (git history, raw data, external source files) on **high-risk requests**; on routine requests, verify the presented artifact and its rendered outputs against its governing standard and requirements.

## 2. Mandatory Forcing Checks

When specifications, requirements, or acceptance criteria exist, preserve full coverage across all stated criteria and answer all five checks explicitly before rendering a `PASS`:

1. **Rendered multimodal output inspection (never code alone or simulations)**: Evaluate the artifact in its actual rendered, multimodal form -- live execution output, rendered PDFs, visual plots, UI screenshots, and built containers. Reading source code is never sufficient, and output renders may **never** be simulated, mocked, or inferred from source text.
2. **Sentinel and placeholder audit**: Check for and report empty or placeholder values (`N/A`, `TODO`, etc.).
3. **Principal's-eye top-line read**: Quote the primary user-facing output verbatim and verify correctness for the actual end user.
4. **Floor versus ceiling**: Answer explicitly: "Amazingly good, or merely working?" Merely working fails fitness tasks.
5. **Durable primary deliverables and logical entailment**: Inspect durable primary deliverables (repository commits, branches, PRs, or PKB records) directly rather than ephemeral container paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container worktrees). Tool-call spans in Phoenix prove execution rather than logical entailment or sufficiency; evaluate whether observed evidence logically entails every acceptance criterion.

## 3. Immediate Fail Triggers

Render an immediate `FAIL` on:

- Absence of any specifications, requirements, or acceptance criteria against which to test the artifact.
- Output renders that are simulated, mocked, or uninspected in their actual rendered multimodal form.
- Falsified empirical claim or missing cited path under per-claim fail-fast (record `UNMET` immediately without searching repo for fixes).
- Asserting Phoenix tool spans or command execution as proof of logical entailment without evaluating whether primary deliverables satisfy acceptance criteria.
- Pointers citing ephemeral container paths (`<appDataDir>/brain/`, `/tmp/`, unpushed container worktrees) instead of durable primary deliverables (repo commits, PRs, PKB tasks/notes).
- Sentinel values or placeholder text in production outputs.
- Silent exception swallowing without error logging.
- Tests that assert existence or tautologies rather than functional behavior, change-detector tests that restate what a file, config or directory holds today, or tests that would still pass with the change's plausible bug introduced.
- Data that diverges from primary source records.
- Edits made directly to runtime install directories instead of source repos.
- Container or Dockerfile changes passed without building the image and showing changed content present in it, or stating plainly that the worker could not build.

## 4. Visual and Multimodal Verification

Evaluate live rendered outputs and screenshots (1920x1080) across three dimensions:

- **Legibility**: Overlapping text, poor contrast, or unreadable sizing.
- **Layout**: Clipped elements, collapsed margins, and unintended whitespace.
- **Hierarchy**: Geometry and visual weight matched to semantic importance.

## 5. Container and Dockerfile Verification

Any change touching a container image or Dockerfile requires:

1. **Built image**: Build the container image.
2. **Content inspection**: Show the changed content present in the built image (files, permissions, or commands).
3. **Inability to build**: If the environment prevents building (daemon unavailable or insufficient permissions), state plainly that the worker could not build and why. Never pass on source inspection or host tests alone.

## 6. Output Format

Emit the report using `/dump`'s handback envelope and record it on the task record. VERDICT is your judgement of the artifact (`PASS`, `REVISE`, or `FAIL`); STATUS is the release status of your own task (`failed` when VERDICT is `FAIL` or `REVISE` with failure evidence and root cause documented; `done` when VERDICT is `PASS`). Never file fix tasks or follow-up tasks.

```markdown
## Handover: <agent> <session-id>

1. **Task**: Task id, title, verified target and bar (`mechanical | fitness | mixed`).
2. **Summary**: Findings, forcing checks (1–5), and remediations for `FAIL`/`REVISE`.
3. **Verdict & Safeguards**:
   - VERDICT: <PASS | REVISE | FAIL>
   - STATUS: <release status: done | partial | failed | cancelled | in_progress>
   - CRITERIA: <acceptance criterion id tested and observed result>
   - CONFIDENCE: <high | med | low> + <what single check would falsify this>
   - CONFOUND CHECK: <clean-room/differential control result, or "NOT RUN">
4. **Output**: <branch + commit SHA> | <PR or artifact link>
5. **Argument**: The `argdown` block recorded under the task's `## Report`, asked by the task's ask ids.
6. **Limitations**: Unresolved items, out-of-scope elements, and verbatim error outputs.
```
