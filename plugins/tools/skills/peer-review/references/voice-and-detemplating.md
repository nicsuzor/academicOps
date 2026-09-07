---
title: Voice & De-templating
permalink: voice-and-detemplating
tags: [reference, peer-review, voice, detemplating]
---

# Voice & De-templating

Convert verified notes into signable prose matching the reviewer's voice, and remove repetitive phrasing across multi-review rounds.

## Two Registers

- **Prep register**: Granular line references, direct quotes, numerical checks, and raw impressions. Retained in reading notes and git history.
- **Final register**: Assertable prose the academic can stand behind from a single read without verifying isolated figures.

Render positions faithfully and boldly. Raise phrasing or severity concerns in conversation rather than silently softening the critique.

## Voice Onboarding Loop

Establish voice calibration across iterative reviews:

1. Draft final-register prose.
2. Academic edits the draft.
3. Compute diff between draft and final text.
4. Codify recurring adjustments into `${ACA_DATA}/STYLE.md` or `{academic}-style.md`.

## De-Templating Procedure (Whole-Round Pass)

Phrases used once reflect voice; phrases repeated across six reviews become artificial fingerprints. Execute across the entire round's draft set:

1. **Census**: Identify recurring pivot formulas ("I have reservations about...", "asserted rather than demonstrated"), AI tropes ("delve", "crucial", "landscape", "robust"), and repeated section openers.
2. **Budget**: Permit signature phrases at most once across the full round review set.
3. **Two-tier rewrite**:
   - **Re-mechanise critiques**: Replace generic scaffold language with the specific proposal mechanism or data point.
   - **Synonym deduplication**: Vary phrasing primarily in low-stakes connective or praise text.
4. **Preserve anchors**: Keep line citations, pin-cites, direct quotes, and evaluative calibration unchanged.
5. **Distinct weighting sentence**: Provide one sentence per review identifying its primary concern (promoted from the reading notes' largest identified vulnerability), varied across reviews.
6. **Parity check**: Verify that pin-cite and quotation counts match pre-pass totals before declaring completion.
