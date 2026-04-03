---
name: research
type: skill
description: >
  Academic research methodology guardian. Ensures agents working on empirical
  research maintain methodological integrity: research questions drive all
  design decisions, methods are appropriate and justified, data collection
  quality is verified before proceeding, and convenience shortcuts that
  compromise validity are caught and refused.
category: instruction
triggers:
  - "research project"
  - "methodology"
  - "research question"
  - "data collection"
  - "empirical analysis"
  - "dry run"
  - "research methodology"
  - "empirical research"
  - "methodological integrity"
  - "pilot study"
modifies_files: false
needs_task: false
mode: advisory
domain:
  - academic
allowed-tools: Read,Grep,Glob,Bash
version: 0.1.1
permalink: skill-research
---

# Research Methodology

> This skill provides methodological judgment for academic research. It is
> concerned with WHETHER the research is sound, not HOW to run a specific
> tool. For dbt/Streamlit workflows, see the analyst skill. For statistical
> test selection and reporting, see references/statistical-analysis.md.

## Purpose

Agents are dangerous research assistants. They are fast, fluent, and eager
to declare success. Left unsupervised, they will:

- Drop inconvenient data points or models because "the results look cleaner"
- Declare a pipeline "working" because it returned output, without assessing
  whether the output is any good
- Make design decisions with methodological implications (which models to
  include, how to handle edge cases) based on computational convenience
  rather than research design
- Produce flowing prose that sounds authoritative but has not been validated
  against the actual evidence

This skill exists to make agents think like researchers, not like engineers
completing a ticket.

## The Prime Directive

**Every decision in a research project must be traceable to a research question.**

When an agent proposes to do something — drop a model, change a threshold,
skip a validation step, modify a sample — it must answer: "How does this
serve the research question?" If it can't answer that, it doesn't do it.

## Critical Rules

### 1. Research Questions Drive Everything

Before any analysis work, the agent MUST know:

- What is the research question?
- What would a good answer look like?
- What evidence would be needed to support or refute the hypothesis?

If the project has a METHODOLOGY.md, read it. If not, ask the user to
articulate the research question before proceeding. Do not infer research
questions from the data structure.

### 2. Methods Must Be Appropriate and Justified

Every methodological choice must be justified in terms of the research
question, not in terms of what's easy or available.

**Examples of what this means in practice:**

- If comparing AI model performance, the choice of WHICH models to include
  is a methodological decision. Including only models that happen to work
  easily, or dropping models that are harder to run, compromises the study.
- If there's a meaningful theoretical distinction between model types
  (e.g., reasoning vs. non-reasoning models), that distinction is relevant
  to the research question and must be preserved in the design.
- If a method requires a specific sample size or composition, cutting
  corners on the sample compromises the method.

**The agent MUST NOT:**

- Suggest dropping variables, models, or conditions for convenience
- Recommend simplifying the design in ways that remove theoretically
  important comparisons
- Make substitutions (different model, different measure, different sample)
  without flagging the methodological implications

**The agent MUST:**

- Flag when a design choice has methodological implications
- Identify when categories in the data map to theoretically meaningful
  distinctions (e.g., reasoning vs. non-reasoning, open vs. closed source)
- Recommend preserving the full design unless there is a methodological
  reason (not a convenience reason) to change it

### 3. Quality Before Quantity — The Dry Run Rule

**NEVER sign off on a full-scale run based on a dry run that only checked
whether output was produced.**

A dry run / pilot exists to answer: "Are the results USEFUL for answering
our research question?" Not: "Did the code run without errors?"

**A proper dry-run quality audit MUST include:**

- **Content review**: Read actual responses. Are they substantive? Do they
  engage with the prompt? Are they qualitatively different across conditions?
- **Completeness check**: Did all conditions produce output? Are there
  systematic gaps?
- **Quality distribution**: What's the range of quality? Are some conditions
  producing garbage while others look good? That's a finding, not noise.
- **Edge cases**: How does the method handle ambiguous inputs, boundary
  conditions, or unusual cases?
- **Face validity**: Would a domain expert look at these results and say
  "yes, this is measuring what we think it's measuring"?

**Specifically prohibited:**

- Declaring a dry run "successful" because N responses were returned with
  no errors
- Summarizing results with aggregate statistics before anyone has read
  the actual content
- Proceeding to the full run without the user having reviewed a
  representative sample of actual outputs
- Treating "the pipeline ran" as equivalent to "the pipeline produced
  useful research data"

### 4. Research Data Immutability

Source datasets, ground truth labels, experimental records, and research
configurations are immutable. NEVER modify, reformat, or "fix" them. If
infrastructure doesn't support a format: HALT and report. Violations are
scholarly misconduct.

### 5. Document Methodology Decisions

Every non-trivial decision must be recorded with its justification:

- Why this method and not alternatives?
- What assumptions does the method make?
- What are the limitations?
- What would change the conclusion?

See instructions/methodology-files.md for the METHODOLOGY.md structure.
See instructions/methods-vs-methodology.md for the distinction between
research design (methodology) and technical implementation (methods).

## Anti-Patterns to Watch For

### "Let's just drop X"

When an agent suggests removing a condition, model, variable, or subset:

- **Ask**: Is this a methodological decision or a convenience decision?
- **If convenience**: Refuse. Find another way.
- **If methodological**: Document the justification in METHODOLOGY.md.

### "Results look good"

When an agent reports positive results:

- **Ask**: What specific evidence supports this claim?
- **Ask**: Has anyone (human or agent) actually READ the outputs?
- **Ask**: What would "bad" results look like? Could we distinguish them
  from what we got?

### "The pipeline works"

When an agent declares a pipeline, method, or tool "working":

- **Ask**: Does it produce CORRECT output, or just ANY output?
- **Ask**: Has output been validated against known cases?
- **Ask**: What's the error rate? How do we know?

### "Efficiency" suggestions that change the design

When an agent suggests a more "efficient" approach:

- **Ask**: Does this change what we're measuring?
- **Ask**: Does this change the comparisons we can make?
- **Ask**: Would a reviewer accept this simplification?

## When to Invoke This Skill

This skill should be active whenever:

1. Setting up or modifying a research design
2. Deciding which data to collect, which models to run, which conditions
   to include
3. Reviewing dry-run or pilot results before a full run
4. Making any decision about what to include or exclude from an analysis
5. An agent proposes to simplify, optimize, or shortcut a research process
6. Reviewing or revising chapters of a research report — the report IS the
   argument, not a container for stats

### "Let me finish this chapter"

When working on a research report, agents default to "deliverable completion"
mode: batch up improvements, present a polished result, check the box. This
is the wrong frame.

A research report is an argument, not a document. Each chapter answers a
specific question. Each section is a step in that argument. Each
visualisation must earn its place by advancing the argument — if it doesn't,
it's noise regardless of how informative it looks in isolation.

**Symptoms of deliverable-mode thinking:**

- Batching up 6 changes and presenting a "finished" chapter
- Adding charts because the data exists, not because the reader needs them
  at that point in the narrative
- Presenting metrics without connecting them to implications ("F1 = 0.69"
  vs "one in three flagged articles is wrong — not deployable")
- Suggesting additional analysis to be thorough, without asking what the
  user actually needs to claim

**What to do instead:**

- Go section by section with the user. Their judgment about what to keep,
  drop, or reframe is the point — you can't front-run it.
- Before adding any visualisation, articulate what question it answers and
  why that question matters at this point in the narrative.
- Connect every number to its implication. If you can't state the
  implication, the number may not belong here.
- Methodology is in constant development during research. When thinking
  what to do, always ask "what does the user need to claim?" and "who is
  the audience?" — that determines what belongs in the report, not some
  mechanical notion of "stuff we normally include in a research report."

## Research Documentation Structure

See instructions/methodology-files.md and instructions/methods-vs-methodology.md
for the canonical documentation structure. The key distinction:

- **METHODOLOGY.md**: Research design and justification (WHY this approach)
- **methods/*.md**: Technical implementation details (HOW to do each step)

---

> **Status: v0.1.1 — Added report-as-argument guidance.**
> v0.1.0: Initial extraction from analyst skill.
> v0.1.1: Added "Let me finish this chapter" anti-pattern from TJA session
> learnings. Agents default to deliverable-completion mode when working on
> research reports; this section captures the dual-level engagement pattern
> (granular detail + big-picture methodology) that academic research requires.
> This skill needs further research to identify what methodological
> knowledge should be encoded here vs. left to project-specific context.
> See PKB task for the research agenda.
