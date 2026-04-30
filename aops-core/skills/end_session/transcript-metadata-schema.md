# Transcript Metadata Schema (`/dump` quality-bar fields)

This document defines the structured metadata fields that
`aops-core/scripts/transcript.py` (via `aops-core/lib/transcript_parser.py`)
extracts from a session's `## Framework Reflection`, `## Output`, and
`## Tasks worked` blocks. It is the wire format consumed by the trend-review,
retro, and sleep-consolidation pipelines.

> Source of truth: `parse_framework_reflection`, `parse_output_section`,
> `parse_tasks_worked_section`, `parse_identifier_precis_pairs`, and
> `assess_reflection_quality` in `aops-core/lib/transcript_parser.py`.

## File location

Per-session insights JSON lives under
`$AOPS_SESSIONS/insights/<date>/<session-slug>.json` (resolved by
`lib.insights_generator.get_insights_file_path`). Schema validation is
performed by `validate_insights_schema`; the new fields below are
additive — missing fields do not fail validation, they emit warnings.

## Top-level fields (added by task-5a54f813)

| Field                  | Type               | Description                                                                           |
| ---------------------- | ------------------ | ------------------------------------------------------------------------------------- |
| `outputs`              | `list[Output]`     | Artefact links extracted from the `## Output` block.                                  |
| `output_explicit_none` | `bool`             | True iff the agent declared `Output: none — <reason>` (i.e. no artefact, on purpose). |
| `output_none_reason`   | `str \| null`      | The free-text reason supplied with `none — …`.                                        |
| `tasks_worked`         | `list[TaskWorked]` | Source-of-truth list of session task activity.                                        |
| `references`           | `list[Reference]`  | Identifier+precis pairs found anywhere in the reflection body.                        |
| `quality_warnings`     | `list[str]`        | Non-fatal quality issues — missing blocks, bare ids, feature-suggestion smell.        |

A session is _never_ silently dropped because of missing fields. If a block
is missing, the warning is added to `quality_warnings` and surfaced on
stderr by `transcript.py`'s reflection saver — the session is still flagged
and indexed.

### `Output`

```json
{
  "kind": "pr | issue | commit | github | doc",
  "url": "https://…"
}
```

Classification rules (`_classify_output_url`):

- contains `/pull/` → `pr`
- contains `/issues/` → `issue`
- contains `/commit/` → `commit`
- contains `github.com` (other) → `github`
- everything else → `doc`

### `TaskWorked`

```json
{
  "id": "task-5a54f813",
  "precis": "/dump + transcript.py: require useful framework reflection",
  "action": "updated | created | completed | cancelled | referenced | null",
  "action_raw": "updated, added quality bar"
}
```

`action` is normalised by keyword-match (`_normalize_action`); `action_raw`
preserves the agent's verbatim phrasing for downstream review.

### `Reference`

```json
{
  "type": "task | pr | issue | pr_or_issue | commit",
  "id": "PR #847",
  "precis": "transcript.py: extract reflection metadata"
}
```

`precis` is `null` when the agent wrote a bare identifier — that case also
appears in `quality_warnings` as `bare-identifier: …`.

## Quality warnings

Warnings are strings of the form `<code>: <message>`. The set:

| Code                     | Triggered by                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------- |
| `missing-output-section` | No `## Output` block (and no `Output: none — …` line) found.                        |
| `empty-output-section`   | `## Output` block had no URLs and did not declare an explicit none.                 |
| `missing-tasks-worked`   | No `## Tasks worked` block found.                                                   |
| `empty-tasks-worked`     | `## Tasks worked` block was empty.                                                  |
| `bare-identifier`        | Reflection mentioned `task-…` / `PR #…` / `commit …` without a `(precis)`.          |
| `feature-suggestion`     | Reflection appears to propose a new tool/feature/skill rather than report friction. |

`feature-suggestion` is a heuristic — it matches phrases like `new tool`,
`we should build`, `propose a new`, etc. False positives are acceptable;
agents can rewrite the reflection. The point is to refuse "agents
reflecting by wishlisting".

## Required blocks (per `SKILL.md`)

A Full-form `/dump` MUST emit, in any order before the handover block:

1. `## Framework Reflection` — friction + improvement (+ optional kept).
2. `## Output` — explicit URL(s) or `Output: none — <reason>`.
3. `## Tasks worked` — every task created / updated / completed / cancelled.

Identifiers in the reflection MUST carry a parenthetical precis (<60 chars).
Bare ids are flagged but not refused.

## Compatibility

- All new fields are additive. Pipelines that did not know about them
  continue to work; they simply ignore the extra keys.
- Sessions that lack the new blocks still produce insights (with warnings).
- Tests: `tests/lib/test_transcript_parser_reflection.py` (extended) and
  `tests/lib/test_dump_quality_bar.py` (added by task-5a54f813).
