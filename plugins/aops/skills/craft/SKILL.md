---
name: craft
description: Authoring standard and quality gate for agent-facing instruction text — SKILL.md bodies, frontmatter descriptions, agent definitions, subagent and dispatch prompts, slash commands, hook reminders, and tool descriptions. Use it whenever writing, reviewing, or revising any instruction an agent will read; when a skill under- or over-triggers; when deciding what belongs in a body versus a reference file; or when judging whether instructions are good enough to ship. Not for human-facing prose (specs, reports, documentation), and not for task briefs or workflow templates, which have their own authoring standards. The bar is excellence, not compliance.
---

# Instruction Craftsmanship

Author and review agent-facing instructions for excellence. When a rule here is
contested — or two published authorities disagree on an authoring question —
read `references/evidence.md`: it carries the measured findings and
adjudications this standard applies, and a verdict that overrules it must cite
stronger evidence.

## First Principles

Good instructions trust a capable, improving agent to exercise judgment; they do not try to mechanically pre-solve every case.

1. **Trust the harness, not today's quirks.** Agents and their tools improve continuously. Never write an instruction to patch a specific client's current limitation, plug a gap that will close on its own, or hard-code a workaround for how one version of an agent happens to behave. If a rule is only true "for now," it does not belong in a durable instruction.
2. **Specify the process, not the keystrokes.** State _when_ to invoke which capability and _what outcome_ proves it worked. Do not spell out sub-steps, tool flags, or branching logic a competent agent already knows how to perform (opening a PR, formatting a table, running a routine lookup). Name the judgment call, not the click-path.
3. **One skill, one job.** An instruction set is constrained to its own pure function. Naming another skill as a delegation or dispatch target is fine; explaining, restating, or summarizing that other skill's internals, procedures, or file layout is not — that creates a hidden dependency that silently rots when the referenced skill changes shape.
4. **Verification must be real, not performed.** "Did the step run?" is not evidence of anything. Instructions must demand direct inspection of the actual artifact — outputs, logs, diffs — with an eye for the failure that looks like success (silent errors, plausible-but-wrong data, a summary standing in for the thing itself).
5. **Every line earns its place.** Brevity is a feature. Cut anything that does not change what the agent does: provenance ("on the 2026-06-25 session…"), incident IDs, and recipes tuned to one past failure all belong in the change record that explains why a rule exists — not in the instruction loaded every run. Write the durable principle the incident illustrates, not the incident.

These are lenses, not a checklist to tick. If instructions feel shallow but match nothing below, trust the feeling and say why — depth is verification specificity, not step count.

## The Deletion Test

Apply to every line of every agent-facing file: if this line were removed,
would the agent behave differently on the median task this file governs? No —
cut it, or relocate it to the surface that loads when it does matter. Content
for rare paths belongs in the skill or reference file owning that path, never
in a file loaded every run.

## The Description Is the Router

A skill's frontmatter description is the only part loaded before invocation:
routing succeeds or fails on it alone, and routers under-trigger by default.
Write it to advocate for its own selection:

- Open with what the skill does, then the trigger conditions in the caller's
  vocabulary — the words a user or dispatching agent would actually type.
  Front-load ruthlessly: the cap is 1,024 characters and listings truncate.
- Add exclusions ("not for…") covering the near-misses that would fire it
  wrongly. A few contraindications beat an exhaustive positive list.
- Promise only what the body delivers. A description asserting obligations the
  body never states ships a defect, not marketing.
- Keep all triggering data in the description itself, because auxiliary
  trigger fields are not portable across harnesses.

## The Body Is a Budget

A skill body loads whole into working context, and attention across a long
file is U-shaped — openings and endings bind, middles get skipped:

- Hold the body to operational content — procedure, decision points,
  verification — under about 200 lines and one to three tightly related jobs.
  Split a skill that outgrows this: small focused skills measure roughly
  double the task-lift of sprawling ones.
- Place load-bearing constraints first or last, and segment with `##` headers;
  models navigate by structure, not by rereading prose.
- Move dense reference matter — schemas, long tables, style guides,
  boilerplate — into `references/` files exactly one level deep, and at each
  point of use instruct the read explicitly ("Read `references/<name>.md` before
  doing Y"). Agents rarely follow bare "see also" pointers and do not traverse
  nested directories.
- Keep content that is mandatory at the moment of action inline. Forking a
  required rule across a summary and a linked file splits the rule, and the
  linked copy loses.
- Give examples of output _shape_ — schemas, formats, report skeletons — and
  withhold worked examples of _logic_: agents copy example logic verbatim into
  novel problems instead of generalising the procedure.

## Voice

- Write positive imperatives, each carrying its functional reason — "use
  parameterised queries because the ORM closes injection paths" — because the
  reason is what lets an agent generalise the rule to cases the author never
  saw. Functional reasons belong; provenance, history, and design narrative
  still do not.
- Where a prohibition is genuinely required, pair it with the affirmative
  alternative and a legitimate escape hatch: bare negative constraints
  measurably fail more often than positive instructions.
- Emphasise by position and structure, not typography. Capitalised absolutes
  ("ALWAYS", "NEVER", "CRITICAL") decay as a file grows and crowd out real
  signal.

## Agent Definition Files

An agent definition is an identity file loaded on every invocation — every
byte is a budget line. The body may contain exactly four kinds of content:

1. **Identity/role** — one to three sentences: who the agent is, enough for a
   caller to route work here.
2. **Behavioral rules** — terse standing constraints the agent must hold
   regardless of task (epistemic standards, safety invariants, delegation
   rules).
3. **Output schema** — verdict states and required report shape; not
   methodology or worked examples.
4. **Routing table** (orchestrators only) — a table, not prose, with no
   per-route rationale.

Skill matter stays in skills (name the skill; never inline its procedure),
reference material stays in reference docs, and mechanics the harness already
enforces or rules the agent is given elsewhere stay out. Apply the deletion
test to every passage; rare-task passages relocate to the relevant skill.

A subagent's routing description is one short sentence saying when to hand
off, because the orchestrator routes on it and length dilutes it. Permissions,
model, tools, and allowlists live in frontmatter only; the body never restates
them in prose.

## Task Naming, Filename, and Decision Craft

- **Task titles are verb-led imperatives:** Brief, descriptive statements of a concrete outcome to achieve (e.g. `Implement X`, `Verify Y`, `Refactor Z`).
- **No person's name in titles or filenames:** A task title, note title, or filename must **never** contain a person's name or persona prefix (e.g. no `nic: decision: ...`, `nic-task-...`, `for-nic.md`). Assignment belongs exclusively in `assigned_to` or `assignee` frontmatter.
- **Decisions as graph relationships:** Never create standalone "decision" tasks or file questions as tasks. Represent competing alternatives as mutually exclusive option nodes with mutual blocking edges where choosing one branch resolves the conflict, and model unknowns as empirical probe tasks (`classification: spike`).
- **Task bodies are strictly concise (50–150 words):** Follow the canonical template in [`specs/meta/naming-and-decisions.md`](../../../../specs/meta/naming-and-decisions.md). Never add extra narrative background, reference essays, or prose task-to-task links.
- **Graph edge economy:** Parent/child (`parent_id`) is already a structural edge. Do not redundantly wire edges between siblings or descendants under the same parent unless there is a specific, genuine interaction (`depends_on`, `supersedes`, data flow).

## Schemas Are Contracts

Constrain every tool-parameter or structured-output schema fully: mark every
mandatory field `required`, use `enum` wherever values are enumerable, and set
`additionalProperties: false` on every object, because a loose schema invites
invented parameters — the leading silent killer of multi-step tool chains.

## Integrity Checks

Each of these blocks shipping on its own:

- An instruction offers a mode, option, or escalation path the runtime does
  not support.
- A pointer does not resolve. An agent holding a dead reference is an agent
  with no instructions.
- A gate or check turns on a term defined nowhere in the reader's materials —
  undecidable, so it will be improvised.
- Two lines contradict and neither yields. An unreconciled contradiction is a
  licence to fabricate, not a tie the agent will surface.

## Common Defect Patterns

Instances of the principles above, worth naming because they recur:

- **Compliance framing.** "Did X run?" instead of "is the output correct, complete, and verified?" Require outcome-based checks, not process-completion checks.
- **Evidence laundering.** Accepting an agent's summary, a partial artifact-channel check (just stdout, not logs/exit-code/schema), or a green test suite as proof — without inspecting the actual output for silent failures, corruption, or placeholders. (Principle 4.)
- **Shape without source.** A step names what the output should _look like_ but not where it comes from or what operation produces it, so the agent satisfies the shape from whatever's cheapest — recycled material, an adjacent step's by-product, memory — silently dropping the real criterion. Name the source, mandate the read, prohibit substitution — without over-specifying the keystrokes (Principle 2's over-specification is the opposite failure).

## Validating a Change

Test instructions blind: hand them to a fresh agent with no authoring context
and watch where it deviates. A reader's question is evidence the text is
unclear — fix the text, not the reader. Treat agent-drafted instruction text
as a draft for curation against this standard, never ship-as-generated:
benchmarked self-generated skills reduce task performance.

## Construction Rule: Static Prefix, Variable Tail

For any code that renders a template with dynamic data (an f-string, `.format()`/`.render()`, or a builder concatenating static scaffolding with session/transcript content): emit all static material first, append variable content last. Prompt caching keys on the longest identical prefix — one variable byte placed early invalidates the cacheable suffix that follows it. Where moving a placeholder to the tail would break meaning for negligible cache gain (a short single-token variable mid-sentence), leave it and say why.
