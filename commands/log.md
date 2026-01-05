---
name: log
description: Log agent performance patterns to GitHub Issues (per AXIOMS #28)
allowed-tools: Skill
permalink: commands/log
---

**IMMEDIATELY** invoke the `[[skills/learning-log/SKILL.md|learning-log]]` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging observations to GitHub Issues, where patterns can accumulate and synthesize to HEURISTICS.md.

See [[specs/reflexivity]] for the complete data architecture and synthesis workflow.

## Usage

**User provides**: Brief description of observation

**Example**: `/log Agent bypassed python-dev skill for Python edits`

The skill will search for existing Issues, create/update as appropriate.
