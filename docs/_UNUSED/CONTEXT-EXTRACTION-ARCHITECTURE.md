# Context Extraction Architecture

## PURPOSE
Enable zero-friction, automatic extraction of project context from conversations while respecting ADHD accommodations.

## CORE PROBLEM
Agents miss rich contextual information that emerges organically in conversations, requiring users to explicitly request saves.

## DESIGN PRINCIPLES

### 1. Passive Listening, Active Capture
- Agents continuously scan for extractable information
- No interruptions for clarification during flow states
- Save first, refine later

### 2. Context Enrichment
Extract not just explicit tasks but:
- **Why** we're doing something (motivation, strategic fit)
- **How** we feel about it (energy levels, concerns)
- **Who** is involved (stakeholders, dependencies)
- **When** things need to happen (implicit deadlines)
- **What** success looks like (qualitative measures)

### 3. Progressive Enhancement
- Start with fragments
- Build complete picture over multiple conversations
- Never lose partial information waiting for completeness

## EXTRACTION PATTERNS

### Strategic Planning Sessions
**Rich Context Available:**
- Resource allocations and trade-offs
- Uncertainty and decision factors
- Energy/excitement assessments
- Risk evaluations

**Extraction Actions:**
```python
# Pseudo-code for strategic session extraction
if discussing_priorities:
    extract_resource_allocations()  # "60% of time on X"
    capture_uncertainty_factors()   # "depends on whether..."
    note_energy_levels()            # "stressed about", "excited by"
    save_strategic_reasoning()      # "because", "in order to"
```

### Project Discussions
**Rich Context Available:**
- Comparative assessments ("highest reward/cost")
- Blockers and dependencies
- Stakeholder relationships
- Implicit success criteria

**Extraction Actions:**
```python
# Pseudo-code for project extraction
if project_mentioned:
    extract_assessment()        # "inefficient", "high-risk"
    capture_dependencies()      # "needs X first"
    note_stakeholders()        # "Jenni @ GLAAD"
    infer_success_metrics()    # from discussion context
```

### Event Planning
**Rich Context Available:**
- Upcoming commitments without explicit dates
- Preparation requirements
- Audience and purpose
- Related deliverables

**Extraction Actions:**
```python
# Pseudo-code for event extraction
if event_mentioned:
    create_task_immediately()      # even without full details
    link_to_relevant_project()    # infer from context
    set_tentative_deadline()       # "next month" → estimate
    note_preparation_needs()       # "need to prepare"
```

## INFORMATION HIERARCHY

### Level 1: Immediate Capture (During Conversation)
- Task fragments
- Names and affiliations
- Rough deadlines
- Key decisions

### Level 2: Context Assembly (Post-Processing)
- Link tasks to projects
- Consolidate related information
- Identify patterns and themes
- Flag gaps for follow-up

### Level 3: Synthesis (Weekly Reviews)
- Update project narratives
- Refine success measures
- Adjust priorities based on patterns
- Generate insights from accumulated context

## IMPLEMENTATION STRATEGY

### Phase 1: Enhanced Triggers
Add contextual triggers beyond keyword matching:
- Temporal references ("next month", "by end of")
- Comparative language ("more important than", "highest priority")
- Emotional indicators ("stressed", "excited", "worried")
- Resource mentions ("X% of time", "one day a week")

### Phase 2: Inference Engine
Build reasonable assumptions from context:
- Event mentioned → task to prepare
- Collaboration discussed → contact to save
- Concern expressed → risk to document
- Success described → metric to track

### Phase 3: Background Processing
After conversation ends:
- Cross-reference extracted items
- Identify relationships
- Fill gaps through inference
- Generate summary of captured context

## SUCCESS MEASURES (Qualitative)

### Agent is Successfully Capturing When:
- User rarely needs to say "save this"
- Project files reflect actual discussions
- Tasks emerge from conversations naturally
- Context accumulates without explicit documentation sessions
- User discovers useful captured information they forgot sharing

### Agent is in Appropriate Context When:
- Strategic discussions → updating goals and priorities
- Project reviews → capturing assessments and decisions
- Email processing → extracting commitments and deadlines
- Planning sessions → documenting resource allocations

### Agent is Saving to Correct Locations When:
- Tasks → inbox with project links
- Contacts → relevant project files
- Strategic decisions → goal files
- Resource allocations → context files
- Event details → both tasks and projects

## FAILURE MODES TO AVOID

### Over-Extraction
- Creating duplicate tasks
- Saving irrelevant details
- Interrupting flow for clarification

### Under-Extraction
- Waiting for explicit commands
- Missing contextual information
- Losing fragments while waiting for complete data

### Wrong Context
- Saving personal notes as project data
- Mixing public and private information
- Misclassifying information types

## TESTING APPROACH

### Conversation Replay Tests
Use historical conversations (like /tmp/strat.json) to verify:
- Would agent extract the resource allocations?
- Would agent create tasks for events?
- Would agent capture project assessments?
- Would agent save stakeholder information?

### Incremental Improvement
- Start with obvious extractions
- Add pattern recognition gradually
- Refine based on user feedback
- Track extraction success rate qualitatively

## INTEGRATION NOTES

### With Existing Systems
- Builds on AUTO-EXTRACTION.md patterns
- Respects accommodations.md requirements
- Follows modes.md constraints
- Uses standard file structures

### With ADHD Accommodations
- Zero additional cognitive load
- No interruptions during hyperfocus
- Captures information in whatever form it appears
- Handles context switching gracefully

## NEXT STEPS
1. Update agent prompts to include extraction patterns
2. Create extraction validation checklist
3. Implement background context assembly
4. Test with real conversations
5. Iterate based on results
