---
trigger: always_on
description: Deprecated files are deleted; instructions, code, and PKB records state current state only with no history; specs may contain one brief rejected-choice bullet.
---

## Current state only

Maintain current state only across the repository and personal knowledge base. Do not preserve backwards compatibility or maintain history in instructions, code, or knowledge nodes.

- **No backwards compatibility:** Deprecated files are deleted, not kept around.
- **No history in instructions or code:** Git holds history; instruction, skill, agent, configuration, and code files state current state only.
- **PKB is current state only (`synthesize-not-accrete`):** The PKB holds what is true now, never how it came to be true. Notes, tasks, and memory nodes state current synthesized truths only. Retaining historical provenance lists (`sources:` frontmatter arrays), session references, chronological changelogs, dated layers, or citations to non-existent or prior-state material is strictly prohibited. When encountered, strip historical source lists immediately.
- **Spec exception:** A specification may carry one very brief bullet naming a rejected choice and the reason it was rejected.
