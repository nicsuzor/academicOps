---
description: All data is private; emit nothing to an external surface without authorisation for that specific surface.
trigger: off
---

## Data Boundaries — private by default

All data in this environment is private unless explicitly marked otherwise. Never emit private data to a public or externally-visible surface — messages, commit messages, PR bodies, issue comments, documentation, framework examples, logs, shared artifacts — without authorisation **for that specific surface**.

- Authorisation for one surface is not authorisation for another. A silent release is a breach even where the content itself would have been approved.
- Obligation scales with blast radius. Quoting back to the user in a private session is low risk; the same content in a remote log or a published artifact demands over-verification first.
- Use the identity the surface requires. Publishing under the wrong identity is itself a boundary breach.

**PKB content is private domain data.** Task titles, task IDs, project and label names, note bodies, and the JSON returned by task or search calls may inform your reasoning, but must not be copied verbatim into any artifact that crosses a trust boundary — a PR body, commit message, issue comment, external-repo file, spec or reference doc, or a delegation, dispatch, or verification brief where the literal value is not required.

- Scan the draft before you write it: raw task IDs matching `task-[a-f0-9]{8}`, titles copied out of task or search output, project labels. Rewrite before writing.
- Prefer structural handles — priority class, status, count, due-date bucket, rank movement, affected UI region — over row content. Where an identifier is genuinely unavoidable, mask it: `task-XXXX`, `[REDACTED_TITLE]`.
