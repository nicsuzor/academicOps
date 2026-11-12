---
name: verify
description: "Universal qualitative verification procedure evaluating artifacts against genre standards, audience empathy, and purpose satisfaction across live rendered multimodal outputs."
---

# Verify

Universal qualitative verification procedure for evaluating whether an artifact meets the framework's bar of excellence across live rendered multimodal outputs.

## 1. Upfront Genre & Audience Alignment

Before inspecting details:

1. **Identify Artifact Genre:** Determine the governing standard for the artifact's genre per `specs/meta/doc-taxonomy.md` (e.g. `craft` for instructions, `writing-specs.md` for specs, visual design standards for UI/plots, publication standards for manuscripts).
2. **Identify Audience & Purpose:** Define who reads or uses this artifact, what cognitive state they bring, and what outcome the artifact must achieve for them.
3. **Set Proportionality Bar:**
   - _Routine / Low-Risk:_ Fast single-pass sanity check; low bar.
   - _High-Stakes / Public:_ Comprehensive aesthetic and cognitive audit.

## 2. Live Rendered Multimodal Inspection

Review the artifact in its actual rendered form as experienced by the user:

1. **Rendered View:** Inspect the compiled document, rendered markdown layout, generated PDF, or UI screenshot (1920x1080).
2. **Legibility & Hierarchy:** Ensure typographic scale matches semantic importance; check contrast, whitespace, and line lengths.
3. **Audience Empathy:** Does the artifact respect the reader's attention? For an ADHD reader, is it scannable in under 2 minutes? For a technical user, is it direct and unambiguous?
4. **Floor vs. Ceiling:** Answer explicitly: _Is this amazingly good for its purpose, or merely mediocre?_

## 3. Review Findings & Self-Fixes

- **Uncontroversial Self-Fixes:** When authorized by the supervising workflow (e.g. in `strategic-review` with `--fix`), directly apply and commit obvious typographic, minor formatting, or visual layout corrections (`fix(review): ...`), documenting them under `### Reviewer Self-Fixes Applied`. In the standard parallel pre-handback review (`wf-finish.md`), report suggested repairs under `### Suggested Fixes` for the writer to incorporate during the single fix pass, preventing concurrent git write conflicts.
- **Substantive Findings:** Document qualitative shortcomings with clear, constructive guidance on tone, layout, structure, or audience alignment.

## 4. Verdict Schema

- `PASS`: The artifact is amazingly good for its intended audience and purpose.
- `REVISE`: The artifact is functional but requires concrete structural, tonal, or layout polish to achieve excellence.
- `FAIL`: The artifact fundamentally fails its intended purpose, exhibits severe cognitive clutter or visual unreadability, or lacks any governing standard or purpose.
