---
description: Log agent performance (successes and failures) to framework learning system
permalink: commands/log
---

**IMMEDIATELY** invoke the `learning-log` skill with the user's observation description.

**Purpose**: Build institutional knowledge by logging patterns to thematic learning files AND adjusting heuristics based on evidence.

## Modes

### Standard Mode (default)
Log observation to thematic learning file.

**User provides**: Brief description of observation (success or failure)

### Heuristic Adjustment Mode
Adjust heuristic confidence based on new evidence.

**User provides**: `adjust-heuristic H[n]: [observation]`

**Example**: `/log adjust-heuristic H3: Agent claimed success without running tests - confirms H3`

## Workflow

The skill will:

1. **Detect mode** - standard logging or heuristic adjustment
2. **Categorize** - assign pattern tags (#verify-first, #instruction-following, #git-safety, etc.)
3. **Link knowledge** (via bmem) - cross-reference related framework concepts
4. **Route** - select target thematic file OR heuristic entry based on pattern tags
5. **Format** - structure entry per learning file specification
6. **Validate** - ensure target file exists with valid format
7. **Append/Update** - add entry to thematic file OR update heuristic evidence in `$AOPS/HEURISTICS.md`

## Thematic Files

- `verification-discipline.md` - verify-first violations, overconfidence
- `instruction-following.md` - ignoring explicit instructions
- `git-and-validation.md` - --no-verify usage, validation bypass
- `skill-and-tool-usage.md` - skill invocation failures
- `test-and-tdd.md` - TDD violations, test discipline
- `technical-wins.md` - successful patterns to reinforce

## Heuristic Adjustment

When adjusting heuristics:
- **Strengthen**: Add dated observation to Evidence, consider raising Confidence
- **Weaken**: Add dated counter-observation, consider lowering Confidence
- **Propose new**: If pattern doesn't match existing heuristic, propose new one with Low confidence

See `$AOPS/HEURISTICS.md` for current heuristics and revision protocol.

See skills/learning-log/SKILL.md for complete workflow specification.
