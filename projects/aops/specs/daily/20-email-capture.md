# `/email` — email-to-task capture workflow

**Status**: draft (cowork-sandbox), proposed 2026-05-19. Spec to land at `~/src/academicOps/projects/aops/specs/daily/20-email-capture.md`. Skill to relocate from `aops-core/commands/email.md` to `aops-tools/skills/email/SKILL.md`.

**Inherits**: [00-architecture.md](00-architecture.md) — persona, time context, shared types (`EmailCapture`).

**Plugin**: `aops-tools` (moves from `aops-core` — see [50-aops-core-vs-tools.md](50-aops-core-vs-tools.md) for rationale).

## Responsibility

Process an email inbox and produce three structured outputs:

1. **Actionable items** → create PKB tasks (one per concrete action Nic must take).
2. **FYI items** → return as structured prose for the daily note.
3. **Archive candidates** → return list of entry_ids safe to bulk-archive.

The skill writes PKB tasks itself (action items) and returns structured data for the caller (FYI + archive). It does NOT archive on its own — archiving is gated on caller confirmation (current `/daily` design) or user confirmation (interactive `/email`).

## Invocation forms

| Form              | Behaviour                                                                                                  |
| ----------------- | ---------------------------------------------------------------------------------------------------------- |
| `/email`          | Interactive mode — present FYI items inline, ask before archiving.                                         |
| `/email --daily`  | Daily mode — return structured `EmailCapture` (see 00-architecture.md). Caller (typically `/daily`) decides on archive confirmation. |
| `/email --clean`  | Aggressive cleanup mode — for explicit "clear out my inbox" requests. Skips interactive confirmation; archives anything matching the safe-archive patterns. Behaviour as in the 2026-05-19 QUT inbox run. |

## Workflow (high-level)

Detail belongs in the SKILL.md; this is the contract.

1. **Window selection**. Last N days (default 1 for `--daily`, 30 for `--clean`).
2. **Pull inbox via Outlook MCP** (`messages_query` with DASL date filter — see news-briefing spec for the syntax quirk).
3. **Cross-reference sent items** — threads where Nic has replied recently default to safe-archive unless re-bounced.
4. **Classify each email** into:
   - **ACTION** — concrete deliverable Nic owns
   - **REPLY** — personal/substantive message awaiting his voice (leave in inbox)
   - **FYI** — useful context, no action (surface in daily note, then archive)
   - **ARCHIVE** — noise (notifications, completed threads, calendar confirmations)
5. **Create PKB tasks** for ACTION items. One task per action, with email metadata in the body (sender, date, entry_id, quoted text, links). Use `parent: inbox-capture-YYYY-MM-DD` as a synthetic parent; fall back to plain `inbox` if not found.
6. **Return structured output** matching `EmailCapture` schema (see 00-architecture.md). In `--daily` mode this is markdown the caller parses; in interactive mode this is presented to the user inline.
7. **Archive on confirm**. `--daily` mode returns archive candidates; caller archives them. `--clean` mode archives directly.

## Quality bar

Every ACTION-derived PKB task must be **self-contained**. Someone pulling the task via `/pull` should understand what's needed without opening the original email. Required fields:

- Quoted email body (relevant snippet — not just subject)
- All links from the body
- Sender, recipients, date, entry_id
- `due` (ISO date) if extractable from email body
- `effort` estimate
- `consequence` prose (what happens if Nic doesn't do this)

See the 2026-05-19 QUT inbox run for a working example: 297 emails archived, 7 self-contained tasks created (e.g. `adhoc-sessions-d7a855a9` — ANU JOLT peer review, has the manuscript ID, journal, deadline, and verbatim invitation in the body).

## Heuristics — auto-archive without reading body

These patterns are noise. Skip body fetch entirely:

- **Sender contains**: `Canvas @ QUT`, `SharePoint Online`, `Email Quarantine`, `Jade Editors`, `Campus Notifications`, `no-reply@qut.appiancloud.com`, `Yammer`
- **Subject starts with**: `Accepted:`, `Declined:`, `Tentative:`, `Canceled:`, `REMINDER:`, `Recent Canvas notifications`, `End User Digest`, `FW: News you might have missed`
- **Always-archive**: royalty statements, payment confirmations, automated bills, faculty-wide broadcasts that don't name Nic

## Heuristics — default ACTION

These patterns are usually actionable. Body read required for confirmation:

- Phrases in body: "please review", "please sign", "by [date]", "deadline", "your response", "approval required", "please confirm"
- Personal request: "could you", "would you", "let me know"
- Attached form to sign
- Supervision meeting prep

## Heuristics — default REPLY (leave in inbox)

- Personal message from a student or named colleague asking a substantive question only Nic can answer
- PhD inquiries, draft feedback requests, reference requests
- Conversations with established collaborators where the ball is in Nic's court

## DRY — what NOT to repeat here

- Persona, time context — see [00-architecture.md](00-architecture.md)
- The Outlook DASL `@SQL=` prefix quirk — described in [30-news-briefing.md](30-news-briefing.md) § Step 1
- Fitness rubric for tasks-as-self-contained — already in the SKILL.md, not duplicated here

## Migration notes

Currently at `aops-core/commands/email.md` (as a command), with workflow logic referenced in `hydrator/workflows/email-capture`. Migration to `aops-tools/skills/email/SKILL.md`:

1. Convert command-style markdown to skill-style SKILL.md (frontmatter, sections per skill-development convention).
2. Inline the `email-capture` workflow content into the SKILL.md or co-locate under `aops-tools/skills/email/workflows/`.
3. Update `/daily` skill to reference the new path.
4. Add to aops-tools SKILLS.md index.
5. Verify the `/email` slash command still resolves (plugin command registration — TBD whether aops-tools registers commands).

Open question: does aops-tools have a `commands/` directory analogous to aops-core, or do all aops-tools skills self-register? Check during PR work.
