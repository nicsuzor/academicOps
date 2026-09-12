---
name: learn
description: Diagnose systemic root causes of errors and file anonymised issues in the appropriate repository. Diagnoses only; never proposes or implements fixes directly.
---

# Learn

Perform root-cause analysis on systemic failure classes. Diagnose observable mechanisms and file an issue at the responsible layer; do not propose or implement fixes directly.

## Protocol

1. **Diagnose systemic cause**: Focus on the class of error rather than proximate mistakes.
   - Ground findings in observable external mechanisms (checks, gates, context placement). Never speculate on agent psychology, attention, or internal states.
   - Inspect the mechanisms in `specs/enforcement/` to identify applicable enforcement controls and verify whether they are active, disconnected, or missing.
2. **Determine scope**:
   - _Project_: Project-specific guidelines or configurations.
   - _User/PKB_: User preferences, habits, or personalized knowledge.
   - _Framework_: Universal axioms, agent roles, or core tooling.
3. **File an issue**: Search for existing issues on this error class before creating a new one. File an anonymized issue in the repository of the owning layer. Strip personal names, credentials, and raw transcripts.
4. **No direct fixes**: Never propose a fix, choose an enforcement mechanism, or open tasks to implement remedies. Findings serve as evidence for the framework enforcement loop (`specs/enforcement/enforcement.md`).

## Output

Return a markdown report containing:

- **Evidence**: Concrete citations and trace snippets.
- **Root cause**: The systemic defect in the mechanism or context design.
- **Impact estimate**: Projected frequency and severity.
- **Artifact**: Link to the filed GitHub issue or PKB reference.
