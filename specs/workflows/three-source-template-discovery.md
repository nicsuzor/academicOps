---
id: workflows-three-source-template-discovery
title: Workflow Templates — Composition and Discovery
type: spec
category: workflow
status: ready
tags: [spec, workflow, templates, discovery, three-tier, resolution, brief, v0.9]
related: [[workflows-task-pipeline]], [[aops-composable-workflow-system]]
---

# Workflow Templates — Composition and Discovery

What a workflow template is, where templates are found, and how a composing pass
assembles them into a process. Supersedes the separate template-library spec,
which is folded in below.

## 1. What a template is

A short markdown file, or PKB document, that a smart agent reads and composes
**in context, by comprehension** — never parsed, never solved. Any template is
defined by carrying `type: template` in its YAML frontmatter. Two kinds:

- **Process templates** describe how a class of work proceeds — `feature-dev`,
  `investigation`, `email-triage`. They carry routing signals, NOT-this signals,
  the steps unique to that class, and exit routing.
- **Gate templates** are reusable QA, vetting and approval obligations —
  `wf-verification`, `wf-qa`, `wf-outbound-review`, `wf-human-approval`. They are
  the units the door-type policy selects among: **two-way versus one-way door is
  expressed as which gates get composed in**, which gives one vocabulary for
  proportionate process everywhere.

Some templates are **fragments** — sub-steps only meaningful composed into a
larger process, and never dispatched standalone. A fragment dispatched alone
sends a worker at half a process. In the universal and project tiers a fragment
carries `kind: fragment`, corroborated by its own first heading
(`# Process fragment: …` rather than `# Process: …`); in the PKB tier the
`planner-data` tag marks the set, corroborated by a `## <slug> — step: …` first
heading. Confirm against the body, never the marker alone.

### Authoring bar

1. **Short and composable.** Several templates must fit comfortably in one
   context window together; target ≲100 lines. Substance that outgrows that
   belongs in a skill the template points at — a template orchestrates, a skill
   executes.
2. **Minimal dependency vocabulary.** `requires` / `pairs-with` / `conflicts` /
   soft `recommends`, as frontmatter hints the composer reasons over. No solver,
   no richer ontology.
3. **Declared stakes.** A gate template states the door type it exists for and
   its skip conditions, so proportionality is legible rather than folk knowledge.
   That section, not the `wf-` prefix, is what makes a template a gate.
4. **Intent and acceptance criteria, not micro-scripting.**
5. **Revisable.** Templates are standardised work, not law: versioned, improved
   from execution feedback.

## 2. Where templates are found

Three sources, one namespace. A PKB template composes exactly like a shipped one.

**`type: template` is the marker in every tier.** The tiers differ only in where
you look for it.

| Tier             | Where to look                                                                | Enumerate with                                   |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------------------------------ |
| **1. Project**   | `$CWD/.agents/templates/*.md`                                                | `ls`; an absent directory is empty, not an error |
| **2. PKB**       | the graph                                                                    | `pkb__list_documents(type="template")`           |
| **3. Universal** | `plugins/aops-core/workflows/*.md`, catalogued by `plugins/aops-core/workflows/INDEX.md` | `ls`                                             |

Frontmatter beyond `type: template`: `kind: process` or `kind: fragment`,
`description` (the one-line routing summary agents scan), and the dependency
hints `requires` / `pairs-with` / `conflicts` / `recommends`.

The project tier is **any** repository's `.agents/templates/`, resolved against
the working directory. There is no separate user-global layer: when you are
working inside the PKB repo, its `.agents/templates/` is the project tier by the
ordinary rule, and nothing about `$ACA_DATA` is special.

**Resolution: project ≻ PKB ≻ universal.** Slugs match case-insensitively and
ignore a `wf-` prefix and `_`/`-` differences, so `feature-dev`,
`wf-feature-dev` and `wf_feature_dev` are one slug. A higher tier shadows a lower
one **whole** — never merge two tiers' text. Name the tier each template came
from in the composition trace, and say what it shadowed.

**Existence is not registration.** A template exists because it has
`type: template` (with project-local lookup in `$CWD/.agents/templates/` as well) —
not because an index lists it. The old invariant _"a template document exists in
the PKB only once it is listed below"_ is repealed. Indexes remain useful for human
orientation and carry notes that source-scanning does not reproduce, but they are
never the discovery mechanism, and a name absent from every index is not thereby
missing.

**Enumerate by running the command, every time.** Describing what the library
probably holds, from memory, is the failure this contract exists to prevent.

### Filtering the PKB tier

The other two tiers are directories and need no filtering. The PKB tier is a
live graph, so a scanning agent excludes:

1. **Retired templates** — `status: retired` or `status: cancelled`, or a
   `retired` / `superseded` tag. **Frontmatter alone is not sufficient**: some
   are marked only in the body. Read the opening lines.
2. **Instance nodes** — a datestamped title or id (`-\d{8}-\d{4}-`), or a live
   execution task. These are runs, not templates.
3. **Out-of-scope projects** — a `custom-template` tag with a project tag
   (`wikijuris`), or a `project:` frontmatter field, matches only when the
   current task's project matches. Check both places.

Fragments are not filtered out; they are available as sub-steps, and only the
never-dispatch-standalone rule applies.

## 3. What the stock plugin ships

The universal tier is the immutable baseline: it sets minimum standards that
cannot be derogated from, and both tiers above it may extend or shadow it.

**23 templates** — 19 `kind: process`, 4 `kind: fragment` (`batch`, `burst`,
`task-tracking`, `tdd`). By the work they cover:

| Group               | Templates                                                                             |
| ------------------- | ------------------------------------------------------------------------------------- |
| Entry and routing   | `framework-gate` (checked first, always), `simple-question`, `interactive-followup`   |
| Generic work spines | `feature-dev` (known cause), `investigation` (unknown cause), `develop-specification` |
| Fragments           | `task-tracking`, `tdd`, `batch`, `burst`                                              |
| Review and closure  | `decision-briefing`, `pr-review`, `worktree-merge`                                    |
| Academic            | `academic-paper`, `reference-letter`, `finalize-report`, `review-response`            |
| Email               | `email-triage`, `email-capture`, `email-reply`                                        |
| Operations          | `external-batch-submission`, `live-fix-loop`, `audit`                                 |

**No gate templates ship.** All six obligation gates — `wf-verification`,
`wf-qa`, `wf-constraint-check`, `wf-handover`, `wf-outbound-review`,
`wf-human-approval` — live in the PKB tier only, so a project taking the
universal tier alone inherits no gates at all. That is a known gap, not a design
intent.

`INDEX.md` sits in the same directory and carries the **routing tree**, which
lives nowhere else: it maps an ask to the template for its class of work.
Routing and composition are different jobs, and most of what the tree routes
never reaches composition at all.

## 4. The composition process

Composition happens in `brief` §5 — read in context, every time, never carried
in the composing agent's own text. It runs only on work already released for
dispatch.

1. **Route.** Read `INDEX.md`'s tree and pick the spine for this class of work.
   `framework-gate` is checked before any other routing.
2. **Enumerate all three tiers** and resolve slugs by the order above.
3. **Read each candidate template.** Do not guess at contents; apply each one
   critically at composition time.
4. **Clip on gates proportionate to stakes.** The escalation ladder is
   `wf-verification` → `wf-qa` → `wf-outbound-review` → `wf-human-approval`;
   each is strictly weaker than the next, and a weaker one never authorises a
   stronger one's crossing.
5. **Emit the checklist** onto the task: the composed steps in order, plus one
   pointer bullet naming the templates used, the tier each resolved from, and
   the proportionality call.

The checklist is not the gate. **Obligations that must block acceptance also
become real task nodes**, and where a step is both a checklist line and an
obligation, the node wins. An empty review set is a library gap `brief` halts
on: record the gap, leave the task `blocked`, write no brief.

## 5. Project-tier file format

A flat directory of `.md` files — `$CWD/.agents/templates/deploy-staging.md`.
Frontmatter:

```yaml
---
title: "Deploy to Staging Pipeline"
type: template
kind: process # or fragment, or gate
category: release # the domain, not the kind
description: "One-line routing summary for agent scanning"
tags: [deploy, staging, release]
---
```

The absence of `$CWD/.agents/templates/` is the standard case across
repositories. Fall through silently; report it as "no project tier here".

## See also

- `plugins/aops-core/workflows/INDEX.md` — the routing tree
- `plugins/aops-core/skills/brief/SKILL.md` §5 — the composition pass
- `plugins/aops-core/skills/workflow-library/SKILL.md` — list, view, add, edit, retire
- [[workflow-library-moc]] — the human-facing map of what currently exists in every tier
