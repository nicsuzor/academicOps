# Criteria

## Overview

This policy detects over-injection of instruction context in high-frequency push tiers. Every line in a push tier (always-on context, every-turn injection) must be load-bearing, compact, and incapable of reactive lookup. Detailed rationale, checklists, and reference guides must be demoted to pull tiers (skills, referenced docs, PKB notes).

## Definition of Terms

- **Agent response**: Proposed prompt designs, system instructions, or hook injection configurations.
- **Over-Injected Push Context**: Adding lengthy checklists, verbose rationale, or detailed reference manuals into push-tier prompts (always-on context, every-turn system messages) instead of referencing external docs.
- **Demotion to Pull Tier**: Moving detailed documentation or reference material into on-demand pull files (`SKILL.md`, reference docs) while keeping push cues compact.

## Interpretation of Language

- Inspect proposed prompt modifications, instruction updates, and hook injection text in **Agent response**.
- Verify whether verbose reference material is being pushed unnecessarily on every turn.
- Compact floor cues in push tiers pointing to detailed pull documentation do not match.

## Definition of Labels

### (PP): Over-Injected Push Context

#### Includes

- **Verbose Reference in Push Tier Class**: An **Agent response** adding multi-page reference manuals or extensive checklists directly into always-on prompt files or every-turn hook injections.
- **Unearned Push Tier Content Class**: An **Agent response** placing static documentation that could be reactively looked up into high-frequency context buffers.
- **Monolithic Instruction File Class**: An **Agent response** expanding core prompt files with redundant explanatory prose instead of modularizing into pull files.

#### Excludes

- **Compact Floor Cue Class**: An **Agent response** maintaining short, high-impact cues in push tiers that link to full pull documentation.
- **Demoted Pull Documentation Class**: An **Agent response** placing detailed procedures and reference guides into skill files or `references/` directories.
- **Load-Bearing Always-On Invariant Class**: An **Agent response** keeping only essential, compact, inviolable rules in the always-on context.
