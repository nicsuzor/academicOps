# Transcript Metadata Schema (`/end-session` quality-bar fields)

> `/dump` (emergency bail) does not produce these fields — it skips the reflection blocks intentionally. Only `/end-session` is bound by this schema.

This document defines the structured metadata fields that
`aops-core/scripts/transcript.py` (via `aops-core/lib/transcript_parser.py`)
extracts from a session's `## Framework Reflection`, `## Output`, and
`## Tasks worked` blocks. It is the wire format consumed by the trend-review,
retro, and sleep-consolidation pipelines.

> Source of truth: `parse_framework_reflection`, `parse_output_section`,
> `parse_tasks_worked_section`, `parse_identifier_precis_pairs`, and
> `assess_reflection_quality` in `aops-core/lib/transcript_parser.py`.

## Framework Reflection label grammar (the parse contract)

The `## Framework Reflection` block is bucketed **deterministically by regex**,
not by an LLM. `SKILL.md`'s template and this grammar must stay in lock-step —
when they drift, the agent writes labels the parser does not recognise, the
structured parse matches nothing, and the whole body falls through to the
unstructured fallback (`_parse_unstructured_reflection`), which dumps every
bullet into `accomplishments` and leaves `friction_points` empty. (This was the
silent-corruption bug fixed in `aops-6a787364`.)

Emit each field on its own line with its **exact bold label** followed by a
colon. The buckets the parser reads (`field_patterns` in
`parse_framework_reflection`):

| Bold label (verbatim)    | Parsed field        | Type          | Notes                                                   |
| ------------------------ | ------------------- | ------------- | ------------------------------------------------------- |
| `**Outcome**:`           | `outcome`           | string        | `success` \| `partial` \| `failure`.                    |
| `**Accomplishments**:`   | `accomplishments`   | array[string] | Comma list, `-` bullets, or single value.               |
| `**Friction points**:`   | `friction_points`   | array[string] | URLs filed via `/learn`; no prose. `none` → empty list. |
| `**Proposed changes**:`  | `proposed_changes`  | array[string] | `none` → empty list.                                    |
| `**Next step(s)**:`      | `next_step`         | string        | Optional.                                               |
| `**Prompts**:`           | `prompts`           | string        | Optional.                                               |
| `**Guidance received**:` | `guidance_received` | string        | Optional.                                               |
| `**Followed**:`          | `followed`          | string        | Optional.                                               |
| `**Root cause**:`        | `root_cause`        | string        | Optional; an inline `(…)` qualifier is tolerated.       |

Tolerances the parser allows (do **not** rely on these instead of the canonical
label — they exist to catch in-the-wild drift, and off-template reflections are
flagged via `quality_warnings`):

- **Friction** is matched on any `**Friction…**` span — `**Friction.**`,
  `**Friction (real bug):**`, `**Friction**:` all bucket to `friction_points`.
- A reflection that uses **no** bold labels (plain `-` bullets or prose) is
  parsed by the unstructured fallback: bullets whose leading label is
  `Friction…`/`Proposed…` route to `friction_points`/`proposed_changes`; all
  other bullets become `accomplishments`. Such a reflection is marked
  `inferred: true` and earns an `inferred-reflection` quality warning (see
  [Quality warnings](#quality-warnings)).

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
| `thread_pickup`        | `dict[str, str]`   | Per-thread pickup instructions extracted from `### Thread Pickup` block (if present). |

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

| Code                          | Triggered by                                                                                                                  |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `missing-output-section`      | No `## Output` block (and no `Output: none — …` line) found.                                                                  |
| `empty-output-section`        | `## Output` block had no URLs and did not declare an explicit none.                                                           |
| `missing-tasks-worked`        | No `## Tasks worked` block found.                                                                                             |
| `empty-tasks-worked`          | `## Tasks worked` block was empty.                                                                                            |
| `bare-identifier`             | Reflection mentioned `task-…` / `PR #…` / `commit …` without a `(precis)`.                                                    |
| `feature-suggestion`          | Reflection appears to propose a new tool/feature/skill rather than report friction.                                           |
| `inferred-reflection`         | Reflection had no structured `**Field**:` labels; categorisation was inferred from bullets/keywords (off the parse contract). |
| `friction-in-accomplishments` | An `accomplishments` item mentions "friction" while `friction_points` is empty — likely miscategorised friction.              |

`feature-suggestion` is a heuristic — it matches phrases like `new tool`,
`we should build`, `propose a new`, etc. False positives are acceptable;
agents can rewrite the reflection. The point is to refuse "agents
reflecting by wishlisting".

## Required blocks (per `SKILL.md`)

A Full-form `/end-session` MUST emit, in any order before the handover block:

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
