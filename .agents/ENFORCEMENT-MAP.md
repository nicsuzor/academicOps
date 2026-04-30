# Enforcement Map

Maps each mechanical enforcement mechanism to the rule(s) it enforces, its
execution context, and its failure tier. Updated whenever a new check is added
or retired (P#65).

## Pre-commit hooks

| Hook ID                     | Script                                 | Rule(s)                    | Tier    | Behaviour                                                                  |
| --------------------------- | -------------------------------------- | -------------------------- | ------- | -------------------------------------------------------------------------- |
| `check-no-new-orphan-md`    | `scripts/check_no_new_orphan_md.py`    | R5.6                       | `warn`  | Exits 1 on new `.md` files outside canonical-location allowlist            |
| `check-framework-integrity` | `scripts/check_framework_integrity.py` | (wikilink index integrity) | `warn`  | Exits 1 on broken wikilinks or missing SKILLS/WORKFLOWS index entries      |
| `lint-axiom-refs`           | `aops-core/lib/lint_axiom_refs.py`     | R1.1, R1.3                 | `block` | Exits 1 when `plugin.json` cites a non-existent or mis-parented Axiom/Rule |

## CI-only checks (whole-repo, too slow for pre-commit)

| Check                    | Script                              | Rule(s)                | Tier    | Behaviour                                                                     |
| ------------------------ | ----------------------------------- | ---------------------- | ------- | ----------------------------------------------------------------------------- |
| `check-orphan-files`     | `scripts/check_orphan_files.py`     | (wikilink orphans)     | `warn`  | Exits 0; reports files with no incoming wikilinks                             |
| `check-skill-line-count` | `scripts/check_skill_line_count.py` | (SKILL.md ≤ 500 lines) | `block` | Exits 1 when any SKILL.md exceeds 500 lines; fails the pre-commit hook and CI |

## Notes

- `data-markdown-only` — referenced in HEURISTICS.md P#105 as a pre-commit hook
  example; superseded by `check-no-new-orphan-md` (R5.6, added in PR #793).
- Hooks with tier `warn` exit non-zero to block the commit but agents may
  surface the add to the user and proceed under R8.1 in-session authorisation
  (`--no-verify`).
- Hooks with tier `block` represent hard constraints; `--no-verify` is itself
  prohibited by R8.1 for this tier.
