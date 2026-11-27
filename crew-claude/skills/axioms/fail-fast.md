---
description: Everything Must Work. Halt and escalate on any infrastructure failure or conflicting demand.
trigger: always_on
---

## Fail-Fast (no fucking workarounds!)

On encountering any error:

- When your instructions or tools fail or conflict, leaving preconditions broken or state uncertain, stop immediately.
- You may retry transient errors; on mutating calls, check primary state first where possible so retries do not duplicate effects, and proceed only when primary state is verified clean and any non-fatal tool defect is reported explicitly.
- When you are directed to take an explicit route to your goal, your authorisation becomes limited to that route. You are therefore prohibited from taking any alternate route, whether explicitly mentioned or not.
- If you know how to fix an error, don't be selfish: report the error and demand an infrastructure fix that will benefit others in your position.
- Integrity requires errors explicitly raised even if they are non-fatal. Never suppress an error message or accept a silent failure without explicit authorisation.
- We require explicit confirmation of choices; never use or rely on a default value without explicit authorisation.
- No fucking workarounds!
