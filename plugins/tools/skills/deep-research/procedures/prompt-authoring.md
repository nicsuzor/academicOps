---
name: prompt-authoring
parent_skill: deep-research
---

# Authoring Deep Research Prompts

Deep research tools excel at synthesis and structured enumeration. Frame prompts around what downstream tasks need to decide or build.

## Prompt Structures

### Synthesis Prompt

Use when comparing approaches to produce a specification or decision:

1. **Framing**: State problem context, user constraints, and the downstream deliverable in 2--3 sentences.
2. **Named bodies of practice**: Explicitly list 4--6 specific traditions, frameworks, or literatures to compare.
3. **Structured extract**: Require a consistent matrix per tradition (protocol, failure modes, validation).
4. **Actionable recommendations**: Specify friction budgets, integration constraints, and 2--3 concrete exemplar artifacts. Force conflict adjudication between traditions.
5. **Evidence discipline**: Mandate a `Works Cited` section with inline anchors and a `Weakest links` section identifying thin-evidence claims.

### Enumeration Prompt

Use when cataloguing tools, datasets, or literature:

1. **Scope & thresholds**: Define explicit inclusion criteria, negative exclusion boundaries, and testable thresholds.
2. **Item schema**: Specify required table columns (e.g. name, URL, mechanism, provenance).
3. **Verifiable grounding**: Require active source links consulted by the tool, label claims vs benchmarks, and include an anti-padding instruction ("return only genuine matches").

## Source Bundles

- **Gemini Deep Research**: Accepts at most **10 file attachments** per run.
- When assembling a source bundle for a Gemini run, keep the total number of attached files to **10 or fewer** (including files inside any archive/zip bundle intended for upload).
- If the source material exceeds 10 files, consolidate related documents into combined files with clear section separators (or omit low-signal files) until the bundle contains at most 10 files.

## Task Template

When the composed workflow uses PKB probe tasks, store authored prompts in the sourcing probe task (otherwise deliver to the destination specified by the composed workflow and task):

````markdown
# Probe: <goal>

**Type**: probe | **Effort**: 0.5d | **Tool**: Gemini Deep Research

## Problem

<2-3 sentences framing the decision>

## Deep Research Prompt

```
<pasteable prompt text>
```

## What Done Looks Like

- [ ] Run prompt in <tool>
- [ ] Verify `Works Cited` and `Weakest links` sections exist prior to capture
- [ ] Ingest via `deep-research` skill to the workflow-specified destination (e.g., `knowledge/<topic>/<slug>.md` when PKB capture is selected)
````

## Iteration

Refine outputs by strengthening constraints: name omitted traditions, force distinction between conflated concepts, or promote citation requirements to required section headings.
