---
name: weave
type: command
description: Stage 3 Composition — weave a set of invariant workflow templates into an aligned constellation of constituent processes, with gates clipped on proportionate to stakes. Composes process only; never applies it to specific work.
allowed-tools: [Skill, Read, Grep, Glob, Bash, mcp__services__pkb__list_documents, mcp__services__pkb__get_document, mcp__services__pkb__search]
---

# /weave — Assemble templates into an aligned constellation

Given a class of work, assemble the invariant workflow templates that govern it into one aligned constellation: a spine, the fragments it composes, and the gates clipped onto it proportionate to what is at stake.

You compose the process. You never apply it to a particular piece of work, and you never invent a process that no template supplies.

## Workflow

1. **Route.**
   Read the routing tree and pick the spine for this class of work. Routing and composition are different jobs, and most of what the tree routes never reaches composition at all.

2. **Enumerate every tier by running the command, every time.**
   Describing what the library probably holds, from memory, is the failure this contract exists to prevent.

   | Tier              | Where to look                                                              |
   | ----------------- | -------------------------------------------------------------------------- |
   | 1. Project        | `$CWD/.agents/templates/*.md` — an absent directory is empty, not an error |
   | 2. Knowledge base | `pkb__list_documents(type="template")`                                     |
   | 3. Universal      | `plugins/aops/workflows/*.md`, catalogued by `INDEX.md`                    |

   Existence is not registration: a template exists because it carries `type: template`, not because an index lists it.

3. **Resolve slugs: project ≻ knowledge base ≻ universal.**
   Matching is case-insensitive and ignores a `wf-` prefix and `_`/`-` differences, so `feature-dev`, `wf-feature-dev` and `wf_feature_dev` are one slug. **A higher tier shadows a lower one whole — never merge two tiers' text.**

   Filter the knowledge-base tier, which is a live graph rather than a directory: exclude retired and superseded templates (read the opening lines — frontmatter alone is not sufficient), instance nodes (datestamped ids, live execution tasks), and templates scoped to a different project. Fragments are not filtered out; they are available as sub-steps and are never dispatched standalone.

4. **Read every candidate template in full.**
   A catalogue row is not the template. Apply each one critically at composition time; never carry a template's contents in your own text.

5. **Clip on gates proportionate to stakes.**
   The escalation ladder runs verification → QA → outbound review → human approval. Each rung is strictly weaker than the next, and **a weaker gate never authorises a stronger one's crossing.** Weight the process against real consequence: heavier is theatre, lighter is unmitigated risk. Two-way versus one-way door is expressed as which gates get composed in.

6. **Emit the constellation and its trace.**
   The constellation is the composed process in order. The trace names every template used, the tier each resolved from, what it shadowed, and the proportionality call.

## Output

```
Constellation for: <class of work>
  spine:     <template> (tier: project|kb|universal) [shadowed: <tier>]
  fragments: <template> (tier) ...
  gates:     <template> (tier) — rung: verification|qa|outbound|approval
  trace:     <proportionality call, one sentence>
  gaps:      <named library gap>   [where applicable]
```

## Must NOT

- **Do not freelance a process.** A template you need that no tier holds is a library gap: name it and halt. An empty gate set is a library gap, not a light-touch process.
- Do not merge two tiers' text for one slug; the higher tier wins whole.
- Do not describe library contents from memory or from an index instead of reading the files.
- Do not project a component through the constellation, cut work into units, or write tasks. The constellation is invariant; applying it to specific work is a later stage.
