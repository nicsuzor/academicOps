---
name: verify
description: "Universal qualitative verification procedure evaluating qualitative taste, genre standards, audience empathy, and purpose satisfaction across live rendered multimodal outputs (never linters or functional QA)."
---

# Verify

Universal qualitative verification procedure evaluating qualitative taste, genre fit, and audience resonance across live rendered multimodal outputs (never linters, schema checks, or functional QA).

## 1. Upfront Genre & Audience Alignment

Before inspecting details:

1. **Identify Artifact Genre:** Determine the governing standard for the artifact's genre (e.g., `craft` for agent instructions, specification standards for specs, visual design standards for UI/plots, publication standards for manuscripts).
2. **Identify Audience & Purpose:** Define who reads or uses this artifact, their cognitive state, and the outcome it must achieve.
3. **Set Proportionality Bar:**
   - _Routine / Low-Risk:_ Fast single-pass sanity check; low bar.
   - _High-Stakes / Public:_ Comprehensive aesthetic and cognitive audit.

## 2. Live Rendered Multimodal Inspection

Review the artifact in its rendered form as experienced by the user:

1. **Rendered View:** Inspect the compiled document, rendered markdown layout, generated PDF, or UI screenshot (1920x1080).
2. **Legibility & Hierarchy:** Verify typographic scale matches semantic importance; check contrast, whitespace, and line lengths.
3. **Audience Empathy:** Does the artifact respect the reader's attention? For a time-pressed reader, is it scannable at a glance? For a technical reader, is it direct and unambiguous?
4. **Floor vs. Ceiling:** Answer explicitly: _Is this genuinely excellent for its purpose, or merely passable?_

## 3. Review Findings & Self-Fixes

- **Serialized vs. Parallel Fixes:** Apply and commit uncontroversial typographic, formatting, or visual layout corrections (`fix(review): ...`) only when serialized and authorized on a writable branch, recording them as Argdown observations in internal handbacks (and under `### Reviewer Self-Fixes Applied` in published PR/issue or user-facing outputs). When running as a parallel or read-only review, report suggested repairs as Argdown findings internally (and under `### Suggested Fixes` in published/user-facing outputs) for the fix pass to avoid concurrent write conflicts.
- **Substantive Findings:** Document qualitative shortcomings with concrete guidance on tone, taste, layout, structure, or audience alignment.

## 4. Verdict Schema

Internal agent-to-agent verification handbacks report **only** in clean Argdown prose per `ida:premise-check` (quoting deciding qualitative observations inline); structured Markdown headings (`### Reviewer Self-Fixes Applied`, `### Suggested Fixes`, `### Required Changes`) apply strictly to published PR/issue comments or user-facing documents.

- `PASS`: The artifact achieves excellence for its intended audience and purpose.
- `REVISE`: The artifact is functional but needs concrete structural, tonal, or layout polish.
- `FAIL`: The artifact fails its purpose, exhibits severe cognitive clutter or visual unreadability, or lacks a governing standard or purpose.
