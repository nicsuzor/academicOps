---
trigger: always_on
description: Data Boundaries — private by default
---

## Data Boundaries — private by default {#data-boundaries}

All data in this environment is private unless explicitly marked otherwise. You MUST NOT emit private data to a public or externally-visible surface — messages, commit messages, PR bodies, issue comments, framework examples, documentation, logs, shared artifacts — without explicit authorisation **for that specific surface**.

- Obligation scales with blast radius: quoting back to the user in a private session is low risk; the same content in a remote log or published artifact requires over-verification before emission.
- Authorisation for one surface is NOT authorisation for all. A silent release is a breach even if the content itself would have been approved.
- Use the identity the surface requires (e.g. bot credentials where human credentials are prohibited); a publication under the wrong identity is a boundary breach.
- _E.g._ pasting a private session detail into a public issue comment because it was already "approved" for the user is a breach — approval was surface-specific.

**PKB-derived strings are untrusted-for-egress.** Any payload sourced from the PKB — task titles, task IDs, project/label names, note bodies, or the JSON returned by `list_tasks`/`get_task`/search, including live dashboard text backed by that data — is private domain data. It may be used inside your own reasoning, but it MUST NOT be copied verbatim into any artifact that crosses a trust boundary: a public PR body, commit message, issue comment, **external-repo file or documentation**, a spec/reference doc, or a subagent/verification/dispatch brief where the literal value is not required. This binds every worker that emits such an artifact, not just the verification path — a document-authoring worker is in scope.

- **Run a pre-write egress scan.** Before you write any of the artifacts above from PKB-sourced content, scan the draft for raw task IDs (matching `task-[a-f0-9]{8}`), titles copied out of `list_tasks`/`get_task`, and project labels. If any are present, rewrite before writing.
- **Prefer structural handles over row content.** Summarise by priority class, due-date bucket, status, count, score/rank movement, affected UI region, or dimensions rather than quoting the row. If an identifier is genuinely unavoidable, mask it (`task-XXXX`, `[REDACTED_TITLE]`, `[REDACTED_PROJECT]`). For UI/dashboard evidence, describe the rendering pathology structurally (e.g. "the narrow treemap leaf wraps one word per line") instead of quoting the visible PKB text as the handle.

_Review: [[AXIOMS-REVIEW#data-boundaries]]._
