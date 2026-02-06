---
name: effectual-planning-agent
title: Effectual Planning Agent
category: spec
---

# Effectual Planning Agent

## Giving Effect

- [[agents/effectual-planner.md]] - Agent definition with strategic planning capabilities
- [[mcp__plugin_aops-core_task_manager__get_task_tree]] - Task tree for strategic planning context
- [[mcp__plugin_aops-core_task_manager__get_graph_metrics]] - Graph metrics for network analysis
- [[mcp__plugin_aops-core_task_manager__get_task_neighborhood]] - Task relationships for context discovery
- [[workflows/strategy.md]] - Strategy workflow for goal decomposition

The Effectual Planning Agent is an AI agent that serves as a strategic planning assistant for academic research and knowledge work under conditions of genuine uncertainty. It receives fragments of information incrementally, organises them into a semantic web of goals, projects, and tasks, surfaces hidden structure, and proposes high-value next steps.

The agent is designed for work where many ideas fail, where you don't know what you don't know, and where the plan must evolve as understanding deepens.

## Vision

i have a key idea: i want to use network mapping methods from maths and science to improve our academic task planning and prioritising in conditions of uncertainty. i have a tasks database that has hierarchical dependencies but also soft dependencies. i want to, for example:
- identify what abstract goals/tasks are ready for deconstruction in to more concrete assortments of specific tasks for things we know how to do and exploratory tasks for things we know we don't know
- prioritise between different tasks based on how much valueable information we are likely to generate from a task and what cross-network work gets unlocked by finding out that info.


### Where we're going

A planning system that feels less like project management and more like thinking with a collaborator who has perfect recall and no ego. You throw fragments at it—half-formed ideas, discovered constraints, sudden connections—and it builds a map of your understanding. The map reveals what you're assuming, what depends on what, where threads converge, and what you'd learn most from doing next.

The system doesn't tell you what to do. It shows you what you know and don't know, and helps you decide what's worth finding out.

### What this enables

For academic researchers and knowledge workers:

- **Reduced cognitive load.** Stop holding the whole project graph in your head. Externalise it in a form that's queryable and navigable.

- **Assumption hygiene.** Research projects fail on unexamined assumptions. Surface them early, test them cheap.

- **Synergy discovery.** When you're working on multiple threads (papers, grants, collaborations, tool-building), notice when they want the same thing.

- **Adaptive planning.** When reality surprises you—a paper gets rejected, a collaboration falls through, a new opportunity appears—the system helps you re-orient rather than just re-schedule.

## Success Criteria

The agent is successful when:

### Functional success

1. **Fragments land gracefully.** Partial, ambiguous, half-baked inputs get placed somewhere sensible and linked appropriately. The system never demands premature specification.

2. **Structure emerges.** After accumulating fragments, the web reveals relationships the user didn't explicitly state: hidden dependencies, convergent threads, orphaned ideas.

3. **Assumptions surface.** Load-bearing hypotheses get identified and tracked. The user knows what they're betting on.

4. **Next steps are insightful.** When asked "what should I do?", the agent proposes actions that would genuinely improve understanding--not just urgent tasks or obvious next items.

5. **The framework evolves.** Friction gets logged, patterns get recognised, amendments happen. The system learns from its own use.

### Quality indicators

- **Low friction-to-insight ratio.** Using the system shouldn't feel like feeding a bureaucracy. If it takes more effort to maintain than it returns in clarity, something's wrong.

- **Appropriate formality gradient.** Early-stage ideas stay loose. Mature plans get more structure. The system doesn't over-specify prematurely or under-specify when precision matters.

- **Useful dead ends.** When a project dies or pivots, the record of why is valuable. The system treats failures as data, not waste.

### Anti-patterns (how we'd know it's failing)

- User avoids logging things because the format is too rigid
- Agent asks clarifying questions instead of making reasonable placements
- Assumptions accumulate but never get reviewed or tested
- The web grows but structure doesn't emerge--just a pile of files
- Agent spec doesn't grow (not learning) or grows unboundedly (not adapting)

## Current Feature Set

**Node types**

- Goals: desired future states, can be vague
- Projects: bounded efforts toward goals
- Tasks: executable actions with optional subtask lists

**Node lifecycle**

- Status values: `seed` → `growing` → `active` → `complete` (or `blocked`, `dormant`, `dead`)
- Tasks can contain subtask checklists
- Tasks can divide (emit children), merge (consolidate), or promote subtasks to full nodes

**Linking**

- Wikilinks for semantic connections

**Assumption tracking**

- Agent surfaces when new material implies unexamined assumptions

**Self-reflexivity**

- Relies on `/log` command to log things that don't fit the model and insights about planning

**Agent behaviours**

- Receives fragments and places them
- Surfaces hidden dependencies and synergies
- Identifies load-bearing unknowns
- Proposes next steps by information value
- Logs friction when the framework fails

## Planned Features

### Near-term (validate core model)

**Probe templates**
When an assumption is critical and untested, suggest specific lightweight experiments to validate it. "You're assuming X. A cheap test might be: [concrete action]."

**Maturity indicators**
Beyond status, a way to express confidence/maturity: how validated is this node's content? This affects how much weight to put on it when reasoning about dependencies.

**Periodic review prompts**
Time-triggered suggestions to revisit dormant nodes, review accumulated friction, or check whether active projects still make sense.

**Link graph visualisation**
Export to a format (Mermaid, Graphviz, or similar) that shows the web structure. Useful for spotting clusters, orphans, and bottlenecks.

### Medium-term (expand capability)

**Multi-agent handoff**
Integration points where the planning agent can hand off to execution agents (research agents, writing agents, etc.) with appropriate context.

**Resource tracking**
Lightweight affordance tracking: what capacities, relationships, and assets are available? Bird-in-hand thinking operationalised.

**Temporal reasoning**
Soft deadlines, windows of opportunity, and time-sensitive dependencies. Not hard scheduling, but awareness of when timing matters.

**Cross-web queries**
"What assumptions am I making across all active projects?" "What tasks are blocked and why?" "Where do my projects converge?"

### Long-term (if validated)

**Learning consolidation**
Periodically synthesise `meta/learnings.md` into updated heuristics or agent behaviours. The system doesn't just log what it learns—it incorporates it.

**Collaborative webs**
Multiple users contributing to shared planning webs. Requires thinking about attribution, conflict resolution, and divergent views.

**Integration with knowledge base**
Connection to the broader academicOps knowledge management layer—notes, sources, concepts—so planning can reference and link to research materials.

## Implementation Choices

### Why markdown + YAML + wikilinks

**Tool-agnostic.** Works with any text editor, any file sync, any version control. No lock-in to specific apps.

**Human-readable.** The planning web is inspectable without the agent. If the agent breaks, you still have your data.

**AI-parseable.** Modern LLMs read markdown natively. No translation layer needed. The agent can reason about content semantically.

**Progressive structure.** YAML frontmatter captures what needs to be structured. Markdown body stays freeform. Structure accretes as needed.

**Ecosystem compatibility.** Plays well with Obsidian, Logseq, and similar tools. Can use their features (graph view, backlinks) without depending on them.

### Why minimal schema

**Premature structure kills emergence.** We don't know yet what fields matter. Better to start sparse and add as needs surface.

**Semantic understanding compensates.** The agent reads prose. It doesn't need everything in structured fields to reason about relationships.

**Friction reveals needs.** When the minimal schema fails, we log it. Repeated friction patterns justify schema extensions. Evidence-based specification.

### Why self-reflexive architecture

**The framework is a hypothesis.** We're applying effectual planning principles to the design of an effectual planning tool. It would be hypocritical not to.

**Learning compounds.** The `meta/` layer means the system gets better at helping you plan, not just better at tracking plans.

**Transparency.** When the framework changes, the rationale is recorded. You can trace why things are the way they are.

### Why Claude Code specifically

**File system native.** Claude Code works directly with files and directories. No API translation layer.

**Agentic capability.** Can read, write, search, and reason about the web autonomously within a session.

**Semantic reasoning.** Strong at inferring relationships, surfacing implications, and generating useful suggestions from unstructured content.

**Conversational interface.** Natural for the fragment-at-a-time input pattern. You talk to it; it updates the web.

## Theoretical Foundations

The agent's design draws on:

**Effectuation** (Sarasvathy): Bird-in-hand thinking, affordable loss, lemonade principle, crazy quilt partnerships. Goals emerge from means; surprises are resources.

**Discovery-Driven Planning** (McGrath & MacMillan): Explicit assumption tracking, knowledge milestones, cheap validation before commitment.

**Cynefin** (Snowden): Recognising complex vs. complicated domains. Probe-sense-respond for genuine uncertainty.

**Set-Based Design** (Toyota): Maintaining optionality, delaying commitment until the last responsible moment.

**Bounded rationality** (Simon): Satisficing over optimising. Human cognition has limits; tools should respect them.

## Integration with academicOps

The Effectual Planning Agent is one component of a broader academicOps toolkit.

**Upstream dependencies:**

- Knowledge base provides context for planning (what do we know about X?)
- Existing research materials inform project scoping

**Downstream consumers:**

- Writing agents receive project briefs and task context
- Analysis pipelines get prioritisation signals
- Coordination tools get dependency information

**Shared principles:**

- Opinionated defaults, progressive complexity (from Buttermilk)
- Tool-agnostic, human-readable, AI-parseable
- Markdown + YAML + wikilinks as common substrate

## Open Questions

Things we don't know yet and are planning to find out:

1. **Granularity.** What's the right size for a node? When should a subtask become its own file?

2. **Review cadence.** How often should the agent prompt for assumption review or friction synthesis?

3. **Maturity representation.** Is status sufficient, or do we need a separate confidence/validation dimension?

4. **Cross-cutting concerns.** Some things (a key relationship, a scarce resource) matter to multiple projects. How do we represent these?

5. **Historical value.** How much should we preserve vs. archive vs. delete? When is a dead project worth keeping?

6. **Agent boundaries.** When should this agent hand off to others? What context needs to transfer?

These are the assumptions we're testing by building and using the system.
