---
trigger: always_on
description: Deprecated files are deleted; instructions and code state current state only with no history; specs may contain one brief rejected-choice bullet.
---

## Current state only

Maintain current state only across the repository. Do not preserve backwards compatibility or maintain history in instructions or code.

- **No backwards compatibility:** Deprecated files are deleted, not kept around.
- **No history in instructions or code:** Git holds history; instruction, skill, agent, configuration, and code files state current state only.
- **Spec exception:** A specification may carry one very brief bullet naming a rejected choice and the reason it was rejected.
