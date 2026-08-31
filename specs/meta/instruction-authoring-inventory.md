---
title: Instruction-authoring guidance — inventory and consolidation map
---

# Instruction-authoring guidance — inventory and consolidation map

Every surface that tells an agent **how to write** an instruction, skill, agent
definition, workflow template, or task brief. Swept 2026-08-31.

Scope test: does the surface govern the _authoring_ of agent-readable text?
General rules an agent must follow, the axiom set, enforcement-lever doctrine,
and report-writing contracts are out — they govern behaviour, not composition.

Destination: **`plugins/aops/skills/craft/`**. `craft` is already named as owner
by three surfaces; it does not currently ship, and its scope covers agent files
only. Both are addressed in the consolidation map below.

## The coverage gap

| Artifact kind             | Shipped      | Authoring standard                                      |
| ------------------------- | ------------ | ------------------------------------------------------- |
| Workflow template         | 42           | `workflow-create/SKILL.md`, `workflow-library/SKILL.md` |
| Rubric                    | —            | `design-rubric/SKILL.md`                                |
| Research prompt           | —            | `deep-research/procedures/prompt-authoring.md`          |
| Task brief                | per-dispatch | `brief/SKILL.md`, `note_a75a3c1f`                       |
| **SKILL.md**              | **26**       | **none — upstream only**                                |
| **Agent definition**      | **9**        | schema only; `agent-authority.md` lint is unbuilt       |
| Instruction file, general | —            | `craft` — does not ship                                 |

Counts: `find plugins -name SKILL.md` → 26; `find plugins -path '*/agents/*.md'`
→ 9; `find plugins -path '*/workflows/*.md'` → 42.

The two artifact kinds the framework ships most have the least authoring
guidance. Every SKILL.md and agent file in `plugins/` was written without a
standard this repository owns.

## A. Ours — repository surfaces

### A1. The quality gate

| Surface                                                   | Carries                                                                                                                       |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `.agents/skills/craft/SKILL.md:31-71`                     | 5 first principles, 4 named defect patterns, the agent-file four-content-kinds boundary, the prompt-caching construction rule |
| `.agents/skills/design-rubric/SKILL.md:30-54, 87-95`      | Rubric-authoring standard; anti-pattern table for rubric text                                                                 |
| `.agents/skills/field-test/SKILL.md:101-111`              | Decidability rule for gate text: a gate turning on a term defined outside the reader's materials is undecidable               |
| `.agents/skills/dogfood/SKILL.md:23-24, 60-74`            | Blind instruction-testing as a mode; the change-cost ladder; the mandatory `/craft` gate on instruction edits                 |
| `.agents/skills/dogfood/references/decomposition-eval.md` | 11-dimension rubric for scoring a decompose-mode instruction set                                                              |
| `plugins/orchestrate/skills/verify/SKILL.md:17`           | Routing rule — an instruction artifact verifies against the skill owning its quality, not a rules file                        |

### A2. Placement — what belongs in an instruction file

| Surface                                            | Carries                                                                                                                        |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `specs/meta/doc-taxonomy.md:7-25, 27-47, 69-83`    | Five-document partition by audience; per-kind contain/shouldn't-contain lists; the shipped-instructions-are-generic rule       |
| `.agents/CORE.md:24-26`                            | "Instructions are operative" — no history, rationale, changelogs, decision logs                                                |
| `specs/ARCHITECTURE.md:49-51`                      | The same rule, stated in full a second time                                                                                    |
| `.agents/templates/authoring-durable-doc.md:16-67` | Seven authoring obligations for repeatedly-loaded documents. Frontmatter `status: retired`; still resolves in the project tier |
| `plugins.disabled/specs/file-taxonomy.md:13-25`    | Earlier seven-category taxonomy. Retired with the disabled plugin set                                                          |

### A3. Task-brief authoring

| Surface                                               | Carries                                                                                                              |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `plugins/aops/skills/brief/SKILL.md:56-94`            | Section-by-section body shape, 150–400 word budget, seven-item exclusion list, two litmus tests                      |
| `lib/hooks/task_body_gate.py:36-47`                   | De facto phrasing convention — a body declares a mandatory gate only with a mandatory word + timing word + gate name |
| `.agents/templates/wf-brief-composition-verify.md:56` | Standing finding: prose instructions at the decision point do not bind composing agents                              |

### A4. Workflow-template authoring

| Surface                                                    | Carries                                                                                           |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `plugins/aops/skills/workflow-create/SKILL.md:12-49`       | Five authoring rules, three validation tests, a self-application clause                           |
| `plugins/aops/skills/workflow-library/SKILL.md:113-217`    | Frontmatter shape, length cap, template-vs-skill boundary, edit-in-place rule, retirement markers |
| `specs/workflows/three-source-template-discovery.md:40-71` | The authoring bar and frontmatter vocabulary                                                      |
| `plugins/aops/workflows/INDEX.md:16-32`                    | Routing-vs-composition split governing where a procedure is written                               |

### A5. Agent-definition conventions

| Surface                                          | Carries                                                                       |
| ------------------------------------------------ | ----------------------------------------------------------------------------- |
| `specs/agents/agent-authority.md:49-95, 296-345` | Frontmatter schema and five lint rules. `:328` — "**Not yet built.**"         |
| `specs/ARCHITECTURE.md:361-398`                  | Per-client frontmatter translation constraints; the always-emit `tools:` rule |
| `specs/enforcement/enforcement.md:91-97`         | Skills are personality-agnostic; a skill assuming one personality is a defect |
| `plugins/aops/agents/ida.md:51`                  | Never instruct history retention in task or note bodies                       |

### A6. Scaffolds

`templates/plugin/skills/example/SKILL.md`, `templates/plugin/commands/example.md`,
`templates/plugin/axioms/example.md`, `templates/github-agent/README.md`.

`templates/plugin/agents/name.md` is **zero bytes** — the agent-definition
scaffold is a path with no guidance in it.

### A7. Prompt authoring

`plugins/tools/skills/deep-research/procedures/prompt-authoring.md:10-59` —
shape selection and section anatomy for research prompts.
`.agents/templates/aops_cd98ee81-*-instruction-tuning-workflow.md:19-81` —
human-in-the-loop protocol for tuning instruction text against a live agent.

## B. Ours — PKB nodes

**Placement and content boundary.** `spec_d4ccc4b4` (the taxonomy, canonical) ·
`mem-7e900425` (ask who reads this before writing a line) · `mem-c4d7dc40`
(doctrine has one home and is never copied) · `mem-a22fd157` (reference, don't
restate) · `mem-90d48823` (disposition in the agent, procedures in skills;
self-containment beats DRY for disposition).

**Brief authoring.** `note_a75a3c1f` — 7 required components, 8 exclusion rules,
the per-sentence deletion test, the 150–400 word budget. The only document-level
authoring specification on the graph. · `note_pauli_brief_checklist` (9 reviewer
checks derived from it) · `note_3a276c36`, `note_b1a9b5a0` (the two working
papers it synthesises) · `mem_007f9189` (brief the goal, never a conclusion
inside the specialist's domain) · `ins_5a7a72b9` (what a brief may contain is
the only control on the deciding surface) · `mem_3fe600f3` (a defect described
in brief prose cannot be claimed or tracked).

**Skill and agent shape.** `framework-dfc3da6b` — contraindications are more
efficient than exhaustive positive triggers. The only node on the graph about
writing a skill's routing entry. · `kb-4fc4dbf2` and `mem-231996ac` —
instructions asking for judgment must forbid the checkbox default, or agents
produce compliance theatre · `mem-4a396dd9` (which file each client reads;
dated April 2026, staleness risk).

**Integrity of instruction text.** `kb_afe0000b` — the strongest single rule
found: _"Instructions must not offer a mode the runtime does not support"_ and
_"An unreconciled contradiction is a licence to fabricate, not a tie the agent
will surface."_ · `kb_67962e73` (a pointer that does not resolve is
indistinguishable from having no instructions) · `kb_310f7e68` (an authorising
line needs a verbatim dated source quote) · `framework-design-d0a23e78`
(context blocks are fully binding, not preamble to numbered steps).

**Validating an instruction change.** `mem-31024f46` and `mem-2fc1e424` — blind
the executor, use fresh pairs, keep gold standards out of agent-reachable
storage · `mem_1142d35a` (a reviewer's question is evidence the artifact is
unclear) · `mem-f9ca6df4` (agents fix their own output without amending the
instruction that caused it).

**Budget for injected instruction text.** `note-108883d4` (measured audit) ·
`sessionstart-vs-b03585c5` (injection budget scales inversely with firing
frequency; session-start reference documents must be timeless).

**Governance.** `mem-5534028b` (the `{#bot-instructions-craft}` rule) ·
`mem_91fe7599` (Nic's ruling on agent-facing document shape) ·
`aops_brief_q_hardening` (prose-only fixes ship flagged `unproven-to-bind`).

**Defect corpus** — instances any standard must explain, tag `instruction-gap`:
`obs_c5bcba44` (three absolute prohibitions followed by a mandatory instance of
the prohibited act) · `lear_e31aba50` (a description promising obligations the
body does not contain) · `obs_3904e56e` (a gate with no definition of the term
it checks) · `obs_d99e5134` (escalates to templates that do not exist) ·
`obs_06e0d9bd`, `obs_e9deb1c2` (a skill mandated for callers who cannot run it)
· `obs_0480e9d4`, `obs_ddd0fb43`, `aops_4469ff06`, `aops_ad8722e9`,
`aops_b516628b`, `obs_6d4ec909`, `lear_7ca89e71`, `aops_8eab784f`.

## C. Upstream — reference, not ours to edit

Point at these; do not restate them.

| Surface                                                                 | Carries                                                                                                                                       | Reachable                              |
| ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| `anthropic-skills:skill-creator`                                        | Create→test→eval loop; description-writing for triggering; three-level progressive disclosure; explain the _why_; imperative form; <500 lines | description always; body on invocation |
| `anthropic-skills:mcp-builder`                                          | Tool-description authoring: narrow, unambiguous, matching actual functionality; snake_case with service prefix                                | description always; body on invocation |
| `code.claude.com/docs/en/skills`                                        | The frontmatter spec. **description + `when_to_use` truncates at 1,536 characters in the listing.** Body cost is recurring per turn           | only if sought                         |
| `code.claude.com/docs/en/sub-agents`                                    | The body becomes the whole system prompt; subagents inherit no Claude Code system prompt                                                      | only if sought                         |
| `code.claude.com/docs/en/best-practices`                                | "Would removing this cause Claude to make mistakes? If not, cut it." Emphasis on one line only                                                | only if sought                         |
| `plugin-dev:skill-development`, `:agent-development`, `:skill-reviewer` | Third-person descriptions; `<example>`/`<commentary>` blocks; system-prompt skeleton; review rubric                                           | not installed                          |
| Gemini CLI `skill-creator`                                              | Degrees-of-freedom model (high-freedom prose vs low-freedom scripts); references one level deep                                               | Gemini sessions only                   |

**Upstream is not one voice.** Five live contradictions, so it cannot be cited
as a single authority:

1. **Explain why** — skill-creator: _"Try hard to explain the **why**"_ vs
   docs/skills: _"State what to do rather than narrating how or why."_
2. **Emphasis** — skill-creator flags all-caps ALWAYS/NEVER as _"a yellow
   flag"_; best-practices endorses _"add emphasis such as 'IMPORTANT' to that
   line alone."_
3. **Description voice** — plugin-dev mandates third person and marks _"Use
   this skill when…"_ as wrong person; skill-creator asks for _"pushy"_.
4. **Subagent descriptions** — plugin-dev requires 2–4 `<example>` blocks;
   docs/sub-agents says _"keep them short"_ and ships one sentence.
5. **`when_to_use`** — skill-reviewer calls it deprecated; docs/skills
   documents it as live and counting toward the 1,536-char cap.

**Upstream silences** (searched: the official plugin marketplace, the
`plugin-dev` cache, the Gemini CLI builtins, the bundled `anthropic-skills`,
and the three doc pages above): no evidence contract for agent reports; no
instruction to write acceptance criteria; no anti-pattern catalogue for
instruction prose; nothing on how to phrase the dispatch prompt handed to a
running subagent, as distinct from the subagent's definition file.

## D. Defects in the corpus

**D1. `craft` cannot reach what it owns.** Named as owner by
`authoring-durable-doc.md:50-52`, `dogfood/SKILL.md:74`, and
`verify/SKILL.md:17`. It exists only at `.agents/skills/craft/` — absent from
`plugins/` and `dist/`. The 26 SKILL.md and 9 agent files it governs are in
plugins it does not ship to.

**D2. No SKILL.md authoring standard exists here.** `craft:56` scopes its
content boundary to agent files. Nothing in this repository states what a
SKILL.md body may contain, how to write a description that triggers, or the
1,536-character listing cap.

**D3. "Instructions are operative" is stated in full twice** —
`.agents/CORE.md:24-26` and `specs/ARCHITECTURE.md:49-51`. Neither links the
other.

**D4. The deletion test exists in four phrasings.** `craft:65` ("would the
agent behave differently on the median task?"), `authoring-durable-doc:65-66`
("would anyone behave differently?"), `brief:90` ("would the executor act
differently, or success be judged differently?"), `note_a75a3c1f` (per
sentence). No canonical statement.

**D5. Template length has three numbers.** `≲100 lines`
(`three-source-template-discovery.md:42`), `under about 100 lines`
(`workflow-library:125`), and `a median of 46 … the budget, not the floor`
(`authoring-durable-doc:33`). A 90-line template is compliant under one and
over budget under another.

**D6. Three-tier template discovery is restated in full** across
`workflow-library/SKILL.md:19-43` and
`specs/workflows/three-source-template-discovery.md:56-93`.

**D7. `authoring-durable-doc.md` is retired and still resolves.** Frontmatter
carries `status: retired` and `superseded_by`; the body carries no banner, so a
reader landing in it gets live-looking guidance.

**D8. The agent scaffold is empty.** `templates/plugin/agents/name.md` is zero
bytes.

**D9. `agent-authority.md`'s lint is unbuilt** (`:328`), so its five authoring
rules — including "no authority inflation in prose" and the `allowed-tools`
requirement — are unenforced. `workflow-create/SKILL.md` and `learn/SKILL.md`
carry only `name` and `description`.

**D10. Four PKB duplicate pairs.** `mem-31024f46` ≈ `mem-2fc1e424` (blind
validation) · `mem-c4d7dc40` ≈ `mem-a22fd157` (doctrine has one home) ·
`note_3a276c36` + `note_b1a9b5a0` superseded by `note_a75a3c1f` ·
`note-108883d4` ≈ `sessionstart-vs-b03585c5` (injection budget).

**D11. One live unmarked contradiction.** `mem-90d48823` — _"Self-containment
beats DRY for agent disposition"_ — against `mem-c4d7dc40`, which forbids
restating a doctrinal rule anywhere. Reconcilable only on the
disposition/doctrine distinction, which the first states and the second does
not acknowledge.

## E. Consolidation map

Target: `plugins/aops/skills/craft/SKILL.md`. Shipped, so generic — no person,
organisation, or local path, per `doc-taxonomy.md:21`.

| Section               | Status                         | Sources                                                                               |
| --------------------- | ------------------------------ | ------------------------------------------------------------------------------------- |
| First principles      | keep as-is                     | `craft:31-41`                                                                         |
| Defect patterns       | extend                         | `craft:43-50` + the `instruction-gap` corpus (§B) + `kb_afe0000b`                     |
| Deletion test         | **canonicalise once**          | resolves D4; the other three become pointers                                          |
| Agent-file boundary   | keep, resolve against upstream | `craft:52-67` + docs/sub-agents                                                       |
| **SKILL.md boundary** | **write — the gap**            | upstream §C + `framework-dfc3da6b` + `mem-90d48823` + `kb_afe0000b` + `lear_e31aba50` |
| Integrity checks      | add                            | `kb_67962e73`, `kb_310f7e68`, `obs_3904e56e`, `obs_c5bcba44`                          |
| Validating a change   | add                            | `mem-31024f46`, `mem-2fc1e424`, `dogfood:23-24`                                       |
| Construction rule     | keep as-is                     | `craft:69-71`                                                                         |
| Brief authoring       | **point, don't absorb**        | `brief/SKILL.md`, `note_a75a3c1f`                                                     |
| Workflow templates    | **point, don't absorb**        | `workflow-library/SKILL.md`                                                           |
| Placement             | **point, don't absorb**        | `specs/meta/doc-taxonomy.md`                                                          |

Three surfaces are complete and owned elsewhere. Absorbing them would reproduce
the duplication this inventory records. `craft` points at them; per
`craft:37`, it names them without restating their internals.

## F. Out of scope

Excluded by the scope test — these govern agent behaviour, not the authoring of
instruction text: `lib/axioms/*` and the axiom loading mechanism; the general
rules in `.agents/rules/RULES.md`; enforcement-lever doctrine
(`specs/enforcement/`, `mem_20b44980`, `mem_ca01e4bf`); rule-shape findings
about what makes a rule bind (`ins_length_rule_base_rate`,
`aops_artifact_relay_loss`, `aops_29ef2b2b`, `mem-7f29e776`, `mem-47c6e37f`,
`kb-872b33ea`); report-writing contracts (`honesty.md`, `hearsay.md`,
`rule-check.md`).

The rule-shape cluster carries three live unmarked contradictions and is the
most likely place a future sweep will need to look.
