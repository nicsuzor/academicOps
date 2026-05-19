# aops-core vs aops-tools — split rationale and migration plan

**Status**: draft (cowork-sandbox), proposed 2026-05-19. Spec to land at `~/src/academicOps/projects/aops/specs/daily/50-aops-core-vs-tools.md`.

**Inherits**: [00-architecture.md](00-architecture.md) — the steady-state design this spec migrates to.

## The split, in one sentence

**aops-core** is **non-fungible epistemic infrastructure**: components Nic could not swap out without losing the framework's identity. **aops-tools** is **optional domain skills**: useful adapters that can be replaced when better external solutions arrive.

This is the [aops-tools convention](https://github.com/nicsuzor/academicOps/blob/main/aops-tools/GEMINI.md) applied consistently.

## The test

To decide whether a skill belongs in core or tools, ask:

1. **Does it own a primary abstraction** (the PKB, the daily note, task hierarchy, memory, the dogfood loop)? → **core**.
2. **Does it depend on a swappable external service** (Outlook, a specific PDF engine, a specific cloud provider)? → **tools**.
3. **Could a different framework user reasonably want to replace it** (alternate mail client, alternate notes system)? → **tools**.
4. **Does its absence break other framework skills**? → **core**.

Where multiple answers apply, the test resolves to whichever side has the strongest single signal. Example: `/daily` depends on the calendar (swappable) — but it owns the daily-note structure (a primary abstraction). It's core.

## Current allocations — audit

| Skill / command          | Current home   | Should be      | Why                                                                                                |
| ------------------------ | -------------- | -------------- | -------------------------------------------------------------------------------------------------- |
| `/daily`                 | aops-core      | aops-core ✓    | Owns daily-note structure (SSoT).                                                                  |
| `/remember`              | aops-core      | aops-core ✓    | Memory primitive — non-fungible.                                                                   |
| `/pull`, `/q`            | aops-core      | aops-core ✓    | PKB task interaction primitives.                                                                   |
| `/end-session`, `/dump`  | aops-core      | aops-core ✓    | Session lifecycle primitives.                                                                      |
| `/email`                 | aops-core      | **aops-tools** | Outlook-MCP-dependent. Domain workflow on a swappable surface.                                     |
| `/news-briefing` (new)   | (drafted core) | **aops-tools** | Outlook-MCP-dependent. Editorial curation is a content workflow.                                   |
| `daily-pdf` (new)        | (n/a)          | aops-tools     | Built on `aops-tools/pdf`. Output-format adapter.                                                  |
| `aops-tools:pdf`         | aops-tools     | aops-tools ✓   | Output adapter — already correct.                                                                  |
| `aops-tools:extract`     | aops-tools     | aops-tools ✓   | Input adapter.                                                                                     |
| `aops-tools:diagram`     | aops-tools     | aops-tools ✓   | Output adapter.                                                                                    |
| `aops-tools:deep-research` | aops-tools   | aops-tools ✓   | External-tool wrapper.                                                                             |

Three migrations needed: `/email` (core → tools), `/news-briefing` (land in tools, not core), `daily-pdf` (new in tools).

## Why `/email` is tools, not core

It's tempting to treat `/email` as core because email-to-task capture *feels* foundational. The test reveals it isn't:

- **Primary abstraction owned**: none. PKB task creation belongs to PKB primitives; email I/O belongs to the Outlook MCP. `/email` is just orchestration between two existing primitives.
- **External dependency**: yes — Outlook MCP, which is itself a fungible adapter (Nic could move to Gmail; the framework should not need a core rewrite).
- **Replaceable**: yes — alternative email integrations would each carry their own `/email`-equivalent. The framework user (another academic) might have Fastmail, Gmail, or a self-hosted IMAP — they'd want a different implementation with the same contract.
- **Breaks other skills if absent**: only `/daily`'s `## What needs attention` section. That section degrades gracefully (mobile-captures only) if `/email` isn't installed.

So: `/email` is a useful tool, not infrastructure. It moves.

## Why `/news-briefing` is tools

Same test:

- Owns no primary abstraction (the `NewsBriefing` type defined in 00-architecture.md is a thin data carrier).
- External dependency: Outlook MCP (same as `/email`).
- Replaceable: yes — different newsletter sources (RSS, Feedly, web scraping) would each warrant their own implementation with the same `NewsBriefing` contract.
- Breaks other skills if absent: only the `## News briefing` section of `/daily`, which already degrades to "_No newsletter activity in the last 24h._" per 10-daily-orchestrator.md.

## Migration plan

### Migration 1: `/email` core → tools

1. **PR**: `move-email-to-tools`
2. Move `aops-core/commands/email.md` → `aops-tools/skills/email/SKILL.md`. Convert from command-style to skill-style markdown (frontmatter, sections per `plugin-dev:skill-development` convention).
3. Inline or co-locate the `hydrator/workflows/email-capture` workflow under `aops-tools/skills/email/workflows/`.
4. Update `/daily`'s call site to reference the new path.
5. Register `/email` slash command in aops-tools (open question — confirm aops-tools command registration during PR).
6. Update `aops-tools/SKILLS.md` index.
7. Smoke test: invoke `/email --daily` and confirm `EmailCapture` schema matches.

### Migration 2: Land `/news-briefing` in tools (NOT core)

1. **Amend PKB task `aops-653897f7`** — currently says "promote to aops-core/skills/"; update to "land in aops-tools/skills/news-briefing/".
2. **PR**: `add-news-briefing-skill`
3. Copy `/Users/suzor/junior/.dogfood-run/proposed/skills/news-briefing/SKILL.md` to `aops-tools/skills/news-briefing/SKILL.md`.
4. Register `/news-briefing` slash command.
5. Update `aops-tools/SKILLS.md` index with description per `plugin-dev:skill-development` triggering-effectiveness conventions.
6. Smoke test: invoke `/news-briefing --daily` and confirm `NewsBriefing.markdown` returned.

### Migration 3: Add `daily-pdf` to tools

1. **PR**: `add-daily-pdf-skill`
2. Create `aops-tools/skills/daily-pdf/SKILL.md` per spec [40-pdf-render.md](40-pdf-render.md).
3. Register `/daily-pdf` slash command.
4. Update `/daily` SKILL.md to add `--pdf` flag (calls `/daily-pdf --bundle`).
5. Smoke test: invoke `/daily --pdf` end-to-end.

### Migration 4: Land the spec series

1. **PR**: `add-daily-pipeline-specs`
2. Copy this directory (`.dogfood-run/proposed/specs/daily/`) to `~/src/academicOps/projects/aops/specs/daily/`.
3. Add a `README.md` linking to all five specs.
4. Cross-link from `aops-core/skills/daily/SKILL.md` and the relevant tools-skill SKILL.md files: "See [projects/aops/specs/daily/](...)".

### Order

Specs land first (Migration 4), then the implementation migrations can each cite the spec in PR description. Email → news-briefing → daily-pdf order minimises co-changes to `/daily` (each PR touches it once, sequentially).

## Risks

- **Plugin command registration in aops-tools**: spec assumes aops-tools registers slash commands; not yet verified. If not, two options: (a) add `commands/` registration to aops-tools; (b) keep slash-command stubs in aops-core that delegate to aops-tools skills. Option (a) is cleaner; option (b) preserves core as the entry-point surface.
- **Backwards compatibility**: anyone already invoking `/email` from a session expects it to work. If aops-tools isn't installed, `/email` shouldn't error out cryptically — it should say "install aops-tools plugin". Add a guard in `/daily` when calling `/email`.
- **Documentation drift**: `aops-core/README` likely mentions `/email`. Audit and update during Migration 1.

## What this spec is NOT

- Not a comprehensive aops-core/tools audit. Only the daily-handling skills are in scope. Other potential migrations (e.g., is `/q` a primitive or a tool?) are out of scope for this design pass.
- Not a deprecation plan for old `/email` invocations. The slash command keeps the same name; only the implementation moves.
