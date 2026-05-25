---
title: Framework Constraints
type: instructions
created: 2026-02-23
modified: 2026-05-20
---

# Framework Constraints

Hard rules for aops framework internals. Enforced by pre-commit hooks where possible, by agents otherwise.

| Check                    | Script                              | Rule(s)                | Tier       | Behaviour                                                    |
| ------------------------ | ----------------------------------- | ---------------------- | ---------- | ------------------------------------------------------------ |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `advisory` | Exits 0; reports files with no incoming wikilinks            |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `advisory` | Exits 1 when any SKILL.md exceeds 500 lines; lists offenders |

## Agent permission envelopes

> **Redirect.** This file no longer carries an authoritative envelope table. The previous table here drifted from the per-agent declarations it was meant to summarise, which is how three places to look becomes one wrong answer per writer.
>
> Agent permissions live in three documents — one per category in the doc-taxonomy spec (brain PKB):
>
> - **Spec** (the schema and axes): [[agent-authority]] + [[agent-permissions]] (brain PKB). Together one logical spec.
> - **State** (per-agent declarations): agents/<name>.md frontmatter. The operative SSoT for what each agent holds.
> - **Audit-artifact** (current-state snapshot): the agent-tools matrix (repo-level). Generated dump for at-a-glance comparison against per-agent frontmatter; drift is reported here, not declared here.
>
> To answer "what tools does agent X hold", read agents/<X>.md. To answer "what is the envelope schema", read the spec pair (brain PKB). To answer "is the corpus currently in drift", read the agent-tools matrix (repo-level).

## GitHub actions

**`.github/agents/*.agent.md`** (`merge-prep`, `pr-reviewer`, `qa`) are GitHub Actions runners. Their authority is governed by the workflow YAML's `permissions:` block and the runner's bot PAT scopes:

TODO: finish this table.
