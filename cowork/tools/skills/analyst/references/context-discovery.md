---
title: Context Discovery Reference
type: reference
category: ref
permalink: analyst-ref-context-discovery
description: What to read and what to extract from a research project before analysis, and what to report back before acting
---

# Context discovery

Read the project before the first analytical action in it. The point is to find
the work that already exists — models, dashboards, conventions, tests — so that
what you build next extends it rather than duplicating or contradicting it.

## What to read, and what to take from each

**`README.md` in the working directory and in every parent up to the project
root** (typically a per-project directory, or the repository root). Take: the
research questions, the phase the project is in, naming and organisation
conventions, and the tools and services it depends on.

**`data/README.md`, and any in data subdirectories** (`data/raw/README.md`,
`data/processed/README.md`). Take: where the data comes from, what tables and
fields exist, field definitions and units, how data is accessed, refresh
frequency, and known quality problems and limitations.

**The project overview note**, where the project keeps one — in this layout,
under a `data/projects/` directory named for the project. Take: why the project
exists, what stage it has reached, decisions already made about method and
tooling, current blockers, and deadlines.

**The transformation layer.** Take: which models exist at each layer (staging,
intermediate, marts), what each is for and what it depends on, the naming
convention in force, and which existing models could be extended instead of
duplicated. Model and column purpose live in the layer's schema documentation
(`dbt/schema.yml` under dbt).

**The presentation layer.** Take: which dashboards or reports exist, which
models each reads, and the code and layout conventions they follow.

Commands for listing models and apps in a specific engine: the `dbt` and
`streamlit` skills.

## Report back before acting

Summarise to the user and stop for direction: the project and its purpose, one
or two of its research questions, where the data comes from, the existing work
counted by kind (models by layer, dashboards), the conventions you found, the
tools in use, and anything the context left unclear.

## When the context is thin or mixed

- **No transformation layer, no README, an empty `data/`** — treat it as a new
  project and ask whether to scaffold the structure in
  `instructions/research-documentation.md` before analysing anything.
- **Mature infrastructure** — read the existing models before proposing any new
  one, and follow the conventions in force even where you would have chosen
  differently.
- **Old and new patterns mixed** — ask which is current rather than inferring
  it, and record the answer where the next reader will find it.
