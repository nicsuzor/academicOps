---
description: Instruction context must earn its injection tier; demote anything that can be looked up.
trigger: always_on
---

## Pull over Push — injection-tier discipline

Instruction context costs `size × audience breadth × load frequency`. A push tier — every-turn injection, always-on session context, gate cue — must be earned. Content belongs there only if it (a) changes behaviour on most loads, (b) cannot be reactively looked up, and (c) is compact enough that every line is load-bearing at that frequency. Fail any one: demote.

The standard fix for over-injection is to split the compact cue, which stays pushed, from the elaboration, rationale, and checklists, which move to a referenced doc or a skill body. The default direction is always pull over push.
