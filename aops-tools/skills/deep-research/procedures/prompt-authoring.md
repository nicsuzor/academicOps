---
name: prompt-authoring
parent_skill: deep-research
---

# Authoring a deep-research prompt

Deep-research tools (Gemini Deep Research, ChatGPT Pro's Deep Research, Perplexity Deep Research) return long synthesis documents with citations. They work best when asked to _compare and synthesise_ bodies of practice — not when asked to "explain" or "summarise".

## Prompt anatomy

A good deep-research prompt has five sections:

1. **Problem framing** (2-3 sentences). What are you designing, and what property does it need? Ground the question in a concrete artefact so the tool knows what "useful" looks like.

2. **Numbered comparison of 4-6 bodies of practice**. Name specific traditions, frameworks, or schools. The tool will otherwise invent a shallow survey.

3. **For each body of practice, ask for a structured extract**: protocol, failure modes, calibration/consistency checks, validation-over-time. Uniform structure makes the output scannable.

4. **Concrete recommendations section**. Who is the user, what are the constraints, what decision does this feed? Be explicit about friction budgets (e.g., "30 seconds per edge"), whether outputs are hard gates or soft signals, and what existing signals they must integrate with.

5. **"Cite sources. Flag anything where consensus is thin."** Always. These two sentences are what differentiate deep-research tools from chat.

## Worked examples

The `pkb-weight-*` spike series ([[task-454ec614]], [[task-744da956]], [[task-d1a916cf]]) are good templates. Each spike body includes:

- A two-paragraph "Problem" framing
- A numbered list of 5-6 named traditions (OKR / AHP / MCDA / Bayesian elicitation / Fermi / Delphi)
- For each: protocol + failure modes + calibration + validation
- Explicit user context: "single-user system, I set weights with justification, weights influence prioritisation but never hard-gate, I want 30-second capture with periodic recalibration"
- `Cite sources. Flag where consensus is thin.`

Read those three prompts before drafting a new one.

## Anti-patterns

- **"Tell me about X"** — returns an undergraduate encyclopaedia entry, not actionable synthesis.
- **Unbounded scope** — "survey all prioritisation research" returns noise. Name 4-6 traditions.
- **No user context** — the tool can't tailor recommendations to constraints it doesn't know.
- **No output spec** — say whether you want a field schema, a formula, a checklist, a ranking. Otherwise you get prose.
- **No cite/thin-consensus clause** — you'll get plausible-sounding unsourced claims.

## Format for the task

Deep-research prompts live in the body of the sourcing spike task:

```markdown
# Spike: <one-line goal>

**Type**: spike (affordable-loss probe)
**Effort**: 0.5d
**Tool**: Gemini Deep Research

## Problem

<2-3 sentences of framing>

## Deep Research prompt
```

<the prompt, ready to paste>

```
## Acceptance criteria

- [ ] Run the prompt in <tool>
- [ ] Capture output via `/deep-research` (produces a note at `knowledge/<topic>/<slug>.md`)
- [ ] Note includes <key artefacts the output should contain>
- [ ] Flag any thin-consensus recommendations
```

## Iteration

Deep-research runs are cheap in time (~10 minutes) and zero in token cost. If the first output is shallow, refine the prompt and re-run. Common refinements:

- Add a tradition you know is relevant but the tool missed
- Sharpen the user-context section — give it numbers and constraints
- Ask for a specific output format in section 4 (field schema, formula, ranking table)
- Add "distinguish between X and Y" if the tool conflates two concepts
