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

4. **Concrete recommendations section**. Who is the user, what are the constraints, what decision does this feed? Be explicit about friction budgets (e.g., "30 seconds per edge"), whether outputs are hard gates or soft signals, and what existing signals they must integrate with. Name the **deliverables** you want (a spec, three guides, a ranking) — but you don't have to dictate their internal format; "you decide the best structure" often produces cleaner output than a prescribed schema (see anti-patterns).

5. **Evidence discipline, as required sections — not a trailing clause.** A one-line "cite sources, flag thin consensus" gets ignored (observed 2026-07: a strong Gemini run produced zero visible citations and flagged nothing). Make it structural. Require:
   - a **`Works Cited`** section _and_ inline citation anchors on every named claim;
   - a **`Weakest links`** section listing the 3–5 places the synthesis is thinnest or where the tool is extrapolating beyond direct evidence;
   - for any **cross-domain design** ask (transferring lessons from field A to your problem in field B), an explicit instruction to **separate what the sources actually establish from its proposed transfer** — mark inferences as inferences. Without this, a research tool will assert analogical leaps ("behaviour trees are the right model for LLM agents") as settled fact.

## Worked examples

Prior spike tasks in your PKB are good templates. Search for tasks tagged `deep-research` or with type `spike` to find examples. A well-structured spike body includes:

- A two-paragraph "Problem" framing
- A numbered list of 5-6 named traditions (OKR / AHP / MCDA / Bayesian elicitation / Fermi / Delphi)
- For each: protocol + failure modes + calibration + validation
- Explicit user context: constraints, friction budgets, how output feeds downstream decisions
- Required `Works Cited` + `Weakest links` sections (not a one-line cite clause — see anatomy §5)

Read a few recent spike prompts before drafting a new one to calibrate the level of detail.

## Anti-patterns

- **"Tell me about X"** — returns an undergraduate encyclopaedia entry, not actionable synthesis.
- **Unbounded scope** — "survey all prioritisation research" returns noise. Name 4-6 traditions.
- **No user context** — the tool can't tailor recommendations to constraints it doesn't know.
- **No named deliverables** — say _what artefacts_ you want back (a spec, three guides, exemplars, a ranking). This is different from dictating their _format_: name the deliverable, and unless a schema/formula/table is genuinely load-bearing, leave the internal shape to the tool ("you decide the structure"). Over-specifying shape tends to flatten the output into filled-in boilerplate.
- **Over-specified output shape** — the opposite failure. A rigid section-by-section template suppresses synthesis. Prescribe format only where the downstream consumer truly needs it.
- **No cite/thin-consensus sections** — you'll get plausible-sounding unsourced claims asserted with false confidence. Make evidence discipline structural (anatomy §5), not a closing sentence.

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
- [ ] Verify the output actually carries citations and a `Weakest links` section before capture — if not, re-run (don't capture an unsourced doc)
- [ ] Capture output via `/deep-research` (produces a note at `knowledge/<topic>/<slug>.md`)
- [ ] Note includes <key artefacts the output should contain>
- [ ] Flag any thin-consensus recommendations
```

## High-leverage techniques

- **Ask for 2–3 concrete exemplars.** For any design/architecture/spec question, "include a few concrete exemplar artefacts" is the single most valuable addition — it grounds the abstraction and is the most directly reusable part of the output. (Observed 2026-07: the exemplar components were the strongest part of a workflow-system synthesis.)
- **Force conflict adjudication.** "Where two traditions give conflicting advice, say so and adjudicate" sharpens the synthesis. Otherwise the tool harmonises tensions it should surface (e.g. prescriptive checklists vs. mission-command delegation).
- **Weight toward the deliverable.** For implementation-oriented asks, add "keep the theory synthesis tight; weight the output toward the implementable spec/guides/exemplars" — otherwise the front half becomes a literature review and the actionable material is buried at the end.
- **Ask for a reasoned position, not a menu.** "Reach a reasoned position (not just options) on X" gets you a decision you can act on rather than a balanced survey.

## Iteration

Deep-research runs are cheap in time (~10 minutes) and zero in token cost. If the first output is shallow, refine the prompt and re-run. Common refinements:

- Add a tradition you know is relevant but the tool missed
- Sharpen the user-context section — give it numbers and constraints
- Add "distinguish between X and Y" if the tool conflates two concepts
- If citations or thin-consensus flags are missing, they usually _weren't forced_ — promote them to required sections (§5) and re-run
