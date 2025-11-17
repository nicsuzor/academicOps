# Framework Learning Log

**Purpose**: Capture patterns from experiments and observations to build institutional knowledge.

**Format**: Append-only monolithic file. Never delete entries. Patterns emerge from viewing successes AND failures over time. All entries in chronological order in this single file.

---

## Behavioral Pattern: Reactive vs Proactive Knowledge Capture

**Date**: 2025-11-17 | **Type**: ❌ Failure | **Pattern**: #proactive-bmem-capture

**What**: Agent required explicit user prompt ("don't forget to add to my documentation") to capture new accommodation information (multi-window cognitive load challenges) that user had just explained.

**Why**: User provided detailed new information about working style challenges. This is exactly the type of knowledge bmem should capture automatically - agent should recognize it and act proactively.

**Lesson**: Agents must recognize when user provides new personal context, work style details, or accommodation needs and proactively use bmem skill to capture without being prompted. "I shouldn't have to tell any agent EVER to remember something with the bmem skill."

---

## Meta-Framework: Scope Misunderstanding - Framework vs Academic Workflow

**Date**: 2025-11-17 | **Type**: ❌ Failure | **Pattern**: #framework-scope #lack-of-ambition

**What**: Framework skill over-indexed on framework development tasks (working in academicOps repo) and under-emphasized that framework exists to automate general academic workflow across ALL projects and repositories.

**Why**: The academicOps framework is both: (1) a coordination system for all academic work, and (2) an example project that gets developed. Agents incorrectly treated it primarily as #2, making recommendations scoped to "when working on framework" rather than "for all academic work everywhere."

**Lesson**: Solutions must serve the broader academic workflow across ALL repositories and contexts. Multi-window cognitive load, task management, and automation benefits apply everywhere Nic works, not just within academicOps. Task system integration isn't a recommendation—it's the whole point. The framework's purpose is to help ALL THE TIME, not just during framework development.

---

## Systemic Failure: Session 2025-11-17 Cascading Framework Deficiencies

**Date**: 2025-11-17 | **Type**: ❌ Critical Systemic Failure | **Pattern**: #meta-framework #just-in-time-failure #skill-architecture #trust-erosion

**What**: Session revealed four interconnected systemic failures in framework architecture:

1. **Timeline estimates despite prohibition** - Meta skill didn't load ACCOMMODATIONS before recommending, violated explicit constraint
2. **Option A vs B hedging** - Offered alternatives despite ROADMAP line 99 stating spec-first is "NOT optional"
3. **Task format uncertainty** - Created spec assuming JSONL when actual format is Markdown (bmem-compliant); foundational infrastructure unknown
4. **bmem reading Python code** - bmem skill attempted to discover its own data format via code inspection instead of knowing it authoritatively
5. **Logging structure ambiguity** - Had to clarify whether LOG.md is monolithic vs broken out

**Why**: Four systemic root causes exposed:

**ROOT CAUSE 1: Authoritative vs Procedural Knowledge Confusion**
- Framework doesn't distinguish facts that must be immediately known (task format, data models, mandatory processes) from procedures loaded just-in-time
- Skills discover their own domains via code reading instead of knowing them authoritatively
- Fundamental questions require file exploration rather than immediate answers

**ROOT CAUSE 2: Skills Don't Load User Constraints**
- Skills load framework docs (VISION, ROADMAP, AXIOMS) but treat user docs (ACCOMMODATIONS, CORE) as optional
- User constraints are as binding as AXIOMS but loaded inconsistently
- Results in recommendations that violate documented accommodations

**ROOT CAUSE 3: No Framework State Snapshot**
- Each session starts fresh with no ground truth for: current stage, mandatory processes, active blockers, foundational facts
- Meta skill can't confidently enforce processes without authoritative state reference
- Leads to hedging on documented mandates ("Option A vs B" when only A is valid)

**ROOT CAUSE 4: Component-Focused Missing System View**
- Skills focus on component domain without system-level awareness
- Meta framework doesn't see how component failures indicate systemic problems
- Example: Task format uncertainty blocks task-viz, but meta skill didn't recognize this as systemic failure requiring immediate attention

**Lesson - Immediate Fixes**:

1. **Create framework/STATE.md** - Ground truth snapshot: current stage, mandatory processes, foundational facts, active blockers. Meta skill loads FIRST before aspirational docs.

2. **Add skill domain knowledge headers** - Each skill SKILL.md must have authoritative frontmatter stating: data format, storage location, required fields, core domain model. Skills know their identity.

3. **Mandatory context loading order** - Meta skill must load: ACCOMMODATIONS/CORE (binding user constraints) → STATE.md (current reality) → VISION/ROADMAP/AXIOMS (aspirational). User constraints come before framework aspirations.

4. **Distinguish MANDATORY vs GUIDANCE** - Documentation must explicitly mark binding requirements. Meta skill cannot offer alternatives when doc says MANDATORY.

**Lesson - Meta Skill Evolution Required**:

Meta framework skill must evolve from "component maintainer" to "strategic systems coordinator":
- See cross-skill dependencies (task format blocks multiple systems)
- Flag systemic problems (foundational uncertainty = architecture failure)
- Enforce binding constraints (ACCOMMODATIONS = AXIOMS in bindingness)
- Maintain strategic awareness (component failures indicate larger patterns)
- System-level pattern recognition (multiple symptoms → root cause diagnosis)

**Lesson - Cognitive Load Transfer**:

User stated: "don't make me carry the cognitive load." When analysis complete, DOCUMENT IMMEDIATELY. Don't wait for confirmation - act, then iterate if wrong. Could be interrupted at any time. Analysis only in chat history = lost knowledge = user must remember = failure.

**Interrelated Problems Map**:
```
NO AUTHORITATIVE DOMAIN KNOWLEDGE
├─> bmem doesn't know bmem format
├─> tasks doesn't know task format
├─> Meta doesn't load user constraints
└─> Everything discovered via file reading

JUST-IN-TIME FAILS FOR FACTS
├─> "What format?" requires exploration
├─> "What's mandatory?" requires re-reading
└─> Uncertainty at foundational level

NO FRAMEWORK STATE SNAPSHOT
├─> Each session uncertain about current state
├─> Can't confidently enforce processes
└─> Hedging on documented mandates

COMPONENT-FOCUS MISSING SYSTEM VIEW
├─> Task format uncertainty blocks task-viz
├─> Meta didn't flag as systemic issue
└─> Wrote spec with wrong assumptions
```

---

## Meta-Framework: README.md Purpose Confusion - Authoritative vs Instructional

**Date**: 2025-11-17 | **Type**: ❌ Failure | **Pattern**: #readme-purpose #authoritative-vs-instructional #bloat

**What**: README.md contained instructional bloat (basic cat commands, "adding components" workflow duplication, "architecture evolution" historical data, core principles duplication) instead of focusing on its authoritative role (directory structure, contact info, session start list).

**Why**: Framework skill doesn't understand the fundamental distinction between authoritative sources (own facts only) and instructional documents (explain how to use). README.md should state "AXIOMS.md exists here" with one-line description, not repeat principles. Should reference deployment docs, not contain them. Should list directory structure with brief inline summaries, not multi-line explanations.

**Lesson**: Authoritative vs instructional distinction must be foundational to framework skill's understanding. Each file is EITHER authoritative (owns facts, states them, stops) OR instructional (explains workflows, provides examples). The visual tree map should be detailed with one-line abstracts, but explanation paragraphs = bloat. "How to use this structure" belongs in separate instructional doc, not in the authoritative structure definition. Framework skill must actively ask: "Does this file OWN this information, or is it explaining how to use information owned elsewhere?"

---

## Meta-Framework: LOG.md Entry Quality - Pattern Transfer vs Optimization

**Date**: 2025-11-17 | **Type**: ✅ Success + Refinement | **Pattern**: #log-quality #knowledge-transfer #optimization

**What**: Tested fresh agent with no conversation history using only LOG.md entry "README.md Purpose Confusion" (2025-11-17). Agent successfully removed all instructional bloat (62% reduction, 241→92 lines) but left suboptimal structure (separate sections duplicating tree content). Required iteration to maximize authoritative density (final: 130 lines, pure structure-as-documentation).

**Why**: LOG.md entry successfully transferred the principle ("authoritative vs instructional separation") but didn't capture the optimization pattern ("maximize density in native structure"). Fresh agent correctly identified "what's wrong" (instructional bloat) but not "what optimal looks like" (tree IS the documentation, inline annotations beat separate sections, multiple trees for different contexts, one level deeper shows file contents).

**Lesson**: LOG.md entries must capture BOTH violation patterns AND optimization patterns. Include positive examples ("installation line 196-198 is PERFECT - concise, practical, actionable") not just negative ("remove X bloat"). For authoritative documents specifically: maximize information density in the structure itself—README.md's directory tree IS the documentation. Use inline annotations (`[SESSION START: loaded first]`) instead of separate sections. Show multiple trees for different contexts (repo structure, user data, installation pattern). Go one level deeper to reveal actual file contents agents need. Fresh agent testing reveals gaps in pattern articulation: if agent succeeds at principle but result isn't optimal, the pattern itself needs refinement.

---

## Framework Architecture: LLM-First Design - Scripts as Utilities Not Orchestrators

**Date**: 2025-11-17 | **Type**: ✅ Architecture Clarification | **Pattern**: #script-role #llm-first #orchestration

**What**: Task visualization spec was initially written with Python script handling visualization generation (creative/analytical work). User clarified: framework approach is to have very small helper scripts for repetitive tasks only. Claude Code agents do ALL creative, thinking, and analytical work. Claude Code INVOKES Python scripts to do repetitive tasks, NOT the other way around.

**Why**: This is a fundamental architectural principle that must be consistently applied across all automations. The division is clear:
- **Agent/LLM work**: Reading, filtering, analyzing, decision-making, reasoning, pattern extraction, visual design, layout decisions, semantic understanding
- **Script work**: Purely mechanical data transformation (chunking, merging, format conversion), no filtering, no reasoning, no decision-making

Example violation: Script that reads files, filters with regex, extracts patterns, and writes outputs → Should be agent reads files, uses LLM judgment to filter, extracts with semantic understanding, decides what to write.

Example correct: Script that splits a file into N-line chunks (mechanical) → Agent calls it when needed, agent processes each chunk with LLM reasoning, agent orchestrates the workflow.

**Lesson**: When designing any automation, ask: "Is this script duplicating Claude Code's built-in capabilities (Read/Write/Edit/Grep/Glob) or LLM reasoning?" If yes, it's wrong. Scripts are simple tools (like `jq` or `split`) that agents call via Bash. Agent orchestrates everything: decides what to process, invokes script for mechanical transformation, processes results with LLM reasoning, invokes another script to aggregate if needed, analyzes final output. The agent does ALL orchestration, decision-making, and reasoning. For task visualization specifically: agent discovers tasks, agent parses and validates, agent enriches with bmem context, agent designs visual layout (creative work), agent generates Excalidraw JSON directly. Optional helper only if file aggregation proves repetitive, but visualization design is LLM work, not scripted.

---

## Behavioral Pattern: Spec Revision Misinterpreted as Implementation Trigger

**Date**: 2025-11-17 | **Type**: ❌ Failure | **Pattern**: #request-interpretation #do-one-thing

**What**: User requested "revise the task vis spec" with detailed requirements. Agent correctly revised spec, updated slash command, and logged to LOG.md (✅), but then immediately started implementing the visualization ("ok, get to work on it") without waiting for user approval of the spec changes.

**Why**: AXIOM #1 violation: "DO ONE THING - Complete the task requested, then STOP." User's request was to revise the spec, not to implement. Agent should have reported spec changes and stopped, allowing user to review before proceeding to implementation.

**Lesson**: When user says "revise X", the task is revision only. Report changes made, then stop. Wait for explicit implementation trigger ("build it", "implement", "get to work") before proceeding to next phase. Don't assume spec revision implies immediate implementation—user may want to review, refine, or defer.

---

## Meta-Framework: Appropriate Rigor Levels - Framework vs Academic Work

**Date**: 2025-11-17 | **Type**: ✅ Success | **Pattern**: #process-pragmatism #ttd-scope

**What**: Framework meta-development (spec revisions, doc updates) uses lightweight iterate-and-test process, while academic work (research code, data analysis via /ttd) requires rigorous TDD with comprehensive testing.

**Why**: Stakes differ—academic work has real-world consequences (publication quality, reproducibility), while framework development is tool-building where user can verify directly and iteration speed matters (ACCOMMODATIONS: "can't spend all time building the system").

**Lesson**: Keep /ttd rigor for production academic work (high stakes, correctness paramount). Use pragmatic iteration for framework meta-development (spec → review → implement → test → iterate). Don't formalize framework development process unless changes start breaking academic workflows or complexity grows to require it.

---

## Component-Level: bmem MCP Parameter Errors - Missing Authoritative API Spec

**Date**: 2025-11-17 | **Type**: ❌ Failure | **Pattern**: #mcp-parameters #authoritative-knowledge

**What**: Agent invoked bmem search_notes with invalid `entity_types` parameter (`entity_types: ["project"]` and `entity_types: ["goal"]` both failed with "not a valid SearchItemType"), then successfully retried without that parameter.

**Why**: Slash command documentation doesn't specify valid bmem MCP parameters—agents guess based on general knowledge rather than knowing authoritatively what the actual MCP server accepts.

**Lesson**: Document authoritative bmem MCP API specification (valid parameters, types, constraints) in framework references so agents know correct usage without trial-and-error, similar to how email-capture workflow documents validated MCP parameters (ROADMAP line 269).
