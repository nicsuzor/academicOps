---
name: verify
description: "Universal qualitative verification procedure evaluating qualitative excellence, audience empathy, and purpose fit across live rendered multimodal outputs when an audience-facing artifact is produced (exclude non-build lookups/diagnostics, linters, fact-checking, and functional QA)."
---

# Verify

Universal qualitative verification procedure evaluating qualitative excellence, audience resonance, and purpose fit across live rendered multimodal outputs when an audience-facing artifact was built (never non-build lookups/diagnostics, linters, schema checks, primary-source fact-checking, or functional QA).

## 1. Scope, Audience & Contextual Standard

Before inspecting details:

1. **Confirm Audience-Facing Artifact:** Verify an audience-facing deliverable exists (document, specification, instruction file, plot, PDF, UI). Skip `verify` on non-build lookups, diagnostics, or pure plumbing with no audience-facing output.
2. **Define Audience, Purpose & Contextual Standard:** Identify who meets the artifact, their cognitive context, and the outcome it serves. Apply any standard set by the user; otherwise evaluate against what is reasonable and appropriate for the audience, medium, and purpose in all the circumstances (e.g., `craft` for agent instructions, specification clarity, visual/cognitive clarity for plots/UI, scholarly polish for manuscripts -- never a rigid genre lookup table).
3. **Direct Qualitative Judgment & Proportionality:**
   - _Internal / Routine / Defeasible:_ Brisk scannability and clarity check, deferring to reasonable stylistic and structural discretion.
   - _Public / High-Stakes:_ Uncompromising aesthetic, structural, and cognitive critique.
   - Evaluate qualitative standards directly with appealable reasons; never invent or demand arbitrary numeric cutoffs, quotas, or countable proxies in place of qualitative judgment (`judgment-non-delegable`).

## 2. Live Rendered Multimodal Inspection

Inspect the artifact in its rendered form as its audience meets it (never raw markup alone):

1. **Rendered View:** Inspect the compiled document, rendered markdown layout, generated PDF, plot, or UI screenshot at a representative viewport.
2. **Legibility & Hierarchy:** Verify typographic and visual hierarchy matches semantic importance across contrast, whitespace, and density.
3. **Audience Empathy:** Check whether a time-pressed reader can scan key claims at a glance and a technical reader finds direct, unambiguous structure.
4. **Excellence vs. Mere Compliance:** Judge whether the artifact is genuinely excellent for its audience and purpose in all the circumstances while respecting reasonable authorial discretion.

## 3. Review Findings & Self-Fixes

- **Fix-in-place vs. exact suggested fixes:** Where defects are clearly fixable without ambiguity -- if permissions and instructions permit (such as serialized review on a writable branch) -- apply and commit them in place (`fix(review): ...`), itemizing applied fixes rather than returning `REVISE`. Where write permissions are absent or instructions bar direct edits (such as parallel read-only passes), suggest the exact fix.
- **Material Defects vs. Taste Preferences:** Separate material structural, tonal, or visual defects for the audience and purpose from mere reviewer phrasing or stylistic preferences within reasonable authorial discretion (which never warrant `REVISE` or `FAIL`).

## 4. Verdict Schema

Handbacks to other agents quote deciding qualitative observations inline and report once when inspection completes (halt verbatim on any guard or harness refusal); structured Markdown headings (`### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Required Changes`) apply strictly to published PR/issue comments or user-facing documents.

- `PASS`: Achieves genuine excellence for its audience and purpose in all the circumstances (clarity, elegance, cognitive ease), respecting reasonable authorial discretion.
- `REVISE`: Material structural, tonal, or presentation defects for its audience and purpose (never mere phrasing or stylistic preference).
- `FAIL`: Fails its intended purpose, applies a standard inappropriate in the circumstances, or suffers severe visual or cognitive clutter.
