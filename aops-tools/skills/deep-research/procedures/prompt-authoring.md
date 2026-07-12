---
name: prompt-authoring
parent_skill: deep-research
---

# Authoring a deep-research prompt

Deep-research tools (Gemini Deep Research, ChatGPT Pro's Deep Research, Perplexity Deep Research) return long synthesis documents with citations. They work best when asked to _compare and synthesise_ bodies of practice — not when asked to "explain" or "summarise".

## Match the anatomy to the output type

The prompt's shape should follow what the output is _for_. Two common shapes recur, and it's worth naming which you're writing before you start — but treat them as illustrations of the principle (anatomy follows output type), not a fixed taxonomy of question types:

- **Synthesis** — "weigh these approaches and tell me how to design/decide X." Output is an argued position or spec. The five-section anatomy below fits it.
- **Enumeration / catalogue** — "find everything matching these criteria and tabulate it." Output is a structured inventory. It needs a membership predicate and per-row verifiability (see further down).

Most asks lean one way; some mix (survey the field _and_ recommend — do the enumeration first, then synthesise over its results). User context and evidence discipline apply whatever the shape. The point is to ask what the reader will _do_ with the output and build backwards from that, not to slot the request into a preset genre.

## Synthesis anatomy

A synthesis prompt has five sections:

1. **Problem framing** (2-3 sentences). What are you designing, and what property does it need? Ground the question in a concrete artefact so the tool knows what "useful" looks like.

2. **Numbered comparison of 4-6 bodies of practice**. Name specific traditions, frameworks, or schools. The tool will otherwise invent a shallow survey.

3. **For each body of practice, ask for a structured extract**: protocol, failure modes, calibration/consistency checks, validation-over-time. Uniform structure makes the output scannable.

4. **Concrete recommendations section**. Who is the user, what are the constraints, what decision does this feed? Be explicit about friction budgets (e.g., "30 seconds per edge"), whether outputs are hard gates or soft signals, and what existing signals they must integrate with. Name the **deliverables** you want (a spec, three guides, a ranking) — but you don't have to dictate their internal format; "you decide the best structure" often produces cleaner output than a prescribed schema (see anti-patterns).

5. **Evidence discipline, as required sections — not a trailing clause.** A one-line "cite sources, flag thin consensus" gets ignored (observed in practice: a strong, otherwise-accurate run produced zero visible citations and flagged nothing). Make it structural. Require:
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

## Enumeration / catalogue anatomy

When the output is an inventory rather than an argument, it lives or dies on its **membership predicate** and its **verifiability**, not on scannable per-theme structure. Cover:

1. **Search scope** — where to look and how hard, plus the exhaustiveness bar ("include any match, however small").
2. **Inclusion predicate** — the positive test for what qualifies.
3. **Exclusion predicate** — the negative boundary, stated explicitly. This is what keeps a catalogue precise, and it's the part a terse request most often leaves implicit.
4. **A testable threshold** — restate the fuzzy ask as something you could check per candidate ("must do X for at least two of {A, B, C}"), so borderline cases resolve consistently.
5. **Per-item schema** — name the exact fields each row must carry (including a source link, provenance, and recency).
6. **Ordering / ranking** — and if you ask for a rating, define the rubric or explicitly tell the tool to state its own.

**Verifiability rules for any inventory:**

- Every row must carry a **working source link the tool actually consulted** — not a bare name or slug. An inventory you can't click is nearly useless, and indistinguishable from an invented one.
- **Anti-padding honesty:** tell it "if the search yields only N genuine matches, return N — do not pad with plausible-but-unverified entries." Enumeration invites confabulation: a full-looking table reads as more complete than an honest short one.
- **Mark claimed metrics as claims:** performance numbers must be cited or labelled as the subject's own claim, not asserted as independently verified.

_Illustration:_ a catalogue run once returned a fluent ranked table with **zero** source links. Spot-checking showed the entries were **real and largely accurate** — so the failure wasn't fabrication, it was that every citable claim went uncited, leaving the whole thing unverifiable at a glance. Forcing a real link per row is what closes that gap; the lesson is genre-general, not specific to any one tool.

## Decomposing a terse request into a full prompt

A one-line ask leaves too much for the tool to resolve, usually badly. The planner's job is to close the ambiguity before handing it over. The highest-value moves, in any genre:

- **Turn fuzzy scope into a checkable predicate** — "relevant plugins" → "does X via the hooks system for ≥2 of {…}".
- **State the exclusions the user left implicit** — the boundary that says what _doesn't_ count is often the difference between a precise result and noise.
- **Name the deliverable's fields / sections** — columns for an inventory, the argued questions for a synthesis.
- **Define any rating or judgement axis** — an ungrounded "rate quality" instruction makes the tool invent its own undocumented scale; give it the rubric or have it state one.

Add these as needed, but don't inflate — a terse request for a genuinely simple lookup stays short. Expand in proportion to how much ambiguity would otherwise be resolved wrongly.

## Anti-patterns

- **"Tell me about X"** — returns an undergraduate encyclopaedia entry, not actionable synthesis.
- **Unbounded scope** — "survey all prioritisation research" returns noise. Name 4-6 traditions.
- **No user context** — the tool can't tailor recommendations to constraints it doesn't know.
- **No named deliverables** — say _what artefacts_ you want back (a spec, three guides, exemplars, a ranking). This is different from dictating their _format_: name the deliverable, and unless a schema/formula/table is genuinely load-bearing, leave the internal shape to the tool ("you decide the structure"). Over-specifying shape tends to flatten the output into filled-in boilerplate.
- **Over-specified output shape** — the opposite failure. A rigid section-by-section template suppresses synthesis. Prescribe format only where the downstream consumer truly needs it.
- **No cite/thin-consensus sections** — you'll get plausible-sounding unsourced claims asserted with false confidence. Make evidence discipline structural (anatomy §5), not a closing sentence.
- **Uncited inventory** — for a catalogue, a table without a real link per row is unverifiable and reads the same whether the entries are real or invented. Require a working link per row.
- **Open-ended "find everything"** without an exclusion predicate or a padding guard — invites a padded list. Give the negative boundary and "return N if only N match".
- **A rating/score column with no rubric** — the tool invents an undocumented scale. Define the axis or tell it to state its own.

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

- **Ask for 2–3 concrete exemplars.** For any design/architecture/spec question, "include a few concrete exemplar artefacts" is the single most valuable addition — it grounds the abstraction and is the most directly reusable part of the output. (Observed: exemplars were the strongest, most reusable part of a design synthesis.)
- **Force conflict adjudication.** "Where two traditions give conflicting advice, say so and adjudicate" sharpens the synthesis. Otherwise the tool harmonises tensions it should surface (e.g. prescriptive checklists vs. mission-command delegation).
- **Weight toward the deliverable.** For implementation-oriented asks, add "keep the theory synthesis tight; weight the output toward the implementable spec/guides/exemplars" — otherwise the front half becomes a literature review and the actionable material is buried at the end.
- **Ask for a reasoned position, not a menu.** "Reach a reasoned position (not just options) on X" gets you a decision you can act on rather than a balanced survey.

## Iteration

Deep-research runs are cheap in time (~10 minutes) and zero in token cost. If the first output is shallow, refine the prompt and re-run. Common refinements:

- Add a tradition you know is relevant but the tool missed
- Sharpen the user-context section — give it numbers and constraints
- Add "distinguish between X and Y" if the tool conflates two concepts
- If citations or thin-consensus flags are missing, they usually _weren't forced_ — promote them to required sections (§5) and re-run
